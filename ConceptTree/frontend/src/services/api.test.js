/**
 * Unit tests for the edge field-mapping utilities in `api.js`.
 *
 * These tests verify that `mapEdgesFromBackend` and `mapEdgesToBackend`
 * correctly translate between the backend's `from_node`/`to_node` field names
 * and the frontend's `from`/`to` field names — and that both functions handle
 * null/undefined inputs without throwing.
 *
 * Run with: `npx vitest` (or `npm test`)
 *
 * @module services/api.test
 */
import { describe, it, expect } from 'vitest';
import { mapEdgesFromBackend, mapEdgesToBackend } from './api.js';

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
