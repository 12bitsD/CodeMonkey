/**
 * calculateLayout - dependency graph layout.
 *
 * Edges mean "from is prerequisite of to". Always rendered as a reverse
 * right-expand tree (Style 3): foundations on the LEFT, target on the RIGHT.
 *
 * For PURE LINEAR CHAINS (every depth has exactly 1 node) with > 5 nodes,
 * the layout snake-wraps into multiple rows of <= 5 nodes each, with
 * alternating direction (β1).
 *
 * @param {Array<{id: string, name: string, domain?: string}>} nodes
 * @param {Array<{from_node?: string, to_node?: string, from?: string, to?: string}>} edges
 * @param {string} targetNodeId
 * @returns {{ [nodeId: string]: { x: number, y: number } }}
 */

const X_STEP = 280;          // depth-to-depth horizontal spacing
const Y_STEP = 130;          // sibling vertical spacing within a depth
const ROW_HEIGHT = 220;      // vertical spacing between snake-wrap rows
const MAX_NODES_PER_ROW = 5; // snake-wrap threshold

export function calculateLayout(nodes, edges, targetNodeId) {
  if (!Array.isArray(nodes) || nodes.length === 0) return {};

  const nodeIds = new Set(nodes.map((node) => node.id));
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const normalizedEdges = (edges || [])
    .map((edge) => ({
      from: edge.from_node || edge.from,
      to: edge.to_node || edge.to,
    }))
    .filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));

  const parents = new Map(nodes.map((node) => [node.id, []]));
  const children = new Map(nodes.map((node) => [node.id, []]));
  const indegree = new Map(nodes.map((node) => [node.id, 0]));

  normalizedEdges.forEach(({ from, to }) => {
    parents.get(to).push(from);
    children.get(from).push(to);
    indegree.set(to, indegree.get(to) + 1);
  });

  const byName = (a, b) => {
    const nodeA = nodeById.get(a);
    const nodeB = nodeById.get(b);
    return (
      (nodeA?.domain || "").localeCompare(nodeB?.domain || "") ||
      (nodeA?.name || "").localeCompare(nodeB?.name || "") ||
      a.localeCompare(b, undefined, { numeric: true })
    );
  };

  // Topological depth assignment.
  const depth = new Map(nodes.map((node) => [node.id, 0]));
  const queue = nodes
    .filter((node) => indegree.get(node.id) === 0)
    .map((node) => node.id)
    .sort(byName);
  const visited = new Set();

  const indegreeWork = new Map(indegree);
  while (queue.length > 0) {
    const current = queue.shift();
    visited.add(current);
    children.get(current).sort(byName).forEach((childId) => {
      depth.set(childId, Math.max(depth.get(childId), depth.get(current) + 1));
      indegreeWork.set(childId, indegreeWork.get(childId) - 1);
      if (indegreeWork.get(childId) === 0) queue.push(childId);
    });
    queue.sort(byName);
  }
  nodes.forEach((node) => {
    if (visited.has(node.id)) return;
    const parentDepths = parents.get(node.id).map((id) => depth.get(id) ?? 0);
    depth.set(node.id, parentDepths.length ? Math.max(...parentDepths) + 1 : 0);
  });

  // Group by depth.
  const levels = new Map();
  nodes.forEach((node) => {
    const d = depth.get(node.id) ?? 0;
    if (!levels.has(d)) levels.set(d, []);
    levels.get(d).push(node.id);
  });
  const orderedLevels = [...levels.keys()].sort((a, b) => a - b);

  // β1: snake-wrap for pure linear chains > 5 nodes.
  const isPureLinear =
    nodes.length > MAX_NODES_PER_ROW &&
    orderedLevels.every((d) => levels.get(d).length === 1);

  if (isPureLinear) {
    const linearOrder = orderedLevels.map((d) => levels.get(d)[0]);
    const total = linearOrder.length;
    const numRows = Math.ceil(total / MAX_NODES_PER_ROW);
    const perRow = Math.ceil(total / numRows);

    const positions = {};
    linearOrder.forEach((id, i) => {
      const row = Math.floor(i / perRow);
      const colInRow = i % perRow;
      const ltr = row % 2 === 0;
      const x = ltr ? colInRow * X_STEP : (perRow - 1 - colInRow) * X_STEP;
      const y = row * ROW_HEIGHT;
      positions[id] = { x: Math.round(x), y: Math.round(y) };
    });
    return positions;
  }

  // Style 3: reverse right-expand tree (LR, target on the right).
  // Barycentric pass to align siblings under/over their parents.
  const indexById = new Map();
  orderedLevels.forEach((d) => {
    levels.get(d).sort(byName);
    levels.get(d).forEach((id, index) => indexById.set(id, index));
  });
  const averageIndex = (ids) => {
    const known = ids
      .map((id) => indexById.get(id))
      .filter((v) => Number.isFinite(v));
    if (known.length === 0) return Number.POSITIVE_INFINITY;
    return known.reduce((sum, v) => sum + v, 0) / known.length;
  };
  orderedLevels.forEach((d) => {
    const ids = levels.get(d);
    ids.sort(
      (a, b) =>
        averageIndex(parents.get(a)) - averageIndex(parents.get(b)) ||
        byName(a, b),
    );
    ids.forEach((id, index) => indexById.set(id, index));
  });
  [...orderedLevels].reverse().forEach((d) => {
    const ids = levels.get(d);
    ids.sort(
      (a, b) =>
        averageIndex(children.get(a)) - averageIndex(children.get(b)) ||
        byName(a, b),
    );
    ids.forEach((id, index) => indexById.set(id, index));
  });

  const positions = {};
  orderedLevels.forEach((d) => {
    const ids = levels.get(d);
    // Center target within its level so it stays visually anchored.
    const tIdx = ids.indexOf(targetNodeId);
    if (tIdx > -1) {
      ids.splice(tIdx, 1);
      ids.splice(Math.floor(ids.length / 2), 0, targetNodeId);
    }
    const totalCross = (ids.length - 1) * Y_STEP;
    const startY = -totalCross / 2;
    ids.forEach((id, index) => {
      positions[id] = {
        x: Math.round(d * X_STEP),
        y: Math.round(startY + index * Y_STEP),
      };
    });
  });

  return positions;
}
