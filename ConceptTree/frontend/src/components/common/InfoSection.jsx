/**
 * InfoSection — a consistently styled card section with an icon, title, and a
 * freeform content slot, used to build detail panels for concept nodes.
 *
 * All InfoSection instances share the same zinc card appearance, ensuring visual
 * consistency across any page that uses multiple sections side by side.
 *
 * The `icon` prop accepts a Lucide component reference (not pre-rendered JSX).
 * InfoSection renders it at 14px size internally — do not wrap it in `<Icon />` yourself.
 *
 * @example
 * import { BookOpen } from 'lucide-react';
 *
 * <InfoSection icon={BookOpen} title="学习目标">
 *   <p>理解矩阵乘法的几何意义...</p>
 * </InfoSection>
 */

import React from 'react';

/**
 * Renders a titled card section with a leading icon and arbitrary children content.
 *
 * @param {Object}              props
 * @param {React.ElementType}   props.icon     - Lucide icon component reference (not JSX);
 *                                               rendered at 14px size inside the heading
 * @param {string}              props.title    - Section heading displayed in small uppercase caps
 * @param {React.ReactNode}     props.children - Body content rendered in relaxed, light-weight text
 */
const InfoSection = ({ icon: Icon, title, children }) => (
  <section className="bg-zinc-50/50 p-6 rounded-2xl border border-zinc-100/50">
    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-3 flex items-center gap-2">
      <Icon size={14} /> {title}
    </h4>
    <div className="text-sm text-zinc-700 leading-relaxed font-light">
      {children}
    </div>
  </section>
);

export default InfoSection;
