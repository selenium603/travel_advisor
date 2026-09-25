"""Local travel knowledge retrieval using OpenRouter, Chroma, and BM25."""

import hashlib
import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Optional

import chromadb
import httpx
import pypdfium2

from backend.config.settings import settings

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
INDEX_VERSION = "paragraph_units_dynamic_places_v1"
MIN_COSINE_SIMILARITY = 0.35
MIN_TOPIC_COVERAGE = 0.35
CHILD_MAX_CHARS = 450
PARENT_MAX_CHARS = 1100

# Inspected sections of the 2025 Shanghai Basic Facts booklet. Other PDFs use
# the general text-page parser; this selection applies only to this edition.
SHANGHAI_2025_SECTIONS = {
    6: "地理位置",
    33: "滨水游览",
    35: "文博场馆",
    36: "文博场馆",
    38: "文博场馆",
    39: "特色旅游",
}
ROUTE_HEADING = re.compile(r"(?m)^[ \t\u3000]*线路\s*(\d+)\s*[（(]([^）)]+)[）)]\s*[：:]\s*([^\r\n]+)")

# A file named after a place belongs to that place. General guides remain unscoped.
PLACE_ALIASES = {
    "shanghai": ("上海", "shanghai"),
    "guangzhou": ("广州", "guangzhou", "canton"),
    "paris": ("巴黎", "paris"),
    "italy": ("意大利", "italy"),
    "europe": ("欧洲", "europe"),
}
CITY_DOCUMENT_WORDS = r"旅游|旅行|景点|景区|线路|路线|攻略|指南|概览|城市|文博|文化|美食|住宿|交通"
CITY_FILE_PREFIX = re.compile(
    rf"^([\u4e00-\u9fff]{{2,6}}?)(?:[-_\s·—]+|市(?={CITY_DOCUMENT_WORDS}))"
)


def _split_document(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    for start in range(0, len(text), chunk_size - overlap):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def _search_passages(text: str, max_chars: int = CHILD_MAX_CHARS) -> list[str]:
    """Keep sentences together; use character splitting only for a long sentence."""
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?])|\n\s*\n", text) if part.strip()]
    passages, current = [], ""
    for sentence in sentences:
        pieces = [sentence] if len(sentence) <= max_chars else _split_document(sentence, max_chars, 0)
        for piece in pieces:
            if current and len(current) + len(piece) + 1 > max_chars:
                passages.append(current)
                current = ""
            current = f"{current}\n{piece}" if current else piece
    if current:
        passages.append(current)
    return passages


def _place_from_filename(stem: str) -> str:
    known = _place(stem)
    if known:
        return known
    match = CITY_FILE_PREFIX.match(stem)
    if match:
        return match.group(1).removesuffix("市")
    return ""


def _is_heading(line: str) -> bool:
    line = line.strip()
    return bool(re.match(r"^#{1,6}\s+\S|^[一二三四五六七八九十]+[、.]\s*\S|^第.{1,15}[章节]\s*", line))


def _join_wrapped_lines(lines: list[str]) -> str:
    result = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if result and not ("\u4e00" <= result[-1] <= "\u9fff" and "\u4e00" <= line[0] <= "\u9fff"):
            result += " "
        result += line
    return result


