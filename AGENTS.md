# AGENTS.md

Guidance for Codex (codex.ai/code) working in this repo. **Full details live in [`CLAUDE.md`](./CLAUDE.md)** — read it first. This file is a short orientation.

## What this is

Course Conquer — a lightweight **course knowledge-base assistant**. Multi-agent pipeline: **Agent 1** parse→enrich→store, **Agent 2** on-demand NebulaGraph-style knowledge graph, **Agent 3** Q&A with ReAct retrieval + Generative-Agents memory + multimodal generation.

## Run

```bash
# Backend
cd Backend && .venv/bin/pip install -r requirements.txt
cp model-config/models.example.yaml model-config/models.yaml   # fill base_url + api_key
.venv/bin/uvicorn main:app --reload                             # :8000

# Frontend
cd Frontend && npm install && npm run dev                       # :5173

# Eval
cd Backend && .venv/bin/python -m eval.harness --sample 6 --tag run
```

## Layout

- `Backend/app/` — `shared/` (llm/parsing/storage/schemas) + `agent1_ingest/` + `agent2_kg/` + `agent3_qa/`. Entry: `main.py`.
- `Backend/model-config/models.yaml` — gateway + keys + model names (gitignored; template `models.example.yaml`). **Unified model `gpt-5.1-high`** (multimodal), `gpt-image-1`, `bge-m3`, `kimi-k2:online`.
- `Backend/eval/` — `harness.py` (LLM-as-judge eval) + `gold_algs26.md` (60 Q&A).
- `Frontend/src/` — React+Vite. IA: Landing → `/workspaces` → `/kb/:id` (sidebar).
- `poster/` — A4 poster + 16:9 cover. `test_data/` — ALG26 test files.

## Conventions

- Models/config in `model-config/`, never hardcoded. Different people, different keys.
- `gpt-5.1-high` is a reasoning model: `max_tokens` ≥ 4000 or `content` comes back empty.
- New algorithm? Import from the relevant agent module, expose as a route in its `routes.py`.
- Storage behind `Storage` interface (`shared/storage/base.py`) — swap SQLite→pgvector there.
- Parser is shared (`shared/parsing/router.py`) on both ingest and query paths.
- Frontend talks to backend via `src/api.js` (default `http://127.0.0.1:8000`, CORS open).

## Gotchas (this machine)

- npm install: proxy + node TLS cert + root-owned cache — see CLAUDE.md "本机 npm install 坑" for the exact `NODE_EXTRA_CA_CERTS` + `--cache=/tmp/cc-npm-cache` + `--userconfig=/dev/null` command.
- Backend LLM client uses `trust_env=False` to bypass the SOCKS proxy (gateway is a direct public IP).

See `CLAUDE.md` for the full endpoint list, agent internals, model routing, and open questions.
