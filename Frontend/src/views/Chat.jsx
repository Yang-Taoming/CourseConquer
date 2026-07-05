import { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'
import Markdown from '../components/Markdown.jsx'

const STEP_LABEL = { plan: '规划', retrieve: '检索', judge: '反思', multi_doc: '多文档', web: '联网', kg: '图谱', synthesize: '合成', memory: '记忆' }
const PROV_LABEL = { kb_full: '全部来自知识库', kb_partial: '部分来自知识库', web: '来自联网', model_only: '模型常识' }

function citationUrl(c) {
  const pos = c.position || {}
  const page = (pos.pages && pos.pages[0]) || null
  return api.fileUrl(c.doc_id, page)
}

function Message({ m }) {
  const [shown, setShown] = useState(m.pending ? 0 : (m.trace?.length || 0))
  useEffect(() => {
    if (!m.trace || m.pending) return
    if (shown >= m.trace.length) return
    const t = setTimeout(() => setShown((n) => n + 1), 320)
    return () => clearTimeout(t)
  }, [m.trace, m.pending, shown])
  const traceDone = m.trace && shown >= m.trace.length
  const showAnswer = m.answer && (!m.trace || traceDone)

  return (
    <div className={'msg ' + m.role}>
      <div className="who">{m.role === 'user' ? '你' : 'CourseMind'}</div>
      {m.role === 'user' ? (
        <div className="body user-body">{m.content}</div>
      ) : null}

      {m.trace && m.trace.length > 0 && (
        <div className="trace">
          {m.trace.slice(0, shown).map((t, i) => (
            <div className={'trace-step ' + t.step} key={i}>
              <span className="marker" />
              <span className="step-text"><span className="step-tag">{STEP_LABEL[t.step] || t.step}</span>{t.text}</span>
            </div>
          ))}
          {!traceDone && <div className="trace-step synthesize"><span className="marker" /><span className="step-text"><span className="spin" /> {m.pending ? '思考中…' : '…'}</span></div>}
        </div>
      )}
      {m.pending && !m.trace && <div className="body"><span className="spin" /> 思考与检索中…</div>}

      {showAnswer && m.role === 'assistant' && (
        <div className="body"><Markdown>{m.answer}</Markdown></div>
      )}
      {showAnswer && m.provenance && (
        <div className={'provenance ' + m.provenance}><span className="dot" /> {PROV_LABEL[m.provenance] || m.provenance}</div>
      )}
      {showAnswer && m.web_links?.length > 0 && (
        <div className="web-links">{m.web_links.map((l, i) => (
          <a key={i} href={l.url} target="_blank" rel="noreferrer">{l.title ? `↗ ${l.title}` : `↗ ${l.url}`}</a>
        ))}</div>
      )}
      {showAnswer && m.citations?.length > 0 && (
        <div className="citations">{m.citations.map((c) => (
          <a className="cite is-link" key={c.ref} href={citationUrl(c)} target="_blank" rel="noreferrer" title={`打开 ${c.filename} · ${c.location || '原文'}`}>
            <span className="ref">[{c.ref}]</span>{c.filename} · {c.location || '原文'}
          </a>
        ))}</div>
      )}
      {showAnswer && m.warnings?.length > 0 && <div className="warn">⚠ {m.warnings.join('；')}</div>}
    </div>
  )
}

export default function Chat({ conversationId, onActivity }) {
  const { workspace } = useWorkspace()
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [allowWeb, setAllowWeb] = useState(false)
  const [cid, setCid] = useState(conversationId || null)
  const [attach, setAttach] = useState(null)      // {filename, markdown}
  const [tool, setTool] = useState('chat')        // chat | gen
  const [genType, setGenType] = useState('image') // image/ppt/csv/doc/md
  const logRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => {
    setCid(conversationId || null); setHistory([])
    if (conversationId) {
      api.getConversation(conversationId).then((conv) => {
        if (conv?.messages) {
          setHistory(conv.messages.map((m) => {
            const meta = m.meta ? JSON.parse(m.meta) : {}
            if (m.role === 'assistant') return { role: 'assistant', answer: m.content, trace: meta.trace || [], provenance: meta.provenance, web_links: meta.web_links || [], citations: meta.citations || [], warnings: [] }
            return { role: 'user', content: m.content }
          }))
        }
      }).catch(() => {})
    }
  }, [conversationId])

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' }) }, [history])

  async function onAttach(file) {
    if (!file) return
    try {
      const p = await api.parse(file)
      setAttach({ filename: file.name, markdown: p.markdown_preview })
    } catch (e) { alert('解析附件失败：' + e.message) }
  }

  async function ask() {
    const q = input.trim()
    if ((!q && !attach) || busy) return
    const content = q + (attach ? `\n\n【附件：${attach.filename}】\n${attach.markdown}` : '')
    setInput(''); setAttach(null)
    // 生成工具：用户选定的类型，下载文件
    if (tool === 'gen') { await doGenerate(genType, q); return }
    const userMsg = { role: 'user', content }
    setHistory((h) => [...h, userMsg, { role: 'assistant', pending: true, answer: '', trace: null }])
    setBusy(true)
    try {
      let convId = cid
      if (!convId) { const c = await api.createConversation(workspace, q.slice(0, 20)); convId = c.id; setCid(convId) }
      const r = await api.chat({ question: content, workspace_id: workspace, conversation_id: convId, history: [], allow_web: allowWeb })
      setHistory((h) => { const copy = [...h]; copy[copy.length - 1] = { role: 'assistant', answer: r.answer, trace: r.trace || [], provenance: r.provenance, web_links: r.web_links || [], citations: r.citations || [], warnings: r.warnings || [], route: r.route, rounds: r.rounds, pending: false }; return copy })
      onActivity?.()
    } catch (e) {
      setHistory((h) => { const copy = [...h]; copy[copy.length - 1] = { role: 'assistant', answer: '请求失败：' + e.message, trace: [], pending: false }; return copy })
    } finally { setBusy(false) }
  }

  function onKeyDown(e) { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); ask() } }

  async function saveToKB() {
    if (!cid) { alert('还没有对话'); return }
    try { await api.saveConvToKB(cid); alert('已存入知识库') }
    catch (e) { alert('存入失败：' + e.message) }
  }

  async function doGenerate(kind, prompt) {
    if (!prompt?.trim()) { alert('请输入你想生成的内容'); return }
    setHistory((h) => [...h, { role: 'user', content: prompt }, { role: 'assistant', pending: true, answer: '', trace: null }])
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('kind', kind); fd.append('topic', prompt); fd.append('workspace_id', workspace)
      const resp = await fetch(api.generateUrl(), { method: 'POST', body: fd })
      if (!resp.ok) throw new Error('生成失败')
      const blob = await resp.blob()
      const cd = resp.headers.get('content-disposition') || ''
      const m = cd.match(/filename="?([^"]+)"?/); const fname = m ? decodeURIComponent(m[1]) : '生成结果'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = fname; a.click()
      URL.revokeObjectURL(url)
      setHistory((h) => { const copy = [...h]; copy[copy.length - 1] = { role: 'assistant', answer: `🛠️ 已生成 **${fname}**，已开始下载。`, trace: [], pending: false, provenance: 'model_only' }; return copy })
    } catch (e) {
      setHistory((h) => { const copy = [...h]; copy[copy.length - 1] = { role: 'assistant', answer: '生成失败：' + e.message, trace: [], pending: false }; return copy })
    } finally { setBusy(false) }
  }

  return (
    <div className="chat-shell">
      <div className="chat-toolbar">
        <button className="btn ghost sm" onClick={saveToKB} disabled={!cid}>存入知识库</button>
        <span className="tiny" style={{ marginLeft: 'auto' }}>{tool === 'gen' ? '生成模式：用自然语言描述你要生成什么' : '对话模式'}</span>
      </div>

      <div className="chat-log" ref={logRef}>
        {history.length === 0 && (
          <div className="card center" style={{ margin: 'auto', padding: 48, maxWidth: 480 }}>
            <div className="serif italic" style={{ fontSize: 22, color: 'var(--ink-2)' }}>提个问题开始对话——</div>
            <div className="tiny mt-16">支持公式、代码、Markdown；可上传附件；切到「生成」用自然语言生成图片/PPT/文档/代码</div>
          </div>
        )}
        {history.map((m, i) => <Message key={i} m={m} />)}
      </div>

      <div className="chat-bottom">
        {attach && (
          <div className="attach-chip">📎 {attach.filename} <button onClick={() => setAttach(null)}>×</button></div>
        )}
        <div className="chat-input">
          <button className="btn ghost sm" onClick={() => fileRef.current?.click()} title="上传附件（解析后随问题发送）">📎</button>
          <input ref={fileRef} type="file" style={{ display: 'none' }} onChange={(e) => onAttach(e.target.files?.[0])} />
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
            placeholder={tool === 'gen' ? '用自然语言描述，如「画一张二叉搜索树的示意图」「做个排序算法的PPT」…' : '输入问题…（⌘/Ctrl+Enter 发送）'} />
          <button className="btn" onClick={ask} disabled={busy || (!input.trim() && !attach)}>
            {tool === 'gen' ? '生成' : '发送'}
          </button>
        </div>
        <div className="chat-tools">
          <div className="tool-switch">
            <button className={'tool-chip' + (tool === 'chat' ? ' active' : '')} onClick={() => setTool('chat')}>💬 对话</button>
            <button className={'tool-chip' + (tool === 'gen' ? ' active' : '')} onClick={() => setTool('gen')}>🛠️ 生成</button>
          </div>
          <label className="tiny"><input type="checkbox" checked={allowWeb} onChange={(e) => setAllowWeb(e.target.checked)} disabled={tool === 'gen'} /> 允许联网</label>
        </div>
        {tool === 'gen' && (
          <div className="gen-types">
            <span className="tiny">类型：</span>
            {[
              { k: 'image', label: '图片' }, { k: 'ppt', label: 'PPT' },
              { k: 'csv', label: 'CSV' }, { k: 'doc', label: 'DOCX' }, { k: 'md', label: 'Markdown' },
            ].map((t) => (
              <button key={t.k} className={'tool-chip sm' + (genType === t.k ? ' active' : '')} onClick={() => setGenType(t.k)}>
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
