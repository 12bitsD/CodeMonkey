import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  suppressErrorRendering: true,
});
mermaid.setParseErrorHandler?.(() => {});
let _uid = 0;

function removeLeakedMermaidErrors() {
  if (typeof document === 'undefined') return;
  document.querySelectorAll('.error-icon, .error-text').forEach(node => {
    const svg = node.closest('svg');
    if (!svg) return;
    const wrapper = svg.parentElement;
    if (wrapper?.parentElement === document.body) {
      wrapper.remove();
      return;
    }
    svg.remove();
  });
}

export default function MermaidDiagram({ code }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !code) return;
    let cancelled = false;
    const id = `mermaid-${++_uid}`;
    const displayFailure = () => {
      if (!ref.current || cancelled) return;
      removeLeakedMermaidErrors();
      ref.current.replaceChildren();
      ref.current.textContent = '[图表渲染失败]';
    };

    ref.current.replaceChildren();

    mermaid.parse(code, { suppressErrors: true })
      .then((parseResult) => {
        if (!parseResult || cancelled) {
          displayFailure();
          return null;
        }
        return mermaid.render(id, code, ref.current);
      })
      .then((renderResult) => {
        if (!renderResult || !ref.current || cancelled) return;
        removeLeakedMermaidErrors();
        ref.current.replaceChildren();
        ref.current.innerHTML = renderResult.svg;
      })
      .catch(displayFailure);

    return () => {
      cancelled = true;
    };
  }, [code]);
  return <div ref={ref} className="my-3 p-4 bg-zinc-50 rounded-xl border border-zinc-200 overflow-x-auto" />;
}
