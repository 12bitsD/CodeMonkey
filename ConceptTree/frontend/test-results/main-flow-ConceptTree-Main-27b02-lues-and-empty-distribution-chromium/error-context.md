# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]: "[plugin:vite:import-analysis] Failed to resolve import \"react-router-dom\" from \"src/App.jsx\". Does the file exist?"
  - generic [ref=e5]: /Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/src/App.jsx:2:55
  - generic [ref=e6]: "16 | } 17 | import React from \"react\"; 18 | import { BrowserRouter, Routes, Route, Navigate } from \"react-router-dom\"; | ^ 19 | import { AuthProvider } from \"./contexts/AuthContext\"; 20 | import { AppProvider } from \"./contexts/AppContext\";"
  - generic [ref=e7]: at formatError (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:44066:46) at TransformContext.error (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:44062:19) at normalizeUrl (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:41845:33) at process.processTicksAndRejections (node:internal/process/task_queues:103:5) at async file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:41999:47 at async Promise.all (index 4) at async TransformContext.transform (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:41915:13) at async Object.transform (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:44356:30) at async loadAndTransform (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:55088:29) at async viteTransformMiddleware (file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/frontend/node_modules/vite/dist/node/chunks/dep-827b23df.js:64699:32
  - generic [ref=e8]:
    - text: Click outside, press Esc key, or fix the code to dismiss.
    - text: You can also disable this overlay by setting
    - code [ref=e9]: server.hmr.overlay
    - text: to
    - code [ref=e10]: "false"
    - text: in
    - code [ref=e11]: vite.config.js.
```