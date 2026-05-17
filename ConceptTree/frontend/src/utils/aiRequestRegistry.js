export const createAiRequestRegistry = () => {
  const requests = new Map();
  let counter = 0;

  const begin = (key, options = {}) => {
    const { dedupe = false } = options;
    const existing = requests.get(key);

    if (existing && !existing.signal.aborted) {
      if (dedupe) {
        return { ...existing, deduped: true };
      }
      existing.controller.abort();
    }

    counter += 1;
    const controller = new AbortController();
    const entry = {
      key,
      requestId: `${key}:${Date.now()}:${counter}`,
      controller,
      signal: controller.signal,
      deduped: false,
    };
    requests.set(key, entry);
    return entry;
  };

  const isCurrent = (key, requestId) =>
    requests.get(key)?.requestId === requestId;

  const finish = (key, requestId) => {
    if (isCurrent(key, requestId)) {
      requests.delete(key);
    }
  };

  const abort = (key) => {
    const existing = requests.get(key);
    if (!existing) return;
    existing.controller.abort();
    requests.delete(key);
  };

  const abortMatching = (predicate) => {
    for (const [key, entry] of requests.entries()) {
      if (!predicate(key, entry)) continue;
      entry.controller.abort();
      requests.delete(key);
    }
  };

  const abortAll = () => {
    abortMatching(() => true);
  };

  return {
    begin,
    isCurrent,
    finish,
    abort,
    abortMatching,
    abortAll,
    size: () => requests.size,
  };
};

export default createAiRequestRegistry;
