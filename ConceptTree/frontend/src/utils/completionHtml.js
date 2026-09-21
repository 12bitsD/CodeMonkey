const BLOCKED_ELEMENTS = 'script,iframe,object,embed,form,input,button,meta,base,link';

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function isSafeUrl(value, attribute) {
  const url = String(value || '').trim();
  if (!url) return true;
  if (/^(https?:|mailto:|#|\/)/i.test(url)) return true;
  return attribute === 'src' && /^data:image\/(png|jpe?g|gif|webp);base64,/i.test(url);
}

export function sanitizeRenderedHtml(contentHtml) {
  const parsed = new DOMParser().parseFromString(
    `<body>${String(contentHtml || '')}</body>`,
    'text/html',
  );
  parsed.body.querySelectorAll(BLOCKED_ELEMENTS).forEach(element => element.remove());
  parsed.body.querySelectorAll('*').forEach(element => {
    Array.from(element.attributes).forEach(attribute => {
      const name = attribute.name.toLowerCase();
      if (name.startsWith('on') || name === 'style') {
        element.removeAttribute(attribute.name);
        return;
      }
      if ((name === 'href' || name === 'src') && !isSafeUrl(attribute.value, name)) {
        element.removeAttribute(attribute.name);
      }
    });
    if (element.tagName === 'A' && element.hasAttribute('href')) {
      element.setAttribute('rel', 'noopener noreferrer');
    }
  });
  return parsed.body.innerHTML;
}

export function buildCompletionHtmlDocument({
  title,
  contentHtml,
  generatedLabel = '',
  language = 'en-US',
}) {
  const safeTitle = escapeHtml(title);
  const safeGeneratedLabel = escapeHtml(generatedLabel);
  const safeContent = sanitizeRenderedHtml(contentHtml);
  const lang = language === 'zh-CN' ? 'zh-CN' : 'en-US';

  return `<!doctype html>
<html lang="${lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${safeTitle}</title>
  <style>
    :root { color-scheme: light; font-family: Inter, "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif; }
    body { margin: 0; background: #f7f6f3; color: #202020; }
    article { box-sizing: border-box; width: min(860px, calc(100% - 32px)); margin: 40px auto; padding: 48px; border: 1px solid #e4e4e1; border-radius: 18px; background: #fff; }
    h1 { margin: 0 0 32px; font-size: 32px; letter-spacing: -.03em; }
    h2 { margin-top: 32px; font-size: 24px; } h3 { margin-top: 24px; font-size: 19px; }
    p, li { line-height: 1.8; } a { color: #087f73; overflow-wrap: anywhere; }
    pre { overflow-x: auto; padding: 16px; border-radius: 10px; background: #f5f5f4; }
    code { font-family: "SFMono-Regular", Consolas, monospace; }
    table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; border: 1px solid #dededb; text-align: left; }
    img { max-width: 100%; height: auto; } blockquote { margin-left: 0; padding-left: 16px; border-left: 3px solid #14b8a6; color: #52525b; }
    footer { margin-top: 40px; color: #a1a1aa; font-size: 12px; }
    @media (max-width: 640px) { article { margin: 0; width: 100%; padding: 28px 20px; border: 0; border-radius: 0; } }
  </style>
</head>
<body>
  <article>
    <h1>${safeTitle}</h1>
    <main>${safeContent}</main>
    <footer>${safeGeneratedLabel}</footer>
  </article>
</body>
</html>`;
}

export function downloadHtmlDocument(documentHtml, filename) {
  const blob = new Blob([documentHtml], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
