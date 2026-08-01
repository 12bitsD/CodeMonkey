import { useEffect, useRef, useState } from 'react';
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  FileText,
  Globe2,
  Loader,
  MessageCircle,
  ExternalLink,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
} from 'lucide-react';
import ChatMarkdownMessage from '../chat/ChatMarkdownMessage';
import { aiApi } from '../../services/api';
import { useLanguage } from '../../contexts/LanguageContext';

const MAX_MARKDOWN_FILE_SIZE = 256 * 1024;

function normalizeUrl(value) {
  const text = value.trim();
  if (!text) return '';
  if (/^(https?:|http:|about:|data:)/i.test(text)) return text;
  if (/^(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?/i.test(text)) {
    return `http://${text}`;
  }
  return `https://${text}`;
}

function isMarkdownFile(file) {
  return Boolean(file?.name && /\.md$/i.test(file.name));
}

function formatFileSize(size = 0) {
  if (size < 1024) return `${size} B`;
  return `${Math.round(size / 1024)} KB`;
}

function buildAttachedMarkdownPrompt(text, files, t) {
  if (!files.length) return text;

  const fileBlocks = files.map(file => (
    `### ${file.name}\n\n\`\`\`markdown\n${file.content}\n\`\`\``
  )).join('\n\n');

  return `${t('assistant.prompt.files')}\n\n${fileBlocks}\n\n${t('assistant.prompt.request')}\n${text || t('assistant.prompt.fallback')}`;
}

export default function DeepLearnAssistant({ nodeName, nodeWhy }) {
  const { t } = useLanguage();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [fileError, setFileError] = useState('');
  const [activeTool, setActiveTool] = useState('chat');
  const [browserInput, setBrowserInput] = useState('');
  const [browserUrl, setBrowserUrl] = useState('');
  const [browserKey, setBrowserKey] = useState(0);
  const fileInputRef = useRef(null);
  const chatScrollRef = useRef(null);
  const streamRef = useRef({ content: '' });

  const scrollToBottom = () => {
    const el = chatScrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const flushAssistant = () => {
    setMessages(prev => prev.map((msg, index) => (
      index === prev.length - 1 && msg.role === 'assistant'
        ? { ...msg, content: streamRef.current.content }
        : msg
    )));
  };

  const send = async () => {
    const text = input.trim();
    if ((!text && attachedFiles.length === 0) || loading) return;

    const filesForMessage = attachedFiles;
    const userMsg = {
      role: 'user',
      content: buildAttachedMarkdownPrompt(text, filesForMessage, t),
      displayContent: text || t('assistant.addedFiles'),
      attachments: filesForMessage.map(({ name, size }) => ({ name, size })),
    };
    const nextMessages = [...messages, userMsg, { role: 'assistant', content: '' }];
    streamRef.current = { content: '' };
    setMessages(nextMessages);
    setInput('');
    setAttachedFiles([]);
    setFileError('');
    setLoading(true);

    try {
      await aiApi.chatStream(
        [...messages, userMsg],
        { nodeName, why: nodeWhy },
        (chunk) => {
          streamRef.current.content += chunk;
          flushAssistant();
        },
      );
      if (!streamRef.current.content) {
        streamRef.current.content = t('assistant.emptyResponse');
        flushAssistant();
      }
    } catch (_err) {
      streamRef.current.content = t('assistant.failed');
      flushAssistant();
    } finally {
      setLoading(false);
    }
  };

  const openFilePicker = () => {
    if (loading) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    setFileError('');

    if (!files.length) return;

    const invalidFile = files.find(file => !isMarkdownFile(file));
    if (invalidFile) {
      setFileError(t('assistant.fileType'));
      return;
    }

    const oversizedFile = files.find(file => file.size > MAX_MARKDOWN_FILE_SIZE);
    if (oversizedFile) {
      setFileError(t('assistant.fileSize', { size: formatFileSize(MAX_MARKDOWN_FILE_SIZE) }));
      return;
    }

    try {
      const nextFiles = await Promise.all(files.map(async file => ({
        name: file.name,
        size: file.size,
        content: await file.text(),
      })));
      setAttachedFiles(prev => [...prev, ...nextFiles]);
      setActiveTool('chat');
    } catch (_err) {
      setFileError(t('assistant.fileRead'));
    }
  };

  const removeAttachedFile = (indexToRemove) => {
    setAttachedFiles(prev => prev.filter((_, index) => index !== indexToRemove));
  };

  const openBrowser = (event) => {
    event?.preventDefault();
    const nextUrl = normalizeUrl(browserInput);
    if (!nextUrl) return;
    setBrowserUrl(nextUrl);
  };

  return (
    <aside
      aria-label={t('deep.sidebar')}
      className="flex h-full min-h-0 w-full flex-col border-l border-black/[0.07] bg-white/70 text-zinc-900 backdrop-blur-xl"
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".md,text/markdown"
        multiple
        className="hidden"
        aria-label={t('assistant.addMarkdown')}
        onChange={handleFileChange}
      />
      <div className="flex h-11 items-center gap-2 border-b border-zinc-100 px-3">
        <button
          type="button"
          onClick={() => setActiveTool('chat')}
          className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
            activeTool === 'chat'
              ? 'bg-white text-zinc-900 shadow-sm'
              : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
          }`}
        >
          <Sparkles size={13} />
          {t('assistant.chat')}
        </button>
        <button
          type="button"
          onClick={() => setActiveTool('browser')}
          className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
            activeTool === 'browser'
              ? 'bg-white text-zinc-900 shadow-sm'
              : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900'
          }`}
        >
          <Globe2 size={13} />
          {t('assistant.browser')}
        </button>
        <button
          type="button"
          onClick={openFilePicker}
          aria-label={t('assistant.addMarkdown')}
          title={t('assistant.addMarkdown')}
          className="ml-auto flex h-7 w-7 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
        >
          <Plus size={15} />
        </button>
      </div>

      {activeTool === 'chat' ? (
        <>
          <div className="flex h-12 items-center gap-3 border-b border-zinc-100 px-4">
            <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
              <Sparkles size={13} fill="currentColor" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-zinc-900">{t('assistant.title')}</p>
              <p className="truncate text-[10px] text-zinc-400">{nodeName || t('assistant.currentConcept')}</p>
            </div>
            <button
              type="button"
              onClick={() => setMessages([])}
              className="ml-auto text-[11px] text-zinc-300 transition-colors hover:text-zinc-500"
            >
              {t('assistant.clear')}
            </button>
          </div>

          <div ref={chatScrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 && (
              <div className="pt-12 text-center text-xs text-zinc-300">
                <MessageCircle size={24} className="mx-auto mb-2 opacity-30" />
                <p>{t('assistant.empty', { name: nodeName || t('assistant.thisConcept') })}</p>
              </div>
            )}
            {messages.map((msg, index) => (
              <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'user' ? (
                  <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[#007AFF] px-3 py-2 text-xs leading-relaxed text-white">
                    {msg.displayContent || msg.content}
                    {msg.attachments?.length > 0 && (
                      <div className="mt-2 space-y-1 border-t border-white/15 pt-2 text-[10px] text-zinc-300">
                        {msg.attachments.map((file, fileIndex) => (
                          <div key={`${file.name}-${fileIndex}`} className="flex items-center gap-1.5">
                            <FileText size={11} />
                            <span className="truncate">{file.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <ChatMarkdownMessage
                    content={msg.content}
                    isPending={!msg.content && loading}
                    className="w-full max-w-full rounded-[18px] text-xs"
                  />
                )}
              </div>
            ))}
            {messages.length > 0 && (
              <button
                type="button"
                aria-label={t('assistant.scrollBottom')}
                title={t('assistant.scrollBottom')}
                onClick={scrollToBottom}
                className="sticky bottom-2 ml-auto flex h-8 w-8 items-center justify-center rounded-full border border-zinc-200 bg-white/95 text-zinc-500 shadow-sm transition-colors hover:bg-zinc-50 hover:text-zinc-900"
              >
                <ArrowDown size={15} />
              </button>
            )}
          </div>

          <div className="border-t border-zinc-100 px-4 py-4">
            {(attachedFiles.length > 0 || fileError) && (
              <div className="mb-2 space-y-2">
                {attachedFiles.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    className="flex items-center gap-2 rounded-xl border border-teal-100 bg-teal-50 px-3 py-2 text-[11px] text-teal-800"
                  >
                    <FileText size={13} className="shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{file.name}</span>
                    <span className="shrink-0 text-teal-500">{formatFileSize(file.size)}</span>
                    <button
                      type="button"
                      onClick={() => removeAttachedFile(index)}
                      className="shrink-0 rounded-md px-1 text-teal-500 transition-colors hover:bg-teal-100 hover:text-teal-800"
                      aria-label={t('assistant.removeFile', { name: file.name })}
                    >
                      ×
                    </button>
                  </div>
                ))}
                {fileError && (
                  <p className="rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] text-amber-700">
                    {fileError}
                  </p>
                )}
              </div>
            )}
            <div className="apple-input rounded-2xl px-3 py-2">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                disabled={loading}
                placeholder={t('assistant.placeholder')}
                rows={3}
                className="h-16 w-full resize-none bg-transparent text-xs text-zinc-900 outline-none placeholder:text-zinc-400 disabled:text-zinc-400"
              />
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={openFilePicker}
                  disabled={loading}
                  aria-label={t('assistant.addMarkdown')}
                  title={t('assistant.addMarkdown')}
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 disabled:opacity-50"
                >
                  <Plus size={15} />
                </button>
                <button
                  type="button"
                  onClick={send}
                  disabled={(!input.trim() && attachedFiles.length === 0) || loading}
                  aria-label={t('deep.send')}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-[#007AFF] text-white transition-[background-color,transform] duration-150 hover:bg-[#0071E3] active:scale-[0.95] disabled:bg-zinc-200 disabled:text-zinc-400"
                >
                  {loading ? <Loader size={12} className="animate-spin" /> : <Send size={13} />}
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="flex h-12 items-center gap-2 border-b border-zinc-100 px-3">
            <button
              type="button"
              disabled
              aria-label={t('assistant.browser.back')}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-300"
            >
              <ArrowLeft size={14} />
            </button>
            <button
              type="button"
              disabled
              aria-label={t('assistant.browser.forward')}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-300"
            >
              <ArrowRight size={14} />
            </button>
            <button
              type="button"
              onClick={() => setBrowserKey(key => key + 1)}
              disabled={!browserUrl}
              aria-label={t('assistant.browser.refresh')}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-900 disabled:text-zinc-200"
            >
              <RefreshCcw size={13} />
            </button>
            <form onSubmit={openBrowser} className="min-w-0 flex-1">
              <input
                value={browserInput}
                onChange={event => setBrowserInput(event.target.value)}
                placeholder={t('assistant.browser.placeholder')}
                aria-label={t('assistant.browser.address')}
                className="h-8 w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 text-xs text-zinc-700 outline-none transition-colors placeholder:text-zinc-400 focus:border-teal-400 focus:bg-white"
              />
            </form>
            <button
              type="button"
              onClick={openBrowser}
              disabled={!browserInput.trim()}
              className="h-8 rounded-lg bg-zinc-900 px-3 text-xs font-semibold text-white transition-colors hover:bg-zinc-700 disabled:bg-zinc-100 disabled:text-zinc-300"
            >
              {t('assistant.browser.open')}
            </button>
          </div>

          {browserUrl && (
            <div className="flex items-center gap-2 border-b border-zinc-100 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-800">
              <span className="min-w-0 flex-1">
                {t('assistant.browser.embedWarning')}
              </span>
              <a
                href={browserUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex shrink-0 items-center gap-1 rounded-md bg-white px-2 py-1 font-semibold text-amber-900 shadow-sm ring-1 ring-amber-200 transition-colors hover:bg-amber-100"
              >
                <ExternalLink size={12} />
                {t('assistant.browser.newWindow')}
              </a>
            </div>
          )}

          <div className="min-h-0 flex-1 bg-zinc-50">
            {browserUrl ? (
              <iframe
                key={browserKey}
                src={browserUrl}
                title={t('assistant.browser.title')}
                className="h-full w-full border-0 bg-white"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-full items-center justify-center px-8 text-center text-xs text-zinc-400">
                <div>
                  <Globe2 size={28} className="mx-auto mb-3 opacity-40" />
                  <p>{t('assistant.browser.empty')}</p>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}
