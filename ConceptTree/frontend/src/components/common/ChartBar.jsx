/**
 * ChartBar — a labeled horizontal progress bar for displaying percentage-based
 * category data (e.g., concept difficulty breakdown in an analytics view).
 *
 * The `value` prop is a 0–100 percentage applied directly as a CSS width.
 * The `color` prop is a Tailwind background-color class string (e.g. `"bg-blue-400"`),
 * giving callers full control over the bar color without internal variant tables.
 *
 * @example
 * <ChartBar label="初级" value={40} color="bg-emerald-400" count={12} />
 * <ChartBar label="中级" value={35} color="bg-amber-400" count={10} />
 * <ChartBar label="高级" value={25} color="bg-red-400"    count={7}  />
 */

import React from 'react';

/**
 * Renders a labeled bar showing a percentage fill and a raw item count.
 *
 * @param {Object} props
 * @param {string} props.label - Category name displayed above the left side of the bar
 * @param {number} props.value - Fill percentage, 0–100; applied as `style={{ width: "${value}%" }}`
 * @param {string} props.color - Tailwind background class for the filled portion (e.g. `"bg-blue-400"`)
 * @param {number} props.count - Raw count displayed to the right of the label (e.g. number of knowledge nodes)
 */
const ChartBar = ({ label, value, color, count }) => (
  <div className="space-y-2">
    <div className="flex justify-between text-xs font-medium text-zinc-500">
      <span>{label}</span>
      <span>{count} 知识点</span>
    </div>
    <div className="h-3 bg-zinc-200/50 rounded-full overflow-hidden">
      {/* Width is set via inline style because Tailwind cannot generate dynamic percentage classes at runtime */}
      <div 
        className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`} 
        style={{ width: `${value}%` }}
      />
    </div>
  </div>
);

export default ChartBar;
