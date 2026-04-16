import { renderMarkdown } from "../../utils/markdown";

export default function MarkdownContent({ content, className = "" }) {
  if (!content) return null;

  return (
    <div className={`space-y-3 text-sm leading-7 text-zinc-700 ${className}`.trim()}>
      {renderMarkdown(content)}
    </div>
  );
}
