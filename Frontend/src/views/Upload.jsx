import { useRef, useState } from 'react'
import { api } from '../api.js'
import { useWorkspace } from '../App.jsx'

export default function Upload({ onUploaded }) {
  const { workspace } = useWorkspace()
  const fileRef = useRef(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)     // {filename, doc_id, category, tags}
  const [progress, setProgress] = useState('')
  const [err, setErr] = useState('')

  async function uploadFile(file) {
    if (!file) return
    setErr(''); setDone(null); setBusy(true); setProgress('上传中…')
    try {
      const r = await api.ingest(file, workspace)
      setProgress('')
      setDone({
        filename: r.document.filename,
        doc_id: r.document.id,
        category: r.document.category,
        tags: r.document.tags,
        n_chunks: r.document.n_chunks,
        warnings: r.warnings || [],
      })
      onUploaded?.()
    } catch (e) {
      setErr('上传失败：' + e.message)
    } finally {
      setBusy(false)
    }
  }

  function onDrop(e) {
    e.preventDefault(); setDrag(false)
    const f = e.dataTransfer.files?.[0]
    if (f) uploadFile(f)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="eyebrow"><span className="num">01</span>数据库上传</div>
          <h1 className="title mt-8">上传 <span className="it">capture</span></h1>
          <div className="sub">拖入任意课件文件，自动解析、摘要、向量化并入库。</div>
        </div>
        <div className="meta">
          <div className="eyebrow">工作区</div>
          <div className="serif italic mt-8" style={{ fontSize: 18 }}>{workspace}</div>
        </div>
      </div>

      <div
        className={'dropzone' + (drag ? ' drag' : '')}
        onClick={() => !busy && fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <input
          ref={fileRef}
          type="file"
          style={{ display: 'none' }}
          onChange={(e) => uploadFile(e.target.files?.[0])}
        />
        <div className="big">
          {busy ? progress : done ? '再传一个？' : '拖入文件，或点击选择'}
        </div>
        <div className="hint">支持 .txt .md .py .c .cpp .pdf .docx .pptx .xlsx .csv .png .jpg …</div>
      </div>

      {err && <div className="warn mt-16">⚠ {err}</div>}

      {done && (
        <div className="card mt-24">
          <div className="between">
            <h3>上传成功</h3>
            <span className="ok">✓ 已入库</span>
          </div>
          <div className="row gap-16 mt-8">
            <span className="serif" style={{ fontSize: 17 }}>{done.filename}</span>
            <span className="tag gold">{done.category || '未分类'}</span>
            <span className="tiny">{done.n_chunks} 块</span>
          </div>
          <div className="tags">
            {done.tags.map((t) => <span className="tag" key={t}>{t}</span>)}
          </div>
          {done.warnings?.length > 0 && (
            <div className="warn mt-16">⚠ {done.warnings.join('；')}</div>
          )}
        </div>
      )}
    </div>
  )
}
