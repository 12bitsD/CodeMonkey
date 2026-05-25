import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { aiApi, mapEdgesFromBackend, mapEdgesToBackend } from './api.js';

describe('Edge Mapping Utility', () => {
  describe('mapEdgesFromBackend', () => {
    it('maps from_node and to_node to from and to, preserving other properties', () => {
      const backendEdges = [{ from_node: 'A', to_node: 'B', style: 'dotted' }];
      const result = mapEdgesFromBackend(backendEdges);
      expect(result).toEqual([{ from: 'A', to: 'B', style: 'dotted' }]);
    });

    it('handles null input gracefully', () => {
      expect(mapEdgesFromBackend(null)).toEqual([]);
    });

    it('handles undefined input gracefully', () => {
      expect(mapEdgesFromBackend(undefined)).toEqual([]);
    });

    it('passes through already-mapped edges safely (防回滚)', () => {
      // Input with from/to (not from_node/to_node) should be preserved
      const mixedEdges = [{ from: 'E', to: 'F', label: 'x' }];
      const result = mapEdgesFromBackend(mixedEdges);
      expect(result[0].from).toBe('E');
      expect(result[0].to).toBe('F');
    });
  });

  describe('mapEdgesToBackend', () => {
    it('maps from and to back to from_node and to_node, preserving other properties', () => {
      const frontendEdges = [{ from: 'C', to: 'D', label: 'x' }];
      const result = mapEdgesToBackend(frontendEdges);
      expect(result).toEqual([{ from_node: 'C', to_node: 'D', label: 'x' }]);
    });

    it('handles null input gracefully', () => {
      expect(mapEdgesToBackend(null)).toEqual([]);
    });
  });
});

describe('aiApi.parseGoal', () => {
  const userProfile = {
    occupation: 'Product Manager',
    education: 'Bachelor',
    programmingLevel: 'beginner',
    mathLevel: 'intermediate',
    abilities: ['Python basics'],
    masteredKnowledge: ['variables', 'loops'],
  };

  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      json: async () => ({
        success: true,
        data: {
          interpretation: 'Understand backpropagation',
          backgroundSummary: [],
          suggestedNodeCount: 5,
          shouldSplit: false,
        },
      }),
      text: async () => JSON.stringify({
        success: true,
        data: {
          interpretation: 'Understand backpropagation',
          backgroundSummary: [],
          suggestedNodeCount: 5,
          shouldSplit: false,
        },
      }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('passes userProfile as userBackground in the parse-goal request', async () => {
    await aiApi.parseGoal('I want to learn backpropagation', userProfile);

    expect(fetch).toHaveBeenCalledWith(
      '/api/ai/parse-goal',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          input: 'I want to learn backpropagation',
          userBackground: userProfile,
        }),
      }),
    );
  });
});
