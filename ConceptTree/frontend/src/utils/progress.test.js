import { describe, it, expect } from 'vitest';
import { calculateProgress } from './progress';

describe('calculateProgress', () => {
  it('counts learned vs non-skipped nodes', () => {
    const nodes = [
      { id: 'n1', status: 'learned' },
      { id: 'n2', status: 'unlearned' },
      { id: 'n3', status: 'skipped' },
    ];
    expect(calculateProgress(nodes)).toEqual({ learned: 1, total: 2 });
  });

  it('returns zeros for empty array', () => {
    expect(calculateProgress([])).toEqual({ learned: 0, total: 0 });
  });

  it('returns zeros for null/undefined', () => {
    expect(calculateProgress(null)).toEqual({ learned: 0, total: 0 });
    expect(calculateProgress(undefined)).toEqual({ learned: 0, total: 0 });
  });

  it('counts all learned when no skipped', () => {
    const nodes = [
      { id: 'n1', status: 'learned' },
      { id: 'n2', status: 'learned' },
    ];
    expect(calculateProgress(nodes)).toEqual({ learned: 2, total: 2 });
  });

  it('excludes all skipped from total', () => {
    const nodes = [
      { id: 'n1', status: 'skipped' },
      { id: 'n2', status: 'skipped' },
    ];
    expect(calculateProgress(nodes)).toEqual({ learned: 0, total: 0 });
  });
});
