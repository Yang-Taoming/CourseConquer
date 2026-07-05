import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import CardSwap, { Card } from '../components/CardSwap.jsx'

// 每页的背景色调（动态切换）
const BG = [
  { bg: 'linear-gradient(170deg,#f3ead2 0%,#ece0c0 55%,#e3d5af 100%)', accent: '#7a3d12' },
  { bg: 'linear-gradient(170deg,#f0e4c8 0%,#e6d6a8 55%,#d8c188 100%)', accent: '#8a5a1a' },
  { bg: 'linear-gradient(170deg,#f5ecd6 0%,#ece1b4 55%,#ddd0a0 100%)', accent: '#6a4a2a' },
  { bg: 'linear-gradient(170deg,#efe2c2 0%,#e2d09a 55%,#cdb878 100%)', accent: '#7a3d12' },
]

const PAGES = ['首页', '捕获', '蒸馏', '复用']

export default function Landing() {
  const [page, setPage] = useState(0)
  const navigate = useNavigate()
  const dragRef = useRef(null)
  const wheelLock = useRef(false)

  // 拖拽翻页：向右或向下拖 → 下一页；向左或向上 → 上一页
  function onPointerDown(e) {
    dragRef.current = { x: e.clientX, y: e.clientY }
  }
  function onPointerUp(e) {
    if (!dragRef.current) return
    const dx = e.clientX - dragRef.current.x
    const dy = e.clientY - dragRef.current.y
    const thresh = 60
    if ((dx > thresh || dy > thresh) && page < PAGES.length - 1) setPage(page + 1)
    else if ((dx < -thresh || dy < -thresh) && page > 0) setPage(page - 1)
    dragRef.current = null
  }

  // 滚轮 / 键盘也能翻页
  useEffect(() => {
    const onKey = (e) => {
      if (['ArrowDown', 'ArrowRight', ' '].includes(e.key) && page < PAGES.length - 1) setPage(page + 1)
      if (['ArrowUp', 'ArrowLeft'].includes(e.key) && page > 0) setPage(page - 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [page])
  // 滚轮翻页：加锁，一次滚动只翻一页，翻页动画期间忽略后续滚动
  const onWheel = (e) => {
    if (wheelLock.current) return
    if (Math.abs(e.deltaY) < 20) return
    wheelLock.current = true
    if (e.deltaY > 0) setPage((p) => Math.min(p + 1, PAGES.length - 1))
    else setPage((p) => Math.max(p - 1, 0))
    setTimeout(() => { wheelLock.current = false }, 900)
  }

  const cur = BG[page]

  return (
    <div
      className="landing"
      style={{ background: cur.bg, transition: 'background 0.8s ease' }}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onWheel={onWheel}
    >
      {/* 顶部刊头 */}
      <div className="landing-top">
        <span className="eyebrow"><span className="num">∎</span>Course Conquer · 课程知识库助手</span>
        <span className="tiny">拖拽 / 滚轮 / 方向键翻页</span>
      </div>

      {/* 页面指示器 */}
      <div className="page-dots">
        {PAGES.map((_, i) => (
          <span key={i} className={'dot' + (i === page ? ' active' : '')} onClick={() => setPage(i)} />
        ))}
      </div>

      {/* 各页内容 */}
      <div className="landing-stage" style={{ transform: `translateY(-${page * 100}vh)`, transition: 'transform 0.7s cubic-bezier(.7,0,.2,1)' }}>
        {/* 0 首页 */}
        <section className="lp" style={{ background: BG[0].bg }}>
          <div className="lp-hero">
            <h1>Course<span className="am">Mind</span><br /><span className="it">conquer</span> your courses.</h1>
            <p className="lp-lede">把课件、代码、表格、图片喂进去，让碎片化的学习与科研资料自动沉淀、可问可答、可成图。</p>
            <button className="btn gold" onClick={() => navigate('/workspaces')}>开始上传 →</button>
            <div className="lp-hint">点击进入知识库 · 或向下拖拽看看介绍</div>
          </div>
        </section>

        {/* 1 捕获 */}
        <section className="lp split" style={{ background: BG[1].bg }}>
          <div className="lp-left">
            <div className="eyebrow"><span className="num">01</span>捕获 · capture</div>
            <h2>任意文件，<br /><span className="it">一次解析</span>。</h2>
            <p>支持文本、代码、PDF、Office、图片。共用解析器把每类文件归一为 Markdown——图片走视觉模型 OCR，扫描页自动识别，代码保留语言标签，表格转为结构化文本。</p>
            <p className="muted">解析只做一次；每个分块带<strong>页码 / 行号</strong>，检索精确定位。</p>
          </div>
          <div className="lp-right">
            <CardSwap width={560} height={340} delay={3800}>
              <Card><div className="card-eyebrow">PDF</div><div className="card-title">混合解析</div><div className="card-body">文字层优先，扫描页渲染成图走 OCR。</div></Card>
              <Card><div className="card-eyebrow">IMAGE</div><div className="card-title">视觉 OCR</div><div className="card-body">qwen-vl-max 逐字转写 + 图表理解。</div></Card>
              <Card><div className="card-eyebrow">CODE</div><div className="card-title">代码入库</div><div className="card-body">.py .c .cpp .md 保留语言标签与行号。</div></Card>
              <Card><div className="card-eyebrow">OFFICE</div><div className="card-title">表格归一</div><div className="card-body">docx/pptx/xlsx/csv → Markdown 表格。</div></Card>
            </CardSwap>
          </div>
        </section>

        {/* 2 蒸馏 */}
        <section className="lp split" style={{ background: BG[2].bg }}>
          <div className="lp-left">
            <div className="eyebrow"><span className="num">02</span>蒸馏 · distill</div>
            <h2>摘要标签，<br /><span className="it">向量入库</span>。</h2>
            <p>入库时自动生成摘要、关键词标签与学科分类。bge-m3 向量编码让语义相近的内容天然聚拢。</p>
            <p className="muted">知识图谱按需而建——按钮触发，跨文档同名概念自动合并，复杂度/约束折叠进节点属性。</p>
          </div>
          <div className="lp-right">
            <div className="lp-card">
              <div className="card-eyebrow">ALG26 · 二叉搜索树</div>
              <div className="lp-tags"><span>二叉搜索树</span><span>BST</span><span>查找</span><span>O(log n)</span></div>
              <div className="lp-summ">二叉搜索树满足左子树小于根、右子树大于根，查找/插入/删除平均 O(log n)…</div>
            </div>
          </div>
        </section>

        {/* 3 复用 */}
        <section className="lp split" style={{ background: BG[3].bg }}>
          <div className="lp-left">
            <div className="eyebrow"><span className="num">03</span>复用 · reuse</div>
            <h2>多轮检索，<br /><span className="it">带引用作答</span>。</h2>
            <p>规划器拆解任务：单文档检索 / 多文档对比 / 联网 / 代码解析。裁判判断「够不够」，不够再搜一轮。</p>
            <p className="muted">答案带文件·页码引用，点开直接跳转；并点出背后的知识点。来源诚实标注：知识库 / 部分知识库 / 模型常识 / 联网。</p>
          </div>
          <div className="lp-right">
            <button className="btn gold big" onClick={() => navigate('/workspaces')}>进入知识库 →</button>
          </div>
        </section>
      </div>
    </div>
  )
}
