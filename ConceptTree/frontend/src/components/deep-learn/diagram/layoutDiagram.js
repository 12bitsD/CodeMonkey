export const DIAGRAM_CANVAS_WIDTH = 900;
export const DIAGRAM_CANVAS_HEIGHT = 480;
export const DIAGRAM_NODE_WIDTH = 176;
export const DIAGRAM_NODE_HEIGHT = 92;

const distribute = (count, start, end) => {
  if (count <= 1) return [(start + end) / 2];
  return Array.from({ length: count }, (_, index) => (
    start + ((end - start) * index) / (count - 1)
  ));
};

const flowLayout = (nodes) => {
  const rows = nodes.length > 4 ? [nodes.slice(0, 4), nodes.slice(4)] : [nodes];
  return rows.flatMap((row, rowIndex) => {
    const xs = distribute(row.length, 120, 780);
    const y = rows.length === 1 ? 240 : 150 + rowIndex * 210;
    const ordered = rowIndex % 2 === 0 ? row : [...row].reverse();
    return ordered.map((node, index) => ({ id: node.id, x: xs[index], y }));
  });
};

const hierarchyLayout = (nodes) => {
  const [root, ...children] = nodes;
  const rows = children.length > 4
    ? [children.slice(0, 4), children.slice(4)]
    : [children];
  return [
    { id: root.id, x: 450, y: 82 },
    ...rows.flatMap((row, rowIndex) => {
      const xs = distribute(row.length, 110, 790);
      return row.map((node, index) => ({
        id: node.id,
        x: xs[index],
        y: rows.length === 1 ? 310 : 260 + rowIndex * 150,
      }));
    }),
  ];
};

const radialLayout = (nodes) => {
  const coreIndex = nodes.findIndex(node => node.role === 'core');
  const center = nodes[coreIndex >= 0 ? coreIndex : 0];
  const others = nodes.filter(node => node.id !== center.id);
  return [
    { id: center.id, x: 450, y: 240 },
    ...others.map((node, index) => {
      const angle = (-Math.PI / 2) + (index * Math.PI * 2) / Math.max(others.length, 1);
      return {
        id: node.id,
        x: 450 + Math.cos(angle) * 300,
        y: 240 + Math.sin(angle) * 160,
      };
    }),
  ];
};

const comparisonLayout = (nodes) => nodes.map((node, index) => {
  const side = index % 2;
  const row = Math.floor(index / 2);
  const rowCount = Math.ceil(nodes.length / 2);
  const ys = distribute(rowCount, 100, 380);
  return { id: node.id, x: side === 0 ? 260 : 640, y: ys[row] };
});

const cycleLayout = (nodes) => nodes.map((node, index) => {
  const angle = (-Math.PI / 2) + (index * Math.PI * 2) / nodes.length;
  return {
    id: node.id,
    x: 450 + Math.cos(angle) * 300,
    y: 240 + Math.sin(angle) * 170,
  };
});

export function layoutDiagram(spec) {
  const nodes = Array.isArray(spec?.nodes) ? spec.nodes : [];
  if (nodes.length === 0) return [];
  switch (spec.layout) {
    case 'hierarchy': return hierarchyLayout(nodes);
    case 'radial': return radialLayout(nodes);
    case 'comparison': return comparisonLayout(nodes);
    case 'cycle': return cycleLayout(nodes);
    default: return flowLayout(nodes);
  }
}

