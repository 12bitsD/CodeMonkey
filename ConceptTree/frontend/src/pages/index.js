/**
 * Pages barrel — import all page components from this single file.
 *
 * Add a new export here whenever you create a new page component so that
 * route definitions in App.jsx can stay clean:
 *
 *   import { HomePage, GraphPage } from './pages';
 *
 * Pages registered here:
 * - HomePage       — landing page; goal input + active plan cards
 * - GraphPage      — interactive concept graph for a single learning plan
 * - MyLearningPage — user profile, archived plans, notes, and stats
 * - AuthPage       — login / registration (supports `?redirect=` param)
 */
export { default as HomePage } from './HomePage';
export { default as GraphPage } from './GraphPage';
export { default as MyLearningPage } from './MyLearningPage';
export { default as AuthPage } from './AuthPage';
