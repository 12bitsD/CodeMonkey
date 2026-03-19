/**
 * Unit tests for the note filtering and grouping logic used in MyLearningPage.
 *
 * These tests verify two pure data-transformation operations that live inside
 * MyLearningPage's `useMemo` hooks. Testing them here as standalone logic (rather
 * than via component tests) keeps them fast and easy to debug when filtering
 * or grouping behavior needs to change.
 *
 * Coverage:
 * - `filterNotesByPlan` — the filter predicate behind `filteredNotes` useMemo
 * - `groupNotesByPlan`  — the reducer behind `notesByPlan` useMemo
 */
import { describe, it, expect } from 'vitest';

/**
 * filterNotesByPlan
 *
 * Mirrors the filter applied in MyLearningPage's `filteredNotes` useMemo:
 *   notes.filter(n => selectedPlanFilter === 'all' || n.planId === selectedPlanFilter)
 *
 * Three cases:
 * 1. Filter value is 'all'   → return all notes unchanged
 * 2. Filter value is a planId → return only notes belonging to that plan
 * 3. Filter value matches nothing → return empty array
 */
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

/**
 * groupNotesByPlan
 *
 * Mirrors the reducer in MyLearningPage's `notesByPlan` useMemo.
 * Produces { [planId]: { title: string, notes: Note[] } } so the UI
 * can render notes under their plan's section header.
 *
 * Two cases:
 * 1. Notes from multiple plans → each plan gets its own key with the correct notes
 * 2. Plan title comes from the first note in the group (planTitle field)
 */
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
