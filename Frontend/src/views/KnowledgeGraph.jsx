import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'

const TYPE_COLOR = {
  Course: '#8a6a2a', Chapter: '#7a5a1a', Concept: '#5a7a4a', Algorithm: '#0891b2',
  Method: '#0891b2', Theorem: '#9a4a4a', Formula: '#6a5a3a', Term: '#7a6a5a',
  Example: '#4a8a7a', Tool: '#9a7a4a', Person: '#8a4a6a',
  Problem: '#ea580c', Complexity: '#7c3aed', Constraint: '#dc2626', Function: '#4f46e5',
}

// 简单力导向布局（无依赖）：节点斥力 + 边弹簧 + 向心，迭代到稳定。
function forceLayout(nodes, edges, W, H, iters = 320) {
  const pos = {}
  const cx = W / 2, cy = H / 2
  const n = nodes.length
  // 初始：圆环随机分布，避免重叠
  nodes.forEach((node, i) => {
    const ang = (i / Math.max(1, n)) * Math.PI * 2
    const r = Math.min(W, H) * 0.32 * (0.6 + Math.random() * 0.4)
    pos[node.id] = { x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang), vx: 0, vy: 0 }
  })
  const adj = {}
  edges.forEach((e) => {
    adj[e.source] = adj[e.source] || []; adj[e.source].push(e.target)
    adj[e.target] = adj[e.target] || []; adj[e.target].push(e.source)
  })
  const k_rep = 9000, k_spring = 0.04, L = 130, damp = 0.82
  for (let it = 0; it < iters; it++) {
    // 斥力
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const a = pos[nodes[i].id], b = pos[nodes[j].id]
        let dx = b.x - a.x, dy = b.y - a.y
        let d2 = dx * dx + dy * dy || 0.01
        let d = Math.sqrt(d2)
        const f = k_rep / d2
        const fx = (dx / d) * f, fy = (dy / d) * f
        a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy
      }
    }
    // 弹簧
    for (const e of edges) {
      const a = pos[e.source], b = pos[e.target]
      if (!a || !b) continue
      let dx = b.x - a.x, dy = b.y - a.y
      let d = Math.sqrt(dx * dx + dy * dy) || 0.01
      const f = k_spring * (d - L)
      const fx = (dx / d) * f, fy = (dy / d) * f
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy
    }
    // 向心 + 阻尼 + 应用
    for (const id in pos) {
      const p = pos[id]
      p.vx += (cx - p.x) * 0.008
      p.vy += (cy - p.y) * 0.008
      p.vx *= damp; p.vy *= damp
      p.x += p.vx; p.y += p.vy
      p.x = Math.max(40, Math.min(W - 40, p.x))
      p.y = Math.max(40, Math.min(H - 40, p.y))
    }
  }
  return pos
}

