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
import LanguageToggle from '../components/common/LanguageToggle';
import { useLanguage } from '../contexts/LanguageContext';

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

function getNoteTitle(note, fallback = 'Untitled note') {
  const firstLine = (note?.content || '').split('\n').find(line => line.trim());
  return firstLine?.replace(/^#+\s*/, '').trim() || fallback;
}

function getNoteSnippet(note) {
  return (note?.content || '')
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function Header({ nodeName, onBack, onRestart, noteHref, isGeneratingNote }) {
  const { t } = useLanguage();
  return (
    <div className="apple-toolbar z-30 mx-3 mt-3 flex shrink-0 items-center gap-2 rounded-[18px] px-3 py-2.5 sm:gap-3 sm:px-4">
      <button
        type="button"
        aria-label={t('deep.backToMap')}
        onClick={onBack}
        className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-600 transition-[background-color,transform] duration-150 hover:bg-black/[0.06] active:scale-[0.94]"
      >
        <ArrowLeft className="w-4 h-4 text-zinc-600" />
      </button>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-400">{t('deep.title')}</p>
        <span className="block truncate text-sm font-semibold text-zinc-900">{nodeName || t('deep.title')}</span>
      </div>
      {isGeneratingNote && (
        <span className="flex animate-pulse items-center gap-1.5 px-2 py-1.5 text-xs text-zinc-400">
          {t('deep.note.generating')}
        </span>
      )}
      {noteHref && !isGeneratingNote && (
        <a
          href={noteHref}
          target="_blank"
          rel="noopener noreferrer"
          className="flex min-h-8 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 transition-[background-color,transform] duration-150 hover:bg-blue-100 active:scale-[0.97]"
        >
          {t('deep.note.complete')}
        </a>
      )}
      <button
        type="button"
        aria-label={t('deep.restart')}
        onClick={onRestart}
        disabled={!onRestart}
        className="flex min-h-8 items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs text-zinc-500 transition-[background-color,color,transform] duration-150 hover:bg-black/[0.05] hover:text-zinc-700 active:scale-[0.97] disabled:text-zinc-300 disabled:hover:bg-transparent"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">{t('deep.restart')}</span>
      </button>
      <LanguageToggle className="hidden md:inline-flex" />
    </div>
  );
}

function RestartConfirmDialog({ open, onCancel, onConfirm }) {
  const { t } = useLanguage();
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <div className="w-full max-w-sm rounded-[24px] border border-white/80 bg-white/95 p-6 shadow-[var(--shadow-float)] backdrop-blur-2xl">
        <div className="mb-4">
          <h2 className="text-base font-semibold text-zinc-900">{t('deep.restartTitle')}</h2>
          <p className="mt-2 text-sm leading-6 text-zinc-500">
            {t('deep.restartHelp')}
          </p>
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600 transition-colors hover:bg-zinc-50"
          >
            {t('common.cancel')}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-full bg-[#007AFF] px-4 py-2 text-sm font-semibold text-white transition-[background-color,transform] duration-150 hover:bg-[#0071E3] active:scale-[0.97]"
          >
            {t('deep.restartConfirm')}
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
  const { t } = useLanguage();
  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="apple-card w-full max-w-xl rounded-[26px] px-6 py-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[13px] bg-blue-50 text-blue-600">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-500" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-900">{t('deep.initializing.title')}</p>
            <p className="text-xs text-zinc-500">{t('deep.initializing.subtitle', { name: nodeName || t('deep.currentConcept') })}</p>
          </div>
        </div>
        <div className="space-y-3 text-sm text-zinc-600">
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
            <span>{t('deep.initializing.concepts')}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
            <span>{t('deep.initializing.depth')}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="h-1.5 w-1.5 rounded-full bg-zinc-300" />
            <span>{t('deep.initializing.lesson')}</span>
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
  const { t } = useLanguage();
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
                  <p className="truncate text-xs font-semibold">{getNoteTitle(note, t('deep.note.untitled'))}</p>
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
              aria-label={t('deep.note.deleteNamed', { name: getNoteTitle(note, t('deep.note.untitled')) })}
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
  const { t } = useLanguage();
  return (
    <aside
      aria-label={t('deep.note.reader')}
      className="flex h-full min-h-0 w-full flex-col border-l border-black/[0.07] bg-white/70 text-zinc-900 backdrop-blur-xl"
    >
      <header className="flex min-h-12 items-center gap-2 border-b border-zinc-100 px-4 py-3">
        <FileText size={16} className="shrink-0 text-amber-600" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-zinc-900">{getNoteTitle(note, t('deep.note.untitled'))}</p>
          <p className="mt-0.5 text-[11px] text-zinc-400">{note.date || note.createdAt || t('deep.note.label')}</p>
        </div>
        <button
          type="button"
          onClick={onEdit}
          aria-label={t('deep.note.edit')}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-amber-50 hover:text-amber-700"
        >
          <Pencil size={15} />
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label={t('deep.note.delete')}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-500"
        >
          <Trash2 size={15} />
        </button>
        <button
          type="button"
          onClick={onClose}
          aria-label={t('deep.note.close')}
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
  const { t } = useLanguage();
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
      <div className="flex h-screen flex-col overflow-hidden bg-[var(--color-canvas)]">
        <Header
          nodeName={null}
          onBack={() => navigate(`/graph/${planId}`)}
          onRestart={null}
          noteHref={null}
          isGeneratingNote={false}
        />
        {error && <ErrorBanner message={error} />}
        <FullScreenLoader text={error ? t('deep.failed') : t('deep.preparing')} />
      </div>
    );
  }

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-[var(--color-canvas)]">
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
      <div ref={layoutRef} className="mx-3 mb-3 mt-2 flex flex-1 overflow-hidden rounded-[22px] border border-white/80 bg-white/55 shadow-[var(--shadow-card)] backdrop-blur-xl">
        <aside
          aria-label={t('deep.conceptsArea')}
          className="shrink-0 overflow-y-auto bg-white/70"
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
          aria-label={t('deep.resizeConcepts')}
          title={t('deep.resizeHint')}
          onMouseDown={event => startResize('left', event)}
          onDoubleClick={resetPaneWidths}
          className="group relative z-10 w-2 shrink-0 cursor-col-resize border-x border-black/[0.06] bg-black/[0.025] transition-colors hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-300"
        >
          <span className="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-300 transition-colors group-hover:bg-blue-400" />
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
          aria-label={t('deep.resizeAssistant')}
          title={t('deep.resizeHint')}
          onMouseDown={event => startResize('right', event)}
          onDoubleClick={resetPaneWidths}
          className="group relative z-10 w-2 shrink-0 cursor-col-resize border-x border-black/[0.06] bg-black/[0.025] transition-colors hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-300"
        >
          <span className="absolute left-1/2 top-1/2 h-10 w-0.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-300 transition-colors group-hover:bg-blue-400" />
        </button>
        <div
          aria-label={t('deep.sidebarContainer')}
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
