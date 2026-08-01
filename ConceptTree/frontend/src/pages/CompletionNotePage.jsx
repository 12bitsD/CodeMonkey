import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import MarkdownContent from '../components/common/MarkdownContent';
import { buildApiUrl } from '../config/api';
import { tokenManager } from '../services/api';
import LanguageToggle from '../components/common/LanguageToggle';
import { useLanguage } from '../contexts/LanguageContext';
import completionIllustration from '../assets/illustrations/completion-path.jpg';

export default function CompletionNotePage() {
  const { planId, nodeId, noteId } = useParams();
  const navigate = useNavigate();
  const { language, t } = useLanguage();
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
        setError(t('completion.failed'));
      } finally {
        setLoading(false);
      }
    };
    fetchNote();
  }, [noteId, t]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-zinc-500 text-sm">
        {t('completion.loading')}
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <p className="text-zinc-500 text-sm">{error || t('completion.missing')}</p>
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="text-xs text-teal-600 hover:underline"
        >
          {t('completion.back')}
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-canvas)]">
      {/* Print-hidden controls */}
      <div className="apple-toolbar print:hidden sticky top-0 z-10 flex items-center gap-3 border-x-0 border-t-0 px-4 py-2.5">
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="p-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
          aria-label={t('common.back')}
        >
          <ArrowLeft className="w-4 h-4 text-zinc-600" />
        </button>
        <span className="flex-1 text-sm font-semibold text-zinc-700">{t('completion.title')}</span>
        <LanguageToggle className="hidden sm:inline-flex" />
        <button
          onClick={() => window.print()}
          className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-50 transition-colors"
        >
          <Printer className="w-3.5 h-3.5" />
          {t('completion.export')}
        </button>
      </div>

      {/* Note content — zhihu-style */}
      <article className="mx-auto my-10 max-w-3xl px-6 py-8 print:my-0 print:max-w-none print:p-0 sm:px-10 sm:py-10">
        <img
          src={completionIllustration}
          alt=""
          className="notion-illustration mx-auto mb-10 w-full max-w-lg print:hidden"
        />
        <div className="mb-8 border-b border-black/[0.1] pb-5">
          <p className="notion-section-label">PathFinder</p>
          <h1 className="mt-2 text-3xl font-bold tracking-[-0.03em] text-[#202020]">{t('completion.title')}</h1>
        </div>
        <div className="note-zhihu">
          <MarkdownContent content={note.content} />
        </div>
        <p className="mt-12 text-xs text-zinc-400 print:hidden">
          {t('completion.generated', { date: new Date(note.created_at).toLocaleDateString(language === 'zh-CN' ? 'zh-CN' : 'en-US') })}
        </p>
      </article>
    </div>
  );
}
