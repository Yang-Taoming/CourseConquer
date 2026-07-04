# Course Conquer · 课程知识库智能助手

一个面向学生与科研者的轻量知识库助手。把课件、代码、表格、图片喂进去，自动摘要与标签，沉淀为可检索、可问答、可成图的个人课程仓库——**捕获 → 蒸馏 → 复用**。

多 Agent 架构：
- **Agent 1 — 解析入库**：任意类型文件 → 规范化 Markdown → 摘要/标签/分类 → 切块（带页码行号）→ 向量入库
- **Agent 2 — 知识图谱**（按钮触发，可选）：从已入库内容抽取实体与关系，构建 NebulaGraph 风格属性图，支持多跳子图与 nGQL Schema
- **Agent 3 — 对话问答**：规划 → 多轮检索 → 带引用作答，实时展示思维链，标注来源（知识库/部分知识库/模型常识/联网）

---

## 快速开始

### 1. 配置模型

后端通过 OpenAI 兼容网关调用大模型。复制模板并填入你自己的地址与 key：

```bash
cd Backend
cp model-config/models.example.yaml model-config/models.yaml
# 编辑 model-config/models.yaml，填入 gateway.base_url 与 gateway.api_key
```

> `models.yaml` 已被 gitignore，不同人用不同 key，不会提交。模板里已给默认模型名（deepseek-v4-flash/pro、qwen-vl-max、bge-m3、kimi-k2:online），可按需覆盖。

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

打开 `http://127.0.0.1:5173`，左侧侧栏切换功能，底部可改 workspace（默认 `alg26` 有测试数据）。

> **本机 npm install 注意**：若环境有系统代理且 node 验证证书失败，参考 `CLAUDE.md` 的 Frontend 章节给出的 `NODE_EXTRA_CA_CERTS` + `--cache` + `no_proxy` 完整命令。

---

## 功能与使用

| 侧栏 | 功能 | 怎么用 |
|---|---|---|
| **首页** | 全屏编辑风介绍页 | 滚动浏览，含收尾联系页 |
| **数据库上传** | Agent 1 | 拖入任意课件文件，自动解析+摘要+标签+向量入库，显示「上传成功」 |
| **知识问答** | Agent 3 | 输入问题，看思维链（在看哪个文档/发现什么/在对比/在联网），答案带引用与来源标签；点引用打开原文件（PDF 自动跳页） |
| **知识图谱** | Agent 2 | 点「构建图谱」从已入库内容抽取实体关系，力导向图可视化，点节点看详情与邻居 |
| **个人与用量** | 统计 | 文档数/分块数/图谱规模/标签云/文档清单 |

### 核心 HTTP 接口

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/ingest` | 上传文件 → 解析+摘要标签+向量入库 |
| POST | `/parse` | 仅解析预览（不入库，不花 token） |
| GET | `/documents?workspace_id=` | 列出文档 |
| GET | `/documents/{doc_id}` | 查看单文档（含 markdown） |
| GET | `/search?q=&workspace_id=&k=` | 向量语义检索（命中带页码行号） |
| GET | `/files/{doc_id}` | 下载/预览原始文件（引用跳转用，PDF 认 `#page=N`） |
| POST | `/chat` | 对话问答（返回答案+思维链 trace+引用+来源 provenance+联网链接） |
| POST | `/kg/build` | 【按钮】构建/扩展知识图谱 |
| GET | `/kg?workspace_id=` | NebulaGraph 风格展示图 |
| GET | `/kg/subgraph?entity=&depth=` | 多跳邻域子图 |
| GET | `/kg/schema` | LLM 抽取用的实体/关系类型 |
| GET | `/kg/ngql` | NebulaGraph nGQL Schema 导出 |

---

## Backend 目录结构与脚本说明

