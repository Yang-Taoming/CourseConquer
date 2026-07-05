"""评测 harness：基于 ALG26 gold 问答集，对 /chat 做自动化评测。

评测点：
  - 问答正确率：LLM-as-judge（强模型）对照 gold 答案判 correct/partial/wrong，解决"答案不会完全一致"问题
  - 检索命中：引用的文件是否包含该题期望来源（按题面关键词映射）
  - 响应速度：端到端延迟
  - token 用量：本次问答消耗

用法：
  python -m eval.harness --sample 6        # 随机抽 6 题
  python -m eval.harness --ids 1,9,25,39   # 指定题号
  python -m eval.harness --all             # 全部 60 题
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 让脚本可独立运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient  # noqa: E402
import main as backend_app  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.shared.llm import client as llm  # noqa: E402

GOLD_PATH = Path(__file__).resolve().parent / "gold_algs26.md"
WORKSPACE = "alg26"

# 期望来源映射：按题面关键词 → 期望被引用的文件名片段
SOURCE_RULES = [
    (("csv",), "alg26_algorithm_complexities.csv"),
    (("图片", "ocr", "image"), "alg26_graph_algorithms_ocr.png"),
    (("kmp_prefix_function", "compute_pi", "kmp_search"), "kmp_prefix_function.py"),
    (("dijkstra_vs_bellman_ford",), "dijkstra_vs_bellman_ford.py"),
    (("c++", "c＋＋"), "graph_algorithm_complexities.cpp"),
    (("c 文件", "c文件", "algorithmfact 结构体"), "graph_algorithm_complexities.c"),
    (("红黑树", "red-black"), "red_black_tree_insert_fixup_outline.md"),
    (("txt",), "alg26_graph_algorithms_note.txt"),
    (("docx",), "alg26_graph_algorithms_note.docx"),
]


def parse_gold(path: Path) -> List[Dict]:
    """解析 md：每个 ### 小节是一道题，含 question 与 理论正确答案。"""
    text = path.read_text(encoding="utf-8")
    section = ""
    out: List[Dict] = []
    cur = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            section = m.group(1).strip()
            continue
        m = re.match(r"^###\s+(\d+)\.\s+(.*)$", line)
        if m:
            if cur:
                out.append(cur)
            cur = {"id": int(m.group(1)), "category": section, "question": m.group(2).strip(), "gold": ""}
            continue
        if cur and line.startswith("理论正确答案"):
            cur["gold"] = line.split("：", 1)[1].strip() if "：" in line else ""
            continue
        if cur and cur["gold"] and line.strip():
            cur["gold"] += "\n" + line.strip()
    if cur:
        out.append(cur)
    return out


def expected_source(q: str) -> Optional[str]:
    ql = q.lower()
    for keys, fname in SOURCE_RULES:
        if any(k.lower() in ql for k in keys):
            return fname
    return None


# ---------- LLM-as-judge ----------
JUDGE_SYS = (
    "你是阅卷人。给定【标准答案】与【模型答案】，判断模型答案是否正确覆盖了标准答案的关键点。"
    "只输出 JSON：{\"score\": \"correct|partial|wrong\", \"reason\": \"一句话\"}。"
    "标准：correct = 关键点全覆盖（措辞可不同）；partial = 覆盖一部分但有遗漏或小错；wrong = 关键错误或答非所问。"
)


def judge(qid: int, gold: str, answer: str) -> Dict:
    user = "【标准答案】%s\n\n【模型答案】%s" % (gold, answer)
    try:
        d = llm.chat_json(JUDGE_SYS, user, model=get_settings().llm_model_strong)
    except Exception:
        d = {}
    score = d.get("score", "wrong")
    if score not in ("correct", "partial", "wrong"):
        score = "wrong"
    return {"score": score, "reason": str(d.get("reason", ""))[:120]}


SCORE_VAL = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}


def run_one(client: TestClient, item: Dict) -> Dict:
    q = item["question"]
    t0 = time.time()
    r = client.post("/chat", json={"question": q, "workspace_id": WORKSPACE}).json()
    latency = round(time.time() - t0, 2)
    answer = r.get("answer", "")
    cites = [c.get("filename", "") for c in r.get("citations", [])]
    # 检索命中：期望来源是否出现在引用里
    exp = expected_source(q)
    cite_hit = (exp is None) or any(exp in c for c in cites)
    # 正确率
    j = judge(item["id"], item["gold"], answer)
    return {
        "id": item["id"],
        "category": item["category"],
        "question": q,
        "answer": answer,
        "gold": item["gold"],
        "score": j["score"],
        "score_val": SCORE_VAL[j["score"]],
        "judge_reason": j["reason"],
        "route": r.get("route"),
        "rounds": r.get("rounds"),
        "citations": cites,
        "expected_source": exp,
        "cite_hit": cite_hit,
        "latency_s": latency,
        "tokens": (r.get("usage") or {}).get("total", 0),
        "provenance": r.get("provenance"),
    }


def summarize(rows: List[Dict]) -> Dict:
    n = len(rows)
    if n == 0:
        return {}
    correct = sum(1 for r in rows if r["score"] == "correct")
    partial = sum(1 for r in rows if r["score"] == "partial")
    wrong = sum(1 for r in rows if r["score"] == "wrong")
    cite_n = sum(1 for r in rows if r["expected_source"])
    cite_hit = sum(1 for r in rows if r["expected_source"] and r["cite_hit"])
    return {
        "n": n,
        "correct": correct, "partial": partial, "wrong": wrong,
        "accuracy": round((correct + 0.5 * partial) / n, 3),
        "correct_rate": round(correct / n, 3),
        "citation_recall": round(cite_hit / cite_n, 3) if cite_n else None,
        "avg_latency_s": round(sum(r["latency_s"] for r in rows) / n, 2),
        "avg_tokens": round(sum(r["tokens"] for r in rows) / n),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--ids", type=str, default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", type=str, default="eval_report.json")
    ap.add_argument("--tag", type=str, default="run")
    args = ap.parse_args()

    gold = parse_gold(GOLD_PATH)
    if args.ids:
        want = {int(x) for x in args.ids.split(",")}
        items = [g for g in gold if g["id"] in want]
    elif args.all:
        items = gold
    elif args.sample:
        random.seed(42)
        items = random.sample(gold, min(args.sample, len(gold)))
    else:
        items = gold[:6]

    print(f"[%s] 评测 {len(items)} 题 (workspace={WORKSPACE})" % args.tag)
    client = TestClient(backend_app.app)
    rows = []
    for i, item in enumerate(items, 1):
        print(f"  {i}/{len(items)}  Q{item['id']} {item['question'][:30]}...", flush=True)
        try:
            rows.append(run_one(client, item))
        except Exception as e:  # noqa: BLE001
            print("    ERROR:", e)
            rows.append({"id": item["id"], "question": item["question"], "error": str(e),
                         "score": "wrong", "score_val": 0.0, "latency_s": 0, "tokens": 0,
                         "citations": [], "cite_hit": False, "expected_source": expected_source(item["question"])})

    summary = summarize(rows)
    report = {"tag": args.tag, "summary": summary, "rows": rows}
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 汇总 [%s] ===" % args.tag)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n=== 逐题 ===")
    for r in rows:
        print(f"Q{r['id']:>2} [{r.get('score','?'):<7}] cite={r.get('cite_hit')} "
              f"lat={r.get('latency_s')}s tok={r.get('tokens')} | {r.get('question','')[:36]}")
    print("\n报告已写入:", out_path.resolve())


if __name__ == "__main__":
    main()
