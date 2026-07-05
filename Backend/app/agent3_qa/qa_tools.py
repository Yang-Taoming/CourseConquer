"""Agent 3 的分支工具：联网搜索、知识图谱路由(导向 Agent 2)。

这些分支是自包含的（各自直接调 LLM / kg 模块），不反向依赖 qa.py，避免循环导入。
"""
from __future__ import annotations

import re
from typing import List, Tuple

from app.config import get_settings
from app.agent2_kg.build import build_kg
from app.agent2_kg.graph_store import get_graph_store
from app.shared.llm import client as llm
from app.shared.schemas.qa import ChatMessage, WebLink


def history_text(history: List[ChatMessage], limit: int = 6) -> str:
    msgs = history[-limit:]
    return "\n".join("%s: %s" % (m.role, m.content) for m in msgs) if msgs else "（无）"


# ---------- 联网搜索分支 ----------
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"(?<![\w/])(https?://[^\s)\]]+)")


def _extract_links(text: str) -> List[WebLink]:
    seen, links = set(), []
    for m in _MD_LINK.finditer(text):
        url, title = m.group(2).rstrip(".,;)"), m.group(1)
        if url not in seen:
            seen.add(url); links.append(WebLink(url=url, title=title))
    for m in _BARE_URL.finditer(text):
        url = m.group(1).rstrip(".,;)")
        if url not in seen:
            seen.add(url); links.append(WebLink(url=url, title=""))
    return links[:8]


def web_answer(question: str, history: List[ChatMessage], warnings: List[str]) -> Tuple[str, List[WebLink]]:
    """联网搜索：返回 (答案, 来源链接)。kimi-k2:online 自带引用，提取为可跳转链接。"""
    s = get_settings()
    system = (
        "你是联网搜索助手。基于实时检索到的网页信息用中文回答用户问题，"
        "在答案里以 Markdown 链接形式 [标题](URL) 标注关键来源。"
    )
    user = "对话历史：\n%s\n\n问题：%s" % (history_text(history), question)
    try:
        text = llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=s.web_model, max_tokens=4000,
        )
        return text, _extract_links(text)
    except Exception as e:  # noqa: BLE001
        warnings.append("联网搜索失败：%s" % e)
        return "联网搜索暂时不可用。", []


# ---------- 知识图谱分支（导向 Agent 2）----------
def _graph_text(graph, node_cap: int = 80, edge_cap: int = 150) -> str:
    byid = {n.id: n for n in graph.nodes}
    lines = ["实体："]
    for n in graph.nodes[:node_cap]:
        lines.append("- %s（%s）" % (n.name, n.type))
    lines.append("关系：")
    cnt = 0
    for e in graph.edges:
        if e.source_id in byid and e.target_id in byid:
            lines.append("- %s --%s--> %s" % (byid[e.source_id].name, e.relation, byid[e.target_id].name))
            cnt += 1
            if cnt >= edge_cap:
                break
    return "\n".join(lines)


def kg_answer(question: str, workspace_id: str, history: List[ChatMessage],
              warnings: List[str]) -> Tuple[str, int, int]:
    """关系/结构/思维导图类问题：确保图谱已建(否则触发 Agent 2)，再基于图作答。"""
    s = get_settings()
    gs = get_graph_store()
    n, e = gs.counts(workspace_id)
    if n == 0:
        warnings.append("知识图谱为空，已自动触发 Agent 2 构建（首次会慢一些）")
        build_kg(workspace_id)      # ← 导向 Agent 2
        n, e = gs.counts(workspace_id)
    if n == 0:
        return "无法构建知识图谱，暂时无法回答关系类问题。", 0, 0

    ctx = _graph_text(gs.graph(workspace_id))
    system = (
        "你是知识库助手。下面是从课程资料抽取的知识图谱（实体+关系）。"
        "请依据这张图回答用户关于关系/依赖/结构/思维导图的问题；图里没有的可以结合常识补充，但要标明。"
        "需要呈现结构时用条目或缩进层级表示。用中文。"
    )
    user = "知识图谱：\n%s\n\n对话历史：\n%s\n\n问题：%s" % (ctx, history_text(history), question)
    try:
        ans = llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=s.llm_model_strong, max_tokens=4000,
        )
    except Exception as ex:  # noqa: BLE001
        warnings.append("KG 问答失败：%s" % ex)
        ans = "知识图谱问答失败。"
    return ans, n, e
