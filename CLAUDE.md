# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product goal

A **lightweight knowledge-base assistant** to be built within a 24-hour hackathon. Learning, research, and development produce large amounts of fragmented information — course notes, paper excerpts, blog content, code snippets, tabular data, image screenshots. The assistant closes a basic loop of **capture → distill → reuse**: it ingests text/code/tables/images, auto-generates summaries and tags, stores everything in a personal knowledge base, and lets the user query, retrieve, and generate derived content (study notes, technical reports, mind maps, PPT outlines).

**Scope focus (our decision):** because enterprise data is hard to obtain, we deliberately narrow the scenario to a **student course knowledge hub** — student course material is the primary data we build around. Keep new features anchored to that use case.

### Reference requirements (the graded core loop)

- **信息输入 / Ingestion** — accept multiple input types: text, code, tables, images.
- **摘要与标签 / Summary & tags** — auto-generate a content summary, keyword tags, and a basic category.
- **知识库沉淀 / Persistence** — store original text, summary, tags, timestamp, and source; support retrieval.
- **知识问答 / Q&A** — natural-language questions answered from stored content.
- **内容生成 / Generation** — produce at least one of: study notes, technical summary, report draft, or PPT outline.

### Advanced challenges (stretch goals, optional)

Browser extension / mini-program / app; multimodal generation (tables, images, diagrams, video scripts); personalization from user feedback; cross-document reasoning (multi-doc / multi-table / multi-image); automatic web/paper/news/repo collection; a multi-dimension evaluation harness (retrieval accuracy, tag quality, answer quality, latency, UX). Anything else that stands out.

## Recommended stack (from the problem statement) vs. current choices

| Layer | Options offered | Chosen / current |
| --- | --- | --- |
| Interaction | Web, CLI | Web (client-server; users install nothing) |
| Frontend | React / Vue / Streamlit / Gradio | TBD (`Frontend/` empty) |
| Backend | FastAPI / Flask / Node.js | **FastAPI** (Agent 1 built) |
| Model API | DeepSeek API or other LLM APIs | **OpenAI-compatible gateway** (base URL + key in `Backend/.env`); routes to DeepSeek / Qwen-VL / bge-m3 |
| Storage / retrieval | Chroma / FAISS / Supabase pgvector / SQLite | **Server-side SQLite + numpy cosine**, behind a `Storage` interface (swap to pgvector later) |

**"Local" storage runs on the server, not the user's machine.** This is a standard web client-server app (like NotebookLM): the browser only renders UI and sends HTTP; parsing, SQLite, vectors, and all LLM calls live on the backend. Per-user isolation is via a `workspace_id` column. Scaling to multiple server instances later means swapping SQLite → Postgres/pgvector through the `Storage` interface.

## Current state

Greenfield project split into three parts; the repository is not yet a git repository.

- `Frontend/` — client/UI layer (not yet started).
- `Backend/` — server/API layer. **FastAPI + Agent 1 (parse → enrich → store) built and tested.**
- `theModel/` — ML / agent logic wrapped by the backend (not yet started).

## Intended architecture — multi-agent design

The system is planned as a **multi-agent pipeline**. A **shared file-parsing function** sits in front of everything: it accepts arbitrary file extensions and normalizes them into processable content. This same parser is reused on both the ingestion path and the query path.

- **Agent 1 — Ingestion & storage. ✅ Built** (see the Agent 1 section below). Parses any file into a canonical `ParsedDocument`, auto-generates summary/tags/category, chunks + embeds, and stores metadata + vectors server-side.
- **Agent 2 — Knowledge graph. ✅ Built, optional/on-demand** (see the Agent 2 section below). Extracts entities + relations over a **predefined type schema** and merges them into a graph (cross-document entities are de-duplicated/merged). **Not on the retrieval critical path** — vector search and Q&A work without it; it powers structure-based features (mind map, cross-doc / multi-hop reasoning). Triggered by a button (`POST /kg/build`), not on every upload. **No re-parsing:** Agent 2 reads the stored `markdown`/chunks that Agent 1 produced — the expensive parse (OCR/VL/office extraction) happens exactly once at ingestion.

  **Why KG is optional, not mandatory:** dense vector retrieval embeds *whole chunks* and needs no keyword/entity extraction at all — it already works. The enrichment `tags` are for browse/filter/display, also not a retrieval prerequisite. So keyword extraction ≠ retrieval prerequisite, and KG ≠ retrieval prerequisite. KG is a heavier, separate layer for the "wow" features (思维导图 / 跨文档推理). If exact-term matching is ever needed, add BM25 hybrid retrieval (tokenizes full text — still no LLM keyword step).
