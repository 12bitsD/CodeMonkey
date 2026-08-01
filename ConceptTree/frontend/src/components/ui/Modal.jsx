import React, { useId } from 'react';
import { X } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const Modal = ({ isOpen, onClose, title, children, footer }) => {
  const { t } = useLanguage();
  const titleId = useId();
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6" role="presentation">
      <div
        className="absolute inset-0 bg-black/20 transition-opacity"
        onClick={onClose}
      />
      <div className="relative z-10 flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-black/[0.12] bg-white shadow-[var(--shadow-float)] animate-in fade-in zoom-in-95 duration-200" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="flex items-center justify-between border-b border-black/[0.08] px-5 py-4 sm:px-6">
          <h3 id={titleId} className="text-lg font-semibold tracking-tight text-[var(--color-label)]">{title}</h3>
          <button 
            onClick={onClose} 
            className="-mr-1 flex h-8 w-8 items-center justify-center rounded-md text-zinc-500 transition-[background-color,color,transform] duration-150 hover:bg-black/[0.06] hover:text-zinc-900 active:scale-[0.96]"
            aria-label={t('common.close')}
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-5 custom-scrollbar sm:px-6">
          {children}
        </div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-black/[0.08] bg-[#fbfbfa] px-5 py-4 sm:px-6">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;
