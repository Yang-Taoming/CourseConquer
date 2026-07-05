import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

export default function Workspaces() {
  const [kbs, setKbs] = useState([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function load() {
    setLoading(true)
    try { setKbs(await api.listWorkspaces()) } catch (e) { setKbs([]) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function create() {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    try {
      const r = await api.createWorkspace(name)
      setNewName('')
      navigate(`/kb/${r.id}`)
    } catch (e) { alert('创建失败：' + e.message) }
    finally { setCreating(false) }
  }

  async function remove(id, name, e) {
    e.stopPropagation()
    if (!confirm(`确定删除知识库「${name}」？所有文档、图谱、对话将被清除。`)) return
    await api.deleteWorkspace(id)
    load()
  }

  async function rename(kb, e) {
    e.stopPropagation()
    const name = prompt('重命名知识库：', kb.name)
    if (name === null || name.trim() === '' || name === kb.name) return
    await api.renameWorkspace(kb.id, name.trim())
    load()
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">∎</span>选择知识库</div>
          <h1 className="title mt-8">你的 <span className="it">知识库</span></h1>
          <div className="sub">在已有知识库上继续构建，或新建一个。每个知识库独立存储文档、图谱与对话。</div>
        </div>
        <div className="meta">
          <a href="#/" className="tiny">← 返回首页</a>
        </div>
      </div>

      <div className="kb-new">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && create()}
          placeholder="新知识库名称，如：数据结构 / 线性代数…"
        />
        <button className="btn gold" onClick={create} disabled={creating || !newName.trim()}>
          {creating ? '创建中…' : '新建知识库'}
        </button>
      </div>

      <div className="kb-grid">
        {loading && <div className="tiny">载入中…</div>}
        {!loading && kbs.length === 0 && (
          <div className="card center" style={{ padding: 40 }}>
            <div className="serif italic" style={{ fontSize: 20, color: 'var(--ink-2)' }}>还没有知识库</div>
            <div className="tiny mt-16">在上面输入名称，新建第一个</div>
          </div>
        )}
        {kbs.map((kb) => (
          <div className="kb-card" key={kb.id} onClick={() => navigate(`/kb/${kb.id}`)}>
            <div className="between">
              <div className="serif" style={{ fontSize: 22 }}>{kb.name}</div>
              <span className="tag gold">{kb.n_docs} 文档</span>
            </div>
            <div className="tiny mt-8" style={{ letterSpacing: '0.06em' }}>
              {kb.n_conv} 个对话 · {kb.id.slice(0, 14)}
            </div>
            <div className="row between mt-16">
              <span className="tiny">{kb.last_used_at ? '最近用过' : (kb.created_at ? '已创建' : '已有数据')}</span>
              <div className="row gap-8">
                <button className="btn ghost sm" onClick={(e) => rename(kb, e)}>重命名</button>
                <button className="btn ghost sm" onClick={(e) => remove(kb.id, kb.name, e)}>删除</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
