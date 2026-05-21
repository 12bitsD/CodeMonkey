import { BookOpen } from 'lucide-react';

export default function NotesButton({ onClick, hasUnsaved = false }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 transition-colors w-full"
    >
      <BookOpen size={16} />
      <span>笔记</span>
      {hasUnsaved && <span className="ml-auto w-2 h-2 rounded-full bg-amber-500" />}
    </button>
  );
}
