const normalizeResourceKey = (resource) => {
  const url = String(resource?.url || "").trim().toLowerCase();
  if (url) return `url:${url}`;

  const name = String(resource?.name || "").trim().toLowerCase();
  return `name:${name}`;
};

export const mergeNodeResources = (resources = [], resourceSearchCache = {}) => {
  const seen = new Set();
  const merged = [];
  const cachedItems = Array.isArray(resourceSearchCache?.items)
    ? resourceSearchCache.items
    : [];

  [...resources, ...cachedItems].forEach((resource) => {
    if (!resource?.name) return;
    const key = normalizeResourceKey(resource);
    if (seen.has(key)) return;
    seen.add(key);
    merged.push(resource);
  });

  return merged;
};

export const hasExpandedResources = (resourceSearchCache = {}) =>
  Array.isArray(resourceSearchCache?.items) && resourceSearchCache.items.length > 0;
