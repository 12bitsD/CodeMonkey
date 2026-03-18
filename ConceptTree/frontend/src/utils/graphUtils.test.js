import { describe, it, expect } from 'vitest';
import { toggleNodeStatus, isAllComplete } from './graphUtils';

describe('toggleNodeStatus', () => {
  it('toggles unlearned to learned', () => {
    expect(toggleNodeStatus('unlearned')).toBe('learned');
  });

  it('toggles learned to unlearned', () => {
    expect(toggleNodeStatus('learned')).toBe('unlearned');
  });

  it('toggles skipped to learned', () => {
    expect(toggleNodeStatus('skipped')).toBe('learned');
  });
});

describe('isAllComplete', () => {
  it('returns true when all non-skipped nodes are learned', () => {
    const nodes = [
      { id: 'n1', status: 'learned' },
      { id: 'n2', status: 'learned' },
      { id: 'n3', status: 'skipped' },
    ];
    expect(isAllComplete(nodes)).toBe(true);
  });

  it('returns false when any non-skipped node is unlearned', () => {
    const nodes = [
      { id: 'n1', status: 'learned' },
      { id: 'n2', status: 'unlearned' },
    ];
    expect(isAllComplete(nodes)).toBe(false);
  });

  it('returns false for empty array', () => {
    expect(isAllComplete([])).toBe(false);
  });

  it('returns false when all nodes are skipped', () => {
    const nodes = [{ id: 'n1', status: 'skipped' }];
    expect(isAllComplete(nodes)).toBe(false);
  });
});
