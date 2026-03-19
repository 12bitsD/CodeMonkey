/**
 * Badge — a small pill-shaped label that optionally includes a delete button.
 *
 * Use it to display tags, categories, or any short classification text. When
 * `onDelete` is provided, an × button appears inside the badge; omit it for a
 * read-only display badge.
 *
 * Always uses the zinc color palette — no color variants are supported. If you
 * need colored badges, extend the `variants` pattern from Button.jsx.
 *
 * @example
 * // Read-only badge
 * <Badge>线性代数</Badge>
 *
 * // Deletable badge (e.g., in a tag editor)
 * <Badge onDelete={() => removeTag(tag.id)}>线性代数</Badge>
 */

import React from 'react';
import { X } from 'lucide-react';

/**
 * Renders a pill label from `children` text, with an optional × delete button.
 *
 * @param {Object}    props
 * @param {React.ReactNode} props.children  - Text or elements displayed inside the pill
 * @param {Function}  [props.onDelete]      - Called when the × button is clicked;
 *                                            omit this prop to render a read-only badge
 */
const Badge = ({ children, onDelete }) => (
  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 border border-zinc-200/50 transition-colors hover:bg-zinc-200/50">
    {children}
    {onDelete && (
      <button 
        onClick={onDelete} 
        className="ml-2 text-zinc-400 hover:text-zinc-700 focus:outline-none"
      >
        <X size={12} strokeWidth={2.5} />
      </button>
    )}
  </span>
);

export default Badge;
