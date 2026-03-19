/**
 * Vitest global test environment setup — runs once before every test file.
 *
 * Importing `@testing-library/jest-dom` extends Vitest's `expect` with
 * DOM-aware matchers such as `toBeInTheDocument()`, `toHaveTextContent()`,
 * and `toBeVisible()`. Without this import those matchers throw
 * "is not a function" errors at runtime.
 *
 * This file is referenced in `vitest.config.js` (or `vite.config.js`) via
 * the `test.setupFiles` option so Vitest loads it automatically — developers
 * do not need to import it manually in individual test files.
 *
 * @module test-setup
 */
import '@testing-library/jest-dom';
