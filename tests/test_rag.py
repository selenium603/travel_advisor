import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from backend.config.settings import settings
from backend.services.knowledge.rag import (
    RAGService, _BM25, _Chunk, _Unit, _load_units, _place_from_filename,
    _route_units, _search_passages,
)


class RAGTests(unittest.TestCase):
    def test_route_units_keep_complete_routes(self):
        text = ("线路1（越秀区）：人文漫步\n线路介绍：参观纪念馆。\n游玩点位：纪念馆→公园\n\n"
                "线路2（海珠区）：滨水漫步\n游玩点位：海心桥→广州塔")
        units = _route_units("广州路线.txt", text, "guangzhou")
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].district, "越秀区")
        self.assertIn("纪念馆→公园", units[0].text)
        self.assertNotIn("海心桥", units[0].text)
        self.assertEqual(_search_passages(units[0].text), [units[0].text])

    def test_route_category_applies_to_following_routes(self):
        text = ("线路5（越秀区）：历史街区\n游玩点位：骑楼\n\n自然生态\n\n"
                "线路6（白云区）：白云山徒步\n游玩点位：白云山\n\n"
                "线路7（从化区）：湿地漫游\n游玩点位：湿地\n\n亲子潮玩\n\n"
                "线路8（番禺区）：乐园游\n游玩点位：乐园")
        units = _route_units("广州路线.txt", text, "guangzhou")
        self.assertEqual([unit.title.split("｜")[0] for unit in units[1:]],
                         ["自然生态", "自然生态", "亲子潮玩"])
        self.assertNotIn("自然生态", units[0].text)

    def test_new_city_filename_and_paragraphs(self):
        self.assertEqual(_place_from_filename("成都市旅游指南"), "成都")
        self.assertEqual(_place_from_filename("成都-旅游指南"), "成都")
        self.assertEqual(_place_from_filename("旅游指南"), "")
        with TemporaryDirectory() as folder:
            path = Path(folder, "成都-旅游指南.txt")
            path.write_text("# 成都游览\n\n武侯祠展示三国文化。\n\n锦里有传统街巷。\n\n"
                            "# 交通\n\n地铁可到达多个景区。", encoding="utf-8")
            units = _load_units(path, Path(folder))
        self.assertEqual(len(units), 3)
        self.assertTrue(all(unit.place == "成都" for unit in units))
        self.assertEqual([unit.title for unit in units], ["成都游览", "成都游览", "交通"])
        self.assertNotIn("锦里", units[0].text)

    def test_long_paragraph_uses_sentence_boundaries(self):
        with TemporaryDirectory() as folder:
            path = Path(folder, "成都-长文.txt")
            path.write_text("第一段介绍。" * 250, encoding="utf-8")
            units = _load_units(path, Path(folder))
        self.assertGreater(len(units), 1)
        self.assertTrue(all(unit.text.endswith("。") for unit in units))
        self.assertTrue(all(len(unit.text) <= 1100 for unit in units))

    def test_generic_pdf_uses_paragraphs_with_page_source(self):
        with TemporaryDirectory() as folder:
            path = Path(folder, "成都-景点.pdf")
            path.write_bytes(b"%PDF-test")
            pdf = MagicMock()
            pdf.__len__.return_value = 1
            pdf.__getitem__.return_value = Mock(get_textpage=Mock(return_value=Mock(
                get_text_range=Mock(return_value="成都景点\n武侯祠展示三国\n文化。\n锦里有传统街巷。"))))
            with patch("backend.services.knowledge.rag.pypdfium2.PdfDocument", return_value=pdf):
                units = _load_units(path, Path(folder))
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0].source, "成都-景点.pdf#page=1")
        self.assertIn("武侯祠展示三国文化", units[0].text)
        self.assertNotIn("锦里", units[0].text)

    def test_shanghai_booklet_keeps_selected_pages(self):
        with TemporaryDirectory() as folder:
            path = Path(folder, "上海.pdf")
            path.write_bytes(b"%PDF-test")
            pages = [""] * 48
            pages[1] = "《上海概览2025》"
            pages[5] = "上海位于中国东部。"
            pages[28] = "上海地铁线路图" * 600
            pages[38] = "特色旅游：朱家角古镇和上海博物馆。"
            pdf = MagicMock()
            pdf.__len__.return_value = len(pages)
            pdf.__getitem__.side_effect = lambda index: Mock(
                get_textpage=Mock(return_value=Mock(get_text_range=Mock(return_value=pages[index])))
            )
            with patch("backend.services.knowledge.rag.pypdfium2.PdfDocument", return_value=pdf):
                units = _load_units(path, Path(folder))
        self.assertEqual([unit.source for unit in units], ["上海.pdf#page=6", "上海.pdf#page=39"])
        self.assertEqual(units[1].title, "特色旅游")

    def test_embedding_response_is_ordered_by_index(self):
        response = Mock(status_code=200)
        response.json.return_value = {"data": [
            {"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]},
        ]}
        with patch.object(settings, "openrouter_api_key", "test-key"), patch(
            "backend.services.knowledge.rag.httpx.post", return_value=response
        ):
            self.assertEqual(RAGService._embed(["first", "second"]), [[1.0], [2.0]])

    def test_temporary_rate_limit_is_retried(self):
        limited = Mock(status_code=429, headers={})
        success = Mock(status_code=200)
        success.json.return_value = {"data": [{"index": 0, "embedding": [1.0]}]}
        with patch("backend.services.knowledge.rag.httpx.post", side_effect=[limited, success]) as post, patch(
            "backend.services.knowledge.rag.time.sleep"
        ):
            self.assertEqual(RAGService._embed(["travel"]), [[1.0]])
        self.assertEqual(post.call_count, 2)

    def test_bm25_matches_chinese_terms(self):
        scores = _BM25(["广州早茶和粤菜", "上海外滩和博物馆"]).scores("广州早茶")
        self.assertGreater(scores[0], scores[1])

    def test_missing_city_needs_no_embedding_call(self):
        parents = [_Unit("Paris.txt", "Paris museums and cafes", "paris")]
        chunks = [_Chunk(0, parents[0].text)]
        with patch.object(RAGService, "_collection", Mock()), patch.object(
            RAGService, "_parents", parents
        ), patch.object(RAGService, "_chunks", chunks), patch.object(
            RAGService, "_bm25", _BM25([parents[0].text])
        ), patch.object(RAGService, "_district_to_place", {}), patch.object(
            RAGService, "_embed"
        ) as embed:
            result = RAGService.query(RAGService.__new__(RAGService), "广州景点", destination="广州")
        self.assertIn("未找到", result)
        embed.assert_not_called()

    def test_new_city_is_filtered_from_index_metadata(self):
        parents = [_Unit("成都-旅游指南.txt", "武侯祠展示三国文化。", "成都", "成都游览")]
        chunks = [_Chunk(0, parents[0].text)]
        collection = Mock()
        collection.query.return_value = {"metadatas": [[{"index": 0}]], "distances": [[0.2]]}
        with patch.object(RAGService, "_collection", collection), patch.object(
            RAGService, "_parents", parents
        ), patch.object(RAGService, "_chunks", chunks), patch.object(
            RAGService, "_bm25", _BM25(["城市：成都；主题：成都游览\n" + chunks[0].text])
        ), patch.object(RAGService, "_district_to_place", {}), patch.object(
            RAGService, "_place_aliases", {"成都": ("成都",)}
        ), patch.object(RAGService, "_embed", return_value=[[1.0, 0.0]]):
            result = RAGService.query(RAGService.__new__(RAGService), "成都武侯祠有什么文化？")
        self.assertIn("武侯祠展示三国文化", result)
        self.assertEqual(collection.query.call_args.kwargs["where"], {"place": "成都"})

    def test_district_inference_returns_complete_parent(self):
        parents = [
            _Unit("广州路线.txt", "线路1（越秀区）：红迹漫步。游玩点位：纪念馆→公园。", "guangzhou", "红迹漫步", "越秀区"),
            _Unit("广州路线.txt", "线路2（海珠区）：滨水漫步。游玩点位：海心桥→广州塔。", "guangzhou", "滨水漫步", "海珠区"),
        ]
        chunks = [_Chunk(0, parents[0].text), _Chunk(1, parents[1].text)]
        collection = Mock()
        collection.query.return_value = {"metadatas": [[{"index": 0}]], "distances": [[0.2]]}
        with patch.object(RAGService, "_collection", collection), patch.object(
            RAGService, "_parents", parents
        ), patch.object(RAGService, "_chunks", chunks), patch.object(
            RAGService, "_bm25", _BM25([parent.text for parent in parents])
        ), patch.object(RAGService, "_district_to_place", {"越秀区": "guangzhou", "海珠区": "guangzhou"}), patch.object(
            RAGService, "_embed", return_value=[[1.0, 0.0]]
        ):
            result = RAGService.query(RAGService.__new__(RAGService), "越秀区有什么旅游线路？")
        self.assertIn("纪念馆→公园", result)
        self.assertNotIn("海心桥", result)
        self.assertEqual(collection.query.call_args.kwargs["where"], {
            "$and": [{"place": "guangzhou"}, {"district": "越秀区"}]
        })

    def test_unrelated_topic_and_low_similarity_are_rejected(self):
        parents = [_Unit("广州.txt", "广州早茶与粤菜值得体验。", "guangzhou")]
        chunks = [_Chunk(0, parents[0].text)]
        collection = Mock()
        collection.query.return_value = {"metadatas": [[{"index": 0}]], "distances": [[0.2]]}
        with patch.object(RAGService, "_collection", collection), patch.object(
            RAGService, "_parents", parents
        ), patch.object(RAGService, "_chunks", chunks), patch.object(
            RAGService, "_bm25", _BM25([parents[0].text])
        ), patch.object(RAGService, "_district_to_place", {}), patch.object(
            RAGService, "_embed", return_value=[[1.0, 0.0]]
        ):
            rag = RAGService.__new__(RAGService)
            self.assertIn("早茶", rag.query("广州早茶", destination="广州"))
            self.assertIn("未找到", rag.query("广州火星殖民基地在哪里？", destination="广州"))
            collection.query.return_value["distances"] = [[0.8]]
            self.assertIn("未找到", rag.query("广州早茶", destination="广州"))


if __name__ == "__main__":
    unittest.main()
