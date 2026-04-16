import React from "react";

function parseInline(text, keyPrefix) {
  const tokenPattern = /(`[^`]+`|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const segments = [];
  let lastIndex = 0;
  let match;

  while ((match = tokenPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push(text.slice(lastIndex, match.index));
    }
    segments.push(match[0]);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push(text.slice(lastIndex));
  }

  return segments.map((segment, index) => {
    const key = `${keyPrefix}-${index}`;

    if (segment.startsWith("`") && segment.endsWith("`")) {
      return (
        <code
          key={key}
          className="rounded-md bg-zinc-900/5 px-1.5 py-0.5 font-mono text-[0.92em] text-teal-700"
        >
          {segment.slice(1, -1)}
        </code>
      );
    }

    const linkMatch = segment.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const [, label, href] = linkMatch;
      return (
        <a
          key={key}
          href={href}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-teal-700 underline decoration-teal-300 underline-offset-4 transition-colors hover:text-teal-900"
        >
          {label}
        </a>
      );
    }

    if (
      (segment.startsWith("**") && segment.endsWith("**")) ||
      (segment.startsWith("__") && segment.endsWith("__"))
    ) {
      return <strong key={key}>{parseInline(segment.slice(2, -2), key)}</strong>;
    }

    if (
      (segment.startsWith("*") && segment.endsWith("*")) ||
      (segment.startsWith("_") && segment.endsWith("_"))
    ) {
      return <em key={key}>{parseInline(segment.slice(1, -1), key)}</em>;
    }

    return <React.Fragment key={key}>{segment}</React.Fragment>;
  });
}

function parseBlocks(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    const codeStart = trimmed.match(/^```(\w+)?$/);
    if (codeStart) {
      const language = codeStart[1] || "";
      const content = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        content.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) {
        i += 1;
      }
      blocks.push({ type: "code", language, content: content.join("\n") });
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        content: headingMatch[2],
      });
      i += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const content = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        content.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ type: "blockquote", content: content.join(" ") });
      continue;
    }

    if (/^[-*+]\s+/.test(trimmed)) {
      const items = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*+]\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "list", ordered: false, items });
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "list", ordered: true, items });
      continue;
    }

    const paragraph = [];
    while (i < lines.length) {
      const current = lines[i].trim();
      if (
        !current ||
        current.startsWith("```") ||
        current.startsWith(">") ||
        /^#{1,3}\s+/.test(current) ||
        /^[-*+]\s+/.test(current) ||
        /^\d+\.\s+/.test(current)
      ) {
        break;
      }
      paragraph.push(current);
      i += 1;
    }
    blocks.push({ type: "paragraph", content: paragraph.join(" ") });
  }

  return blocks;
}

export function renderMarkdown(markdown) {
  return parseBlocks(markdown).map((block, index) => {
    const key = `md-block-${index}`;

    if (block.type === "heading") {
      const className =
        block.level === 1
          ? "text-base font-semibold text-zinc-900"
          : block.level === 2
            ? "text-sm font-semibold text-zinc-900"
            : "text-sm font-medium text-zinc-800";
      const Tag = block.level === 1 ? "h1" : block.level === 2 ? "h2" : "h3";
      return (
        <Tag key={key} className={className}>
          {parseInline(block.content, key)}
        </Tag>
      );
    }

    if (block.type === "blockquote") {
      return (
        <blockquote
          key={key}
          className="border-l-2 border-teal-200/90 bg-white/75 px-4 py-3 italic text-zinc-600"
        >
          {parseInline(block.content, key)}
        </blockquote>
      );
    }

    if (block.type === "code") {
      return (
        <pre
          key={key}
          className="overflow-x-auto rounded-2xl border border-zinc-900/5 bg-zinc-950 px-4 py-3 text-[12px] leading-6 text-zinc-100 shadow-inner"
        >
          <code data-language={block.language || undefined}>{block.content}</code>
        </pre>
      );
    }

    if (block.type === "list") {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag
          key={key}
          className={block.ordered ? "ml-5 list-decimal space-y-2" : "ml-5 list-disc space-y-2"}
        >
          {block.items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`}>{parseInline(item, `${key}-${itemIndex}`)}</li>
          ))}
        </ListTag>
      );
    }

    return (
      <p key={key} className="text-zinc-700">
        {parseInline(block.content, key)}
      </p>
    );
  });
}
