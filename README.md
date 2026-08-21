# IntelliEdit

An AST-Driven Text Editor with Predictive Autocomplete and AI-Assisted Code Optimization. Developed as a compiler design course project for parsing and optimizing **C** language.

## Project Structure
- `frontend/`: React application utilizing Monaco Editor for a sleek user interface.
- `backend/`: FastAPI Python server utilizing `tree-sitter` for AST parsing and AI mocked endpoints.

## Setup Instructions

### Backend Setup
1. Navigate to the `backend` directory in your terminal.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install the requirements: `pip install -r requirements.txt`
5. Start the backend server: `python server.py`
   *(The server will start at `http://localhost:8000`)*

### Frontend Setup
1. Navigate to the `frontend` directory in another terminal.
2. Start the development server: `npm run dev`
   *(The app will open at `http://localhost:5173`)*

## Features
- **Modern UI**: Glassmorphism design and dark mode.
- **Predictive Autocomplete**: Customized Monaco Editor completions connected to backend.
- **AI Optimization**: Right-side panel that debounces code changes and suggests best practices based on the backend API.
