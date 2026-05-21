import { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, Plus, Save, Trash2, X } from 'lucide-react';
import MarkdownContent from '../common/MarkdownContent';
import { useNoteContext } from '../../contexts/NoteContext';

function noteBelongsToNode(note, planId, nodeId) {
  if (!note || note.planId !== planId || !nodeId) return false;
  const candidates = new Set([nodeId, `${planId}_${nodeId}`]);
  if (String(nodeId).startsWith(`${planId}_`)) {
    candidates.add(String(nodeId).slice(planId.length + 1));
  }
  return candidates.has(note.nodeId);
}

function getNoteTitle(note) {
  const firstLine = (note?.content || '').split('\n').find(line => line.trim());
  return firstLine?.replace(/^#+\s*/, '').trim() || '未命名笔记';
}

export default function NotesModal({ open, onClose, planId, nodeId, initialContent = '', selectedNoteId = null }) {
  if (!open) return null;

  return (
    <OpenNotesModal
      onClose={onClose}
      planId={planId}
      nodeId={nodeId}
      initialContent={initialContent}
      selectedNoteId={selectedNoteId}
    />
  );
}

function OpenNotesModal({ onClose, planId, nodeId, initialContent = '', selectedNoteId = null }) {
  const { allNotes, actions: noteActions } = useNoteContext();
  const nodeNotes = useMemo(
    () => allNotes.filter(note => noteBelongsToNode(note, planId, nodeId)),
    [allNotes, nodeId, planId],
  );
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [content, setContent] = useState(initialContent);
  const [saving, setSaving] = useState(false);
  const [savedToast, setSavedToast] = useState(false);
  const consumedInitialContentRef = useRef(false);
  const initializedSelectionRef = useRef(false);

  const selectedNote = editingNoteId
    ? nodeNotes.find(note => note.id === editingNoteId)
    : null;
  const isCreating = !editingNoteId;

  useEffect(() => {
    if (initializedSelectionRef.current) return;

    if (selectedNoteId) {
      const selected = nodeNotes.find(note => note.id === selectedNoteId);
      if (selected) {
        initializedSelectionRef.current = true;
        setEditingNoteId(selected.id);
        setContent(selected.content || '');
        return;
      }
    }

    if (initialContent.trim() && !consumedInitialContentRef.current) {
      consumedInitialContentRef.current = true;
      initializedSelectionRef.current = true;
      setEditingNoteId(null);
      setContent(initialContent);
      return;
    }

    if (editingNoteId || content.trim()) return;

    const firstNote = nodeNotes[0];
    if (firstNote) {
      initializedSelectionRef.current = true;
      setEditingNoteId(firstNote.id);
      setContent(firstNote.content || '');
    }
  }, [content, editingNoteId, initialContent, nodeNotes, selectedNoteId]);

  const openNewNote = () => {
    setEditingNoteId(null);
    setContent('');
    setSavedToast(false);
  };

  const openExistingNote = (note) => {
    setEditingNoteId(note.id);
    setContent(note.content || '');
    setSavedToast(false);
  };

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      if (editingNoteId) {
        await noteActions.updateNote(editingNoteId, content);
      } else {
        const newNote = await noteActions.addNote(planId, nodeId, content);
        if (newNote?.id) setEditingNoteId(newNote.id);
      }
      setSavedToast(true);
      setTimeout(() => setSavedToast(false), 1200);
    } catch (e) {
      console.error('save note failed:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editingNoteId) return;
    setSaving(true);
    try {
      await noteActions.deleteNote(editingNoteId);
      setEditingNoteId(null);
      setContent('');
      setSavedToast(false);
      initializedSelectionRef.current = true;
    } catch (e) {
      console.error('delete note failed:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="flex h-[82vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={event => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">笔记</h3>
            <p className="mt-0.5 text-xs text-zinc-400">当前节点共 {nodeNotes.length} 条笔记</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
            aria-label="关闭笔记"
          >
            <X size={18} />
          </button>
        </header>

        <div className="flex min-h-0 flex-1">
          <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-100 bg-zinc-50/70">
            <div className="border-b border-zinc-100 p-3">
              <button
                type="button"
                onClick={openNewNote}
                className={`flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  isCreating
                    ? 'border-amber-200 bg-amber-50 text-amber-900'
                    : 'border-zinc-200 bg-white text-zinc-700 hover:border-amber-200 hover:text-amber-800'
                }`}
              >
                <Plus size={15} />
                新建笔记
              </button>
            </div>

            <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
              {nodeNotes.length > 0 ? (
                nodeNotes.map(note => (
                  <button
                    key={note.id}
                    type="button"
                    onClick={() => openExistingNote(note)}
                    className={`w-full rounded-xl border p-3 text-left transition-colors ${
                      editingNoteId === note.id
                        ? 'border-amber-200 bg-white text-zinc-900 shadow-sm'
                        : 'border-transparent bg-white/70 text-zinc-600 hover:border-zinc-200 hover:bg-white'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <FileText size={14} className="mt-0.5 shrink-0 text-amber-600" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold">{getNoteTitle(note)}</p>
                        <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-zinc-400">
                          {(note.content || '').replace(/\s+/g, ' ').slice(0, 90)}
                        </p>
                      </div>
                    </div>
                    <p className="mt-2 text-[10px] text-zinc-300">{note.date || note.createdAt || ''}</p>
                  </button>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-zinc-200 bg-white p-4 text-center text-xs leading-5 text-zinc-400">
                  这个节点还没有笔记。
                </div>
              )}
            </div>
          </aside>

          <main className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-zinc-900">
                  {isCreating ? '新建笔记' : getNoteTitle(selectedNote)}
                </p>
                <p className="mt-0.5 text-xs text-zinc-400">左侧编辑，右侧实时预览</p>
              </div>
              {savedToast && <span className="text-xs text-emerald-600">已保存</span>}
            </div>

            <div className="flex min-h-0 flex-1">
              <textarea
                className="min-w-0 flex-1 resize-none border-r border-zinc-100 p-4 font-mono text-sm leading-6 text-zinc-800 outline-none placeholder:text-zinc-300"
                value={content}
                onChange={event => setContent(event.target.value)}
                placeholder="支持 Markdown 语法..."
              />
              <div className="min-w-0 flex-1 overflow-y-auto bg-zinc-50 p-4">
                <MarkdownContent content={content || '_预览区_'} />
              </div>
            </div>

            <footer className="flex justify-end gap-2 border-t border-zinc-200 p-4">
              {!isCreating && (
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={saving}
                  className="mr-auto flex items-center gap-1.5 rounded-lg border border-red-100 px-3 py-1.5 text-sm text-red-500 transition-colors hover:bg-red-50 disabled:opacity-40"
                >
                  <Trash2 size={14} />
                  删除
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm text-zinc-700 transition-colors hover:bg-zinc-50"
              >
                关闭
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !content.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-3 py-1.5 text-sm text-white transition-colors hover:bg-zinc-700 disabled:opacity-40"
              >
                <Save size={14} />
                {saving ? '保存中...' : '保存'}
              </button>
            </footer>
          </main>
        </div>
      </div>
    </div>
  );
}
