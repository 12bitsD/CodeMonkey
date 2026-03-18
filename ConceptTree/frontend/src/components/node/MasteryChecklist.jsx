import { CheckCircle2 } from 'lucide-react';

export function MasteryChecklist({ items }) {
  if (!items?.length) return null;
  return (
    <section data-testid="mastery-section" className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <CheckCircle2 size={12} /> 掌握标准
      </h4>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-sm text-zinc-600">
            <span className="mt-1 w-3.5 h-3.5 rounded-full border border-zinc-300 flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
