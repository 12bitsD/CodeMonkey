/**
 * Button — a flexible, accessible button with 5 visual variants and 3 sizes,
 * supporting an optional leading icon.
 *
 * This is the single button primitive for the entire app. Always use this
 * component instead of a bare <button> element to ensure consistent styling,
 * focus rings, and disabled behaviour.
 *
 * Variants (controls color/style):
 *  - primary   — dark fill, white text; the default and most prominent action
 *  - secondary — white fill, border; for secondary actions alongside primary
 *  - ghost     — no background until hover; for low-emphasis actions in toolbars
 *  - outline   — thin border, zinc text; between ghost and secondary
 *  - danger    — red tones; for destructive actions (delete, remove)
 *
 * Sizes (controls padding and font size):
 *  - sm — compact inline use
 *  - md — default form/card use
 *  - lg — hero CTAs or prominent page actions
 *
 * @example
 * // Primary action with an icon
 * import { Plus } from 'lucide-react';
 * <Button icon={Plus} onClick={handleAdd}>新增节点</Button>
 *
 * // Danger variant, small size
 * <Button variant="danger" size="sm" onClick={handleDelete}>删除</Button>
 *
 * // Disabled state (reduces opacity and prevents clicks via CSS)
 * <Button disabled>保存</Button>
 */

import React from 'react';

/**
 * Renders an accessible <button> element with variant, size, and optional icon support.
 *
 * @param {Object}          props
 * @param {React.ReactNode} props.children          - Button label text or content
 * @param {'primary'|'secondary'|'ghost'|'outline'|'danger'} [props.variant='primary']
 *                                                  - Visual style; falls back to primary if unrecognised
 * @param {'sm'|'md'|'lg'}  [props.size='md']       - Controls padding and font size
 * @param {string}          [props.className='']    - Extra Tailwind classes merged after variant styles
 * @param {Function}        [props.onClick]         - Click handler
 * @param {React.ElementType} [props.icon]          - Lucide icon component (not JSX) rendered before children;
 *                                                    size scales automatically with the `size` prop
 * @param {boolean}         [props.disabled]        - Disables the button (opacity + no pointer events)
 */
const Button = ({ 
  children, 
  variant = 'primary', 
  className = '', 
  onClick, 
  icon: Icon, 
  disabled, 
  size = 'md' 
}) => {
  const baseStyle = "group relative inline-flex items-center justify-center font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-full focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-zinc-200";
  
  const sizes = {
    sm: "px-4 py-1.5 text-xs",
    md: "px-6 py-2.5 text-sm",
    lg: "px-8 py-3.5 text-base"
  };

  const variants = {
    primary: "bg-zinc-900 text-white hover:bg-zinc-800 shadow-[0_2px_10px_rgba(24,24,27,0.15)] hover:shadow-[0_4px_20px_rgba(24,24,27,0.2)] active:scale-[0.98]",
    secondary: "bg-white text-zinc-700 border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 shadow-sm active:scale-[0.98]",
    ghost: "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100/50 active:scale-[0.98]",
    outline: "border border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 active:scale-[0.98]",
    danger: "text-red-600 bg-red-50 hover:bg-red-100 border border-red-100 active:scale-[0.98]",
  };

  // Falls back to primary styles if an unrecognised variant string is passed
  const variantStyle = variants[variant] || variants.primary;

  return (
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`${baseStyle} ${sizes[size]} ${variantStyle} ${className}`}
    >
      {Icon && (
        <Icon 
          size={size === 'sm' ? 14 : 16} 
          strokeWidth={2} 
          className="mr-2 transition-transform group-hover:scale-105" 
        />
      )}
      {children}
    </button>
  );
};

export default Button;
