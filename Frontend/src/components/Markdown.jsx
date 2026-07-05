import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

export default function Markdown({ children }) {
  return (
    <div className="md-body">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children || ''}
      </ReactMarkdown>
    </div>
  )
}
