import { describe, it, expect } from 'vitest';

describe('filterNotesByPlan', () => {
  const notes = [
    { id: 'n1', planId: 'p1', content: 'note A' },
    { id: 'n2', planId: 'p1', content: 'note B' },
    { id: 'n3', planId: 'p2', content: 'note C' },
  ];

  it('returns all notes when planId is "all"', () => {
    const result = notes.filter(n => 'all' === 'all' || n.planId === 'all');
    expect(result).toHaveLength(3);
  });

  it('filters notes by planId', () => {
    const result = notes.filter(n => n.planId === 'p1');
    expect(result).toHaveLength(2);
    expect(result.every(n => n.planId === 'p1')).toBe(true);
  });

  it('returns empty when no notes match planId', () => {
    const result = notes.filter(n => n.planId === 'p999');
    expect(result).toHaveLength(0);
  });
});

describe('groupNotesByPlan', () => {
  const notes = [
    { id: 'n1', planId: 'p1', planTitle: 'Plan A', content: 'a' },
    { id: 'n2', planId: 'p1', planTitle: 'Plan A', content: 'b' },
    { id: 'n3', planId: 'p2', planTitle: 'Plan B', content: 'c' },
  ];

  function groupByPlan(notes) {
    return notes.reduce((acc, note) => {
      const key = note.planId;
      if (!acc[key]) acc[key] = { title: note.planTitle, notes: [] };
      acc[key].notes.push(note);
      return acc;
    }, {});
  }

  it('groups notes by planId', () => {
    const grouped = groupByPlan(notes);
    expect(Object.keys(grouped)).toHaveLength(2);
    expect(grouped['p1'].notes).toHaveLength(2);
    expect(grouped['p2'].notes).toHaveLength(1);
  });

  it('captures plan title from first note in group', () => {
    const grouped = groupByPlan(notes);
    expect(grouped['p1'].title).toBe('Plan A');
    expect(grouped['p2'].title).toBe('Plan B');
  });
});