export default function KnowledgeGraph() {
  const { workspace } = useWorkspace()
  const [data, setData] = useState({ nodes: [], edges: [], view: '', stats: {}, schema: {} })
  const [busy, setBusy] = useState(false)
  const [buildResult, setBuildResult] = useState(null)
  const [err, setErr] = useState('')
  const [selected, setSelected] = useState(null)
  const [hover, setHover] = useState(null)
  const [tf, setTf] = useState({ x: 0, y: 0, k: 1 })  // pan/zoom transform
  const dragRef = useRef(null)
  const svgRef = useRef(null)

  const W = 1100, H = 640

  const load = useCallback(async () => {
    try {
      const g = await api.kgGraph(workspace)
      setData(g)
      setSelected(null); setTf({ x: 0, y: 0, k: 1 })
    } catch (e) {
      setErr('读取图谱失败：' + e.message)
    }
  }, [workspace])

  useEffect(() => { load() }, [load])

  async function build() {
    setBusy(true); setErr('')
    try {
      const r = await api.kgBuild(workspace)
      setBuildResult(r); await load()
    } catch (e) {
      setErr('构建失败：' + e.message)
    } finally {
      setBusy(false)
    }
  }

  const pos = useMemo(
    () => forceLayout(data.nodes, data.edges, W, H),
    [data.nodes, data.edges],
  )
  const byId = useMemo(() => Object.fromEntries(data.nodes.map((n) => [n.id, n])), [data.nodes])
  const neighbors = useMemo(() => {
    const m = {}
    data.edges.forEach((e) => {
      m[e.source] = m[e.source] || new Set(); m[e.source].add(e.target)
      m[e.target] = m[e.target] || new Set(); m[e.target].add(e.source)
    })
    return m
  }, [data.edges])
  const types = useMemo(() => [...new Set(data.nodes.map((n) => n.type))].sort(), [data.nodes])

  const focusId = selected || hover
  const isDim = (id) => focusId && focusId !== id && !(neighbors[focusId] && neighbors[focusId].has(id))
  const isDimEdge = (e) => focusId && e.source !== focusId && e.target !== focusId

  // pan/zoom
  function onWheel(e) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setTf((t) => ({ ...t, k: Math.max(0.3, Math.min(3, t.k * delta)) }))
  }
  function onPointerDown(e) {
    if (e.target.tagName !== 'rect' && e.target.tagName !== 'svg') return
    dragRef.current = { x: e.clientX, y: e.clientY, tx: tf.x, ty: tf.y }
    e.target.setPointerCapture?.(e.pointerId)
  }
  function onPointerMove(e) {
    if (!dragRef.current) return
    setTf((t) => ({ ...t, x: dragRef.current.tx + (e.clientX - dragRef.current.x), y: dragRef.current.ty + (e.clientY - dragRef.current.y) }))
  }
  function onPointerUp() { dragRef.current = null }

  function resetView() { setTf({ x: 0, y: 0, k: 1 }) }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">03</span>知识图谱 · NebulaGraph 风格</div>
          <h1 className="title mt-8">图谱 <span className="it">connect</span></h1>
          <div className="sub">按需构建——NebulaGraph 风格属性图，属性折叠为节点详情，结构边可视化。点击节点看邻居，滚轮缩放，拖拽平移。</div>
        </div>
        <div className="meta">
          <button className="btn gold" onClick={build} disabled={busy}>
            {busy ? '构建中…' : data.nodes.length ? '重建图谱' : '构建图谱 →'}
          </button>
        </div>
      </div>

      {(buildResult || err) && (
        <div className="row gap-16" style={{ marginBottom: 16 }}>
          {buildResult && (
            <span className="ok">
              ✓ 新增 {buildResult.nodes_added} 节点 / {buildResult.edges_added} 边 · 共 {buildResult.nodes_total} / {buildResult.edges_total}
            </span>
          )}
          {err && <span className="warn">⚠ {err}</span>}
        </div>
      )}

      <div className="kg-wrap">
        <div className="kg-canvas" style={{ position: 'relative' }}>
          {data.nodes.length === 0 ? (
            <div className="kg-empty">
              <div className="big">图谱尚未构建</div>
              <div className="tiny">点击右上「构建图谱」，从已入库文档抽取实体与关系</div>
            </div>
          ) : (
            <svg
              ref={svgRef}
              viewBox={`0 0 ${W} ${H}`}
              onWheel={onWheel}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              style={{ touchAction: 'none', cursor: 'grab', background: 'var(--paper)' }}
            >
              <rect x={0} y={0} width={W} height={H} fill="transparent" />
              <g transform={`translate(${tf.x},${tf.y}) scale(${tf.k})`}>
                {/* 边 */}
                {data.edges.map((e) => {
                  const s = pos[e.source], t = pos[e.target]
                  if (!s || !t) return null
                  const dim = isDimEdge(e)
                  const hl = focusId && (e.source === focusId || e.target === focusId)
                  return (
                    <line
                      key={e.id}
                      className="kg-edge"
                      x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                      stroke={hl ? 'var(--gold)' : 'var(--rule-2)'}
                      strokeWidth={hl ? 2 : 1}
                      opacity={dim ? 0.12 : 0.7}
                    />
                  )
                })}
                {/* 节点 */}
                {data.nodes.map((node) => {
                  const p = pos[node.id]
                  if (!p) return null
                  const r = 6 + Math.min(16, (node.mentions || 1) * 1.8)
                  const col = TYPE_COLOR[node.type] || '#7a6a5a'
                  const dim = isDim(node.id)
                  const sel = selected === node.id
                  return (
                    <g
                      key={node.id}
                      className="kg-node"
                      transform={`translate(${p.x},${p.y})`}
                      opacity={dim ? 0.18 : 1}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setHover(node.id)}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => setSelected(selected === node.id ? null : node.id)}
                    >
                      <circle r={r} fill={col} fillOpacity={0.85} stroke={sel ? 'var(--ink)' : 'var(--ink)'} strokeWidth={sel ? 3 : 1} />
                      <text x={r + 5} y={4} fill="var(--ink)" fontWeight={sel ? 600 : 400} fontSize={11}>
                        {node.name}
                      </text>
                    </g>
                  )
                })}
              </g>
            </svg>
          )}
          {data.nodes.length > 0 && (
            <button className="btn ghost sm" onClick={resetView} style={{ position: 'absolute', top: 12, right: 12 }}>
              重置视图
            </button>
          )}
          {data.stats && (
            <div className="tiny" style={{ position: 'absolute', bottom: 10, left: 14, letterSpacing: '0.08em' }}>
              {data.stats.vertices ?? data.nodes.length} 顶点 · {data.stats.edges ?? data.edges.length} 边
              {data.stats.collapsed_property_facts ? ` · 折叠 ${data.stats.collapsed_property_facts} 属性` : ''}
              {' · '}view: {data.view}
            </div>
          )}
        </div>

        <div className="kg-side">
          <div className="card">
            <div className="eyebrow"><span className="num">∎</span>实体类型</div>
            <div className="legend mt-16">
              {types.map((t) => (
                <div className="legend-item" key={t}>
                  <span className="legend-dot" style={{ background: TYPE_COLOR[t] || '#7a6a5a' }} />
                  {t}
                </div>
              ))}
              {types.length === 0 && <span className="tiny">（无）</span>}
            </div>
          </div>

          {selected && byId[selected] ? (
            <div className="card mt-16">
              <div className="between">
                <div className="eyebrow"><span className="num">∎</span>选中节点</div>
                <span className="tag gold">{byId[selected].type}</span>
              </div>
              <h3 className="mt-8">{byId[selected].name}</h3>
              <div className="tiny mt-8">
                mentions {byId[selected].mentions} · {byId[selected].doc_ids?.length || 0} 文档
              </div>
              {byId[selected].property_values && Object.keys(byId[selected].property_values).length > 0 && (
                <div className="mt-16">
                  <div className="tiny" style={{ letterSpacing: '0.16em' }}>属性（折叠）</div>
                  {Object.entries(byId[selected].property_values).map(([k, v]) => (
                    <div key={k} className="mt-8" style={{ fontSize: 13 }}>
                      <span className="tiny" style={{ color: 'var(--gold)' }}>{k}: </span>
                      <span>{Array.isArray(v) ? v.join('、') : String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
              {byId[selected].description && (
                <p className="mt-16" style={{ fontFamily: 'var(--serif)', fontSize: 14, color: 'var(--ink-2)', whiteSpace: 'pre-wrap' }}>
                  {byId[selected].description}
                </p>
              )}
              {neighbors[selected] && (
                <div className="tiny mt-16" style={{ letterSpacing: '0.16em' }}>
                  邻居：{[...neighbors[selected]].map((id) => byId[id]?.name).filter(Boolean).join('、') || '无'}
                </div>
              )}
            </div>
          ) : (
            <div className="card mt-16">
              <div className="eyebrow"><span className="num">∎</span>提示</div>
              <p className="mt-16" style={{ fontFamily: 'var(--serif)', fontSize: 14, color: 'var(--ink-2)' }}>
                点击节点查看详情与邻居；滚轮缩放；拖拽空白处平移。复杂度/约束等已折叠进节点属性。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
