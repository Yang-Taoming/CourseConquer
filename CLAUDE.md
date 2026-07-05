# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product goal

A **lightweight knowledge-base assistant** built for a 24h hackathon. Closes the loop **capture → distill → reuse**: ingest text/code/tables/images → auto summary/tags → store → query/retrieve → generate derived content (notes, reports, mind maps, PPT).

**Scope:** a **student course knowledge hub** — student course material is the primary data. Keep features anchored to that use case.

### Graded core loop
- **信息输入** — text, code, tables, images
- **摘要与标签** — summary, keyword tags, category
- **知识库沉淀** — store original + summary + tags + timestamp + source; retrieval
- **知识问答** — NL questions answered from stored content
- **内容生成** — study notes / technical report / PPT / etc.

## Stack

| Layer | Chosen |
| --- | --- |
| Interaction | Web (client-server; users install nothing) |
| Frontend | **React + Vite** + react-router + react-markdown + KaTeX + gsap |
| Backend | **FastAPI** |
| Model API | **OpenAI-compatible gateway** (base URL + key in `Backend/model-config/models.yaml`); unified to `gpt-5.1-high` (multimodal) + `gpt-image-1` + `bge-m3` |
| Storage / retrieval | **Server-side SQLite + numpy cosine**, behind a `Storage` interface (swap to pgvector later) |

"Local" storage runs on the **server**, not the user's machine (like NotebookLM). Per-user isolation via `workspace_id`. Scaling = swap SQLite → Postgres/pgvector through the `Storage` interface.

## Current state — all three agents built & integrated

- `Backend/` — FastAPI, 3 agents + shared infra, model-config, eval harness. **Built and tested.**
- `Frontend/` — React+Vite, landing → workspaces → within-KB sidebar. **Built.**
- `poster/` — A4 poster (HTML+PNG) + 16:9 cover PNG.
- `test_data/` — ALG26 multimodal test files.
- `Backend/eval/` — harness + 60-question gold set.

Repository is a git repo (GitHub: Yang-Taoming/CourseConquer).

## Run commands

```bash
# 后端
cd Backend && .venv/bin/pip install -r requirements.txt
cp model-config/models.example.yaml model-config/models.yaml   # 填你的 base_url + api_key
.venv/bin/uvicorn main:app --reload                             # → :8000

# 前端
cd Frontend && npm install && npm run dev                       # → :5173

# 评测
cd Backend && .venv/bin/python -m eval.harness --sample 6 --tag run
```

## Architecture — multi-agent

A **shared file parser** sits in front; **Agent 1** persists, **Agent 2** is an on-demand derived graph, **Agent 3** orchestrates Q&A.

- **Agent 1 — Ingestion & storage.** `parse (once) → enrich (summary/tags/category) → chunk (with page/line provenance) → embed → store`. Files: `app/agent1_ingest/`.
- **Agent 2 — Knowledge graph.** Optional/button-triggered. Extracts entities+relations over a fixed schema, merges into a NebulaGraph-style property graph. **No re-parsing** — reads stored markdown. Not on the retrieval critical path. Files: `app/agent2_kg/`.
- **Agent 3 — Q&A / task planner.** `plan → execute (multi-round retrieve / kg / web) → synthesize`. **ReAct-style judge** (Thought→Action, with SeaKR conflict awareness) drives the multi-round loop. **Generative Agents memory** (importance×recency×relevance) recalls past turns. Answers cite sources by file+page and self-tag provenance. Files: `app/agent3_qa/`.

## Backend structure (`Backend/app/`)

```
config.py                     reads model-config/models.yaml → get_settings()
shared/                       shared infrastructure
  llm/client.py               chat/chat_json/vision/embed/generate_image + track_usage (token 记账)
  parsing/                    mime/text/office/pdf/image/chunk/router  (shared parse entry)
  storage/                    base.py interface + local.py (SQLite + numpy, incl. conversations/memory/usage)
  schemas/                    document.py / kg.py / qa.py
agent1_ingest/                ingest.py  enrich.py  routes.py  routes_workspaces.py
agent2_kg/                    schema.py  extract.py  graph_store.py  build.py  nebula_view.py  routes.py
agent3_qa/                    qa.py (orchestrator)  qa_tools.py (web/kg)  generate.py (multimodal skill)  routes.py
```

Other: `main.py` (FastAPI entry, mounts routers), `model-config/models.yaml` (gitignored, keys), `eval/harness.py` (eval).

## Model routing (in `model-config/models.yaml`)

| Purpose | Default |
| --- | --- |
| All text (plan/judge/summary/synth/code/generate) | `gpt-5.1-high` |
| Image understanding (OCR + figures) | `gpt-5.1-high` (multimodal) |
| Image generation | `gpt-image-1` |
| Embeddings | `BAAI/bge-m3` (1024-dim) |
| Web search (only `allow_web`) | `moonshotai/kimi-k2:online` |

