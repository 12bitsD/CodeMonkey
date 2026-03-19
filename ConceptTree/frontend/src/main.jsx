/**
 * Application entry point — mounts the React root into the DOM.
 *
 * This is the first file executed by the browser bundle. It performs one job:
 * attach the React component tree to the `#root` element declared in
 * `index.html`. Global base styles (`index.css`) are also imported here so
 * they are loaded before any component renders.
 *
 * React.StrictMode is intentionally kept enabled. In development builds it
 * double-invokes renders and effects to surface accidental side-effects early;
 * it has zero runtime cost in production builds.
 *
 * @module main
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
