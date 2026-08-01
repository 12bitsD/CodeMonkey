import { useMemo, useRef, useEffect, useState } from 'react';
import { List, Pin, Send } from 'lucide-react';
import ChatMarkdownMessage from '../chat/ChatMarkdownMessage';
import MarkdownContent from '../common/MarkdownContent';
import CommandBar from './CommandBar';
import DalleImage from './DalleImage';
import MermaidDiagram from './MermaidDiagram';
import { useLanguage } from '../../contexts/LanguageContext';

function AssessmentCard({ data }) {
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${
      data.is_correct ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
    }`}>
      <div className="font-medium mb-1">{data.is_correct ? '✅' : '❌'} {data.explanation}</div>
      {data.feedback && <div className="text-zinc-600">{data.feedback}</div>}
    </div>
  );
}

function QuestionsCard({ items }) {
  const { t } = useLanguage();
  return (
    <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm shadow-sm">
      <p className="mb-3 font-medium text-zinc-500">{t('deep.answerPrompt')}</p>
      <ol className="list-decimal space-y-2 pl-5 text-zinc-700">
        {items.map((q, i) => (
          <li key={i} className="pl-1">
            <MarkdownContent content={q} className="space-y-1 leading-6" />
          </li>
        ))}
      </ol>
    </div>
  );
}

function getOutlineTitle(msg, index, t) {
  if (msg.kind === 'questions') return t('deep.outline.question', { count: index + 1 });
  if (msg.kind === 'assessment') return t('deep.outline.feedback', { count: index + 1 });
  if (msg.kind === 'mermaid') return t('deep.outline.diagram', { count: index + 1 });
  if (msg.kind === 'dalle_image') return t('deep.outline.image', { count: index + 1 });
  if (msg.kind !== 'text') return null;
  const lines = String(msg.content || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean);
  const heading = lines.find(line => /^#{1,4}\s+/.test(line) || /^[一二三四五六七八九十]+[、.]\s*/.test(line) || /^\d+[.、]\s*/.test(line));
  const fallback = heading || lines[0];
  if (!fallback) return null;
  return fallback
    .replace(/^#{1,4}\s+/, '')
    .replace(/\*\*/g, '')
    .slice(0, 32);
}

export default function DeepLearnChat({
  messages,
  isStreaming,
  canSendMessage = true,
  uiFlags,
  onSendMessage,
  onSendCommand,
  onPinImage,
}) {
  const { t } = useLanguage();
  const [input, setInput] = useState('');
  const [outlineOpen, setOutlineOpen] = useState(false);
  const scrollAreaRef = useRef(null);
  const messageRefs = useRef(new Map());

  useEffect(() => {
    const scrollArea = scrollAreaRef.current;
    if (!scrollArea) return;
    scrollArea.scrollTop = scrollArea.scrollHeight;
  }, [messages]);

  const outlineItems = useMemo(() => messages
    .map((msg, index) => ({ id: msg.id, title: getOutlineTitle(msg, index, t) }))
    .filter(item => item.title)
    .slice(-10), [messages, t]);

  const scrollToMessage = (id) => {
    const scrollArea = scrollAreaRef.current;
    const element = messageRefs.current.get(id);
    if (!scrollArea || !element) return;
    scrollArea.scrollTo({
      top: element.offsetTop - scrollArea.offsetTop - 12,
      behavior: 'smooth',
    });
    setOutlineOpen(false);
  };

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || isStreaming || !canSendMessage) return;
    setInput('');
    onSendMessage(text);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const { showCommands, showTestConfirm, showFailOptions } = uiFlags;
  const hasPendingAssistant = isStreaming && messages.some(
    (msg) => msg.role === 'assistant' && msg.kind === 'text' && !msg.content,
  );

  return (
    <div className="relative flex flex-col h-full">
      {outlineItems.length > 0 && (
        <div className="absolute right-4 top-4 z-20">
          <button
            type="button"
            aria-label={t('deep.outline.open')}
            onClick={() => setOutlineOpen(open => !open)}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white/95 text-zinc-500 shadow-sm transition-colors hover:bg-zinc-50 hover:text-zinc-900"
          >
            <List size={17} />
          </button>
          {outlineOpen && (
            <div className="mt-2 w-64 rounded-2xl border border-zinc-800/10 bg-zinc-950/95 p-3 text-sm text-zinc-300 shadow-2xl">
              {outlineItems.map(item => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => scrollToMessage(item.id)}
                  className="block w-full truncate rounded-lg px-3 py-2 text-left transition-colors hover:bg-white/10 hover:text-white"
                >
                  {item.title}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div ref={scrollAreaRef} className="min-h-0 flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg) => {
          if (msg.role === 'user') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)} className="flex justify-end">
                <div className="max-w-[70%] rounded-[20px] rounded-tr-[6px] bg-[#007AFF] px-4 py-2.5 text-sm text-white shadow-[0_3px_10px_rgba(0,122,255,0.18)]">
                  {msg.content}
                </div>
              </div>
            );
          }
          if (msg.kind === 'text') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)} className="flex justify-start">
                <div className="w-full max-w-[85%]">
                  <ChatMarkdownMessage
                    content={msg.content}
                    isPending={isStreaming && !msg.content}
                    className={isStreaming && !msg.content ? 'w-full min-w-[min(440px,100%)]' : 'w-fit min-w-[min(360px,100%)]'}
                  />
                </div>
              </div>
            );
          }
          if (msg.kind === 'mermaid') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)} className="group relative max-w-[85%]">
                <MermaidDiagram code={msg.content} />
                <button
                  onClick={() => onPinImage?.(msg.id, `mermaid:${msg.content}`, t('deep.diagram'))}
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-white/90 hover:bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity"
                  title={t('deep.pin')}
                >
                  <Pin size={14} />
                </button>
              </div>
            );
          }
          if (msg.kind === 'dalle_pending' || msg.kind === 'dalle_image') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)} className="max-w-[85%]">
                <DalleImage
                  id={msg.id}
                  url={msg.kind === 'dalle_image' ? msg.content : null}
                  reason={msg.reason}
                  pending={msg.kind === 'dalle_pending'}
                  onPin={onPinImage}
                />
              </div>
            );
          }
          if (msg.kind === 'questions') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)}>
                <QuestionsCard items={msg.content} />
              </div>
            );
          }
          if (msg.kind === 'assessment') {
            return (
              <div key={msg.id} ref={el => el && messageRefs.current.set(msg.id, el)}>
                <AssessmentCard data={msg.content} />
              </div>
            );
          }
          return null;
        })}
        {isStreaming && !hasPendingAssistant && (
          <div className="flex justify-start">
            <div className="w-full max-w-[85%] rounded-[22px] rounded-bl-sm border border-teal-100/80 bg-gradient-to-br from-white via-teal-50/70 to-cyan-50/80 px-4 py-3 shadow-[0_10px_30px_rgba(20,184,166,0.08)]">
              <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-teal-500">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
                {t('deep.aiReply')}
              </div>
              <div className="space-y-2">
                <div className="h-3 w-3/4 animate-pulse rounded-full bg-teal-100" />
                <div className="h-3 w-full animate-pulse rounded-full bg-zinc-100" />
                <div className="h-3 w-4/5 animate-pulse rounded-full bg-zinc-100" />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3 border-t border-black/[0.06] bg-white/75 px-4 py-3 backdrop-blur-xl sm:px-6">
        {showTestConfirm && (
          <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm">
            <p className="text-blue-800 mb-2">{showTestConfirm.message}</p>
            <CommandBar commands={showTestConfirm.commands} onCommand={onSendCommand} />
          </div>
        )}
        {showFailOptions && (
          <div className="rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm">
            <p className="text-yellow-800 mb-2">{showFailOptions.message}</p>
            <CommandBar
              commands={showFailOptions.options.map(o => o.command)}
              labels={Object.fromEntries(showFailOptions.options.map(o => [o.command, o.label]))}
              onCommand={onSendCommand}
            />
          </div>
        )}
        {showCommands && !showTestConfirm && !showFailOptions && (
          <CommandBar commands={['continue', 'expand', 'skip', 'reteach']} onCommand={onSendCommand} />
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming || !canSendMessage}
            placeholder={
              isStreaming
                ? t('deep.input.thinking')
                : canSendMessage
                  ? t('deep.input.answer')
                  : t('deep.input.choose')
            }
            rows={2}
            className="apple-input flex-1 resize-none rounded-xl px-3 py-2 text-sm outline-none disabled:bg-zinc-50 disabled:text-zinc-400"
          />
          <button
            onClick={handleSubmit}
            disabled={isStreaming || !canSendMessage || !input.trim()}
            className="self-end rounded-xl bg-[#007AFF] p-2.5 text-white transition-[background-color,transform] duration-150 hover:bg-[#0071E3] active:scale-[0.95] disabled:opacity-40"
            aria-label={t('deep.send')}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
