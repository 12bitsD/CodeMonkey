export const toggleNodeStatus = (currentStatus) => {
  if (currentStatus === 'learned') return 'unlearned';
  return 'learned';
};

export const isAllComplete = (nodes) => {
  const relevant = nodes.filter(n => n.status !== 'skipped');
  return relevant.length > 0 && relevant.every(n => n.status === 'learned');
};