- **Agent 3 — Q&A / task planner. ✅ Built** (see the Agent 3 section below). The orchestrator behind the chat box: **plan → execute → synthesize**. An LLM planner routes each question (retrieve / multi-doc / kg / web / direct), retrieval runs with a **multi-round sufficiency loop** (an LLM judge decides "enough?" and, if not, issues the next query), and a final LLM synthesizes an answer that cites sources by file + location. Conversation history is threaded through so a user's chat description can disambiguate an unclear file (e.g. a bare CSV). Relation/structure/mind-map questions route to Agent 2 (auto-building the graph if empty).

When any cross-component contract is settled (Frontend ↔ Backend protocol, Backend ↔ `theModel` invocation, the agent message shapes), document it here so future work stays consistent.

## Open questions (unresolved design decisions)

These are the hard problems flagged in planning — resolve and record the decision here as each is settled:

1. ~~**Multi-round retrieval / sufficiency**~~ **(v1 built):** Agent 3 runs an LLM "sufficiency judge" after each retrieval round (`judge_sufficiency` in `agents/qa.py`) that returns `{sufficient, next_query}`; loops until sufficient / no new results / `QA_MAX_ROUNDS`. Residual: tune the judge, add a confidence threshold, avoid over-searching.
2. **Conversation memory** — for multi-turn Q&A, dialogue is currently **stateless** (client passes `history` per `/chat` request). Server-side/persistent session memory is not yet built.
3. ~~**Storage target**~~ **(resolved for Agent 1):** the uploaded content lives in **server-side storage** — original file on disk, normalized markdown + chunks + vectors in SQLite (see Agent 1). The knowledge graph (Agent 2) is a *derived* structure built from those stored chunks, not a replacement for them. Residual: decide the graph's own storage (SQLite tables vs. NetworkX vs. a graph DB) — currently SQLite `kg_nodes`/`kg_edges`.

## Backend (FastAPI)

Stack: Python 3.9 + FastAPI + uvicorn. Code lives in `Backend/`, dependencies in a local venv at `Backend/.venv/` (gitignored).

```bash
# 安装依赖（首次）
cd Backend && .venv/bin/pip install -r requirements.txt

# 启动开发服务（改代码自动重载）
cd Backend && .venv/bin/uvicorn main:app --reload
```

- App instance: `Backend/main.py` → `app` (`main:app`)
- 示例接口: `GET /` → `{"message":"Hello, World!"}`
- 自动文档: `http://127.0.0.1:8000/docs` (Swagger) — FastAPI 生成，无需手写
- 约定：新增算法接口时，从 `theModel/` 导入算法并在 `main.py`（或拆分的路由模块）里暴露成 HTTP 路由

### Agent 1 — 解析 + 摘要标签 + 向量入库 (built)

Pipeline: **parse (once) → enrich (summary/tags/category) → chunk → embed → store**. Each step is independently guarded; a failed step logs to `warnings` but still persists the record.

Module map (all under `Backend/app/`):

