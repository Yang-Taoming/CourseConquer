"""Agent 3 —— 对话式问答：规划 → 执行(多轮检索/多文档/KG/联网) → 带引用的合成。

关键设计：
  - **思维链 trace**：每一步（规划/检索/裁判/多文档/联网/合成）都往 trace 里 append 一条
    人可读记录，前端按顺序动态展示「我在看哪个文档、发现了什么、在对比还是在联网」。
  - **尽量回答**：证据不足时不要说"无法回答"，而是结合模型自身知识回答，并诚实标注来源
    （provenance: kb_full / kb_partial / web / model_only）。
  - **强模型合成**：最终答案用 LLM_MODEL_STRONG；提示词只表达规则，不过度限制。
对话历史全程带入，用于"用户描述反推文件含义"。
"""
from __future__ import annotations

import concurrent.futures as cf
import re
from typing import Any, Dict, List, Optional, Tuple

from app.agent3_qa import qa_tools
from app.config import get_settings
from app.shared.llm import client as llm
from app.shared.schemas.qa import ChatMessage, ChatRequest, ChatResponse, Citation, TraceStep, WebLink
from app.shared.storage.local import get_storage

_ROUTES = {"retrieve", "multi_doc", "kg", "web", "direct"}


def _history_text(history: List[ChatMessage], limit: int = 6) -> str:
    msgs = history[-limit:]
    return "\n".join("%s: %s" % (m.role, m.content) for m in msgs) if msgs else "（无）"


# ---------------- 规划 ----------------
PLANNER_SYS = (
    "你是知识库问答系统的任务规划器。根据用户问题、对话历史和知识库文档清单，决定如何回答。只输出 JSON。\n"
    "route 取值：\n"
    "- retrieve：常规，从知识库向量检索后回答（默认；单/多文档都用它，通过 search_queries 控制）\n"
    "- kg：涉及概念之间的关系/依赖、课程结构、思维导图、跨文档串联（如“哪些算法依赖递归”“这门课有哪些章”）\n"
    "- web：需要知识库之外的实时/外部信息\n"
    "- direct：闲聊或无需查资料\n"
    "intent 取值：single_doc / multi_doc_compare / structure / multi_hop / table / code / general\n"
    "search_queries：为检索准备的 1-3 个查询（多文档对比就给多个针对性子查询，会并行检索）。\n"
    "target_filenames：用户明确针对某些文件时填文件名，否则空。"
)


def plan_query(question: str, history: List[ChatMessage], docs) -> Dict[str, Any]:
    s = get_settings()
    catalog = "\n".join(
        "- %s（%s，%s）：%s" % (d.filename, d.doc_type, d.category or "", (d.summary or "")[:40])
        for d in docs[:40]
    ) or "（知识库为空）"
    user = (
        "对话历史：\n%s\n\n知识库文档：\n%s\n\n用户问题：%s\n\n"
        '只输出 JSON：{"route":"retrieve|kg|web|direct","intent":"...",'
        '"search_queries":["..."],"target_filenames":[],"use_web":false,"reason":"..."}'
    ) % (_history_text(history), catalog, question)

    data = llm.chat_json(PLANNER_SYS, user, model=s.llm_model)
    route = data.get("route")
    if route not in _ROUTES:
        route = "retrieve"
    queries = [q for q in (data.get("search_queries") or []) if isinstance(q, str) and q.strip()][:4]
    return {
        "route": route,
        "intent": str(data.get("intent", "")),
        "search_queries": queries or [question],
        "target_filenames": [f for f in (data.get("target_filenames") or []) if isinstance(f, str)],
        "use_web": bool(data.get("use_web")),
        "reason": str(data.get("reason", "")),
    }


