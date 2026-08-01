import { Pin } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function DalleImage({ id, url, reason, onPin, pending = false }) {
  const { language, t } = useLanguage();
  const [timedOut, setTimedOut] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const reasonMatchesLanguage = reason && (
    (language === 'en' && !/[\u3400-\u9fff]/.test(reason))
    || (language === 'zh-CN' && /[\u3400-\u9fff]/.test(reason))
  );
  const diagramTopic = reasonMatchesLanguage ? reason : t('deep.image.fallbackTopic');

  useEffect(() => {
    setTimedOut(false);
    setLoadFailed(false);
    if (pending) {
      const timeoutId = setTimeout(() => setTimedOut(true), 30000);
      return () => clearTimeout(timeoutId);
    }
  }, [pending, url]);

  if (pending && !url && !timedOut) {
    return (
      <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-dashed border-zinc-300 text-center text-sm text-zinc-500">
        {t('deep.image.generating')}
      </div>
    );
  }

  if (!url || timedOut || loadFailed) {
    return (
      <div className="my-3 overflow-hidden rounded-xl border border-black/[0.1] bg-[#fbfbfa] p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
            {t('deep.image.fallbackTitle')}
          </p>
          <span className="text-[11px] text-zinc-400">{t('deep.image.fallbackNote')}</span>
        </div>
        <svg
          role="img"
          aria-label={t('deep.image.fallbackAria', { name: diagramTopic })}
          viewBox="0 0 720 210"
          className="h-auto w-full"
        >
          <defs>
            <marker id={`arrow-${id}`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 Z" fill="#a1a1aa" />
            </marker>
          </defs>
          <text x="360" y="24" textAnchor="middle" fill="#3f3f46" fontSize="13" fontWeight="600">
            {diagramTopic}
          </text>
          <line x1="206" y1="116" x2="268" y2="116" stroke="#a1a1aa" strokeWidth="2" markerEnd={`url(#arrow-${id})`} />
          <line x1="452" y1="116" x2="514" y2="116" stroke="#a1a1aa" strokeWidth="2" markerEnd={`url(#arrow-${id})`} />
          {[
            [32, t('deep.image.concept')],
            [278, t('deep.image.mechanism')],
            [524, t('deep.image.outcome')],
          ].map(([x, label], index) => (
            <g key={label}>
              <rect x={x} y="72" width="164" height="88" rx="14" fill={index === 1 ? '#f0fdfa' : '#ffffff'} stroke={index === 1 ? '#5eead4' : '#d4d4d8'} />
              <circle cx={x + 24} cy="94" r="5" fill={index === 1 ? '#14b8a6' : '#a1a1aa'} />
              <text x={x + 82} y="122" textAnchor="middle" fill="#27272a" fontSize="14" fontWeight="600">{label}</text>
            </g>
          ))}
        </svg>
      </div>
    );
  }

  return (
    <div className="my-3 group relative inline-block max-w-full">
      <img
        src={url}
        alt={reason || ''}
        onError={() => setLoadFailed(true)}
        className="max-w-full rounded-xl border border-zinc-200"
      />
      <button
        onClick={() => onPin?.(id, url, reason)}
        className="absolute top-2 right-2 p-1.5 rounded-full bg-white/90 hover:bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity"
        title={t('deep.pin')}
      >
        <Pin size={14} />
      </button>
    </div>
  );
}