> **Reasoning-model gotcha:** `gpt-5.1-high` is a reasoning model — emits `reasoning_content` then `content`. Give `max_tokens` ≥ 4000 or reasoning eats the budget and `content` comes back empty. `chat()` returns only `content`. DeepSeek-OCR was tried & dropped (garbage on real images); `qwen-vl-max-latest` had no channel on the gateway.

Secrets live in `Backend/model-config/models.yaml` (gitignored); `models.example.yaml` is the template. Different people use different keys. Never hardcode.

## Key HTTP endpoints

- `POST /ingest` `/parse` — upload / preview-parse
- `GET /documents` `/documents/{id}` `DELETE /documents/{id}` — docs CRUD
- `POST /documents/{id}/summarize` — regenerate one doc's summary
- `GET /search?q=&workspace_id=&k=` — vector search (hits carry page/line `position`)
- `GET /files/{id}` — serve original inline (PDF honors `#page=N`)
- `POST /chat` — Q&A (returns answer + trace + citations + provenance + web_links + usage)
- `POST /generate` — multimodal skill: `kind` ∈ notes/report/ppt/doc/code/csv/md/image (or `auto` = intent-classify)
- `GET/POST/PATCH/DELETE /workspaces[/{id}]` — KB CRUD
- `POST /workspaces/{id}/summarize_all` — overall KB summary
- `GET/POST/DELETE /conversations[/{id}]` — conversation memory CRUD
- `POST /conversations/{id}/save_to_kb` — save a conversation as a doc
- `POST /kg/build` `GET /kg` `/kg/subgraph` `/kg/ngql` — knowledge graph
- `GET /usage?workspace_id=` — token usage stats

## Frontend structure (`Frontend/src/`)

IA: `/` Landing (drag-nav showcase, CardSwap) → `/workspaces` (KB list, create/rename/delete) → `/kb/:wsId` (left sidebar: 概览/上传/问答/图谱/用量).

- `App.jsx` routes; `api.js` fetch wrapper to `VITE_API_BASE` (default `http://127.0.0.1:8000`); `styles.css` hand-written editorial style.
- `views/`: Landing, Workspaces, WithinKB (sidebar + Overview/Usage), Upload, Chat (markdown + memory + generate), KnowledgeGraph (concentric radial layout).
- `components/`: CardSwap (gsap), Markdown (react-markdown + KaTeX).

Workspace defaults to `alg26` (has test data); change in the sidebar.

## Key design decisions (settled)

1. **Multi-round retrieval** — ReAct judge `{thought, action: synthesize|retrieve|web, conflict, next_query}` loops to `QA_MAX_ROUNDS` (3). SeaKR-style conflict flag.
2. **Memory** — Generative Agents: `messages` table with `importance` + `embedding`; `retrieve_memory()` scores `importance×0.4 + recency×0.3 + relevance×0.3`. T1 (raw turns) implemented; T2 (rolling summary) / T3 (extracted facts) are optional extensions.
3. **Storage** — server-side SQLite + numpy. KG is a derived structure (SQLite `kg_nodes`/`kg_edges`) built from stored chunks, not a replacement.
4. **Provenance** — synthesis self-tags `[[来源:知识库|部分知识库|模型常识|联网]]` → `provenance` field; doesn't refuse when KB lacks info.
5. **Generation** — a skill module (`generate.py`) calling the unified model; no model switching. Image via `gpt-image-1`.
6. **Context compression** — `_prep_evidence`: dedupe → top-8 → tiered char caps → `QA_CONTEXT_BUDGET` tail-trim.

## Open questions / known limits

- T2/T3 memory layers (rolling summary, extracted facts) not yet built.
- KG is NebulaGraph **style** (no real NebulaGraph server).
- Conversation memory: server-side persistence built (per-conversation); cross-session fact memory is T3 (optional).
- No BM25 hybrid retrieval yet (dense-only); no reranker.
- Poster/cover fonts depend on Google Fonts online.

## ⚠️ 本机 npm install 坑

环境有 `http_proxy/https_proxy/all_proxy → 127.0.0.1:7897`，且 node 23 不读 macOS 钥匙串（`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`），且 `~/.npm/_cacache/.../6f/` 被 root 占着。完整命令：

```bash
cd Frontend
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > /tmp/cc-ca.pem
security find-certificate -a -p ~/Library/Keychains/login.keychain-db >> /tmp/cc-ca.pem
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy \
  no_proxy='*' NO_PROXY='*' NODE_EXTRA_CA_CERTS=/tmp/cc-ca.pem \
  npm install --cache=/tmp/cc-npm-cache --userconfig=/dev/null --no-audit --no-fund
```

后端同理绕开 SOCKS 代理：`app/shared/llm/client.py` 用 `httpx.Client(trust_env=False)`（网关是直连公网 IP）。
