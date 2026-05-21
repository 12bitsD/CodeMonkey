import { useEffect, useState } from 'react';
import { Maximize2, X } from 'lucide-react';
import MermaidDiagram from './MermaidDiagram';

export default function PinnedImages({ pinned = [], onUnpin }) {
  const [previewImage, setPreviewImage] = useState(null);

  useEffect(() => {
    if (!previewImage) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') setPreviewImage(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [previewImage]);

  if (pinned.length === 0) return null;

  const openPreview = (img) => setPreviewImage(img);
  const closePreview = () => setPreviewImage(null);

  const renderPinnedContent = (img, enlarged = false) => {
    if (img.url?.startsWith('mermaid:')) {
      return (
        <div className={enlarged ? 'min-w-[720px]' : 'p-2'}>
          <MermaidDiagram code={img.url.slice(8)} />
        </div>
      );
    }
    if (img.url) {
      return (
        <img
          src={img.url}
          alt={img.caption || ''}
          className={enlarged ? 'max-h-[76vh] w-full object-contain' : 'w-full'}
        />
      );
    }
    return <div className="p-6 text-center text-zinc-400 text-sm">图片加载失败</div>;
  };

  return (
    <>
      <div className="px-4 pb-4 space-y-3 border-t border-zinc-100 pt-3">
        <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">钉图区</p>
        {pinned.map(img => (
          <div key={img.id} className="relative bg-zinc-50 rounded-xl overflow-hidden border border-zinc-200">
            <div
              role="button"
              tabIndex={0}
              onClick={() => openPreview(img)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  openPreview(img);
                }
              }}
              className="group cursor-zoom-in outline-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:ring-offset-2"
            >
              {renderPinnedContent(img)}
              <span className="absolute bottom-2 right-2 rounded-full bg-white/85 p-1.5 text-zinc-600 opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                <Maximize2 size={14} />
              </span>
            </div>
            <button
              type="button"
              aria-label="取消钉图"
              onClick={(event) => {
                event.stopPropagation();
                onUnpin(img.id);
              }}
              className="absolute top-1.5 right-1.5 p-1 rounded-full bg-white/80 hover:bg-white shadow"
            >
              <X size={14} />
            </button>
            {img.caption && <p className="px-3 py-2 text-xs text-zinc-500">{img.caption}</p>}
          </div>
        ))}
      </div>

      {previewImage && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-5"
          onClick={closePreview}
        >
          <div
            className="relative max-h-[88vh] w-full max-w-6xl overflow-auto rounded-xl bg-white p-4 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              aria-label="关闭大图"
              onClick={closePreview}
              className="absolute right-3 top-3 z-10 rounded-full bg-white/90 p-2 text-zinc-700 shadow hover:bg-white"
            >
              <X size={18} />
            </button>
            <div className="pt-6">{renderPinnedContent(previewImage, true)}</div>
            {previewImage.caption && (
              <p className="px-2 pt-3 text-sm text-zinc-600">{previewImage.caption}</p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
