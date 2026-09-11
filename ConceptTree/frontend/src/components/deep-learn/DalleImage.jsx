import { AlertCircle, Pin } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function DalleImage({ id, url, reason, onPin, pending = false }) {
  const { t } = useLanguage();
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    setLoadFailed(false);
  }, [url]);

  if (pending && !url) {
    return (
      <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-dashed border-zinc-300 text-center text-sm text-zinc-500">
        {t('deep.image.generating')}
      </div>
    );
  }

  if (!url || loadFailed) {
    return (
      <div role="status" className="my-3 flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        <AlertCircle size={17} className="shrink-0" />
        <span>{t('deep.image.failed')}</span>
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
