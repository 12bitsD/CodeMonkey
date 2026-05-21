import React from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

function sanitizeLatex(input) {
  return String(input || "")
    .trim()
    .replace(/^\\\(/, "")
    .replace(/\\\)$/, "")
    .replace(/^\\\[/, "")
    .replace(/\\\]$/, "")
    .replace(/^\$\$/, "")
    .replace(/\$\$$/, "")
    .replace(/\\beginbmatrix/g, "\\begin{bmatrix}")
    .replace(/\\endbmatrix/g, "\\end{bmatrix}")
    .replace(/\\beginpmatrix/g, "\\begin{pmatrix}")
    .replace(/\\endpmatrix/g, "\\end{pmatrix}")
    .replace(/\/\/\s*(.*?)\s*\/\//g, "\\|$1\\|")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeLatex(input) {
  return String(input || "")
    .replace(/\\left/g, "")
    .replace(/\\right/g, "")
    .replace(/\\begin\{?bmatrix\}?/g, "[")
    .replace(/\\end\{?bmatrix\}?/g, "]")
    .replace(/\\begin\{?pmatrix\}?/g, "(")
    .replace(/\\end\{?pmatrix\}?/g, ")")
    .replace(/\\mathbf\{([^}]+)\}/g, "$1")
    .replace(/\\mathrm\{([^}]+)\}/g, "$1")
    .replace(/\\mathbb\{R\}/g, "R")
    .replace(/\^\\top/g, "^T")
    .replace(/\\top/g, "^T")
    .replace(/\\mu/g, "mu")
    .replace(/\\lambda/g, "lambda")
    .replace(/\\det/g, "det")
    .replace(/\\min/g, "min")
    .replace(/\\max/g, "max")
    .replace(/\\in/g, "in")
    .replace(/\\geq?/g, ">=")
    .replace(/\\leq?/g, "<=")
    .replace(/\\cdot/g, "*")
    .replace(/\\times/g, "x")
    .replace(/\\nabla/g, "grad")
    .replace(/\\\|/g, "||")
    .replace(/\\\(/g, "")
    .replace(/\\\)/g, "")
    .replace(/\\\[/g, "")
    .replace(/\\\]/g, "")
    .replace(/\^\{([^}]+)\}/g, "^$1")
    .replace(/\^\^/g, "^")
    .replace(/_\{([^}]+)\}/g, "_$1")
    .replace(/\{([^{}]+)\}/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function MathText({ children, block = false }) {
  const latex = sanitizeLatex(children);
  const fallback = normalizeLatex(latex);
  const html = katex.renderToString(latex, {
    displayMode: block,
    output: "html",
    strict: false,
    throwOnError: false,
    trust: false,
  });

  if (block) {
    return (
      <div className="my-3 overflow-x-auto rounded-2xl border border-teal-100 bg-white/80 px-4 py-3 text-[15px] leading-7 text-zinc-900">
        <span dangerouslySetInnerHTML={{ __html: html }} />
        <span className="sr-only">{fallback}</span>
      </div>
    );
  }

  return (
    <span className="inline-flex max-w-full align-baseline text-zinc-900">
      <span dangerouslySetInnerHTML={{ __html: html }} />
      <span className="sr-only">{fallback}</span>
    </span>
  );
}

function renderPlainText(text, keyPrefix) {
  const latexPattern =
    /(\\begin\{?bmatrix\}?[\s\S]+?\\end\{?bmatrix\}?|\\begin\{?pmatrix\}?[\s\S]+?\\end\{?pmatrix\}?|[A-Za-z][A-Za-z0-9_\\{}()[\]\s+\-*/^=<>|&,.]*=\s*[A-Za-z0-9_\\{}()[\]\s+\-*/^=<>|&,.]+|\\(?:det|mathbf|mathrm|mathbb|frac|sqrt|mu|lambda|min|max|in|top|leq?|geq?|cdot|times|nabla)(?:\{[^}]*\})?(?:(?:\s*[A-Za-z0-9()[\]{}_^+\-=<>|,.&]+|\\[A-Za-z]+(?:\{[^}]*\})?)+)?)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = latexPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push({ math: match[0] });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.map((part, index) => {
    const key = `${keyPrefix}-plain-${index}`;
    if (typeof part === "string") {
      return <React.Fragment key={key}>{part}</React.Fragment>;
    }
    return (
      <MathText key={key}>
        {part.math}
      </MathText>
    );
  });
}

function parseInline(text, keyPrefix) {
  const tokenPattern =
    /(\\\(.+?\\\)|\$[^$\n]+\$|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
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
          {normalizeLatex(segment.slice(1, -1))}
        </code>
      );
    }

    if (
      (segment.startsWith("\\(") && segment.endsWith("\\)")) ||
      (segment.startsWith("$") && segment.endsWith("$"))
    ) {
      const content = segment.startsWith("\\(")
        ? segment.slice(2, -2)
        : segment.slice(1, -1);
      return (
        <MathText key={key}>
          {content}
        </MathText>
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

    return <React.Fragment key={key}>{renderPlainText(segment, key)}</React.Fragment>;
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
      if (i < lines.length) i += 1;
      blocks.push({ type: "code", language, content: content.join("\n") });
      continue;
    }

    if (trimmed === "\\[" || trimmed === "$$") {
      const closeToken = trimmed === "\\[" ? "\\]" : "$$";
      const content = [];
      i += 1;
      while (i < lines.length && lines[i].trim() !== closeToken) {
        content.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) i += 1;
      blocks.push({ type: "math", content: content.join(" ") });
      continue;
    }

    const oneLineMath = trimmed.match(/^\\\[(.+)\\\]$/) || trimmed.match(/^\$\$(.+)\$\$$/);
    if (oneLineMath) {
      blocks.push({ type: "math", content: oneLineMath[1] });
      i += 1;
      continue;
    }

    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i + 1])
    ) {
      const splitRow = (row) => row
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map(cell => cell.trim());
      const headers = splitRow(lines[i]);
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].trim().includes("|")) {
        rows.push(splitRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: "table", headers, rows });
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
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
        current === "\\[" ||
        current === "$$" ||
        /^\\\[.+\\\]$/.test(current) ||
        /^\$\$.+\$\$$/.test(current) ||
        current.startsWith(">") ||
        /^#{1,6}\s+/.test(current) ||
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

    if (block.type === "math") {
      return (
        <MathText key={key} block>
          {block.content}
        </MathText>
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

    if (block.type === "table") {
      return (
        <div key={key} className="overflow-x-auto rounded-2xl border border-zinc-200 bg-white">
          <table className="min-w-full border-collapse text-left text-xs">
            <thead className="bg-zinc-50 text-zinc-600">
              <tr>
                {block.headers.map((header, headerIndex) => (
                  <th key={`${key}-h-${headerIndex}`} className="border-b border-zinc-200 px-3 py-2 font-semibold">
                    {parseInline(header, `${key}-h-${headerIndex}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={`${key}-r-${rowIndex}`} className="border-t border-zinc-100">
                  {block.headers.map((_, cellIndex) => (
                    <td key={`${key}-r-${rowIndex}-${cellIndex}`} className="px-3 py-2 align-top text-zinc-700">
                      {parseInline(row[cellIndex] || "", `${key}-r-${rowIndex}-${cellIndex}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <p key={key} className="text-zinc-700">
        {parseInline(block.content, key)}
      </p>
    );
  });
}
