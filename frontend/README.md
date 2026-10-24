# IntelliEdit Frontend

React + Vite application for the ML Code Optimizer & CFG Workbench.

## Setup

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at **http://localhost:5173**.

> **Important:** The backend must be running on **http://localhost:8000** before using the app. See the [root README](../README.md) for backend setup instructions.

## Key Dependencies

- **[@monaco-editor/react](https://www.npmjs.com/package/@monaco-editor/react)** — Monaco Diff Editor for side-by-side code comparison
- **[mermaid](https://www.npmjs.com/package/mermaid)** — Control Flow Graph rendering from backend-generated Mermaid markup
- **[framer-motion](https://www.npmjs.com/package/framer-motion)** — UI animations
- **[lucide-react](https://www.npmjs.com/package/lucide-react)** — Icons

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Build production bundle |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run Oxlint |

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