| Module | Responsibility |
| --- | --- |
| `config.py` | `.env`-driven settings: gateway URL/key, model routing, parse knobs, data paths. `get_settings()`. |
| `schemas/document.py` | Canonical `ParsedDocument` (markdown + typed `Block`s + meta), `DocumentRecord`, `IngestResult`. Shared with the future KG agent. |
| `llm/client.py` | One OpenAI-compatible client → `chat` / `chat_json` / `vision` / `embed`. Bypasses the env SOCKS proxy (`trust_env=False`) since the gateway is a direct IP. |
| `parsing/router.py` | Single entry `parse(data, filename)` → dispatches by type. Shared by ingestion **and** the query path. |
| `parsing/{mime,text,office,pdf,image}.py` | Per-type parsers (see routing table). |
| `parsing/chunk.py` | `chunk_blocks(...)` — chunks **per block** (one embedding per chunk, not per file) and carries **source location** into each chunk: PDF→page, PPT→slide, xlsx→sheet, text/code→line range, else→paragraph. This is what lets search point to "第7页 / 第120-135行". |
| `enrich/summarize.py` | LLM → `{summary, tags[], category}` JSON. |
| `storage/{base,local}.py` | `Storage` interface + `LocalStorage` (SQLite metadata/chunks + numpy cosine). `get_storage()`. |
| `agents/ingest.py` | `ingest_file(...)` orchestrator. |
| `routes/ingest.py` | HTTP endpoints. |

Parsing tool-routing (decided by extension in `parsing/mime.py`):

| Input | Tool | Notes |
| --- | --- | --- |
| `.txt .md` / code (`.py .c .cpp .java .js .go .sql .json …`) | direct UTF-8 read | code wrapped in fenced block with language tag |
| `.docx` / `.pptx` / `.xlsx` / `.csv` | python-docx / python-pptx / openpyxl / stdlib csv | tables → markdown |
| `.pdf` | PyMuPDF **hybrid** | per page: text-layer if present; else render page → image pipeline (scanned) |
| images (`.png .jpg .jpeg .webp .bmp .gif .tiff …`) | **vision model** (OCR prompt →理解 prompt) | one vision model does both: first transcribe text, then if sparse/garbage retry with an understand prompt |

Model routing — **unified to 2 text models (same family) + 1 vision + 1 embed + 1 web** (names must have a live channel on the gateway — verify with `GET /v1/models`):

| Purpose | Env var | Default | Notes |
| --- | --- | --- | --- |
| Text workhorse (planner/judge/summary/tags/KG extract/code) | `LLM_MODEL` | `bailian/deepseek-v4-flash` | Called per-chunk/per-step — needs to be fast/cheap. |
| Agent 3 final synthesis only | `LLM_MODEL_STRONG` | `bailian/deepseek-v4-pro` | Aggregates many sources → long context + stronger reasoning. |
| All image understanding (OCR + figures) | `VISION_MODEL` | `qwen-vl-max` | `qwen-vl-max-latest` and `Qwen/…`-cased names had **no channel**. (DeepSeek-OCR was tried & dropped — garbage on real images.) |
| Embeddings | `EMBED_MODEL` | `BAAI/bge-m3` | 1024-dim, multilingual |
| Web search (only when `allow_web`) | `WEB_MODEL` | `moonshotai/kimi-k2:online` | |

> **Reasoning-model gotcha:** `deepseek-v4-flash/pro` are reasoning models — they emit `reasoning_content` *then* `content`. Give a generous `max_tokens` (≥800) or the reasoning eats the whole budget and `content` comes back empty. The `chat()` wrapper returns only `content` (the final answer), which is correct.

Secrets live in `Backend/.env` (gitignored); `Backend/.env.example` is the template. Never hardcode the key.

HTTP endpoints:

