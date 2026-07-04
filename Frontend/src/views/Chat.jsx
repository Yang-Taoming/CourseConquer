import { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'

const STEP_LABEL = {
  plan: '规划', retrieve: '检索', judge: '裁判', multi_doc: '多文档',
  web: '联网', kg: '图谱', synthesize: '合成',
}
const PROV_LABEL = {
  kb_full: '全部来自知识库', kb_partial: '部分来自知识库',
  web: '来自联网', model_only: '模型常识',
}

function citationUrl(c) {
  const pos = c.position || {}
  const page = (pos.pages && pos.pages[0]) || null
  return api.fileUrl(c.doc_id, page)
}

function Message({ m }) {
  // 动画：逐步揭示 trace 步骤
  const [shown, setShown] = useState(m.pending ? 0 : (m.trace?.length || 0))
  useEffect(() => {
    if (!m.trace || m.pending) return
    if (shown >= m.trace.length) return
    const t = setTimeout(() => setShown((n) => n + 1), 360)
    return () => clearTimeout(t)
  }, [m.trace, m.pending, shown])

  const traceDone = m.trace && shown >= m.trace.length
  const showAnswer = m.answer && (!m.trace || traceDone)

  return (
    <div className={'msg ' + m.role}>
      <div className="who">{m.role === 'user' ? '你' : 'CourseMind'}</div>

      {m.trace && m.trace.length > 0 && (
        <div className="trace">
          {m.trace.slice(0, shown).map((t, i) => (
            <div className={'trace-step ' + t.step} key={i}>
              <span className="marker" />
              <span className="step-text">
                <span className="step-tag">{STEP_LABEL[t.step] || t.step}</span>
                {t.text}
              </span>
            </div>
          ))}
          {!traceDone && (
            <div className="trace-step synthesize">
              <span className="marker" />
              <span className="step-text"><span className="spin" /> {m.pending ? '思考中…' : '…'}</span>
            </div>
          )}
        </div>
      )}

      {m.pending && !m.trace && (
        <div className="body"><span className="spin" /> 思考与检索中…</div>
      )}

      {showAnswer && <div className="body">{m.answer}</div>}

      {showAnswer && m.provenance && (
        <div className={'provenance ' + m.provenance}>
          <span className="dot" /> {PROV_LABEL[m.provenance] || m.provenance}
        </div>
      )}

      {showAnswer && m.web_links?.length > 0 && (
        <div className="web-links">
          {m.web_links.map((l, i) => (
            <a key={i} href={l.url} target="_blank" rel="noreferrer">
              {l.title ? `↗ ${l.title}` : `↗ ${l.url}`}
            </a>
          ))}
        </div>
      )}

      {showAnswer && m.citations?.length > 0 && (
        <div className="citations">
          {m.citations.map((c) => (
            <a
              className="cite is-link"
              key={c.ref}
              href={citationUrl(c)}
              target="_blank"
              rel="noreferrer"
              title={`打开 ${c.filename} · ${c.location || '原文'}`}
            >
              <span className="ref">[{c.ref}]</span>
              {c.filename} · {c.location || '原文'}
            </a>
          ))}
        </div>
      )}

      {showAnswer && m.warnings?.length > 0 && (
        <div className="warn">⚠ {m.warnings.join('；')}</div>
      )}
    </div>
  )
}

export default function Chat() {
  const { workspace } = useWorkspace()
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [allowWeb, setAllowWeb] = useState(false)
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [history])

  async function ask() {
    const q = input.trim()
    if (!q || busy) return
    setInput('')
    const userMsg = { role: 'user', content: q }
    const pendingMsg = { role: 'assistant', pending: true, answer: '', trace: null }
    setHistory((h) => [...h, userMsg, pendingMsg])
    setBusy(true)
    try {
      const hist = [...history, userMsg].map((m) => ({ role: m.role, content: m.content }))
      const r = await api.chat({ question: q, workspace_id: workspace, history: hist, allow_web: allowWeb })
      setHistory((h) => {
        const copy = [...h]
        copy[copy.length - 1] = {
          role: 'assistant',
          answer: r.answer,
          trace: r.trace || [],
          provenance: r.provenance,
          web_links: r.web_links || [],
          citations: r.citations || [],
          warnings: r.warnings || [],
          route: r.route,
          rounds: r.rounds,
          pending: false,
        }
        return copy
      })
    } catch (e) {
      setHistory((h) => {
        const copy = [...h]
        copy[copy.length - 1] = { role: 'assistant', answer: '请求失败：' + e.message, trace: [], pending: false }
        return copy
      })
    } finally {
      setBusy(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); ask() }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">02</span>知识问答</div>
          <h1 className="title mt-8">问答 <span className="it">inquire</span></h1>
          <div className="sub">规划→多轮检索→带引用作答。思考过程实时展示：在看哪个文档、发现了什么、在对比还是联网。</div>
        </div>
        <div className="meta">
          <div className="eyebrow">工作区</div>
          <div className="serif italic mt-8" style={{ fontSize: 18 }}>{workspace}</div>
        </div>
      </div>

      <div className="chat-wrap">
        <div className="chat-log" ref={logRef}>
          {history.length === 0 && (
            <div className="card center" style={{ padding: 48 }}>
              <div className="serif italic" style={{ fontSize: 22, color: 'var(--ink-2)' }}>
                提个问题开始对话——
              </div>
              <div className="tiny mt-16">例如：为什么 KMP 搜索时文本指针不需要回退？背后的知识点是什么？</div>
            </div>
          )}
          {history.map((m, i) => <Message key={i} m={m} />)}
        </div>

        <div>
          <div className="chat-input">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="输入你的问题…（⌘/Ctrl + Enter 发送）"
            />
            <button className="btn" onClick={ask} disabled={busy || !input.trim()}>
              发送
            </button>
          </div>
          <div className="chat-options mt-8">
            <label>
              <input type="checkbox" checked={allowWeb} onChange={(e) => setAllowWeb(e.target.checked)} />
              允许联网搜索
            </label>
            <span className="tiny">点击引用可打开原文件；PDF 自动跳到对应页</span>
          </div>
        </div>
      </div>
    </div>
  )
}