def _paragraph_units(source: str, text: str, place: str, default_title: str = "", pdf: bool = False) -> list["_Unit"]:
    """Use headings and paragraphs as complete retrieval parents for general documents."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if pdf:
        # PDF line breaks often reflect page layout, not paragraph boundaries.
        text = re.sub(r"(?<=[。！？!?\.])\n(?=\S)", "\n\n", text)
    title = default_title
    paragraphs: list[tuple[str, str]] = []
    lines: list[str] = []

    def flush() -> None:
        if lines:
            paragraph = _join_wrapped_lines(lines)
            if paragraph:
                paragraphs.append((title, paragraph))
            lines.clear()

    raw_lines = text.split("\n")
    for index, raw in enumerate(raw_lines):
        line = raw.strip()
        standalone_title = (not pdf and 0 < len(line) <= 32
                            and (index == 0 or not raw_lines[index - 1].strip())
                            and index + 1 < len(raw_lines) and not raw_lines[index + 1].strip()
                            and not re.search(r"[。！？!?；;：:]$", line))
        if _is_heading(line) or standalone_title:
            flush()
            title = re.sub(r"^#{1,6}\s*", "", line)
        elif not line:
            flush()
        else:
            lines.append(line)
    flush()

    units = []
    for heading, paragraph in paragraphs:
        pieces = ([paragraph] if len(paragraph) <= PARENT_MAX_CHARS
                  else _search_passages(paragraph, PARENT_MAX_CHARS))
        units.extend(_Unit(source, piece, place, heading) for piece in pieces)
    return units


@dataclass(frozen=True)
class _Unit:
    source: str
    text: str
    place: str
    title: str = ""
    district: str = ""


@dataclass(frozen=True)
class _Chunk:
    parent: int
    text: str


def _route_units(source: str, text: str, place: str) -> list[_Unit]:
    matches = list(ROUTE_HEADING.finditer(text))
    if not matches:
        return _paragraph_units(source, text, place)
    units = []
    categories = r"自然生态|科创实践|人文研学|亲子潮玩"
    category = next((line.strip() for line in text[:matches[0].start()].splitlines()
                     if re.fullmatch(categories, line.strip())), "")
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start():end].strip()
        # Category headings between routes belong to the following route, not
        # to the previous route's answer text.
        next_category = re.search(rf"(?m)^\s*({categories})\s*$", body[match.end() - match.start():])
        body = re.split(rf"\n\s*\n(?:{categories})\s*$", body, maxsplit=1, flags=re.MULTILINE)[0].strip()
        district = match.group(2).strip()
        title = f"{category + '｜' if category else ''}线路{match.group(1)}：{match.group(3).strip()}"
        units.append(_Unit(source, body, place, title, district))
        if next_category:
            category = next_category.group(1)
    return units


def _load_units(path: Path, root: Path) -> list[_Unit]:
    source = path.relative_to(root).as_posix()
    place = _place_from_filename(path.stem)
    if path.suffix.lower() == ".txt":
        text = path.read_text(encoding="utf-8-sig")
        return _route_units(source, text, place)
    pdf = pypdfium2.PdfDocument(path)
    try:
        pages = [pdf[index].get_textpage().get_text_range().strip() for index in range(len(pdf))]
    finally:
        pdf.close()
    selected = (
        SHANGHAI_2025_SECTIONS
        if place == "shanghai" and any("上海概览2025" in page.replace(" ", "") for page in pages[:3])
        else None
    )
    units = []
    for number, text in enumerate(pages, 1):
        if not text or (selected is not None and number not in selected):
            continue
        # Very dense map labels and tables make poor travel-answer evidence.
        if len(text) > 5000:
            logger.info("Skipping dense PDF page %s#page=%s", source, number)
            continue
        title = selected[number] if selected else next((line.strip() for line in text.splitlines() if line.strip()), "")
        page_source = f"{source}#page={number}"
        if selected:
            units.append(_Unit(page_source, text, place, title))
        else:
            units.extend(_paragraph_units(page_source, text, place, title, pdf=True))
    return units


def _tokens(text: str) -> list[str]:
    """English words and overlapping Chinese bigrams without a tokenizer service."""
    tokens = []
    for piece in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()):
        if "\u4e00" <= piece[0] <= "\u9fff":
            tokens.extend(piece[i:i + 2] for i in range(len(piece) - 1))
            if len(piece) == 1:
                tokens.append(piece)
        else:
            tokens.append(piece)
    return tokens


def _normalize_question(text: str) -> str:
    """Map common travel question wording to terms used by the route guide."""
    topic = text.replace("经过哪些地点", "游玩点位").replace("路线", "线路")
    return re.sub(r"有哪些|有什么|在哪里|怎么样|怎样|怎么|如何|适合|请问|可以|附近|周边|的", " ", topic)


def _topic_terms(text: str) -> set[str]:
    """Check substantive terms rather than question phrasing."""
    return set(_tokens(_normalize_question(text)))


def _place(text: str) -> str:
    lowered = text.lower()
    for place, aliases in PLACE_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return place
    return ""


def _match_place(text: str, aliases: dict[str, tuple[str, ...]]) -> str:
    lowered = text.lower()
    matches = ((alias, place) for place, names in aliases.items() for alias in names if alias in lowered)
    return max(matches, key=lambda item: len(item[0]), default=("", ""))[1]


class _BM25:
    def __init__(self, documents: list[str]):
        self.terms = [Counter(_tokens(document)) for document in documents]
        self.lengths = [sum(terms.values()) for terms in self.terms]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 0
        document_frequency = Counter(term for terms in self.terms for term in terms)
        total = len(self.terms)
        self.idf = {
            term: math.log1p((total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def scores(self, query: str) -> list[float]:
        terms = set(_tokens(query))
        scores = []
        for counts, length in zip(self.terms, self.lengths):
            norm = 1 - 0.75 + 0.75 * length / (self.average_length or 1)
            scores.append(sum(
                self.idf.get(term, 0) * count * 2.2 / (count + 1.2 * norm)
                for term in terms if (count := counts.get(term, 0))
            ))
        return scores


class RAGService:
    """Retrieve short passages and return their complete source units."""

    _init_lock = Lock()
    _collection = None
    _parents: list[_Unit] = []
    _chunks: list[_Chunk] = []
    _bm25: Optional[_BM25] = None
    _district_to_place: dict[str, str] = {}
    _place_aliases: dict[str, tuple[str, ...]] = PLACE_ALIASES

    def __init__(self, knowledge_base_path: Optional[str] = None):
        self.knowledge_base_path = (
            Path(knowledge_base_path) if knowledge_base_path else PROJECT_ROOT / "data" / "travel_knowledge"
        )
        if RAGService._collection is None:
            with RAGService._init_lock:
                if RAGService._collection is None:
                    try:
                        self._initialize()
                    except Exception:
                        logger.exception("Travel knowledge initialization failed")

    @staticmethod
    def _embed(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
        body = {"model": settings.openrouter_embedding_model, "input": texts}
        for attempt in range(4):
            try:
                response = httpx.post(EMBEDDINGS_URL, headers=headers, json=body, timeout=45)
            except httpx.RequestError as exc:
                if attempt == 3:
                    raise RuntimeError("OpenRouter embeddings connection failed") from exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else 2 ** attempt
                time.sleep(min(delay, 8))
                continue
            response.raise_for_status()
            data = response.json()["data"]
            vectors = [None] * len(texts)
            for item in data:
                vectors[item["index"]] = item["embedding"]
            if any(vector is None for vector in vectors):
                raise ValueError("OpenRouter returned an incomplete embedding batch")
            return vectors
        raise RuntimeError("OpenRouter embeddings failed after retries")

    def _initialize(self) -> None:
        if not settings.openrouter_api_key:
            logger.info("OPENROUTER_API_KEY not set; travel knowledge index unavailable")
            return

        files = sorted(path for path in self.knowledge_base_path.rglob("*") if path.suffix.lower() in {".txt", ".pdf"})
        if not files:
            logger.info("No travel knowledge documents found")
            return

        parents: list[_Unit] = []
        manifest = hashlib.sha256()
        for path in files:
            raw = path.read_bytes()
            relative = path.relative_to(self.knowledge_base_path).as_posix()
            try:
                units = _load_units(path, self.knowledge_base_path)
            except pypdfium2.PdfiumError:
                logger.exception("Skipping unreadable travel PDF: %s", relative)
                continue
            manifest.update(relative.encode("utf-8") + b"\0" + raw)
            parents.extend(units)
        chunks = [_Chunk(parent_index, passage)
                  for parent_index, unit in enumerate(parents)
                  for passage in _search_passages(unit.text)]
        if not chunks:
            return

        aliases = {place: PLACE_ALIASES.get(place, (place,))
                   for place in {unit.place for unit in parents} if place}

        def searchable(chunk: _Chunk) -> str:
            unit = parents[chunk.parent]
            city = " ".join(aliases.get(unit.place, ()))
            return f"城市：{city}；地区：{unit.district}；主题：{unit.title}；来源：{unit.source}\n{chunk.text}"

        search_texts = [searchable(chunk) for chunk in chunks]

        model_hash = hashlib.sha256(
            f"{settings.openrouter_embedding_model}:{INDEX_VERSION}".encode()
        ).hexdigest()[:10]
        name = f"travel_knowledge_{model_hash}_{manifest.hexdigest()[:10]}"
        client = chromadb.PersistentClient(path=str(PROJECT_ROOT / "data" / "chroma_db"))
        collection = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        if collection.count() != len(chunks):
            logger.info("Indexing %s travel knowledge chunks with OpenRouter", len(chunks))
            ids = [f"chunk_{index}" for index in range(len(chunks))]
            for start in range(0, len(chunks), 8):
                batch = chunks[start:start + 8]
                vectors = self._embed(search_texts[start:start + len(batch)])
                collection.upsert(
                    ids=ids[start:start + len(batch)],
                    embeddings=vectors,
                    documents=search_texts[start:start + len(batch)],
                    metadatas=[{
                        "source": parents[chunk.parent].source,
                        "place": parents[chunk.parent].place,
                        "district": parents[chunk.parent].district,
                        "parent": chunk.parent,
                        "index": start + offset,
                    } for offset, chunk in enumerate(batch)],
                )
        RAGService._parents = parents
        RAGService._chunks = chunks
        RAGService._bm25 = _BM25(search_texts)
        district_places: dict[str, set[str]] = {}
        for unit in parents:
            if unit.district and unit.place:
                district_places.setdefault(unit.district, set()).add(unit.place)
        RAGService._district_to_place = {district: next(iter(places))
                                         for district, places in district_places.items() if len(places) == 1}
        RAGService._place_aliases = aliases
        RAGService._collection = collection
        logger.info("Travel knowledge index ready: %s chunks", collection.count())

    def query(self, query: str, destination: Optional[str] = None, k: int = 3) -> str:
        collection = RAGService._collection
        parents = RAGService._parents
        chunks = RAGService._chunks
        bm25 = RAGService._bm25
        if collection is None or bm25 is None or not chunks:
            return "知识库暂不可用。"

        search_query = f"{destination} {query}" if destination else query
        aliases = RAGService._place_aliases
        requested_place = _match_place(destination, aliases) if destination else _match_place(query, aliases)
        district_map = RAGService._district_to_place
        requested_district = next((district for district in sorted(district_map, key=len, reverse=True)
                                   if district in search_query), "")
        if not requested_place and requested_district:
            requested_place = district_map[requested_district]
        if requested_place:
            eligible = {index for index, chunk in enumerate(chunks)
                        if parents[chunk.parent].place == requested_place
                        and (not requested_district or parents[chunk.parent].district == requested_district)}
        elif destination:
            eligible = {index for index, chunk in enumerate(chunks)
                        if destination.strip().lower() in parents[chunk.parent].source.lower()}
        else:
            eligible = set(range(len(chunks)))
        if not eligible:
            return f"知识库未找到与“{destination or query}”对应的资料。"
        try:
            topic_query = query
            if requested_place:
                for alias in aliases[requested_place]:
                    topic_query = re.sub(re.escape(alias), " ", topic_query, flags=re.IGNORECASE)
            topic_terms = _topic_terms(topic_query if topic_query.strip() else query)
            lexical_scores = bm25.scores(_normalize_question(topic_query if topic_query.strip() else query))
            lexical_ranking = sorted(eligible, key=lambda index: lexical_scores[index], reverse=True)[:20]
            vector = self._embed([search_query])[0]
            where = {"place": requested_place} if requested_place else None
            if requested_district:
                where = {"$and": [{"place": requested_place}, {"district": requested_district}]}
            vector_results = collection.query(
                query_embeddings=[vector], n_results=min(len(eligible), 20),
                where=where,
                include=["metadatas", "distances"],
            )
            vector_ranking = []
            similarities = {}
            for metadata, distance in zip(vector_results["metadatas"][0], vector_results["distances"][0]):
                index = metadata["index"]
                if index in eligible:
                    vector_ranking.append(index)
                    similarities[index] = 1 - distance
            fused = Counter()
            for ranking in (lexical_ranking, vector_ranking):
                for rank, index in enumerate(ranking, 1):
                    fused[index] += 1 / (60 + rank)
            relevant = [index for index, _ in fused.most_common()
                        if lexical_scores[index] > 0
                        and similarities.get(index, 0) >= MIN_COSINE_SIMILARITY
                        and len(topic_terms & set(_tokens(chunks[index].text)))
                        / max(len(topic_terms), 1) >= MIN_TOPIC_COVERAGE]
            if not relevant:
                return f"知识库未找到与“{destination or query}”足够相关的资料。"
            parts = [f"## 旅行知识库检索结果\n\n**问题：** {query}"]
            seen = set()
            for index in relevant:
                unit = parents[chunks[index].parent]
                if chunks[index].parent in seen:
                    continue
                seen.add(chunks[index].parent)
                parts.append(f"### 结果 {len(seen)}：{unit.title or '相关资料'}\n{unit.text}\n\n*来源：{unit.source}*")
                if len(seen) >= k:
                    break
            return "\n\n".join(parts)
        except Exception as exc:
            logger.error("Travel knowledge query failed: %s", type(exc).__name__)
            return "知识库检索暂不可用。"
