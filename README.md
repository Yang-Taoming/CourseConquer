# Course Conquer · 课程知识库智能助手

一个面向学生与科研者的轻量知识库助手。把课件、代码、表格、图片喂进去，自动摘要与标签，沉淀为可检索、可问答、可成图的个人课程仓库——**捕获 → 蒸馏 → 复用**。

## 特色

- **多类型文件解析**（文本/代码/PDF/Office/图片）：图片走视觉模型 OCR，PDF 文字层+扫描页混合，每个分块带**页码/行号溯源**
- **多轮检索 + ReAct 反思**：LLM 裁判 Thought→Action 决定检索/合成/联网，含 SeaKR 式知识冲突觉察
- **Generative Agents 记忆**：对话持久化，按 重要性×新近度×相关性 召回历史轮次，支持多轮上下文
- **NebulaGraph 风格知识图谱**（按钮触发，可选）：稳定 VID、属性折叠、多跳子图、nGQL Schema
- **答案带引用 + 来源标注**：[n] 引用可点击打开原文件（PDF 跳页），来源诚实标注 知识库/部分/模型常识/联网
- **多模态生成 skill**：对话里切「生成」→ 选 图片/PPT/CSV/DOCX/Markdown，一键下载
- **评测 harness**：基于 60 题 gold 问答集，LLM-as-judge 判正确率 + 检索命中 + 延迟 + token

多 Agent 架构：**Agent 1** 解析入库 · **Agent 2** 知识图谱 · **Agent 3** 对话问答。

---

## 快速开始

### 1. 配置模型

后端通过 OpenAI 兼容网关调用大模型。复制模板填入你自己的地址与 key：

```bash
cd Backend
cp model-config/models.example.yaml model-config/models.yaml
# 编辑 model-config/models.yaml，填 gateway.base_url 与 gateway.api_key
```

> `models.yaml` 已 gitignore，不同人用不同 key，不会提交。默认模型统一为 `gpt-5.1-high`（多模态），图像生成 `gpt-image-1`，向量 `bge-m3`，联网 `kimi-k2:online`。

### 2. 启动后端

```bash
cd Backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload
# → http://127.0.0.1:8000  （Swagger 文档 /docs）
```

### 3. 启动前端

```bash
cd Frontend
npm install
npm run dev
# → http://127.0.0.1:5173
```

打开 `http://127.0.0.1:5173/`：落地页拖拽翻页 → 点「开始上传」→ 选/建知识库 → 进入知识库（左侧栏：概览/上传/问答/图谱/用量）。

> **本机 npm install 注意**：若环境有系统代理且 node 验证证书失败，用以下完整命令（导出钥匙串 CA + 换缓存目录 + 清代理 env）：
> ```bash
> cd Frontend
> security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/cc-ca.pem
> security find-certificate -a -p ~/Library/Keychains/login.keychain-db >> /tmp/cc-ca.pem
> env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
>   no_proxy='*' NO_PROXY='*' NODE_EXTRA_CA_CERTS=/tmp/cc-ca.pem \
>   npm install --cache=/tmp/cc-npm-cache --userconfig=/dev/null --no-audit --no-fund
> ```

---

## 功能使用

| 位置 | 功能 | 说明 |
|---|---|---|
| 落地页 `/` | 介绍 | 拖拽/滚轮/方向键翻页，CardSwap 卡片展示，点「开始上传」进入 |
| 知识库列表 `/workspaces` | 管理 | 新建 / 进入 / 重命名 / 删除知识库 |
| 概览 | 文档+对话 | 文档（文件名+关键词+日期+摘要，可生成总摘要存入库）；对话记录（点击续聊/删除/新建） |
| 上传 | Agent 1 | 拖入文件自动解析+摘要+标签+向量入库 |
| 问答 | Agent 3 | 对话（Markdown 渲染公式/代码）、思维链动画、引用跳转、附件上传、生成工具、存入知识库 |
| 图谱 | Agent 2 | 构建图谱，同心圆布局，点节点看详情，缩放/平移 |
| 用量 | 统计 | token 用量（每次问答/建图/入库）、文件清单 |

