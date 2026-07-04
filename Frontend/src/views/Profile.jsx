import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'

export default function Profile() {
  const { workspace } = useWorkspace()
  const [docs, setDocs] = useState([])
  const [kg, setKg] = useState({ nodes: [], edges: [] })
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancel = false
    setLoading(true); setErr('')
    Promise.all([api.listDocuments(workspace), api.kgGraph(workspace)])
      .then(([d, g]) => {
        if (cancel) return
        setDocs(d); setKg(g)
      })
      .catch((e) => !cancel && setErr('读取失败：' + e.message))
      .finally(() => !cancel && setLoading(false))
    return () => { cancel = true }
  }, [workspace])

  const totalChunks = docs.reduce((s, d) => s + (d.n_chunks || 0), 0)
  const allTags = [...new Set(docs.flatMap((d) => d.tags || []))].slice(0, 24)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">04</span>个人与用量</div>
          <h1 className="title mt-8">用量 <span className="it">ledger</span></h1>
          <div className="sub">当前工作区的资料库存与知识图谱规模一览。</div>
        </div>
        <div className="meta">
          <div className="eyebrow">工作区</div>
          <div className="serif italic mt-8" style={{ fontSize: 18 }}>{workspace}</div>
        </div>
      </div>

      {err && <div className="warn">⚠ {err}</div>}

      <div className="stats-grid mt-16">
        <div className="stat">
          <div className="k">文档</div>
          <div className="v">{loading ? '—' : docs.length}<span className="unit">篇</span></div>
        </div>
        <div className="stat">
          <div className="k">分块</div>
          <div className="v">{loading ? '—' : totalChunks}<span className="unit">块</span></div>
        </div>
        <div className="stat">
          <div className="k">图谱节点</div>
          <div className="v">{loading ? '—' : kg.nodes.length}</div>
        </div>
        <div className="stat">
          <div className="k">图谱关系</div>
          <div className="v">{loading ? '—' : kg.edges.length}</div>
        </div>
      </div>

      {allTags.length > 0 && (
        <div className="card mt-32">
          <div className="eyebrow"><span className="num">∎</span>标签云</div>
          <div className="tags">
            {allTags.map((t) => <span className="tag" key={t}>{t}</span>)}
          </div>
        </div>
      )}

      <div className="mt-32">
        <div className="between" style={{ padding: '0 4px 12px', borderBottom: '1px solid var(--rule-2)' }}>
          <span className="eyebrow"><span className="num">∎</span>文档清单</span>
          <span className="tiny">{docs.length} 篇</span>
        </div>
        <div className="doc-list">
          {docs.length === 0 && !loading && (
            <div className="tiny mt-16" style={{ padding: 16 }}>（空——上传文件后将出现在这里）</div>
          )}
          {docs.map((d) => (
            <div className="doc-row" key={d.id}>
              <div className="name">
                {d.filename}
                <small>{d.summary?.slice(0, 70) || '（无摘要）'}</small>
              </div>
              <div className="cat">{d.category || '—'}</div>
              <div className="type">{d.doc_type}</div>
              <div className="n">{d.n_chunks} 块</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
