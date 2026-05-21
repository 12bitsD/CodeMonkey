/**
 * calculateLayout - topological learning-path layout.
 *
 * Edges mean "from is prerequisite of to", so the graph is arranged as:
 * foundations at the top, dependent concepts below, applications last.
 *
 * @param {Array<{id: string, name: string, domain?: string}>} nodes
 * @param {Array<{from_node?: string, to_node?: string, from?: string, to?: string}>} edges
 * @param {string} targetNodeId
 * @returns {{ [nodeId: string]: { x: number, y: number } }}
 */
export function calculateLayout(nodes, edges, targetNodeId) {
  const Y_STEP = 220;
  const X_STEP = 230;

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

  const depth = new Map(nodes.map((node) => [node.id, 0]));
  const queue = nodes
    .filter((node) => indegree.get(node.id) === 0)
    .map((node) => node.id)
    .sort(byName);
  const visited = new Set();

  while (queue.length > 0) {
    const current = queue.shift();
    visited.add(current);
    children.get(current).sort(byName).forEach((childId) => {
      depth.set(childId, Math.max(depth.get(childId), depth.get(current) + 1));
      indegree.set(childId, indegree.get(childId) - 1);
      if (indegree.get(childId) === 0) queue.push(childId);
    });
    queue.sort(byName);
  }

  // If the LLM returns a cycle, still produce a stable layout instead of collapsing nodes.
  nodes.forEach((node) => {
    if (visited.has(node.id)) return;
    const parentDepths = parents.get(node.id).map((id) => depth.get(id) ?? 0);
    depth.set(node.id, parentDepths.length ? Math.max(...parentDepths) + 1 : 0);
  });

  const levels = new Map();
  nodes.forEach((node) => {
    const level = depth.get(node.id) ?? 0;
    if (!levels.has(level)) levels.set(level, []);
    levels.get(level).push(node.id);
  });

  const orderedLevels = [...levels.keys()].sort((a, b) => a - b);
  const indexById = new Map();

  orderedLevels.forEach((level) => {
    levels.get(level).sort(byName);
    levels.get(level).forEach((id, index) => indexById.set(id, index));
  });

  const averageIndex = (ids) => {
    const known = ids
      .map((id) => indexById.get(id))
      .filter((value) => Number.isFinite(value));
    if (known.length === 0) return Number.POSITIVE_INFINITY;
    return known.reduce((sum, value) => sum + value, 0) / known.length;
  };

  // A light barycentric pass keeps edges closer to vertical learning lanes.
  orderedLevels.forEach((level) => {
    const ids = levels.get(level);
    ids.sort(
      (a, b) =>
        averageIndex(parents.get(a)) - averageIndex(parents.get(b)) ||
        byName(a, b),
    );
    ids.forEach((id, index) => indexById.set(id, index));
  });

  [...orderedLevels].reverse().forEach((level) => {
    const ids = levels.get(level);
    ids.sort(
      (a, b) =>
        averageIndex(children.get(a)) - averageIndex(children.get(b)) ||
        byName(a, b),
    );
    ids.forEach((id, index) => indexById.set(id, index));
  });

  const positions = {};
  orderedLevels.forEach((level) => {
    const ids = levels.get(level);
    const targetIndex = ids.indexOf(targetNodeId);
    if (targetIndex > -1) {
      ids.splice(targetIndex, 1);
      ids.splice(Math.floor(ids.length / 2), 0, targetNodeId);
    }

    const totalWidth = (ids.length - 1) * X_STEP;
    const startX = -totalWidth / 2;
    ids.forEach((id, index) => {
      positions[id] = {
        x: Math.round(startX + index * X_STEP),
        y: Math.round(level * Y_STEP),
      };
    });
  });

  return positions;
}
