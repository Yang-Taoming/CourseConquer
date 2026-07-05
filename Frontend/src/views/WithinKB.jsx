import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'
import Markdown from '../components/Markdown.jsx'
import Upload from './Upload.jsx'
import Chat from './Chat.jsx'
import KnowledgeGraph from './KnowledgeGraph.jsx'

const NAV = [
  { key: 'overview', idx: '00', label: '概览' },
  { key: 'upload', idx: '01', label: '数据库上传' },
  { key: 'chat', idx: '02', label: '知识问答' },
  { key: 'kg', idx: '03', label: '知识图谱' },
  { key: 'usage', idx: '04', label: '用量' },
]

export default function WithinKB() {
  const { wsId } = useParams()
  const { setWorkspace } = useWorkspace()
  const [tab, setTab] = useState('overview')
  const [conv, setConv] = useState(null)
  const [tick, setTick] = useState(0)
  const refresh = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => { setWorkspace(wsId) }, [wsId, setWorkspace])

  return (
    <div className="app">
      <aside className="sidebar">
        <Link to="/workspaces" className="brand">Course Conquer<span className="dot">.</span></Link>
        <div className="brand-sub">{wsId}</div>
        <div className="masthead"><span>EST. 2026</span><span>PC EDITION</span></div>
        <nav className="nav">
          <div className="nav-section-label">导航</div>
          {NAV.map((n) => (
            <div key={n.key} className={'nav-item' + (tab === n.key ? ' active' : '')} onClick={() => setTab(n.key)}>
              <span className="idx">{n.idx}</span><span>{n.label}</span>
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <Link to="/workspaces" className="tiny">← 切换知识库</Link>
          <div className="tiny mt-16" style={{ letterSpacing: '0.15em' }}>后端 127.0.0.1:8000</div>
        </div>
      </aside>

      <main className="main">
        {tab === 'overview' && <Overview wsId={wsId} tick={tick} onOpenConv={(id) => { setConv(id); setTab('chat') }} onNewConv={() => { setConv(null); setTab('chat') }} refresh={refresh} />}
        {tab === 'upload' && <Upload key={wsId} onUploaded={refresh} />}
        {tab === 'chat' && <Chat key={conv || 'new'} conversationId={conv} wsId={wsId} onActivity={refresh} />}
        {tab === 'kg' && <KnowledgeGraph key={wsId} onActivity={refresh} />}
        {tab === 'usage' && <Usage wsId={wsId} tick={tick} />}
      </main>
    </div>
  )
}

// ---------- 概览：文件 + 总摘要 + 对话 + 标签云 ----------
function Overview({ wsId, tick, onOpenConv, onNewConv, refresh }) {
  const [docs, setDocs] = useState([])
  const [convs, setConvs] = useState([])
  const [allSummary, setAllSummary] = useState('')
  const [sumAllBusy, setSumAllBusy] = useState(false)

  useEffect(() => {
    Promise.all([api.listDocuments(wsId), api.listConversations(wsId)])
      .then(([d, c]) => { setDocs(d); setConvs(c) }).catch(() => {})
  }, [wsId, tick])

  async function genAllSummary() {
    setSumAllBusy(true)
    try { const r = await api.summarizeAll(wsId); setAllSummary(r.summary || '') }
    catch (e) { alert('生成失败：' + e.message) }
    finally { setSumAllBusy(false) }
  }
  async function saveAllToKB() {
    try {
      const blob = new Blob([allSummary], { type: 'text/markdown' })
      const file = new File([blob], '知识库总摘要.md', { type: 'text/markdown' })
      await api.ingest(file, wsId)
      alert('已存入知识库')
      refresh()
    } catch (e) { alert('存入失败：' + e.message) }
  }
  async function delDoc(id, e) {
    e.stopPropagation(); if (!confirm('删除该文档？')) return
    await api.deleteDocument(id); refresh()
  }
  async function delConv(id, e) {
    e.stopPropagation(); if (!confirm('删除该对话？')) return
    await api.deleteConversation(id); refresh()
  }

  const allTags = [...new Set(docs.flatMap((d) => d.tags || []))].slice(0, 32)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">00</span>概览</div>
          <h1 className="title mt-8">知识库 <span className="it">overview</span></h1>
          <div className="sub">文档、对话与关键词标签。</div>
        </div>
      </div>

      {allTags.length > 0 && (
        <div className="tag-strip">
          <span className="eyebrow"><span className="num">∎</span>关键词</span>
          <div className="tags">{allTags.map((t) => <span className="tag" key={t}>{t}</span>)}</div>
        </div>
      )}

      <div className="mt-32">
        <div className="between" style={{ paddingBottom: 12, borderBottom: '1px solid var(--rule-2)' }}>
          <span className="eyebrow"><span className="num">∎</span>文档 ({docs.length})</span>
          <button className="btn ghost sm" onClick={genAllSummary} disabled={sumAllBusy || docs.length === 0}>
            {sumAllBusy ? '生成中…' : '生成总摘要'}
          </button>
        </div>

        {allSummary && (
          <div className="card mt-16">
            <div className="between">
              <div className="eyebrow"><span className="num">∎</span>知识库总摘要</div>
              <button className="btn gold sm" onClick={saveAllToKB}>存入知识库</button>
            </div>
            <div className="mt-16"><Markdown>{allSummary}</Markdown></div>
          </div>
        )}

        <div className="doc-list">
          {docs.length === 0 && <div className="tiny" style={{ padding: 16 }}>（空——去「上传」添加文件）</div>}
          {docs.map((d) => (
            <div className="doc-card2" key={d.id}>
              <div className="dc2-head" onClick={() => window.open(api.fileUrl(d.id), '_blank')}>
                <span className="dc2-name">{d.filename}</span>
                <span className="dc2-tags">{(d.tags || []).slice(0, 5).map((t) => <span className="tag" key={t}>{t}</span>)}</span>
                <span className="dc2-date">{(d.created_at || '').slice(0, 10)}</span>
                <button className="btn ghost sm" onClick={(e) => delDoc(d.id, e)}>删除</button>
              </div>
              <div className="dc2-summary">{d.summary || '（无摘要）'}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-32">
        <div className="between" style={{ paddingBottom: 12, borderBottom: '1px solid var(--rule-2)' }}>
          <span className="eyebrow"><span className="num">∎</span>对话记录 ({convs.length})</span>
          <button className="btn gold sm" onClick={onNewConv}>+ 新建对话</button>
        </div>
        <div className="doc-list">
          {convs.length === 0 && <div className="tiny" style={{ padding: 16 }}>（还没有对话）</div>}
          {convs.map((c) => (
            <div className="doc-row" key={c.id} onClick={() => onOpenConv(c.id)} style={{ cursor: 'pointer' }}>
              <div className="name">{c.title || '未命名对话'}<small>{c.n_msgs} 条消息</small></div>
              <div className="cat">{c.id.slice(0, 14)}</div>
              <div className="type">对话</div>
              <div className="n"><button className="btn ghost sm" onClick={(e) => delConv(c.id, e)}>删除</button></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------- 用量 ----------
function Usage({ wsId, tick }) {
  const [u, setU] = useState(null)
  const [docs, setDocs] = useState([])
  useEffect(() => {
    api.usage(wsId).then(setU).catch(() => {})
    api.listDocuments(wsId).then(setDocs).catch(() => {})
  }, [wsId, tick])
  if (!u) return <div className="page"><div className="tiny">载入中…</div></div>
  const byOp = u.by_operation || {}
  const unused = u.total_tokens === 0
  const stat = (label, v, sub) => (
    <div className="stat"><div className="k">{label}</div><div className="v">{v}<span className="unit">{sub}</span></div></div>
  )
  return (
    <div className="page">
      <div className="page-head"><div>
        <div className="eyebrow"><span className="num">04</span>用量</div>
        <h1 className="title mt-8">用量 <span className="it">ledger</span></h1>
        <div className="sub">token 消耗统计。</div>
      </div></div>
      {unused ? (
        <div className="card center" style={{ padding: 40 }}>
          <div className="serif italic" style={{ fontSize: 20, color: 'var(--ink-2)' }}>未使用</div>
          <div className="tiny mt-16">还没有问答或构建图谱。</div>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            {stat('总 token', u.total_tokens?.toLocaleString(), 'tok')}
            {stat('问答次数', byOp.chat?.calls || 0, '次')}
            {stat('每次问答', Math.round(u.avg_per_answer || 0), 'tok/次')}
            {stat('图谱构建', byOp.kg_build?.calls || 0, '次')}
          </div>
          <div className="stats-grid mt-16">
            {stat('每次建图', Math.round(u.avg_per_kg_build || 0), 'tok/次')}
            {stat('入库次数', byOp.ingest?.calls || 0, '次')}
            {stat('输入', u.tokens_in?.toLocaleString(), 'in')}
            {stat('输出', u.tokens_out?.toLocaleString(), 'out')}
          </div>
        </>
      )}
      <div className="mt-32">
        <div className="eyebrow" style={{ paddingBottom: 12, borderBottom: '1px solid var(--rule-2)' }}><span className="num">∎</span>文件清单 ({docs.length})</div>
        <div className="doc-list">
          {docs.map((d) => (
            <div className="doc-row" key={d.id} onClick={() => window.open(api.fileUrl(d.id), '_blank')} style={{ cursor: 'pointer' }}>
              <div className="name">{d.filename}<small>{d.summary?.slice(0, 60) || '（无摘要）'}</small></div>
              <div className="cat">{d.category || '—'}</div><div className="type">{d.doc_type}</div><div className="n">{d.n_chunks} 块</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
