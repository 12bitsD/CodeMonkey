import { Pin } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function DalleImage({ id, url, reason, onPin, pending = false }) {
  const { t } = useLanguage();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (pending) {
      const t = setTimeout(() => setTimedOut(true), 30000);
      return () => clearTimeout(t);
    }
  }, [pending]);

  if (pending && !url) {
    return (
      <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-dashed border-zinc-300 text-center text-sm text-zinc-500">
        {timedOut ? t('deep.image.failed') : t('deep.image.generating')}
      </div>
    );
  }

  if (!url) {
    return (
      <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-zinc-200 text-center text-sm text-zinc-400">
        {t('deep.image.unavailable')}
      </div>
    );
  }

  return (
    <div className="my-3 group relative inline-block max-w-full">
      <img src={url} alt={reason || ''} className="rounded-xl border border-zinc-200 max-w-full" />
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
