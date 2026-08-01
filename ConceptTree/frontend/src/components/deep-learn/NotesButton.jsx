import { BookOpen } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function NotesButton({ onClick, hasUnsaved = false }) {
  const { t } = useLanguage();
  return (
    <button
      onClick={onClick}
      className="flex min-h-10 w-full items-center gap-2 rounded-md border border-black/[0.1] bg-white px-3 py-2 text-sm font-medium text-zinc-700 transition-[background-color,transform] duration-150 hover:bg-black/[0.035] active:scale-[0.98]"
    >
      <BookOpen size={16} />
      <span>{t('deep.notes')}</span>
      {hasUnsaved && <span className="ml-auto w-2 h-2 rounded-full bg-amber-500" />}
    </button>
  );
}
