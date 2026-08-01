import { useState, useEffect, useCallback, useRef } from 'react';
import { deepLearnApi } from '../services/deepLearnApi';

async function consumeSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 2);
      if (block.startsWith('data:')) {
        try { onEvent(JSON.parse(block.slice(5).trim())); } catch (_) { /* skip */ }
      }
    }
  }
}

export function useDeepLearnSession({ planId, nodeId }) {
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conceptsStatus, setConceptsStatus] = useState({});
  const [weakPoints, setWeakPoints] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [uiFlags, setUiFlags] = useState({
    showCommands: false,
    showTestConfirm: null,
    showFailOptions: null,
  });
  const [error, setError] = useState(null);
  const [pinnedImages, setPinnedImages] = useState([]);
  const [noteSuggestion, setNoteSuggestion] = useState(null);
  const noteSuggestionTimestampRef = useRef(null);
  const [noteId, setNoteId] = useState(null);
  const [isGeneratingNote, setIsGeneratingNote] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);

  const sessionIdRef = useRef(null);
  const streamingMsgIdRef = useRef(null);
  const sessionStateRef = useRef(null);
  const handleEventRef = useRef(null);
  const restartInProgressRef = useRef(false);
  const restartSessionReceivedRef = useRef(false);
  const pinnedStorageLoadedRef = useRef(false);
  const pinnedStorageKey = planId && nodeId ? `deep-learn:pinned:${planId}:${nodeId}` : null;

  const deriveUiFlags = useCallback((state) => {
    if (state === 'AWAITING_COMMAND') {
      return { showCommands: true, showTestConfirm: null, showFailOptions: null };
    }
    return { showCommands: false, showTestConfirm: null, showFailOptions: null };
  }, []);

  const canAcceptFreeText = useCallback((state) => (
    state === 'QUESTIONING' || state === 'TESTING'
  ), []);

  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case 'assistant_start': {
        if (!streamingMsgIdRef.current) {
          const id = Date.now() + Math.random();
          streamingMsgIdRef.current = id;
          setMessages(prev => [...prev, { id, role: 'assistant', kind: 'text', content: '' }]);
        }
        break;
      }
      case 'chunk': {
        const msgId = streamingMsgIdRef.current;
        if (msgId) {
          setMessages(prev => prev.map(m =>
            m.id === msgId ? { ...m, content: m.content + event.text } : m
          ));
        } else {
          const id = Date.now() + Math.random();
          streamingMsgIdRef.current = id;
          setMessages(prev => [...prev, { id, role: 'assistant', kind: 'text', content: event.text }]);
        }
        break;
      }
      case 'image_mermaid':
        setMessages(prev => [...prev, {
          id: Date.now() + Math.random(),
          role: 'assistant', kind: 'mermaid', content: event.code,
        }]);
        break;
      case 'state_change':
        sessionStateRef.current = event.to;
        setSession(prev => prev ? { ...prev, state: event.to } : prev);
        break;
      case 'concept_update':
        setConceptsStatus(prev => ({ ...prev, [String(event.index)]: event.status }));
        break;
      case 'questions':
        setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
        setMessages(prev => [...prev, {
          id: Date.now() + Math.random(),
          role: 'assistant', kind: 'questions', content: event.items,
        }]);
        break;
      case 'assessment':
        setMessages(prev => [...prev, {
          id: Date.now() + Math.random(),
          role: 'assistant', kind: 'assessment', content: event,
        }]);
        break;
      case 'show_commands':
        setUiFlags({ showCommands: true, showTestConfirm: null, showFailOptions: null });
        break;
      case 'test_confirm_prompt':
        setUiFlags({ showCommands: false, showTestConfirm: event, showFailOptions: null });
        break;
      case 'fail_options':
        setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: event });
        break;
      case 'node_completed':
        setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
        setIsCompleted(true);
        break;
      case 'restart':
        restartSessionReceivedRef.current = true;
        sessionIdRef.current = event.new_session_id;
        sessionStateRef.current = 'INITIALIZING';
        setSession(prev => prev ? { ...prev, sessionId: event.new_session_id, state: 'INITIALIZING' } : prev);
        setConceptsStatus({});
        setWeakPoints([]);
        setIsInitializing(true);
        setIsRestarting(true);
        setError(null);
        setMessages([]);
        setPinnedImages([]);
        setNoteSuggestion(null);
        setNoteId(null);
        setIsGeneratingNote(false);
        setIsCompleted(false);
        setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
        streamingMsgIdRef.current = null;
        deepLearnApi.initialize(event.new_session_id).then(res =>
          consumeSSE(res, nextEvent => handleEventRef.current?.(nextEvent))
        ).catch(e => setError(e.message))
          .finally(() => {
            setIsInitializing(false);
            setIsRestarting(false);
            setIsStreaming(false);
            restartInProgressRef.current = false;
            streamingMsgIdRef.current = null;
          });
        break;
      case 'image_dalle_pending':
        setMessages(prev => [...prev, {
          id: event.id,
          role: 'assistant', kind: 'dalle_pending',
          content: null, reason: event.reason,
        }]);
        // Auto-timeout: if no done within 30s, show failure
        setTimeout(() => {
          setMessages(prev => prev.map(m =>
            m.kind === 'dalle_pending' && m.id === event.id
              ? { ...m, kind: 'dalle_image', content: '' }
              : m
          ));
        }, 30000);
        break;
      case 'image_dalle_done':
        setMessages(prev => prev.map(m =>
          (m.kind === 'dalle_pending' || m.kind === 'dalle_image') && m.id === event.id
            ? { ...m, kind: 'dalle_image', content: event.url }
            : m
        ));
        break;
      case 'notes_suggestion': {
        const ts = Date.now();
        noteSuggestionTimestampRef.current = ts;
        setNoteSuggestion({ snippet: event.snippet, timestamp: ts });
        setTimeout(() => {
          setNoteSuggestion(curr => curr?.timestamp === ts ? null : curr);
        }, 5000);
        break;
      }
      case 'note_generating':
        setIsGeneratingNote(true);
        break;
      case 'note_ready':
        setIsGeneratingNote(false);
        setNoteId(event.note_id);
        break;
      case 'error':
        setError(event.error?.message || '未知错误');
        break;
      case 'done':
        setIsStreaming(false);
        streamingMsgIdRef.current = null;
        break;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    handleEventRef.current = handleEvent;
  }, [handleEvent]);

  const streamFrom = useCallback(async (fetchPromise) => {
    setIsStreaming(true);
    setError(null);
    streamingMsgIdRef.current = null;
    try {
      const res = await fetchPromise;
      if (!res.ok) {
        setError(`请求失败: ${res.status}`);
        setIsStreaming(false);
        return;
      }
      await consumeSSE(res, handleEvent);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsStreaming(false);
      streamingMsgIdRef.current = null;
    }
  }, [handleEvent]);

  const sendMessage = useCallback(async (text) => {
    if (!sessionIdRef.current || isStreaming || restartInProgressRef.current) return;
    if (!canAcceptFreeText(sessionStateRef.current)) {
      setUiFlags(deriveUiFlags(sessionStateRef.current));
      return;
    }
    setMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      role: 'user', kind: 'text', content: text,
    }]);
    setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
    await streamFrom(deepLearnApi.sendMessage(sessionIdRef.current, text));
  }, [canAcceptFreeText, deriveUiFlags, isStreaming, streamFrom]);

  const sendCommand = useCallback(async (cmd) => {
    if (!sessionIdRef.current || isStreaming || restartInProgressRef.current) return;
    if (cmd === 'restart') {
      restartInProgressRef.current = true;
      restartSessionReceivedRef.current = false;
      sessionStateRef.current = 'INITIALIZING';
      setIsRestarting(true);
      setIsInitializing(true);
      setError(null);
      setMessages([]);
      setConceptsStatus({});
      setWeakPoints([]);
      setPinnedImages([]);
      setNoteSuggestion(null);
      setNoteId(null);
      setIsGeneratingNote(false);
      setIsCompleted(false);
      setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
      streamingMsgIdRef.current = null;
      setSession(prev => prev ? { ...prev, state: 'INITIALIZING' } : prev);
    }
    setUiFlags({ showCommands: false, showTestConfirm: null, showFailOptions: null });
    await streamFrom(deepLearnApi.sendCommand(sessionIdRef.current, cmd));
    if (cmd === 'restart' && !restartSessionReceivedRef.current) {
      restartInProgressRef.current = false;
      setIsRestarting(false);
      setIsInitializing(false);
    }
  }, [isStreaming, streamFrom]);

  useEffect(() => {
    if (!planId || !nodeId) return;
    let cancelled = false;

    (async () => {
      try {
        const res = await deepLearnApi.createSession({ nodeId, planId });
        if (cancelled) return;
        const data = res.data;
        sessionIdRef.current = data.session_id;
        sessionStateRef.current = data.state;
        setSession({
          sessionId: data.session_id,
          state: data.state,
          nodeName: data.node_name,
          nodeWhy: data.node_why,
          whatList: data.what_list,
        });
        setConceptsStatus(data.concepts_status);
        setWeakPoints(data.weak_points);

        if (data.state === 'INITIALIZING') {
          setIsInitializing(true);
          await streamFrom(deepLearnApi.initialize(data.session_id));
          setIsInitializing(false);
        } else {
          const restoredMessages = data.recent_turns.map(t => ({
            id: Date.now() + Math.random(),
            role: t.role,
            kind: t.kind || 'text',
            content: t.content,
            reason: t.reason,
          }));
          const hasQuestionCard = restoredMessages.some(m => m.kind === 'questions');
          if (data.state === 'QUESTIONING' && !hasQuestionCard) {
            const concept = data.what_list?.[data.current_concept_index] || data.node_name;
            restoredMessages.push({
              id: Date.now() + Math.random(),
              role: 'assistant',
              kind: 'questions',
              content: [`请用你自己的话解释「${concept}」，并举一个具体使用场景。`],
            });
          }
          setMessages(restoredMessages);
          setUiFlags(deriveUiFlags(data.state));
        }
      } catch (e) {
        setIsInitializing(false);
        if (!cancelled) setError(e.message);
      }
    })();

    return () => { cancelled = true; };
  }, [deriveUiFlags, planId, nodeId, streamFrom]);

  useEffect(() => {
    if (!pinnedStorageKey) return;
    try {
      const raw = localStorage.getItem(pinnedStorageKey);
      setPinnedImages(raw ? JSON.parse(raw) : []);
    } catch (_error) {
      setPinnedImages([]);
    } finally {
      pinnedStorageLoadedRef.current = true;
    }
  }, [pinnedStorageKey]);

  useEffect(() => {
    if (!pinnedStorageKey || !pinnedStorageLoadedRef.current) return;
    localStorage.setItem(pinnedStorageKey, JSON.stringify(pinnedImages));
  }, [pinnedImages, pinnedStorageKey]);

  const pinImage = useCallback((id, url, caption) => {
    setPinnedImages(prev =>
      prev.find(p => p.id === id) ? prev : [...prev, { id, url, caption }]
    );
  }, []);

  const unpinImage = useCallback((id) => {
    setPinnedImages(prev => prev.filter(p => p.id !== id));
  }, []);

  const dismissNoteSuggestion = useCallback(() => {
    setNoteSuggestion(null);
  }, []);

  return {
    session,
    messages,
    conceptsStatus,
    weakPoints,
    isStreaming,
    isInitializing,
    isRestarting,
    canSendMessage: canAcceptFreeText(session?.state),
    uiFlags,
    sendMessage,
    sendCommand,
    error,
    pinnedImages,
    pinImage,
    unpinImage,
    noteSuggestion,
    dismissNoteSuggestion,
    noteId,
    isGeneratingNote,
    isCompleted,
  };
}
