import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import MarkdownContent from '../components/common/MarkdownContent';
import { buildApiUrl } from '../config/api';
import { tokenManager } from '../services/api';

export default function CompletionNotePage() {
  const { planId, nodeId, noteId } = useParams();
  const navigate = useNavigate();
  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNote = async () => {
      try {
        const token = tokenManager?.get?.();
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(buildApiUrl(`/deep-learn/notes/${noteId}`), { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setNote(await res.json());
      } catch (e) {
        setError('无法加载笔记内容');
      } finally {
        setLoading(false);
      }
    };
    fetchNote();
  }, [noteId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-zinc-500 text-sm">
        加载笔记中...
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <p className="text-zinc-500 text-sm">{error || '笔记不存在'}</p>
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="text-xs text-teal-600 hover:underline"
        >
          返回学习页
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Print-hidden controls */}
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-zinc-100 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="p-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
          aria-label="返回"
        >
          <ArrowLeft className="w-4 h-4 text-zinc-600" />
        </button>
        <span className="text-sm text-zinc-500 flex-1">完成笔记</span>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-50 transition-colors"
        >
          <Printer className="w-3.5 h-3.5" />
          导出 PDF
        </button>
      </div>

      {/* Note content — zhihu-style */}
      <article className="mx-auto max-w-2xl px-6 py-12 print:py-8 print:px-0 print:max-w-none">
        <div className="note-zhihu">
          <MarkdownContent content={note.content} />
        </div>
        <p className="mt-12 text-xs text-zinc-400 print:hidden">
          生成于 {new Date(note.created_at).toLocaleDateString('zh-CN')}
        </p>
      </article>
    </div>
  );
}
