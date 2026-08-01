import { BookOpen } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function NotesButton({ onClick, hasUnsaved = false }) {
  const { t } = useLanguage();
  return (
    <button
      onClick={onClick}
      className="flex min-h-10 w-full items-center gap-2 rounded-xl border border-blue-100 bg-blue-50/80 px-3 py-2 text-sm font-medium text-blue-800 transition-[background-color,transform] duration-150 hover:bg-blue-100 active:scale-[0.98]"
    >
      <BookOpen size={16} />
      <span>{t('deep.notes')}</span>
      {hasUnsaved && <span className="ml-auto w-2 h-2 rounded-full bg-amber-500" />}
    </button>
  );
}
