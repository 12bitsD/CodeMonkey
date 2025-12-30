import React from 'react';
import { X } from 'lucide-react';

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
