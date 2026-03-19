/**
 * StatCard — a centered metric card showing one large number and a small label.
 *
 * Use it in dashboard grids or summary sections to display a key statistic.
 * On hover, the card lifts to a white background with a shadow to signal
 * interactivity — even though the card itself is not clickable by default.
 *
 * Both `value` and `label` are required; there are no defaults. Pass any
 * renderable value (number, string, JSX) as `value`.
 *
 * @example
 * <StatCard label="知识点总数" value={42} />
 * <StatCard label="已掌握" value="73%" />
 */

import React from 'react';

/**
 * Renders a metric card with a large `value` above a small uppercase `label`.
 *
 * @param {Object}          props
 * @param {string}          props.label  - Short descriptive label rendered in small caps below the value
 * @param {React.ReactNode} props.value  - The primary metric to display (number, percentage, or any renderable content)
 */
const StatCard = ({ label, value }) => (
  <div className="bg-zinc-50 border border-zinc-100 p-6 rounded-2xl text-center hover:bg-white hover:shadow-md transition-all">
    <div className="text-3xl font-light text-zinc-900 mb-2">{value}</div>
    <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">{label}</div>
  </div>
);

export default StatCard;
