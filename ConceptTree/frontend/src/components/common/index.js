/**
 * Common components barrel — import InfoSection, StatCard, and ChartBar from
 * this single path instead of their individual files.
 *
 * Note: ProtectedRoute is intentionally excluded here because it wraps router
 * elements directly and is always imported by path in the route definition file.
 *
 * @example
 * import { InfoSection, StatCard, ChartBar } from '@/components/common';
 */

export { default as InfoSection } from './InfoSection';
export { default as StatCard } from './StatCard';
export { default as ChartBar } from './ChartBar';