```
Backend/
├── main.py                      # FastAPI 入口，挂载三个 agent 的路由 + CORS
├── requirements.txt             # Python 依赖
├── model-config/
│   ├── models.example.yaml      # 模型配置模板（提交）—— 网关 url / apikey 占位 / 模型名默认值
│   └── models.yaml              # 实际配置（gitignore）—— 填你自己的 key
└── app/
    ├── config.py                # 读取 model-config/models.yaml，提供 get_settings()
    │
    ├── shared/                  # 三個 Agent 共用的基础设施
    │   ├── llm/client.py        # OpenAI 兼容网关封装：chat / chat_json / vision / embed
    │   ├── parsing/             # 共用文件解析器（入库与问答路径都用）
    │   │   ├── router.py        #   总入口 parse(data, filename) → 按类型分派
    │   │   ├── mime.py          #   按扩展名分类 doc_type + 语言标签
    │   │   ├── text.py          #   .txt/.md/代码 直接读（代码包 fenced block）
    │   │   ├── office.py        #   .docx/.pptx/.xlsx/.csv → Markdown（表格归一化）
    │   │   ├── pdf.py           #   PyMuPDF 混合：文字层优先，扫描页渲染成图走视觉
    │   │   ├── image.py         #   图片：视觉模型 OCR，稀疏/崩坏时视觉兜底
    │   │   └── chunk.py         #   按 Block 切块，每块带来源位置（页码/行号）
    │   ├── storage/
    │   │   ├── base.py          #   Storage 接口（可换 pgvector/Chroma）
    │   │   └── local.py         #   默认实现：SQLite 元数据+分块+向量，numpy 余弦检索
    │   └── schemas/
    │       ├── document.py      #   ParsedDocument / Block / Chunk / DocumentRecord / IngestResult
    │       ├── kg.py            #   KGNode / KGEdge / GraphView / BuildResult
    │       └── qa.py            #   ChatRequest/Response / Citation / TraceStep / WebLink
    │
    ├── agent1_ingest/           # Agent 1 —— 解析 + 摘要标签 + 向量入库
    │   ├── ingest.py            #   ingest_file() 编排：parse → enrich → chunk → embed → store
    │   ├── enrich.py            #   LLM 生成 {summary, tags, category}
    │   └── routes.py            #   /ingest /parse /documents /documents/{id} /search /files
    │
    ├── agent2_kg/               # Agent 2 —— 知识图谱（按钮触发，可选）
    │   ├── schema.py            #   限定实体/关系类型 schema + 抽取提示词
    │   ├── extract.py           #   LLM → {entities, relations}，按 schema 过滤
    │   ├── graph_store.py       #   SQLite kg_nodes/kg_edges，实体去重合并（跨文档同名合并）
    │   ├── build.py             #   build_kg() 从已入库 markdown 分批抽取并入图
    │   ├── nebula_view.py       #   NebulaGraph 风格视图：稳定 VID / 关系归一化 / 属性折叠 / 多跳子图 / nGQL
    │   └── routes.py            #   /kg /kg/build /kg/subgraph /kg/schema /kg/ngql
    │
    └── agent3_qa/               # Agent 3 —— 对话式问答
        ├── qa.py                #   编排：plan → retrieve(多轮+裁判) → synthesize，构建 trace + provenance
        ├── qa_tools.py          #   分支工具：web_answer（联网+抽链接）/ kg_answer（路由到 Agent 2）
        └── routes.py            #   /chat
```

### 模型路由（统一在 `model-config/models.yaml`）

| 用途 | 默认模型 |
|---|---|
| 文本主力（规划/裁判/摘要标签/KG抽取/代码） | `bailian/deepseek-v4-flash` |
| Agent 3 最终合成（长上下文+更强推理） | `bailian/deepseek-v4-pro` |
| 图片 OCR + 图表理解 | `qwen-vl-max` |
| 向量化 | `BAAI/bge-m3`（1024 维） |
| 联网搜索（仅 `allow_web`） | `moonshotai/kimi-k2:online` |

> 三个模型族职能清晰：文本 2 个（同族 flash/pro）+ 视觉 1 个 + 向量 1 个 + 联网 1 个。换模型只改 yaml，代码不动。

---

## 技术栈

- **后端**：Python 3.9 + FastAPI + uvicorn + SQLite + numpy
- **前端**：React + Vite + react-router，手写 CSS（编辑拼贴视觉语言）
- **模型**：OpenAI 兼容网关，路由到 DeepSeek / Qwen-VL / bge-m3
- **存储**：服务器端 SQLite + numpy 余弦（接口可换 pgvector/Chroma）

## 数据隔离与扩展

- 多用户通过 `workspace_id` 字段隔离（每条数据/向量/图谱节点都带它）
- `Storage` 接口可整体替换为 Postgres/pgvector，Agent 代码不变
- 知识图谱是**派生结构**，从已入库分块构建，不重新解析原文件；不在检索关键路径上

## 已知限制

- 对话记忆无状态（客户端每次传 `history`）
- 知识图谱为 NebulaGraph **风格**模型（属性图 + nGQL Schema），未接真实 NebulaGraph 服务
- 海报字体依赖 Google Fonts 在线加载
