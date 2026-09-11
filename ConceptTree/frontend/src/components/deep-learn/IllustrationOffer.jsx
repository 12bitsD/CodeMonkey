import { ImagePlus } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function IllustrationOffer({ id, caption, onGenerate }) {
  const { t } = useLanguage();
  return (
    <div className="my-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-xl bg-white p-2 text-amber-600 shadow-sm">
          <ImagePlus size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
            {t('deep.illustration.offerTitle')}
          </p>
          <p className="mt-1 text-sm leading-6 text-zinc-700">{caption || t('deep.illustration.defaultCaption')}</p>
          <p className="mt-1 text-xs text-zinc-500">{t('deep.illustration.costNote')}</p>
          <button
            type="button"
            onClick={() => onGenerate?.(id)}
            className="mt-3 rounded-full bg-zinc-900 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-black"
          >
            {t('deep.illustration.generate')}
          </button>
        </div>
      </div>
    </div>
  );
}
