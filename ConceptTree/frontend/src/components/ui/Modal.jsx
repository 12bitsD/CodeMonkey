import React from 'react';
import { X } from 'lucide-react';

const Modal = ({ isOpen, onClose, title, children, footer }) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div 
        className="absolute inset-0 bg-zinc-50/80 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      <div className="bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-zinc-100 w-full max-w-lg relative z-10 flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200 overflow-hidden">
        <div className="flex justify-between items-center px-8 py-6 border-b border-zinc-50">
          <h3 className="text-lg font-semibold text-zinc-900 tracking-tight">{title}</h3>
          <button 
            onClick={onClose} 
            className="p-2 -mr-2 text-zinc-400 hover:text-zinc-800 transition-colors rounded-full hover:bg-zinc-50"
          >
            <X size={20} strokeWidth={1.5} />
          </button>
        </div>
        <div className="px-8 py-6 overflow-y-auto custom-scrollbar">
          {children}
        </div>
        {footer && (
          <div className="px-8 py-6 border-t border-zinc-50 bg-zinc-50/30 flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;
