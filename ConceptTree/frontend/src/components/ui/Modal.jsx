/**
 * Modal — a centered overlay dialog with a title bar, scrollable body, and
 * optional footer for action buttons.
 *
 * The component adds zero DOM cost when closed: it returns null immediately
 * when `isOpen` is false, so parent components do not need to conditionally
 * render it.
 *
 * Layout anatomy (top → bottom):
 *  1. Semi-transparent backdrop — clicking it calls `onClose`
 *  2. White card with rounded corners (max-width: 32rem, max-height: 85vh)
 *     a. Header — title text + × close button
 *     b. Body   — scrollable `children` area
 *     c. Footer — optional; right-aligned action buttons slot
 *
 * @example
 * // Basic info modal (no footer)
 * <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="节点详情">
 *   <p>内容...</p>
 * </Modal>
 *
 * // Confirmation modal with footer actions
 * <Modal
 *   isOpen={showConfirm}
 *   onClose={() => setShowConfirm(false)}
 *   title="确认删除"
 *   footer={<>
 *     <Button variant="ghost" onClick={() => setShowConfirm(false)}>取消</Button>
 *     <Button variant="danger" onClick={handleDelete}>删除</Button>
 *   </>}
 * >
 *   <p>此操作不可撤销。</p>
 * </Modal>
 */

import React from 'react';
import { X } from 'lucide-react';

/**
 * Renders a full-screen overlay dialog; returns null when `isOpen` is false.
 *
 * @param {Object}          props
 * @param {boolean}         props.isOpen    - Controls visibility; false → no DOM output
 * @param {Function}        props.onClose   - Called when × button or backdrop is clicked
 * @param {string}          props.title     - Heading text shown in the modal header
 * @param {React.ReactNode} props.children  - Scrollable main body content
 * @param {React.ReactNode} [props.footer]  - Right-aligned actions (e.g. Cancel + Confirm buttons);
 *                                            omit to hide the footer section entirely
 */
const Modal = ({ isOpen, onClose, title, children, footer }) => {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      {/* Backdrop — clicking outside the card dismisses the modal */}
      <div 
        className="absolute inset-0 bg-zinc-50/80 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      <div className="bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-zinc-100 w-full max-w-lg relative z-10 flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-200 overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center px-8 py-6 border-b border-zinc-50">
          <h3 className="text-lg font-semibold text-zinc-900 tracking-tight">{title}</h3>
          <button 
            onClick={onClose} 
            className="p-2 -mr-2 text-zinc-400 hover:text-zinc-800 transition-colors rounded-full hover:bg-zinc-50"
          >
            <X size={20} strokeWidth={1.5} />
          </button>
        </div>

        {/* Scrollable body — custom-scrollbar class defined globally in index.css */}
        <div className="px-8 py-6 overflow-y-auto custom-scrollbar">
          {children}
        </div>

        {/* Footer — only rendered when a footer prop is supplied */}
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
