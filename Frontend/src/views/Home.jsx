import { Link } from 'react-router-dom'

function Hero() {
  return (
    <section className="hero">
      <div className="hero-top">
        <span className="eyebrow"><span className="num">01</span>课程知识库智能助手</span>
        <span className="issue">Vol. 01 — Capture, Distill, Reuse.</span>
      </div>

      <h1>
        Course<span className="am">Mind</span>
        <br />
        <span className="it">conquer</span> your courses.
      </h1>

      <div className="hero-lede">
        <p>
          一个为学习与科研碎片信息打造的轻量知识库——上传课件、代码、表格、图片，
          自动摘要与标签，沉淀为可检索、可问答、可成图的个人课程仓库。
        </p>
        <div className="cta">
          <Link to="/upload" className="btn">开始上传 →</Link>
          <Link to="/chat" className="btn ghost">进入问答</Link>
        </div>
      </div>
    </section>
  )
}

function Section({ idx, title, children }) {
  return (
    <section className="editorial">
      <div className="section-head">
        <span className="marker">— {idx}</span>
        <h2>{title}</h2>
      </div>
      <div className="section-body">
        <span className="gap" />
        <div>{children[0]}</div>
        <div>{children[1]}</div>
      </div>
    </section>
  )
}

function Closing() {
  return (
    <footer className="closing">
      <div className="top">
        <span className="eyebrow"><span className="num">∎</span>联系方式</span>
        <span className="eyebrow" style={{ color: '#8a7c63' }}>END OF ISSUE 01</span>
      </div>

      <div className="mid">
        <h2>
          让碎片<br />
          <span className="it">归位</span>。
        </h2>
        <div className="contacts">
          <div>
            <div className="k">项目</div>
            <div className="v">Course Conquer<br />24h Hackathon Build</div>
          </div>
          <div>
            <div className="k">联系</div>
            <div className="v">hello@courseconquer.cn<br />+86 010 0000 0000</div>
          </div>
          <div>
            <div className="k">技术栈</div>
            <div className="v">React · Vite · FastAPI<br />DeepSeek · bge-m3 · qwen-vl</div>
          </div>
        </div>
      </div>

      <div className="foot">
        <span>© 2026 Course Conquer</span>
        <span>Atelier Zero · Editorial Edition</span>
        <span>Made with care</span>
      </div>
    </footer>
  )
}

export default function Home() {
  return (
    <>
      <Hero />
      <Section idx="01" title={<>捕获 <span className="it">capture</span></>}>
        <p>
          支持文本、代码、PDF、Office、图片等任意后缀。一个共用的解析函数把每类文件
          归一化为 Markdown——<strong>图片走视觉模型 OCR</strong>，扫描页自动识别，
          代码保留语言标签，表格转为结构化文本。
        </p>
        <p>
          解析只做一次。产出的规范文档同时喂给向量化、摘要标签与知识图谱三条下游，
          昂贵的 OCR 不再重复。每个分块携带<strong>页码 / 行号</strong>，检索可精确定位。
        </p>
      </Section>
      <Section idx="02" title={<>蒸馏 <span className="it">distill</span></>}>
        <p>
          入库时自动生成<strong>摘要、关键词标签与学科分类</strong>，让零散资料瞬间
          变成可浏览、可过滤的知识卡片。向量编码让语义相近的内容天然聚拢。
        </p>
        <p>
          知识图谱按需而建——按钮触发，从已入库内容抽取实体与关系，跨文档同名概念
          自动合并。它不在检索的关键路径上，却让<strong>思维导图与跨文档推理</strong>成为可能。
        </p>
      </Section>
      <Section idx="03" title={<>复用 <span className="it">reuse</span></>}>
        <p>
          对话框提问，规划器拆解任务：单文档检索、多文档对比、联网搜索、代码解析各走其路。
          <strong>多轮检索</strong>由裁判判断“够不够”，不够就再搜一轮。
        </p>
        <p>
          最终答案带<strong>引用来源</strong>——文件名加页码行号，并点出背后的知识点。
          不仅会做这道题，更懂题目背后的原理。
        </p>
      </Section>
      <Closing />
    </>
  )
}
