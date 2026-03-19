/**
 * MasteryChecklist — shows a read-only list of mastery criteria for a concept node.
 *
 * The circles next to each item are decorative only; this component has no
 * checked/unchecked state. If you need interactive checkboxes, you must add
 * checked state and onChange handling at the parent level.
 *
 * Safe to always render: returns null when `items` is absent or empty, so the
 * parent does not need a conditional guard around this component.
 *
 * @example
 * <MasteryChecklist items={node.masteryItems} />
 *
 * // items is a plain string array — no object shape required:
 * // ['手算 2x3 矩阵相乘', '判断矩阵能否相乘']
 */

import { CheckCircle2 } from 'lucide-react';

/**
 * Renders a titled section listing what a learner must be able to do to master this concept.
 *
 * Returns null when `items` is falsy or empty — no wrapper is injected,
 * so sibling layout is unaffected.
 *
 * @param {Object}   props
 * @param {string[]} props.items - Plain strings describing mastery criteria;
 *                                 null/undefined/[] → nothing rendered
 */
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
            {/* Decorative circle — visual placeholder only, not an interactive checkbox */}
            <span className="mt-1 w-3.5 h-3.5 rounded-full border border-zinc-300 flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