- `POST /ingest` — multipart `file` (+ `workspace_id`, `source`) → parse+enrich+store → `IngestResult`.
- `GET /documents?workspace_id=` — list documents.
- `GET /documents/{doc_id}` — one document incl. normalized markdown.
- `GET /search?q=&workspace_id=&k=` — semantic (vector) search over chunks. Each hit returns `filename`, `location` (human-readable, e.g. `第2页` / `第120-135行`), `position` (structured: pages/slides/lines/blocks), `score`, and `text` — so answers can cite the exact source location.
- `POST /parse` — **test-only** preview: parse a file and return normalized markdown + `doc_type` + `parse_method`, without enrich/embed/store (fast, ~no tokens). For quickly checking whether a file type parses.
- `GET /files/{doc_id}` — serve the original uploaded file (inline, for citation click-to-open; browsers' PDF viewer honors `#page=N`).

Runtime data (gitignored) lives in `Backend/data/`: `knowledge.db` (SQLite) + `files/` (original uploads).

Quick manual test (server-free, uses FastAPI `TestClient`; makes real gateway calls):

```bash
cd Backend && .venv/bin/python - <<'PY'
from fastapi.testclient import TestClient; import main
c = TestClient(main.app)
r = c.post("/ingest", files={"file": ("bst.md", b"# BST\n二叉搜索树查找O(log n)", "text/markdown")}, data={"workspace_id":"demo"})
print(r.json()["document"]["tags"])
print(c.get("/search", params={"q":"BST 复杂度","workspace_id":"demo","k":3}).json())
PY
```

### Agent 2 — 知识图谱 (built, optional/button-triggered)

Extracts entities + relations from **already-stored** document markdown and merges them into a graph. It does **not** re-parse originals and is **not** required for search/Q&A — it's a separate, on-demand layer for structure-based features.

Module map (`Backend/app/`):

| Module | Responsibility |
| --- | --- |
| `kg/schema.py` | The **fixed type schema**: `ENTITY_TYPES` (Course/Chapter/Concept/Algorithm/Method/Theorem/Formula/Term/Example/Tool/Person) + `RELATION_TYPES` (PART_OF/PREREQUISITE_OF/DEPENDS_ON/DEFINES/EXAMPLE_OF/USES/HAS_COMPLEXITY/CONTRASTS_WITH/PROPOSED_BY/RELATED_TO) + extraction prompts. **Edit here to adjust the taxonomy, then rebuild.** |
| `kg/extract.py` | LLM → `{entities, relations}`, filtered to the allowed types. |
| `kg/graph_store.py` | SQLite `kg_nodes` / `kg_edges` (same `knowledge.db`). Entity resolution: nodes de-duped by `(workspace_id, normalized name)`; cross-doc mentions merge and increment `mentions`; more specific types override generic `Concept`/`Term`. |
| `kg/build.py` | `build_kg(workspace_id, doc_id=None)` — batches each doc's markdown (`kg_batch_chars`), extracts, upserts. |
| `kg/nebula_view.py` | **NebulaGraph-style view** (ported from `hackson1`, no real NebulaGraph server): stable VIDs, relation normalization (aliases→canonical edge types), **property folding** (HAS_COMPLEXITY/REQUIRES/DETECTS collapse into node `property_values`, keeping structural edges visible), GET SUBGRAPH multi-hop, nGQL schema export. |
| `schemas/kg.py` | `KGNode`, `KGEdge`, `GraphView`, `BuildResult`. |
| `routes/kg.py` | Endpoints below. |

HTTP endpoints:

- `POST /kg/build` — **the button.** Form `workspace_id` (+ optional `doc_id`); builds/extends the KG from stored docs. Synchronous. Returns `BuildResult` (nodes/edges added + totals).
- `GET /kg?workspace_id=` — **NebulaGraph-style presentation graph**: `nodes` (with `vid`, `type`, `property_values`, `mentions`, `doc_ids`) + `edges` (with `relation`, `support_count`, `source_documents`) + `schema` + `stats` (incl. `collapsed_property_facts`).
- `GET /kg/subgraph?entity=&workspace_id=&depth=` — GET SUBGRAPH-style bounded multi-hop neighborhood around an entity.
- `GET /kg/schema` — the LLM extraction schema (entity/relation types).
- `GET /kg/ngql` — exported NebulaGraph nGQL `CREATE SPACE/TAG/EDGE` schema (for show; no server needed).

Model: `LLM_MODEL` (default `bailian/deepseek-v4-flash`). Verified on ALG26: `/kg/build` → 122 nodes / 266 edges / 28 folded property facts; algorithms carry `complexities` in `property_values`; structural edges (PART_OF/USES/CONTRASTS_WITH/DEPENDS_ON) stay visible; `/kg/subgraph?entity=Dijkstra` reaches 算法与数据结构/Shortest Paths/非负权重/BFS/Kruskal in 2 hops. Frontend renders it as an interactive force-directed graph (pan/zoom/click-to-select).

### Agent 3 — 对话式问答 (built)

The chat orchestrator: **plan → execute → synthesize**, with a multi-round retrieval loop. Endpoint `POST /chat` (body = `ChatRequest`).

Module map (`Backend/app/`):

| Module | Responsibility |
| --- | --- |
| `agents/qa.py` | Orchestrator. `plan_query` (LLM routes the question), `retrieve` / `parallel_retrieve` (multi sub-query), `judge_sufficiency` (LLM "enough?" critic — the multi-round loop), `synthesize` (cited answer), `chat` (ties it together). |
| `agents/qa_tools.py` | Branch tools: `web_answer` (live search via `WEB_MODEL`), `kg_answer` (routes to Agent 2 — auto-builds the graph if empty, then answers from it). |
| `schemas/qa.py` | `ChatRequest` (question, workspace_id, history, allow_web, top_k, max_rounds), `Citation`, `ChatResponse`. |
| `routes/chat.py` | `POST /chat`. |

Routing (planner picks `route`):

- `retrieve` / `multi_doc` — vector search (sub-queries run in parallel for comparisons), then the **sufficiency loop**: after each round an LLM judges `{sufficient, next_query}`; if not sufficient and something new is found, it searches again — up to `QA_MAX_ROUNDS` (default 3). Answer synthesized with `[n]` citations resolving to `filename · location` (page/line).
- `kg` — relation / structure / mind-map questions → Agent 2 (`kg_answer`); builds the graph on demand if empty.
- `web` — needs external/live info; only runs if the request sets `allow_web: true` (otherwise falls back to local retrieval with a warning).
- `direct` — no retrieval needed.

Code-intent and all synthesis use the **strong model** (`LLM_MODEL_STRONG`, `bailian/deepseek-v4-pro`) — it aggregates many retrieved chunks so the long context + stronger reasoning matter; the planner/judge use the workhorse (`LLM_MODEL`). Conversation `history` is threaded into planning + synthesis so a user's chat description can disambiguate an unclear file (e.g. a bare CSV).

**Context compression** (`_prep_evidence`): dedupe by chunk_id → top-8 by score → **tiered char caps** (rank-1 chunk gets 1200 chars, lower ranks get progressively less) → hard `QA_CONTEXT_BUDGET` (default 7000 chars) tail-trim. Lossless on the most relevant chunk, lossy on the tail, no extra LLM calls. Plus history capped to `QA_HISTORY_TURNS` (4).

**Answer shape (for the student-learning goal):** the synthesis prompt requires (1) answer the question — **use evidence, but if KB lacks it, use the model's own knowledge rather than refusing**, (2) then surface the **背后的知识点/概念** so the student learns the principle behind the problem, (3) mark evidence-backed claims with `[n]`, (4) end with a self-tagged `[[来源:知识库|部分知识库|模型常识|联网]]` → parsed into the `provenance` field (`kb_full`/`kb_partial`/`model_only`/`web`). Each `Citation` carries `doc_id`, `filename`, `location` (human-readable `第7页`/`第120-135行`), and **`position`** (structured `{pages|slides|lines, blocks}`) — the frontend turns a citation into `GET /files/{doc_id}#page=N` to open the source file at the right page.

**Thinking trace:** `chat()` appends `TraceStep`s as it runs — `plan` → `retrieve`（命中的文件·位置·score）→ `judge`（够不够 + next_query）→ `multi_doc` / `web` / `kg` → `synthesize`. The frontend reveals them progressively (staggered animation) so the user sees "我在看哪个文档、发现了什么、在对比还是联网".

**Web links:** `web_answer` extracts Markdown/bare URLs from the web model's answer into `web_links[]` (clickable in the UI).

Models: `LLM_MODEL` (plan + judge + enrich + KG extract), `LLM_MODEL_STRONG` (synthesis + KG answer), `VISION_MODEL`, `WEB_MODEL`. Verified on ALG26: Dijkstra-vs-Bellman-Ford → `multi_doc`, 3 retrieval rounds (judge twice requested deeper "原理" queries), `provenance=kb_full`, 5 cited sources with line ranges; KMP surfaces 前缀函数 + 线性时间匹配; "2024 图灵奖" → `web` (Barto & Sutton) with source links.

**Note on conversation memory (open question #2):** currently stateless — the client passes `history` in each request. Server-side persistence (per-session memory) is not yet built.

## Conventions to establish early

Since nothing is committed yet, prefer setting these up in the first change rather than retrofitting later:

- Initialize git (`git init`) and commit a `.gitignore` appropriate for each layer's stack.
- Keep model artifacts / large files out of git (use Git LFS or external storage); note where weights and checkpoints live in this file.
- Add the run commands for each component here as soon as they exist (e.g., how to start the frontend dev server, the backend API, and how to run/test the model).

## Frontend (React + Vite)

"Course Conquer" — 编辑拼贴视觉语言（Atelier Zero / Monocle / Apartamento），淡黄色系，PC 端，版心 1700px。React + Vite + react-router (HashRouter)，手写 CSS。代码在 `Frontend/`。

```bash
# 安装依赖（首次；见下方环境注意事项）
cd Frontend && npm install

# 启动开发服务（改代码自动重载）
cd Frontend && npm run dev    # → http://127.0.0.1:5173/
```

- 入口：`Frontend/index.html` → `src/main.jsx` → `App.jsx`
- 路由（侧栏切换）：`/` 首页（全屏 hero + 编辑性章节 + 全屏收尾页）、`/upload` 数据库上传、`/chat` 知识问答、`/kg` 知识图谱、`/profile` 个人与用量
- 后端对接：`src/api.js` 封装 `fetch` 到 `VITE_API_BASE`（默认 `http://127.0.0.1:8000`），调 `/ingest /parse /documents /search /chat /kg /kg/build`。后端已开 CORS。
- 工作区：侧栏底部输入框，默认 `alg26`（有测试数据）；可改成任意 ID。
- 字体：Fraunces（衬线标题）+ Inter（无衬线正文），Google Fonts 加载。

### ⚠️ 本机 npm install 注意事项（已踩过的坑）

本机环境有三个会卡住 npm 的因素，安装时必须绕开：

1. **系统代理**：环境里有 `http_proxy/https_proxy/all_proxy → 127.0.0.1:7897`，npm 会用，且对 npmmirror 很慢。→ 项目 `.npmrc` 已固定 `registry=https://registry.npmmirror.com` + `noproxy=*`，安装时还要 `env -u` 清掉代理 env。
2. **TLS 证书**：node 23 不读 macOS 钥匙串，验证 npmmirror 证书失败（`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`）。→ 导出钥匙串 CA 给 node：`security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/cc-ca.pem` + login keychain，再 `NODE_EXTRA_CA_CERTS=/tmp/cc-ca.pem`（**不要**用 `--strict-ssl=false`，已保留 TLS 验证）。
3. **root 拥有的缓存目录**：`~/.npm/_cacache/.../6f/` 是 root 拥有（历史 `sudo npm install` 残留），用户级 npm 写不进。→ 安装时用 `--cache=/tmp/cc-npm-cache` 换个干净缓存目录。

完整可用的安装命令：

```bash
cd Frontend
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  no_proxy='*' NO_PROXY='*' NODE_EXTRA_CA_CERTS=/tmp/cc-ca.pem \
  npm install --cache=/tmp/cc-npm-cache --userconfig=/dev/null --no-audit --no-fund
```

（已验证：`added 65 packages in 21s`，`vite build` 通过。）

> 若浏览器装了系统代理打不开 127.0.0.1:5173，给 127.0.0.1/localhost 加不走代理即可。
