<p align="center">
  <img src="https://img.shields.io/badge/Built%20by-100%25%20AI-blueviolet?style=for-the-badge" alt="Built by AI">
  <img src="https://img.shields.io/badge/Maintained%20by-AI%20Agents-success?style=for-the-badge" alt="Maintained by AI">
  <img src="https://img.shields.io/badge/Human%20Code-0%25-lightgrey?style=for-the-badge" alt="Human Code 0%">
</p>

<h1 align="center">
  <br>
  <img src="https://api.iconify.design/fluent-emoji:brain.svg" width="80" alt="PathFinder Logo">
  <br>
  PathFinder
  <br>
</h1>

<h4 align="center">
  🧠 AI-Powered Learning Path Generator — Built & Maintained by AI
</h4>

<p align="center">
  <em>Type what you want to learn. Get a knowledge dependency graph. Master anything, one node at a time.</em>
</p>

---

## 🤖 This Project Is Different

**No human wrote this code.** 

This entire project — from architecture design to implementation — was created and is maintained by AI agents. The codebase structure, naming conventions, documentation, and even this README are all optimized for AI comprehension and modification.

> "When AI builds for AI, everything becomes a specification."

---

## 🎯 What Is PathFinder?

PathFinder is a **learning path generator** that transforms any learning goal into a visual knowledge graph with clear dependencies.

**Input:** `"I want to understand backpropagation in deep learning. I know Python but my math is weak."`

**Output:** A beautiful, interactive knowledge graph showing exactly what you need to learn, in what order, with resources and checkpoints.

<p align="center">
  <img src="https://api.iconify.design/fluent-emoji:world-map.svg" width="60">
</p>

### Core Features

| Feature | Description |
|---------|-------------|
| **Smart Goal Parsing** | AI analyzes your input and extracts learning objectives + existing knowledge |
| **Knowledge Graph Generation** | Creates dependency-aware learning paths down to formula level |
| **Adaptive Learning** | Considers your background to skip what you already know |
| **Progress Tracking** | Visual progress on each node: `unlearned → learned → mastered` |
| **Personal Notes** | Markdown notes attached to each knowledge node |
| **Resource Recommendations** | Curated learning materials for each concept |

---

## 🏗️ Architecture Philosophy

This codebase is designed with one principle: **AI-first maintainability**.

```
📁 ConceptTree/
├── 📁 spec/              ← Source of truth. AI reads this FIRST.
│   ├── 前端-架构总览.md   ← Frontend architecture spec
│   ├── 后端-通用规范.md   ← Backend conventions
│   └── ...               ← Page-by-page specifications
├── 📁 backend/           ← FastAPI application
│   ├── routers/          ← API endpoints (1 file = 1 domain)
│   ├── services/         ← Business logic
│   ├── adapters/         ← Database abstraction
│   └── tests/            ← Test-first development
└── 📁 frontend/          ← React + Vite application
    ├── pages/            ← Route components
    ├── components/       ← Reusable UI
    ├── services/         ← API client
    └── contexts/         ← State management
```

### Why This Structure?

1. **Specs Before Code** — Every feature is documented in `/spec` before implementation. AI reads specs, writes tests, then code.

2. **Flat & Explicit** — No deeply nested folders. Each file has a clear, single responsibility.

3. **Convention Over Configuration** — Naming patterns are strict and predictable. AI can infer file locations from names.

4. **Test-Driven** — Tests serve as executable documentation. AI validates its own work.

---

## 🚀 Quick Start

```bash
# One command to rule them all
./start-dev.sh
```

**That's it.** Frontend runs on `http://localhost:5173`, Backend on `http://localhost:8000`.

<details>
<summary>Manual setup (if you must)</summary>

**Backend:**
```bash
cd ConceptTree/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd ConceptTree/frontend
npm install && npm run dev
```
</details>

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **Backend** | FastAPI + Pydantic |
| **Database** | SQLite (local) / Supabase (cloud) |
| **AI Integration** | LLM-powered goal parsing & graph generation |

---

## 📜 The Rules

AI agents follow these rules when modifying this codebase:

1. **Read `/spec` before writing any code**
2. **Update spec first, then write tests, then implement**
3. **Never commit without passing tests**
4. **Mark implementation status in specs** (`✅` / `❌`)
5. **Keep the single source of truth in sync**

These rules exist in `.trae/rules/project_rules.md` and are enforced by the AI development workflow.

---

## 🔮 Roadmap

- [ ] Multi-user support with authentication
- [ ] Cloud sync for learning progress
- [ ] Export learning paths as shareable links
- [ ] Mobile-responsive graph visualization
- [ ] AI tutor integration for each knowledge node

---

## 📊 Project Status

| Component | Status |
|-----------|--------|
| Core Graph Engine | ✅ Complete |
| Goal Parsing AI | ✅ Complete |
| User Authentication | ✅ Complete |
| Frontend UI | ✅ Complete |
| Cloud Database | 🔄 In Progress |
| Mobile Support | ⏳ Planned |

---

## 🤝 Contributing

**Want to contribute?** Here's the twist — you can either:

1. **Submit specs** — Write a feature specification in `/spec` format, and AI will implement it
2. **Code directly** — Traditional PRs welcome, but please update specs accordingly

Remember: In this repo, documentation IS the source code.

---

## 📄 License

MIT License — Use it, fork it, let your AI build upon it.

---

<p align="center">
  <sub>
    Built with 🤖 by AI, for humans who want to learn anything.
  </sub>
</p>
