/**
 * ResourceList — renders a clickable list of external learning resources for a concept node.
 *
 * Safe to include in any node detail panel: it renders nothing when the resource
 * array is absent or empty, so no conditional guard is needed at the call site.
 *
 * Each resource opens in a new browser tab with `rel="noopener noreferrer"` to
 * prevent the opened page from accessing the opener's `window` object (a standard
 * security practice for external links).
 *
 * @example
 * // Typical usage inside a node detail panel
 * <ResourceList resources={node.resources} />
 *
 * // Each resource object shape expected by this component:
 * // { name: string, url: string, reason?: string }
 */

import { ExternalLink } from 'lucide-react';

/**
 * Displays a titled section of external resource links for a concept node.
 *
 * Returns null if `resources` is falsy or an empty array — no wrapper div is
 * added, so layout siblings are unaffected when there are no resources.
 *
 * @param {Object}   props
 * @param {Array<{
 *   name:   string,   - Display name shown as the link label
 *   url:    string,   - Href for the anchor; falls back to '#' if missing
 *   reason: string    - Optional one-line explanation of why this resource is useful
 * }>} props.resources - List of resource objects to render; null/undefined/[] → nothing rendered
 */
export function ResourceList({ resources }) {
  if (!resources?.length) return null;
  return (
    <section className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <ExternalLink size={12} /> 推荐资源
      </h4>
      <div className="space-y-2">
        {resources.map((r, i) => (
          <a
            key={i}
            href={r.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-3 bg-zinc-50 rounded-xl hover:bg-zinc-100 transition-colors"
          >
            <div className="flex-1 min-w-0">
              {/* Resource name truncates at one line so long titles don't break layout */}
              <div className="text-sm font-medium text-zinc-800 truncate">{r.name}</div>
              {/* Reason is optional; rendered only when the field is truthy */}
              {r.reason && <div className="text-xs text-zinc-500 mt-0.5">{r.reason}</div>}
            </div>
            <ExternalLink size={12} className="text-zinc-400 flex-shrink-0 mt-1" />
          </a>
        ))}
      </div>
    </section>
  );
}