# ---------------- 检索 ----------------
def retrieve(workspace_id: str, query: str, k: int,
             doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    emb = llm.embed([query])[0]
    return get_storage().search(workspace_id, emb, k, doc_ids)


def parallel_retrieve(workspace_id: str, queries: List[str], k: int,
                      doc_ids: Optional[List[str]]) -> List[List[Dict[str, Any]]]:
    if len(queries) == 1:
        return [retrieve(workspace_id, queries[0], k, doc_ids)]
    with cf.ThreadPoolExecutor(max_workers=min(4, len(queries))) as ex:
        return list(ex.map(lambda q: retrieve(workspace_id, q, k, doc_ids), queries))


JUDGE_SYS = (
    "你是检索充分性裁判。看用户问题和已检索到的证据，判断这些证据是否足以准确回答。"
    '只输出 JSON：{"sufficient": true/false, "missing": "还缺什么", "next_query": "若不足，下一步该检索的查询；足够就留空"}。'
    "证据已能回答就判 true，否则给出更有针对性的 next_query。"
)


def judge_sufficiency(question: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    s = get_settings()
    brief = "\n".join(
        "- (%s · %s) %s" % (h.get("filename", "?"), h.get("location", ""), (h.get("text", ""))[:200])
        for h in sorted(evidence, key=lambda x: x.get("score", 0), reverse=True)[:10]
    ) or "（无）"
    return llm.chat_json(JUDGE_SYS, "问题：%s\n\n已检索到的证据：\n%s" % (question, brief),
                         model=s.llm_model)


# ---------------- 合成 ----------------
SYNTH_SYS = (
    "你是面向学生的知识库问答助手。规则：\n"
    "1) 优先用【证据】回答；证据不够时，可以用你自己的知识补全，让用户得到有用回答，不要轻易说「无法回答」。\n"
    "2) 回答完问题后，点出背后的知识点/概念，帮助学生理解原理。\n"
    "3) 来自【证据】的结论用 [n] 标注引用编号；来自你自己知识的结论不用标注。\n"
    "4) 用中文，条理清晰；涉及代码保留关键片段。\n"
    "5) 回答最末另起一行，写一个来源标记，只能是下面四个之一：\n"
    "   [[来源:知识库]] 全部来自知识库证据\n"
    "   [[来源:部分知识库]] 部分来自证据、部分来自模型常识\n"
    "   [[来源:模型常识]] 知识库没有相关内容，全靠模型自身知识\n"
    "   [[来源:联网]] 主要来自联网信息\n"
    "只写这一个标记，不要多余解释。"
)

_PROV_RE = re.compile(r"\[\[来源:(知识库|部分知识库|模型常识|联网)\]\]")
_PROV_MAP = {"知识库": "kb_full", "部分知识库": "kb_partial", "模型常识": "model_only", "联网": "web"}


def _prep_evidence(evidence: List[Dict[str, Any]], budget: int,
                   max_items: int = 8) -> Tuple[str, List[Citation]]:
    """上下文压缩：按相似度排序取 top-N，越靠后的块给越少字数；再按总预算砍尾。"""
    used = sorted(evidence, key=lambda h: h.get("score", 0), reverse=True)[:max_items]
    caps = [1200, 900, 700, 550, 450, 350, 300, 250, 200, 200][:len(used)]
    items = []
    for h, cap in zip(used, caps):
        items.append((h, (h.get("text", "") or "")[:cap]))
    while sum(len(t) for _, t in items) > budget and len(items) > 1:
        items.pop()
    lines, cits = [], []
    for i, (h, txt) in enumerate(items, 1):
        loc = h.get("location", "")
        src = h.get("filename", "?") + (" · %s" % loc if loc else "")
        lines.append("[%d]（%s）\n%s" % (i, src, txt))
        cits.append(Citation(ref=i, doc_id=h.get("document_id", ""), filename=h.get("filename", ""),
                             location=loc, position=h.get("position") or {}, score=h.get("score", 0.0)))
    return ("\n\n".join(lines) or "（无）"), cits


def synthesize(question: str, evidence: List[Dict[str, Any]], history: List[ChatMessage],
               budget: int, history_turns: int, extra: str = "") -> Tuple[str, List[Citation], str]:
    """返回 (答案, 引用, provenance)。provenance 由模型自标 + 兜底推断。"""
    s = get_settings()
    numbered, cits = _prep_evidence(evidence, budget=budget)
    user = "对话历史：\n%s\n\n【证据】\n%s\n%s\n\n问题：%s" % (
        _history_text(history, limit=history_turns * 2), numbered, extra, question)
    raw = llm.chat([{"role": "system", "content": SYNTH_SYS}, {"role": "user", "content": user}],
                   model=s.llm_model_strong, max_tokens=1200)

    # 解析来源标记
    m = _PROV_RE.search(raw)
    if m:
        prov = _PROV_MAP.get(m.group(1), "model_only")
        answer = _PROV_RE.sub("", raw).rstrip()
    else:
        # 模型没标 → 兜底：有证据就 kb_partial，否则 model_only
        prov = "kb_partial" if cits else "model_only"
        answer = raw
    return answer, cits, prov


def _resolve_doc_ids(filenames: List[str], docs) -> Optional[List[str]]:
    if not filenames:
        return None
    fset = set(filenames)
    ids = [d.id for d in docs if d.filename in fset]
    return ids or None


def _trace(step: str, text: str, **detail) -> TraceStep:
    return TraceStep(step=step, text=text, detail=detail)


# ---------------- 编排 ----------------
def chat(req: ChatRequest) -> ChatResponse:
    s = get_settings()
    warnings: List[str] = []
    trace: List[TraceStep] = []
    docs = get_storage().list_documents(req.workspace_id)
    if not docs:
        return ChatResponse(answer="知识库还没有内容，请先上传文件再提问。", route="empty",
                            trace=[_trace("plan", "知识库为空，无法检索")])

    plan = plan_query(req.question, req.history, docs)
    route = plan["route"]
    k = req.top_k or s.qa_top_k
    max_rounds = max(1, req.max_rounds or s.qa_max_rounds)

    route_zh = {"retrieve": "知识库检索", "multi_doc": "多文档检索", "kg": "知识图谱",
                "web": "联网搜索", "direct": "直接回答"}.get(route, route)
    trace.append(_trace("plan", "规划：%s · %s" % (route_zh, plan.get("reason", "") or plan.get("intent", "")),
                        route=route, intent=plan.get("intent"), queries=plan["search_queries"]))

    # --- KG 分支：导向 Agent 2 ---
    if route == "kg":
        trace.append(_trace("kg", "调用知识图谱（Agent 2）", action="route_to_kg"))
        ans, n, e = qa_tools.kg_answer(req.question, req.workspace_id, req.history, warnings)
        plan["kg"] = {"nodes": n, "edges": e}
        trace.append(_trace("kg", "基于 %d 节点 / %d 关系作答" % (n, e), nodes=n, edges=e))
        trace.append(_trace("synthesize", "生成结构化回答"))
        return ChatResponse(answer=ans, route="kg", intent=plan["intent"], plan=plan,
                            trace=trace, provenance="kb_full", warnings=warnings)

    # --- 联网分支 ---
    if route == "web":
        if req.allow_web:
            trace.append(_trace("web", "联网搜索中…", model=s.web_model))
            ans, links = qa_tools.web_answer(req.question, req.history, warnings)
            trace.append(_trace("web", "检索到 %d 条来源" % len(links), links=[l.url for l in links]))
            trace.append(_trace("synthesize", "汇总联网结果作答"))
            return ChatResponse(answer=ans, route="web", intent=plan["intent"], plan=plan,
                                trace=trace, provenance="web", web_links=links, warnings=warnings)
        warnings.append("该问题可能需要联网，但未开启 allow_web，已改用本地知识库回答。")
        trace.append(_trace("plan", "未开启联网，改走知识库检索"))
        route = "retrieve"

    # --- 直接回答 ---
    if route == "direct":
        trace.append(_trace("synthesize", "无需检索，直接作答"))
        ans, _, prov = synthesize(req.question, [], req.history, s.qa_context_budget,
                                  s.qa_history_turns, extra="（此问题无需检索资料，可直接回答）")
        trace.append(_trace("synthesize", "来源：%s" % prov))
        return ChatResponse(answer=ans, route="direct", intent=plan["intent"], plan=plan,
                            trace=trace, provenance=prov, warnings=warnings)

    # --- 检索分支（含多文档并行 + 多轮检索）---
    target = _resolve_doc_ids(plan["target_filenames"], docs)
    evidence: List[Dict[str, Any]] = []
    seen = set()
    multi_doc = len(plan["search_queries"]) > 1
    if multi_doc:
        trace.append(_trace("multi_doc", "多文档对比：%d 个子查询并行检索" % len(plan["search_queries"]),
                            queries=plan["search_queries"]))

    def _log_hits(query: str, hits: List[Dict[str, Any]]):
        if not hits:
            trace.append(_trace("retrieve", "检索「%s」→ 无命中" % query, query=query))
            return
        top = hits[0]
        trace.append(_trace("retrieve", "检索「%s」→ 命中 %s · %s（score %.2f，共 %d 条）" % (
            query, top.get("filename", "?"), top.get("location", ""),
            top.get("score", 0), len(hits)), query=query,
            top="%s·%s" % (top.get("filename"), top.get("location"))))

    for q, hits in zip(plan["search_queries"], parallel_retrieve(req.workspace_id, plan["search_queries"], k, target)):
        _log_hits(q, hits)
        for h in hits:
            if h["chunk_id"] not in seen:
                seen.add(h["chunk_id"])
                evidence.append(h)

    rounds = 1
    while rounds < max_rounds:
        verdict = judge_sufficiency(req.question, evidence)
        if verdict.get("sufficient") or not str(verdict.get("next_query", "")).strip():
            trace.append(_trace("judge", "裁判：证据充分，开始作答"))
            break
        nq = str(verdict["next_query"]).strip()
        trace.append(_trace("judge", "裁判：证据不足（%s），再查「%s」" % (
            verdict.get("missing", "") or "缺漏", nq), next_query=nq))
        hits = retrieve(req.workspace_id, nq, k, target)
        _log_hits(nq, hits)
        new = [h for h in hits if h["chunk_id"] not in seen]
        if not new:
            break
        for h in new:
            seen.add(h["chunk_id"])
            evidence.append(h)
        rounds += 1

    trace.append(_trace("synthesize", "汇总 %d 条证据，生成带引用的答案" % len(evidence),
                        n_evidence=len(evidence)))
    ans, cits, prov = synthesize(req.question, evidence, req.history, s.qa_context_budget,
                                 s.qa_history_turns)
    trace.append(_trace("synthesize", "来源：%s" % prov, provenance=prov))
    route_label = "multi_doc" if multi_doc else "retrieve"
    return ChatResponse(answer=ans, route=route_label, intent=plan["intent"],
                        rounds=rounds, citations=cits, trace=trace, provenance=prov,
                        plan=plan, warnings=warnings)
