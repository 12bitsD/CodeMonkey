export const calculateProgress = (nodes) => {
  if (!nodes?.length) return { learned: 0, total: 0 };
  const relevant = nodes.filter(n => n.status !== 'skipped');
  const learned = relevant.filter(n => n.status === 'learned').length;
  return { learned, total: relevant.length };
};
