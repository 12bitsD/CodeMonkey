import { BookOpen, X } from 'lucide-react';

export default function NotesSuggestionToast({ suggestion, onAdd, onDismiss }) {
  if (!suggestion) return null;
  return (
    <div className="fixed bottom-6 right-6 z-40 max-w-md bg-white rounded-2xl shadow-2xl border border-amber-200 p-4">
      <div className="flex items-start gap-3">
        <BookOpen size={18} className="text-amber-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs text-zinc-500 mb-1">加入笔记？</p>
          <p className="text-sm text-zinc-800 truncate">{suggestion.snippet}</p>
        </div>
        <button onClick={onDismiss}><X size={14} /></button>
      </div>
      <div className="flex gap-2 mt-3 justify-end">
        <button
          onClick={onDismiss}
          className="px-3 py-1 text-xs rounded-lg text-zinc-500 hover:bg-zinc-100"
        >
          忽略
        </button>
        <button
          onClick={() => onAdd(suggestion.snippet)}
          className="px-3 py-1 text-xs rounded-lg bg-amber-500 text-white"
        >
          加入
        </button>
      </div>
    </div>
  );
}
