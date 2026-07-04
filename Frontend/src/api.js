// 后端 API 客户端。默认指向本地 8000；可用 VITE_API_BASE 覆盖。
const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function j(res) {
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  base: BASE,

  // —— Agent 1：解析 / 入库 / 检索 ——
  parse(file) {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`${BASE}/parse`, { method: 'POST', body: fd }).then(j)
  },
  ingest(file, workspace_id = 'default', source = null) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('workspace_id', workspace_id)
    if (source) fd.append('source', source)
    return fetch(`${BASE}/ingest`, { method: 'POST', body: fd }).then(j)
  },
  listDocuments(workspace_id = 'default') {
    return fetch(`${BASE}/documents?workspace_id=${encodeURIComponent(workspace_id)}`).then(j)
  },
  getDocument(doc_id) {
    return fetch(`${BASE}/documents/${doc_id}`).then(j)
  },
  search(q, workspace_id = 'default', k = 5) {
    return fetch(
      `${BASE}/search?q=${encodeURIComponent(q)}&workspace_id=${encodeURIComponent(workspace_id)}&k=${k}`,
    ).then(j)
  },

  // —— Agent 2：知识图谱 ——
  kgBuild(workspace_id = 'default') {
    const fd = new FormData()
    fd.append('workspace_id', workspace_id)
    return fetch(`${BASE}/kg/build`, { method: 'POST', body: fd }).then(j)
  },
  kgGraph(workspace_id = 'default') {
    return fetch(`${BASE}/kg?workspace_id=${encodeURIComponent(workspace_id)}`).then(j)
  },
  kgSchema() {
    return fetch(`${BASE}/kg/schema`).then(j)
  },

  // —— Agent 3：问答 ——
  chat({ question, workspace_id = 'default', history = [], allow_web = false, top_k, max_rounds }) {
    return fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, workspace_id, history, allow_web, top_k, max_rounds }),
    }).then(j)
  },

  // 原始文件地址（供引用点击打开；PDF 可用 #page=N 跳页）
  fileUrl(doc_id, page) {
    const u = `${BASE}/files/${doc_id}`
    return page ? `${u}#page=${page}` : u
  },
}
