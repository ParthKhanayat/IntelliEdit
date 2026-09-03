from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ast_engine
import ai_engine

app = FastAPI(title="IntelliEdit Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    code: str
    cursor_line: int = 0
    cursor_column: int = 0

@app.post("/api/autocomplete")
async def autocomplete(request: CodeRequest):
    suggestions = ast_engine.get_completions(request.code, request.cursor_line, request.cursor_column)
    return {"suggestions": suggestions}

@app.post("/api/optimize")
async def optimize(request: CodeRequest):
    optimizations = await ai_engine.get_optimizations(request.code)
    return {"optimizations": optimizations}

@app.post("/api/ast")
async def get_ast(request: CodeRequest):
    tree_data = ast_engine.parse_code_to_json(request.code)
    return {"ast": tree_data}

@app.post("/api/compiler-processes")
async def compiler_processes(request: CodeRequest):
    tokens = ast_engine.get_lexical_tokens(request.code)
    ast_tree = ast_engine.parse_code_to_json(request.code)
    phases_data = await ai_engine.get_compiler_phases(request.code)
    
    return {
        "lexical_analysis": tokens,
        "syntax_analysis": ast_tree,
        "semantic_analysis": phases_data["semantic_analysis"],
        "intermediate_code": phases_data["intermediate_code"],
        "code_optimization": phases_data["code_optimization"],
        "target_code": phases_data["target_code"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
