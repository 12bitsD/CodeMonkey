import { renderMarkdown } from "../../utils/markdown";

export default function MarkdownContent({ content, className = "" }) {
  if (!content) return null;

  return (
    <div className={`min-w-0 max-w-full space-y-3 overflow-hidden break-words text-sm leading-7 text-zinc-700 [overflow-wrap:anywhere] ${className}`.trim()}>
      {renderMarkdown(content)}
    </div>
  );
}
