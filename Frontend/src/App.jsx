import { createContext, useState, useContext } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Home from './views/Home.jsx'
import Upload from './views/Upload.jsx'
import Chat from './views/Chat.jsx'
import KnowledgeGraph from './views/KnowledgeGraph.jsx'
import Profile from './views/Profile.jsx'

const WorkspaceCtx = createContext({ workspace: 'alg26', setWorkspace: () => {} })
export const useWorkspace = () => useContext(WorkspaceCtx)

const NAV = [
  { to: '/', idx: '00', label: '首页', exact: true },
  { to: '/upload', idx: '01', label: '数据库上传' },
  { to: '/chat', idx: '02', label: '知识问答' },
  { to: '/kg', idx: '03', label: '知识图谱' },
  { to: '/profile', idx: '04', label: '个人与用量' },
]

function Sidebar() {
  const { workspace, setWorkspace } = useWorkspace()
  const loc = useLocation()
  return (
    <aside className="sidebar">
      <div className="brand">
        Course Conquer<span className="dot">.</span>
      </div>
      <div className="brand-sub">课程知识库 · 第 01 卷</div>

      <div className="masthead">
        <span>EST. 2026</span>
        <span>PC EDITION</span>
      </div>

      <nav className="nav">
        <div className="nav-section-label">导航</div>
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.exact}
            className={() => 'nav-item' + (loc.pathname === n.to ? ' active' : '')}
          >
            <span className="idx">{n.idx}</span>
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="ws-field">
          <label>Workspace</label>
          <input value={workspace} onChange={(e) => setWorkspace(e.target.value)} placeholder="工作区 ID" />
        </div>
        <div className="tiny mt-16" style={{ letterSpacing: '0.15em' }}>
          后端 127.0.0.1:8000
        </div>
      </div>
    </aside>
  )
}

export default function App() {
  const [workspace, setWorkspace] = useState('alg26')
  return (
    <WorkspaceCtx.Provider value={{ workspace, setWorkspace }}>
      <div className="app">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/kg" element={<KnowledgeGraph />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </main>
      </div>
    </WorkspaceCtx.Provider>
  )
}
