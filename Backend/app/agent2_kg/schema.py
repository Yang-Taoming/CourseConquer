"""知识图谱的实体/关系类型（限定集合）——学生课程场景。

用「限定 schema」而非自由抽取：类型固定后图谱更干净、去重更稳、前端好上色。
想调整就改这两个字典 + 重建图谱即可，其他代码不用动。
"""
from __future__ import annotations

# 实体类型: 英文键(存储/前端用) -> 中文说明(喂给模型)
ENTITY_TYPES = {
    "Course": "课程（如：数据结构、线性代数）",
    "Chapter": "章节 / 主题（如：树与二叉树）",
    "Concept": "概念（如：二叉搜索树、递归、特征值）",
    "Algorithm": "算法（如：快速排序、Dijkstra）",
    "Method": "方法 / 技术 / 思想（如：分治、动态规划）",
    "Theorem": "定理 / 性质 / 定律（如：主定理、鸽巢原理）",
    "Formula": "公式 / 复杂度（如：O(n log n)、欧拉公式）",
    "Term": "术语 / 定义（不属于以上更具体类型的名词）",
    "Example": "例子 / 习题 / 应用场景",
    "Tool": "工具 / 库 / 编程语言（如：Python、NumPy）",
    "Person": "人物（如：提出者、科学家）",
}

# 关系类型: 英文键 -> 中文说明
RELATION_TYPES = {
    "PART_OF": "属于（章节属于课程、概念属于章节）",
    "PREREQUISITE_OF": "是……的前置 / 基础",
    "DEPENDS_ON": "依赖 / 建立在……之上",
    "DEFINES": "定义了 / 引出",
    "EXAMPLE_OF": "是……的例子 / 应用",
    "USES": "使用 / 应用了",
    "HAS_COMPLEXITY": "复杂度为",
    "CONTRASTS_WITH": "与……对比 / 区别",
    "PROPOSED_BY": "由……提出",
    "RELATED_TO": "相关（无更具体关系时的兜底）",
}

DEFAULT_ENTITY_TYPE = "Concept"  # 关系端点缺类型时的兜底
FALLBACK_RELATION = "RELATED_TO"


def build_system_prompt() -> str:
    ent = "\n".join("  - %s: %s" % (k, v) for k, v in ENTITY_TYPES.items())
    rel = "\n".join("  - %s: %s" % (k, v) for k, v in RELATION_TYPES.items())
    return (
        "你是知识图谱抽取器，面向学生课程资料。"
        "从给定文本中抽取实体和它们之间的关系，用于构建可检索的知识图谱。\n\n"
        "只允许使用以下实体类型（type 用英文键）：\n" + ent + "\n\n"
        "只允许使用以下关系类型（relation 用英文键）：\n" + rel + "\n\n"
        "规则：\n"
        "- 实体 name 用文本中出现的规范中文/英文名称，去掉多余修饰。\n"
        "- 同一实体只出现一次；关系的 source/target 必须是已抽取实体的 name。\n"
        "- 不确定关系类型时用 RELATED_TO；不要臆造文本中没有的关系。\n"
        "- 只输出 JSON，不要解释。"
    )


def user_prompt(context: str, text: str) -> str:
    return (
        "【课程/来源背景】%s\n\n【文本】\n%s\n\n"
        "请只输出如下 JSON：\n"
        '{"entities":[{"name":"...","type":"实体类型英文键","description":"一句话说明"}],'
        '"relations":[{"source":"实体name","target":"实体name","relation":"关系类型英文键"}]}'
    ) % (context, text)
