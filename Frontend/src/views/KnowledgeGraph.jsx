import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'

const TYPE_COLOR = {
  Course: '#8a6a2a', Chapter: '#7a5a1a', Concept: '#5a7a4a', Algorithm: '#0891b2',
  Method: '#0891b2', Theorem: '#9a4a4a', Formula: '#6a5a3a', Term: '#7a6a5a',
  Example: '#4a8a7a', Tool: '#9a7a4a', Person: '#8a4a6a',
  Problem: '#ea580c', Complexity: '#7c3aed', Constraint: '#dc2626', Function: '#4f46e5',
}

// 同心圆辐射布局（按度数排圈，节点均匀分布在环上）——彻底避免四角堆叠。
function forceLayout(nodes, edges, W, H) {
  const pos = {}
  const cx = W / 2, cy = H / 2
  // 计算每个节点的度数
  const deg = {}
  nodes.forEach((n) => { deg[n.id] = 0 })
  edges.forEach((e) => { deg[e.source] = (deg[e.source] || 0) + 1; deg[e.target] = (deg[e.target] || 0) + 1 })
  // 按度数降序（度数高的靠中心）
  const sorted = [...nodes].sort((a, b) =>
    (deg[b.id] || 0) - (deg[a.id] || 0) || (b.mentions || 0) - (a.mentions || 0))
  // 分环：ring0 中心 1 个；ring1 8；ring2 16；ring3 24；ring4 剩余
  const rings = [[], [], [], [], []]
  const caps = [1, 8, 16, 24, 9999]
  sorted.forEach((n) => {
    for (let i = 0; i < rings.length; i++) {
      if (rings[i].length < caps[i]) { rings[i].push(n); break }
    }
  })
  const radii = [0, Math.min(W, H) * 0.16, Math.min(W, H) * 0.30, Math.min(W, H) * 0.42, Math.min(W, H) * 0.52]
  rings.forEach((ring, ri) => {
    const r = radii[ri]
    const cnt = ring.length
    ring.forEach((n, i) => {
      // 起始角度错开，让各环视觉上对齐
      const ang = (i / Math.max(1, cnt)) * Math.PI * 2 + (ri % 2) * (Math.PI / cnt)
      pos[n.id] = { x: cx + r * Math.cos(ang), y: cy + r * Math.sin(ang) }
    })
  })
  return pos
}

export default function KnowledgeGraph({ onActivity }) {
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
      onActivity?.()
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
        {/* 缩放控件放在画布外，避免与节点重合 */}
        {data.nodes.length > 0 && (
          <div className="kg-controls-bar">
            <button className="btn ghost sm" onClick={() => setTf((t) => ({ ...t, k: Math.min(3, t.k * 1.2) }))}>＋ 放大</button>
            <button className="btn ghost sm" onClick={() => setTf((t) => ({ ...t, k: Math.max(0.3, t.k / 1.2) }))}>－ 缩小</button>
            <button className="btn ghost sm" onClick={resetView}>重置</button>
            <span className="tiny" style={{ marginLeft: 'auto' }}>
              {data.stats?.vertices ?? data.nodes.length} 顶点 · {data.stats?.edges ?? data.edges.length} 边
            </span>
          </div>
        )}

        {/* 画布 + 右侧实体类型 */}
        <div className="kg-main">
          <div className="kg-canvas">
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
                  {data.edges.map((e) => {
                    const s = pos[e.source], t = pos[e.target]
                    if (!s || !t) return null
                    const dim = isDimEdge(e)
                    const hl = focusId && (e.source === focusId || e.target === focusId)
                    return (
                      <line key={e.id} className="kg-edge" x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                        stroke={hl ? 'var(--gold)' : 'var(--rule-2)'} strokeWidth={hl ? 2 : 1}
                        opacity={dim ? 0.12 : 0.7} />
                    )
                  })}
                  {data.nodes.map((node) => {
                    const p = pos[node.id]
                    if (!p) return null
                    const r = 6 + Math.min(16, (node.mentions || 1) * 1.8)
                    const col = TYPE_COLOR[node.type] || '#7a6a5a'
                    const dim = isDim(node.id)
                    const sel = selected === node.id
                    return (
                      <g key={node.id} className="kg-node" transform={`translate(${p.x},${p.y})`}
                        opacity={dim ? 0.18 : 1} style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHover(node.id)} onMouseLeave={() => setHover(null)}
                        onClick={() => setSelected(selected === node.id ? null : node.id)}>
                        <circle r={r} fill={col} fillOpacity={0.85} stroke="var(--ink)" strokeWidth={sel ? 3 : 1} />
                        <text x={r + 5} y={4} fill="var(--ink)" fontWeight={sel ? 600 : 400} fontSize={11}>{node.name}</text>
                      </g>
                    )
                  })}
                </g>
              </svg>
            )}
          </div>

          <aside className="kg-legend">
            <div className="eyebrow"><span className="num">∎</span>实体类型</div>
            <div className="legend mt-16">
              {types.map((t) => (
                <div className="legend-item" key={t}>
                  <span className="legend-dot" style={{ background: TYPE_COLOR[t] || '#7a6a5a' }} />{t}
                </div>
              ))}
              {types.length === 0 && <span className="tiny">（无）</span>}
            </div>
          </aside>
        </div>

        {/* 选中节点：画布正下方，整宽，不偏移 */}
        {selected && byId[selected] && (
          <div className="kg-selected">
            <div className="between">
              <div className="eyebrow"><span className="num">∎</span>选中节点</div>
              <div className="row gap-8">
                <span className="tag gold">{byId[selected].type}</span>
                <button className="kg-close" onClick={() => setSelected(null)}>×</button>
              </div>
            </div>
            <h3 className="mt-8">{byId[selected].name}</h3>
            <div className="tiny mt-8">mentions {byId[selected].mentions} · {byId[selected].doc_ids?.length || 0} 文档</div>
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
        )}
      </div>
    </div>
  )
}
