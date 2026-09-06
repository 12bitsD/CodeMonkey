import { BookOpen, X } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function NotesSuggestionToast({ suggestion, onAdd, onDismiss }) {
  const { t } = useLanguage();
  if (!suggestion) return null;
  return (
    <div className="apple-card fixed bottom-6 right-6 z-40 max-w-md rounded-xl p-4 shadow-[var(--shadow-float)]">
      <div className="flex items-start gap-3">
        <BookOpen size={18} className="text-amber-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="mb-1 text-xs text-zinc-500">{t('deep.note.suggest')}</p>
          <p className="text-sm text-zinc-800 truncate">{suggestion.snippet}</p>
        </div>
        <button onClick={onDismiss} aria-label={t('common.close')}><X size={14} /></button>
      </div>
      <div className="flex gap-2 mt-3 justify-end">
        <button
          onClick={onDismiss}
          className="px-3 py-1 text-xs rounded-lg text-zinc-500 hover:bg-zinc-100"
        >
          {t('deep.note.ignore')}
        </button>
        <button
          onClick={() => onAdd(suggestion.snippet)}
          className="rounded-md bg-[#202020] px-3 py-1.5 text-xs font-medium text-white"
        >
          {t('deep.note.add')}
        </button>
      </div>
    </div>
  );
}
