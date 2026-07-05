import { createContext, useState, useContext, useEffect } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import Landing from './views/Landing.jsx'
import Workspaces from './views/Workspaces.jsx'
import WithinKB from './views/WithinKB.jsx'

const WorkspaceCtx = createContext({ workspace: 'alg26', setWorkspace: () => {} })
export const useWorkspace = () => useContext(WorkspaceCtx)

export default function App() {
  const [workspace, setWorkspace] = useState('alg26')
  return (
    <WorkspaceCtx.Provider value={{ workspace, setWorkspace }}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/workspaces" element={<Workspaces />} />
        <Route path="/kb/:wsId/*" element={<WithinKB />} />
      </Routes>
    </WorkspaceCtx.Provider>
  )
}
