import { CheckCircle2, Circle, HelpCircle } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export function MasteryChecklist({ items, passedKeys = new Set(), getItemKey, onStartQuiz }) {
  const { t } = useLanguage();
  if (!items?.length) return null;
  return (
    <section data-testid="mastery-section" className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <CheckCircle2 size={12} /> {t('node.mastery')}
      </h4>
      <ul className="space-y-2">
        {items.map((item, i) => {
          const key = getItemKey ? getItemKey(item, i) : String(i);
          const passed = passedKeys instanceof Set
            ? passedKeys.has(key)
            : Boolean(passedKeys?.[key]);

          return (
            <li key={key} className="text-sm text-zinc-600">
              <button
                type="button"
                onClick={() => onStartQuiz?.(item, i)}
                className={`group flex w-full items-start gap-3 rounded-2xl px-2 py-1.5 text-left transition-colors ${
                  passed
                    ? "bg-teal-50/70 text-teal-800"
                    : "hover:bg-zinc-50 hover:text-zinc-900"
                }`}
              >
                <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center">
                  {passed ? (
                    <CheckCircle2 size={16} className="text-teal-500" />
                  ) : (
                    <Circle size={15} className="text-zinc-300 group-hover:text-teal-400" />
                  )}
                </span>
                <span className="min-w-0 flex-1 leading-relaxed">{item}</span>
                {!passed && (
                  <HelpCircle
                    size={14}
                    className="mt-0.5 flex-shrink-0 text-zinc-300 group-hover:text-teal-400"
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
