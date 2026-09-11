const HEADER = /^(?:graph|flowchart)\s+(LR|RL|TD|TB|BT)$/i;
const TOKEN = '([A-Za-z][A-Za-z0-9_-]{0,31})(?:\\[([^\\]\\n]{1,64})\\]|\\(([^)\\n]{1,64})\\)|\\{([^}\\n]{1,64})\\})?';
const EDGE = new RegExp(`^\\s*${TOKEN}\\s*(-->|---|-\\.->|<-->)\\s*${TOKEN}\\s*$`);

const nodeLabel = (id, ...labels) => labels.find(value => value?.trim())?.trim() || id;

export function convertLegacyMermaid(code) {
  if (typeof code !== 'string' || new TextEncoder().encode(code).length > 8 * 1024) return null;
  const lines = code.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const header = lines.length >= 2 ? lines[0].match(HEADER) : null;
  if (!header) return null;

  const nodes = new Map();
  const edges = [];
  for (const line of lines.slice(1)) {
    const match = line.match(EDGE);
    if (!match) return null;
    const [, source, sourceSquare, sourceRound, sourceBrace, arrow, target, targetSquare, targetRound, targetBrace] = match;
    if (!nodes.has(source)) nodes.set(source, nodeLabel(source, sourceSquare, sourceRound, sourceBrace));
    const targetLabel = nodeLabel(target, targetSquare, targetRound, targetBrace);
    if (!nodes.has(target) || targetLabel !== target) nodes.set(target, targetLabel);
    edges.push({
      source,
      target,
      relation: {
        '-->': 'sequence',
        '---': 'related',
        '-.->': 'related',
        '<-->': 'contrasts',
      }[arrow],
    });
  }
  if (nodes.size < 2 || nodes.size > 8 || edges.length < 1 || edges.length > 12) return null;

  return {
    version: 1,
    title: '旧版知识关系图',
    layout: ['LR', 'RL'].includes(header[1].toUpperCase()) ? 'flow' : 'hierarchy',
    nodes: [...nodes.entries()].map(([id, title], index) => ({
      id,
      title: title.slice(0, 32),
      summary: title.slice(0, 96),
      role: index === 0 ? 'core' : 'support',
      details: { key_points: [] },
    })),
    edges,
  };
}

export function normalizeLegacyVisualMessage(message) {
  if (message?.kind !== 'mermaid') return message;
  const spec = convertLegacyMermaid(message.content);
  if (spec) return { ...message, kind: 'diagram', content: spec };
  return {
    id: message.id,
    role: message.role || 'assistant',
    kind: 'legacy_diagram_unavailable',
    content: null,
  };
}

export function migratePinnedVisuals(items) {
  if (!Array.isArray(items)) return [];
  return items.flatMap(item => {
    if (!item?.url?.startsWith('mermaid:')) return [item];
    const spec = convertLegacyMermaid(item.url.slice(8));
    return spec ? [{ id: item.id, kind: 'diagram', content: spec, caption: item.caption }] : [];
  });
}
