# IntelliEdit Architecture & Workflow

**IntelliEdit** is a full-stack web application designed to act as a modern, educational code editor for the **C** programming language.

It demonstrates how standard compiler phases (Lexical Analysis, Parsing) interact with modern AI models to provide real-time suggestions and code insights.

Here is a detailed breakdown of how the whole system connects and what each file does:

---

## 1. The Big Picture

Whenever you type code in the browser, the **Frontend (React)** sends your code to the **Backend (FastAPI)**. The backend uses a library called `tree-sitter` to parse your C code structurally, and it asks an AI Engine (mocked for now) for code improvements. The frontend then dynamically displays the autocomplete suggestions, AST (Abstract Syntax Tree), and optimizations.

---

## 2. The Frontend (User Interface)

Built with React and Vite, the frontend handles the visual presentation and state.

*   **`frontend/src/App.jsx`**:
    *   This is the main entry point. It holds your `code` state and determines which tab ("AI Suggestions" or "Compiler Processes") is currently active on the right panel.
*   **`frontend/src/components/CodeEditor.jsx`**:
    *   Uses **Monaco Editor** (the same core engine that powers VS Code).
    *   It applies a custom `intelliDark` transparent theme to achieve the "glassmorphism" look.
    *   **How Autocomplete Works:** It registers a custom "Completion Item Provider". When you type, it sends an HTTP POST to `http://localhost:8000/api/autocomplete` on the backend, retrieves suggestions (like `printf` or `for` loops), and injects them right next to your cursor.
*   **`frontend/src/components/SuggestionsPanel.jsx`**:
    *   This runs a "debounce" timer (it waits 1.5 seconds after you stop typing). Once you pause, it sends your code to the backend (`/api/optimize`).
    *   It renders the responses as clean badges (e.g., `performance`, `best-practice`) telling you how to improve your C code.
*   **`frontend/src/components/CompilerProcesses.jsx`** *(and its CSS)*:
    *   Fetches data from `/api/compiler-processes` and displays different stages of a compiler: Lexical tokens (keywords, identifiers), the parsed AST tree, Intermediate Representation (IR), and Target Assembly code.

---

## 3. The Backend (Server Logic)

Built with FastAPI (Python), it exposes REST endpoints that the frontend calls.

*   **`backend/server.py`**:
    *   The router of the backend. It defines API endpoints like `/api/autocomplete`, `/api/optimize`, and `/api/compiler-processes`. It simply receives the incoming code, passes it to the engines below, and returns the JSON responses to the frontend.
*   **`backend/ast_engine.py`**:
    *   The **"Compiler"** brain. It uses `tree-sitter-c` to parse the raw text string of your C code into an intelligent data structure (Abstract Syntax Tree).
    *   `get_lexical_tokens()`: Breaks code into basic elements (words, symbols).
    *   `parse_code_to_json()`: Converts the raw tree into a JSON structure so the frontend can display it visually.
    *   `get_completions()`: Provides context-aware C snippets (currently mocked with static `printf`/`scanf`/`for` templates, but intended to traverse the tree-sitter AST to know what context your cursor is in).
*   **`backend/ai_engine.py`**:
    *   The **"AI"** brain. It is pre-configured to use `google.generativeai` (Gemini API) to analyze your code for improvements.
    *   `get_optimizations()`: Currently returning mock data suggesting you use `const` variables or compiler flags like `-O3` to unroll loops.
    *   `get_compiler_phases()`: Returns mocked but highly realistic compiler logs (like LLVM IR and x86 Assembly) to visually demonstrate what happens when C code is compiled down to machine code.

---

## Summary Workflow

When you type `int main() {`, Monaco detects a change. `SuggestionsPanel` waits 1.5s, sends it to `server.py`, which routes to `ai_engine.py`. Simultaneously, if you trigger autocomplete, `CodeEditor` asks `ast_engine.py` for completions based on the C syntax tree.
