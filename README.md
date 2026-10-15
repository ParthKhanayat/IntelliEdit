# IntelliEdit

An AST-Driven Text Editor with Predictive Autocomplete and AI-Assisted Code Optimization. Developed as a compiler design course project (BCSE307L) for parsing and optimizing **C** language, featuring an **ML-powered Code Optimizer & Control Flow Graph (CFG) Workbench**.

## Project Structure
- `frontend/`: React + Vite application with Monaco Diff Editor and Mermaid CFG visualizer.
- `backend/`: FastAPI Python server with two modes:
  - `server.py` — Original IntelliEdit server (AST parsing via `tree-sitter`, AI mock endpoints).
  - `main.py` — **ML Code Optimizer** (Random Forest model, 6 compiler optimization passes, CFG analysis with reaching definitions).

## Prerequisites

- **Python 3.10+** (with `pip`)
- **Node.js 18+** (with `npm`)

## Setup & Running

### Step 1: Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv

# Activate the virtual environment
# Mac/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 2: Start the Backend Server

You have two backend server options:

#### Unified Server (Recommended) — Runs Both Milestone 1 and Milestone 2

`main.py` now serves as the **unified backend**: it runs both the new ML Optimizer & CFG analyzer AND all original IntelliEdit compiler phases and Tree-Sitter autocomplete on port 8000.

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

The server will start at **http://localhost:8000**.

> **Note:** The frontend has a top navigation tab bar allowing you to switch between the **ML Optimizer & CFG Workbench** (Module 5 update) and the **IntelliEdit C IDE** (30% Milestone demo) with a single click, both served by this single backend!

#### Running Two Independent Servers on Separate Ports (Alternative)

If you need to run `server.py` and `main.py` simultaneously as separate processes:
- **Original server (`server.py`)**: `uvicorn server:app --port 8000`
- **ML Optimizer server (`main.py`)**: `uvicorn main:app --port 8001`

### Step 3: Frontend Setup & Start

Open a **new terminal** (keep the backend running):

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

The app will open at **http://localhost:5173**.

### Quick Start (TL;DR)

```bash
# Terminal 1 — Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

## Features

### ML Code Optimizer & CFG Workbench (`main.py`)
- **Random Forest ML Model**: Predicts which compiler optimization passes to apply based on 10 structural/lexical code features.
- **6 Compiler Optimization Passes**:
  1. Loop Optimization (Code Motion & Induction Variable Elimination)
  2. Dead & Unreachable Code Elimination
  3. Constant Folding & Propagation
  4. Algebraic Simplification & Strength Reduction
  5. Common Subexpression Elimination & Copy Propagation
  6. Peephole Optimization (Machine Idioms, Redundant Load/Store, Jump Chains)
- **Control Flow Graph (CFG)**: Basic block partitioning using leader rules, flow graph edge construction, and Mermaid.js visualization.
- **Reaching Definitions Data Flow Analysis**: Computes gen[B], kill[B], in[B], out[B] for each basic block.
- **Monaco Diff Editor**: Side-by-side comparison of original vs. optimized code with syntax highlighting.
- **4 Built-in Presets**: Pre-loaded code samples from BCSE307L Module 5 slides.

### Original IntelliEdit (`server.py`)
- **Modern UI**: Glassmorphism design and dark mode.
- **Predictive Autocomplete**: Customized Monaco Editor completions connected to backend.
- **AI Optimization**: Right-side panel that debounces code changes and suggests best practices.
- **Compiler Process Visualization**: 6-phase compiler pipeline breakdown (Lexical → Syntax → Semantic → IR → Optimization → Target Code).

## API Endpoints

### ML Optimizer (`main.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/optimize` | Accepts `{ "code": "..." }`, returns optimized code, ML passes, transformation logs, and CFG analysis |

### Original Server (`server.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/autocomplete` | AST-driven code completions |
| POST | `/api/optimize` | AI-powered optimization suggestions |
| POST | `/api/ast` | Parse code to AST JSON |
| POST | `/api/compiler-processes` | Full compiler pipeline breakdown |
