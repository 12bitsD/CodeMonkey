import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Pencil, RotateCcw, Trash2, X } from 'lucide-react';
import { useDeepLearnSession } from '../hooks/useDeepLearnSession';
import { useNoteContext } from '../contexts/NoteContext';
import ConceptProgress from '../components/deep-learn/ConceptProgress';
import DeepLearnChat from '../components/deep-learn/DeepLearnChat';
import DeepLearnAssistant from '../components/deep-learn/DeepLearnAssistant';
import NotesButton from '../components/deep-learn/NotesButton';
import NotesModal from '../components/deep-learn/NotesModal';
import NotesSuggestionToast from '../components/deep-learn/NotesSuggestionToast';
import MarkdownContent from '../components/common/MarkdownContent';

const MIN_LEFT_WIDTH = 220;
const MAX_LEFT_WIDTH = 420;
const MIN_CENTER_WIDTH = 420;
const MIN_RIGHT_WIDTH = 320;
const MAX_RIGHT_WIDTH = 640;
const DEFAULT_LEFT_WIDTH = 288;
const DEFAULT_RIGHT_WIDTH = 440;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

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

function getNoteSnippet(note) {
  return (note?.content || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function Header({ nodeName, onBack, onRestart, noteHref, isGeneratingNote }) {
  return (
    <div className="flex items-center gap-3 px-6 py-3 border-b border-zinc-200 bg-white shrink-0">
      <button
        type="button"
        aria-label="返回图谱"
        onClick={onBack}
        className="p-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
      >
        <ArrowLeft className="w-4 h-4 text-zinc-600" />
      </button>
      <span className="font-semibold text-zinc-900 flex-1 truncate">{nodeName || '深入学习'}</span>
      {isGeneratingNote && (
        <span className="flex items-center gap-1.5 text-xs text-zinc-400 animate-pulse px-2 py-1.5">
          正在生成笔记...
        </span>
      )}
      {noteHref && !isGeneratingNote && (
        <a
          href={noteHref}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-lg transition-colors"
        >
          完成笔记 ↗
        </a>
      )}
      <button
        type="button"
        aria-label="重新开始"
        onClick={onRestart}
        disabled={!onRestart}
        className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-700 disabled:text-zinc-300 disabled:hover:bg-transparent px-2 py-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        重新开始
      </button>
    </div>
  );
}

function RestartConfirmDialog({ open, onCancel, onConfirm }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-5 shadow-2xl">
        <div className="mb-4">
          <h2 className="text-base font-semibold text-zinc-900">确认重新开始？</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            当前深度学习进度会被清空，并从第一个概念重新生成讲解。
          </p>
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600 transition-colors hover:bg-zinc-50"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white transition-colors hover:bg-zinc-700"
          >
            确认重新开始
          </button>
        </div>
      </div>
    </div>
  );
}

function FullScreenLoader({ text }) {
  return (
    <div className="flex flex-1 items-center justify-center text-zinc-500 text-sm">
      {text}
    </div>
  );
}

function InitializationPanel({ nodeName }) {
  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="w-full max-w-xl rounded-2xl border border-teal-100 bg-white px-6 py-5 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-teal-500" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-900">正在准备第一次深度学习</p>
            <p className="text-xs text-zinc-500">{nodeName || '当前知识点'} 的会话只会初始化一次，之后会自动恢复进度。</p>
          </div>
        </div>
        <div className="space-y-3 text-sm text-zinc-600">
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
            <span>读取节点概念列表和学习目标</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
            <span>校准当前概念的教学深度</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300" />
            <span>生成第一段讲解和诊断问题</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function ErrorBanner({ message }) {
  return (
    <div className="mx-4 mt-3 px-4 py-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
      {message}
    </div>
  );
}

function SidebarNoteList({ notes, selectedNoteId, onSelectNote, onDeleteNote }) {
  if (!notes.length) return null;

  return (
    <div className="mt-3 space-y-2">
      {notes.map(note => (
        <div
          key={note.id}
          className={`group rounded-xl border p-2 transition-colors ${
            selectedNoteId === note.id
              ? 'border-amber-200 bg-amber-50 text-zinc-900'
              : 'border-zinc-100 bg-white text-zinc-600 hover:border-amber-200 hover:bg-amber-50/40'
          }`}
        >
          <div className="flex items-start gap-2">
            <button
              type="button"
              onClick={() => onSelectNote(note.id)}
              className="min-w-0 flex-1 text-left"
            >
              <div className="flex items-start gap-2">
                <FileText size={14} className="mt-0.5 shrink-0 text-amber-600" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold">{getNoteTitle(note)}</p>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-zinc-400">
                    {getNoteSnippet(note).slice(0, 72)}
                  </p>
                </div>
              </div>
              <p className="mt-2 text-[10px] text-zinc-300">{note.date || note.createdAt || ''}</p>
            </button>
            <button
              type="button"
              onClick={() => onDeleteNote(note.id)}
              aria-label={`删除笔记 ${getNoteTitle(note)}`}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-zinc-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 focus:opacity-100"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function NoteReaderPanel({ note, onEdit, onDelete, onClose }) {
  return (
    <aside
      aria-label="笔记阅读区"
      className="flex h-full min-h-0 w-full flex-col border-l border-zinc-200 bg-white text-zinc-900 shadow-[-8px_0_24px_rgba(15,23,42,0.04)]"
    >
      <header className="flex min-h-12 items-center gap-2 border-b border-zinc-100 px-4 py-3">
        <FileText size={16} className="shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-zinc-900">{getNoteTitle(note)}</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">{note.date || note.createdAt || '笔记'}</p>
        </div>
        <button
          type="button"
          onClick={onEdit}
          aria-label="编辑笔记"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-amber-50 hover:text-amber-700"
        >
          <Pencil size={15} />
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label="删除笔记"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-500"
        >
          <Trash2 size={15} />
        </button>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭笔记阅读"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
        >
          <X size={16} />
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto bg-zinc-50 px-5 py-5">
        <div className="rounded-xl border border-zinc-100 bg-white p-5">
          <MarkdownContent content={note.content || ''} />
        </div>
      </div>
    </aside>
  );
}

export default function DeepLearnPage() {
  const { planId, nodeId } = useParams();
  const navigate = useNavigate();
  const { allNotes, actions: noteActions } = useNoteContext();
  const layoutRef = useRef(null);
  const resizeRef = useRef(null);
  const [paneWidths, setPaneWidths] = useState({
    left: DEFAULT_LEFT_WIDTH,
    right: DEFAULT_RIGHT_WIDTH,
  });
  const {
    session, messages, conceptsStatus, weakPoints, isStreaming,
    isInitializing, isRestarting, canSendMessage, uiFlags, sendMessage, sendCommand, error,
    pinnedImages, pinImage, unpinImage, noteSuggestion, dismissNoteSuggestion,
    noteId, isGeneratingNote, isCompleted,
  } = useDeepLearnSession({ planId, nodeId });

  const [notesOpen, setNotesOpen] = useState(false);
  const [notesInitial, setNotesInitial] = useState('');
  const [notesEditingId, setNotesEditingId] = useState(null);
  const [selectedNoteId, setSelectedNoteId] = useState(null);
  const [restartConfirmOpen, setRestartConfirmOpen] = useState(false);

  const nodeNotes = useMemo(
    () => allNotes.filter(note => noteBelongsToNode(note, planId, nodeId)),
    [allNotes, nodeId, planId],
  );
  const selectedNote = useMemo(
    () => nodeNotes.find(note => note.id === selectedNoteId) || null,
    [nodeNotes, selectedNoteId],
  );

  const openNotesEditor = useCallback((noteId = null, initialContent = '') => {
    setNotesEditingId(noteId);
    setNotesInitial(initialContent);
    setNotesOpen(true);
  }, []);

  const handleDeleteNote = useCallback(async (noteId) => {
    try {
      await noteActions.deleteNote(noteId);
      if (selectedNoteId === noteId) setSelectedNoteId(null);
      if (notesEditingId === noteId) setNotesEditingId(null);
    } catch (error) {
      console.error('delete note failed:', error);
    }
  }, [noteActions, notesEditingId, selectedNoteId]);

  const handleConfirmRestart = useCallback(() => {
    setRestartConfirmOpen(false);
    sendCommand('restart');
  }, [sendCommand]);

  const getMaxWidth = useCallback((side, widths = paneWidths) => {
    const totalWidth = layoutRef.current?.getBoundingClientRect().width || window.innerWidth || 1440;
    if (side === 'left') {
      return Math.max(MIN_LEFT_WIDTH, Math.min(MAX_LEFT_WIDTH, totalWidth - widths.right - MIN_CENTER_WIDTH));
    }
    return Math.max(MIN_RIGHT_WIDTH, Math.min(MAX_RIGHT_WIDTH, totalWidth - widths.left - MIN_CENTER_WIDTH));
  }, [paneWidths]);

  const startResize = useCallback((side, event) => {
    event.preventDefault();
    resizeRef.current = {
      side,
      pointerX: event.clientX,
      left: paneWidths.left,
      right: paneWidths.right,
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [paneWidths]);

  const resetPaneWidths = useCallback(() => {
    setPaneWidths({
      left: DEFAULT_LEFT_WIDTH,
      right: DEFAULT_RIGHT_WIDTH,
    });
  }, []);

  useEffect(() => {
    const handleMouseMove = (event) => {
      const resize = resizeRef.current;
      if (!resize) return;
      const deltaX = event.clientX - resize.pointerX;

      setPaneWidths(current => {
        if (resize.side === 'left') {
          const maxLeft = getMaxWidth('left', { ...current, right: resize.right });
          return {
            ...current,
            left: clamp(resize.left + deltaX, MIN_LEFT_WIDTH, maxLeft),
          };
        }

        const maxRight = getMaxWidth('right', { ...current, left: resize.left });
        return {
          ...current,
          right: clamp(resize.right - deltaX, MIN_RIGHT_WIDTH, maxRight),
        };
      });
    };

    const handleMouseUp = () => {
      if (!resizeRef.current) return;
      resizeRef.current = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [getMaxWidth]);

  useEffect(() => {
    if (selectedNoteId && !selectedNote) {
      setSelectedNoteId(null);
    }
  }, [selectedNote, selectedNoteId]);

  useEffect(() => {
    if (!isCompleted) return;
    const destination = noteId
      ? `/deep-learn/${planId}/${nodeId}/note/${noteId}`
      : `/graph/${planId}`;
    navigate(destination, { replace: true });
  }, [isCompleted, navigate, nodeId, noteId, planId]);

  if (!session) {
    return (
      <div className="flex flex-col h-screen bg-[#FAFAFA] overflow-hidden">
        <Header
          nodeName={null}
          onBack={() => navigate(`/graph/${planId}`)}
          onRestart={null}
          noteHref={null}
          isGeneratingNote={false}
        />
        {error && <ErrorBanner message={error} />}
        <FullScreenLoader text={error ? "学习环境准备失败" : "正在准备学习环境..."} />
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-screen bg-[#FAFAFA] overflow-hidden">
      <Header
        nodeName={session.nodeName}
        onBack={() => navigate(`/graph/${planId}`)}
        onRestart={isRestarting || isInitializing || isStreaming ? null : () => setRestartConfirmOpen(true)}
        noteHref={noteId ? `/deep-learn/${planId}/${nodeId}/note/${noteId}` : null}
        isGeneratingNote={isGeneratingNote}
      />
      <RestartConfirmDialog
        open={restartConfirmOpen}
        onCancel={() => setRestartConfirmOpen(false)}
        onConfirm={handleConfirmRestart}
      />
      <div ref={layoutRef} className="flex flex-1 overflow-hidden">
        <aside
          aria-label="概念列表区域"
          className="shrink-0 bg-white overflow-y-auto"
          style={{ width: `${paneWidths.left}px` }}
        >
          <ConceptProgress
            whatList={session.whatList}
            conceptsStatus={conceptsStatus}
            weakPoints={weakPoints}
            pinnedImages={pinnedImages}
            onUnpinImage={unpinImage}
          />
          <div className="px-4 pb-4">
            <NotesButton onClick={() => openNotesEditor(null, '')} />
            <SidebarNoteList
              notes={nodeNotes}
              selectedNoteId={selectedNoteId}
              onSelectNote={setSelectedNoteId}
              onDeleteNote={handleDeleteNote}
            />
          </div>
        </aside>
        <button
          type="button"
          aria-label="调整概念列表和学习区宽度"
          title="拖动调整宽度，双击重置布局"
          onMouseDown={event => startResize('left', event)}
          onDoubleClick={resetPaneWidths}
          className="group relative z-10 w-2 shrink-0 cursor-col-resize border-x border-zinc-200 bg-zinc-50 transition-colors hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-teal-300"
        >
          <span className="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-300 transition-colors group-hover:bg-teal-400" />
        </button>
        <main className="flex-1 overflow-hidden flex flex-col">
          {error && <ErrorBanner message={error} />}
          {isInitializing && messages.length === 0 ? (
            <InitializationPanel nodeName={session.nodeName} />
          ) : (
            <DeepLearnChat
              messages={messages}
              isStreaming={isStreaming}
              canSendMessage={canSendMessage}
              uiFlags={uiFlags}
              onSendMessage={sendMessage}
              onSendCommand={sendCommand}
              onPinImage={pinImage}
              noteHref={noteId ? `/deep-learn/${planId}/${nodeId}/note/${noteId}` : null}
              onBack={() => navigate(`/graph/${planId}`)}
            />
          )}
        </main>
        <button
          type="button"
          aria-label="调整学习区和侧边工作区宽度"
          title="拖动调整宽度，双击重置布局"
          onMouseDown={event => startResize('right', event)}
          onDoubleClick={resetPaneWidths}
          className="group relative z-10 w-2 shrink-0 cursor-col-resize border-x border-zinc-200 bg-zinc-50 transition-colors hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-teal-300"
        >
          <span className="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-300 transition-colors group-hover:bg-teal-400" />
        </button>
        <div
          aria-label="侧边工作区容器"
          className="shrink-0"
          style={{ width: `${paneWidths.right}px` }}
        >
          {selectedNote ? (
            <NoteReaderPanel
              note={selectedNote}
              onEdit={() => openNotesEditor(selectedNote.id, '')}
              onDelete={() => handleDeleteNote(selectedNote.id)}
              onClose={() => setSelectedNoteId(null)}
            />
          ) : (
            <DeepLearnAssistant nodeName={session.nodeName} nodeWhy={session.nodeWhy} />
          )}
        </div>
      </div>
      <NotesModal
        open={notesOpen}
        onClose={() => setNotesOpen(false)}
        planId={planId}
        nodeId={nodeId}
        initialContent={notesInitial}
        selectedNoteId={notesEditingId}
      />
      <NotesSuggestionToast
        suggestion={noteSuggestion}
        onAdd={(snippet) => { openNotesEditor(null, snippet); dismissNoteSuggestion(); }}
        onDismiss={dismissNoteSuggestion}
      />
    </div>
  );
}
