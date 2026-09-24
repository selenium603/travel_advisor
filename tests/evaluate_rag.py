"""Run a small real-provider retrieval check: python -m tests.evaluate_rag."""

import json
from pathlib import Path

from backend.services.knowledge.rag import RAGService


def main() -> None:
    cases = json.loads(Path(__file__).with_name("rag_eval_cases.json").read_text(encoding="utf-8"))
    rag = RAGService()
    passed = 0
    for case in cases:
        answer = rag.query(case["query"], case.get("destination"))
        if case.get("no_hit"):
            ok = "未找到" in answer
        else:
            ok = case["source"] in answer and case["contains"] in answer
        passed += ok
        print(json.dumps({"ok": ok, "query": case["query"], "sources": [
            line.removeprefix("*来源：").removesuffix("*")
            for line in answer.splitlines() if line.startswith("*来源：")
        ], "no_hit": "未找到" in answer}, ensure_ascii=True), flush=True)
    print(f"RAG evaluation: {passed}/{len(cases)} passed", flush=True)
    if passed != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