### 核心 HTTP 接口

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/ingest` | 上传文件 → 解析+摘要标签+向量入库 |
| POST | `/parse` | 仅解析预览（不入库） |
| GET | `/documents?workspace_id=` | 列出文档 |
| GET | `/documents/{id}` | 查看单文档 |
| DELETE | `/documents/{id}` | 删除文档 |
| POST | `/documents/{id}/summarize` | 重新生成单文档摘要 |
| GET | `/search?q=&workspace_id=&k=` | 向量语义检索 |
| GET | `/files/{id}` | 预览原文件（inline，PDF 认 #page=N） |
| POST | `/chat` | 对话问答（思维链+引用+来源+记忆） |
| POST | `/generate` | 多模态生成 skill（notes/report/ppt/doc/code/csv/md/image） |
| GET | `/workspaces` | 列出知识库 |
| POST | `/workspaces` | 新建知识库 |
| PATCH | `/workspaces/{id}` | 重命名 |
| DELETE | `/workspaces/{id}` | 删除（级联） |
| POST | `/workspaces/{id}/summarize_all` | 生成知识库总摘要 |
| GET/POST/DELETE | `/conversations` | 对话 CRUD |
| POST | `/conversations/{id}/save_to_kb` | 对话存入知识库 |
| POST | `/kg/build` | 构建知识图谱 |
| GET | `/kg` | NebulaGraph 风格展示图 |
| GET | `/kg/subgraph?entity=&depth=` | 多跳邻域 |
| GET | `/kg/ngql` | nGQL Schema 导出 |
| GET | `/usage?workspace_id=` | token 用量统计 |

---

## 目录结构

```
CourseConquer/
├── README.md
├── CLAUDE.md                       # Claude Code 项目指引
├── AGENTS.md                       # Codex 项目指引
├── poster/                         # A4 海报（HTML + PNG）
├── test_data/                      # 多模态测试文件（ALG26 算法基础）
├── Backend/
│   ├── main.py                     # FastAPI 入口
│   ├── requirements.txt
│   ├── model-config/
│   │   ├── models.example.yaml     # 模型配置模板（提交）
│   │   └── models.yaml             # 实际配置（gitignore，含 key）
│   ├── eval/
│   │   ├── harness.py              # 评测 harness（LLM-as-judge + 检索命中）
│   │   └── gold_algs26.md          # 60 题 gold 问答集
│   └── app/
│       ├── config.py               # 读 model-config/models.yaml
│       ├── shared/                 # 三 Agent 共用基础设施
│       │   ├── llm/client.py       #   网关封装 chat/vision/embed/generate_image + token 记账
│       │   ├── parsing/            #   文件解析（mime/text/office/pdf/image/chunk/router）
│       │   ├── storage/            #   Storage 接口 + SQLite+numpy 实现（含对话/记忆/用量）
│       │   └── schemas/            #   document / kg / qa 数据结构
│       ├── agent1_ingest/          # Agent 1 解析入库
│       │   ├── ingest.py  enrich.py  routes.py  routes_workspaces.py
│       ├── agent2_kg/              # Agent 2 知识图谱
│       │   ├── schema.py  extract.py  graph_store.py  build.py  nebula_view.py  routes.py
│       └── agent3_qa/              # Agent 3 问答
│           ├── qa.py               #   规划→多轮检索(ReAct)→合成 + Generative Agents 记忆
│           ├── qa_tools.py         #   联网 / KG 路由
│           ├── generate.py         #   多模态生成 skill
│           └── routes.py
└── Frontend/
    ├── index.html  vite.config.js  package.json
    ├── poster/                     # （已移至根 poster/）
    └── src/
        ├── main.jsx  App.jsx  api.js  styles.css
        ├── components/             # CardSwap / Markdown
        └── views/                  # Landing / Workspaces / WithinKB / Upload / Chat / KnowledgeGraph
```

---

## 评测 harness

```bash
cd Backend
.venv/bin/python -m eval.harness --ids 1,9,25,33,39,45 --tag run --out eval_run.json   # 指定题
.venv/bin/python -m eval.harness --sample 10 --tag sample                              # 随机抽
.venv/bin/python -m eval.harness --all --tag full                                      # 全 60 题
```

评测点：**问答正确率**（LLM-as-judge 对照 gold，判 correct/partial/wrong，解决"答案措辞不一致"）、**检索命中**（引用是否含期望来源）、**响应延迟**、**token 用量**。输出 JSON 报告 + 汇总。

---

## 模型路由

统一在 `model-config/models.yaml`：

| 用途 | 默认模型 |
|---|---|
| 文本（规划/裁判/摘要/合成/代码/生成） | `gpt-5.1-high` |
| 图片理解（OCR + 图表） | `gpt-5.1-high` |
| 图像生成 | `gpt-image-1` |
| 向量化 | `BAAI/bge-m3` |
| 联网搜索 | `moonshotai/kimi-k2:online` |

> gpt-5.1-high 是推理模型，`max_tokens` 需 ≥4000，否则推理吃光预算导致 `content` 为空。

## 技术栈

- **后端**：Python 3.9 + FastAPI + uvicorn + SQLite + numpy + PyMuPDF + python-docx/pptx + openpyxl
- **前端**：React + Vite + react-router + react-markdown + KaTeX + gsap（CardSwap）
- **存储**：服务器端 SQLite + numpy 余弦（`Storage` 接口可换 pgvector）
- **模型**：OpenAI 兼容网关

## 用到的高级技术

RAG · 多轮检索 + 充分性裁判 · ReAct 反思 · SeaKR 知识冲突觉察 · Generative Agents 记忆流（importance×recency×relevance）· NebulaGraph 风格属性图（VID/属性折叠/多跳子图/nGQL）· OCR-first + VL fallback · 页/行级 provenance + click-to-source · LLM-as-judge 评测 harness · 上下文压缩 · 来源自标注（provenance）· 思维链 trace · 多模态生成 skill · 多 Agent 编排

## 已知限制

- 对话记忆已持久化（T1 原始轮 + 向量召回）；T2 滚动摘要 / T3 抽取事实为可选扩展
- 知识图谱为 NebulaGraph **风格**模型，未接真实 NebulaGraph 服务
- 海报字体依赖 Google Fonts 在线加载
