import os
import re
import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from features import extract_code_features, OPTIMIZATION_LABELS
from cfg_analyzer import BasicBlockCFGAnalyzer
import ast_engine
import ai_engine

MODEL_PATH = "code_optimizer_model.pkl"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Could not find '{MODEL_PATH}'. Please place the .pkl file downloaded from Google Colab into the backend/ folder."
    )

ml_model = joblib.load(MODEL_PATH)
cfg_analyzer = BasicBlockCFGAnalyzer()

def normalize_c_code(code: str) -> str:
    """
    Normalizes standard C syntax into clean assignment statements 
    so the optimizer can process them.
    """
    lines = code.split('\n')
    normalized = []
    for line in lines:
        l = line.strip()
        # Strip C data types like 'int ', 'float ', 'double ' from declarations
        l = re.sub(r'^\s*(int|float|double|char|long)\s+', '', l)
        # Convert C print statements or trailing semicolons if needed
        l = l.rstrip(';')
        if l:
            normalized.append(l)
    return "\n".join(normalized)

class CompilerOptimizer:
    def __init__(self, model):
        self.ml_model = model

    def pass_constant_folding_and_propagation(self, lines: List[str], logs: List[str]) -> List[str]:
        constants: Dict[str, Any] = {}
        new_lines = []
        for line in lines:
            lhs_match = re.match(r'^(\s*[a-zA-Z_]\w*\s*:?=\s*)(.+?)(;?\s*)$', line)
            if lhs_match and not line.strip().startswith("if"):
                prefix, rhs, suffix = lhs_match.groups()
                lhs_var = re.sub(r'[:=\s]', '', prefix)
                for const_var, const_val in constants.items():
                    if re.search(rf'\b{const_var}\b', rhs):
                        rhs = re.sub(rf'\b{const_var}\b', str(const_val), rhs)
                        logs.append(f"[Constant Propagation] Replaced '{const_var}' with {const_val}")

                def eval_math(match):
                    expr = match.group(0)
                    try:
                        val = eval(expr)
                        res = round(val, 2) if isinstance(val, float) and not val.is_integer() else int(val)
                        logs.append(f"[Constant Folding] Folded '{expr}' -> {res}")
                        return str(res)
                    except Exception:
                        return expr

                rhs = re.sub(
                    r'\(?\b\d+(?:\.\d+)?\s*[\+\-\*\/]\s*\d+(?:\.\d+)?(?:\s*[\+\-\*\/]\s*\d+(?:\.\d+)?)?\b\)?',
                    eval_math,
                    rhs
                )
                if re.match(r'^\d+(?:\.\d+)?$', rhs.strip()):
                    constants[lhs_var] = float(rhs.strip()) if '.' in rhs else int(rhs.strip())
                elif lhs_var in constants:
                    del constants[lhs_var]
                new_lines.append(f"{prefix}{rhs}{suffix}")
            else:
                new_lines.append(line)
        return new_lines

    def pass_algebraic_and_strength_reduction(self, lines: List[str], logs: List[str]) -> List[str]:
        new_lines = []
        for line in lines:
            orig = line
            if re.match(r'^\s*([a-zA-Z_]\w*)\s*:?=\s*\1\s*(\+\s*0|\*\s*1)\s*;?\s*$', line):
                logs.append(f"[Algebraic Simplification] Eliminated identity '{line.strip()}'")
                continue
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\+\s*0\b', r'\1', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\*\s*1\b', r'\1', line)
            line = re.sub(r'\b1\s*\*\s*([a-zA-Z_]\w*)', r'\1', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\^\s*2\b', r'\1 * \1', line)
            line = re.sub(r'\b2\s*\*\s*([a-zA-Z_]\w*)\b', r'\1 + \1', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\*\s*2\b', r'\1 << 1', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\*\s*4\b', r'\1 << 2', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\*\s*8\b', r'\1 << 3', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\/\s*2\b', r'\1 >> 1', line)
            if line != orig:
                logs.append(f"[Strength Reduction / Algebraic] '{orig.strip()}' -> '{line.strip()}'")
            new_lines.append(line)
        return new_lines

    def pass_cse_and_copy_propagation(self, lines: List[str], logs: List[str]) -> List[str]:
        available_exprs: Dict[str, str] = {}
        copies: Dict[str, str] = {}
        new_lines = []
        for line in lines:
            lbl_match = re.match(r'^(\s*[a-zA-Z_]\w*\s*:\s*)(.+)$', line)
            lbl_prefix = lbl_match.group(1) if lbl_match else ""
            stmt_body = lbl_match.group(2) if lbl_match else line

            assign_match = re.match(r'^(\s*)([a-zA-Z_]\w*)(\s*:?=\s*)(.+?)(;?\s*)$', stmt_body)
            if assign_match and not stmt_body.strip().startswith("if"):
                indent, lhs, op, rhs, suffix = assign_match.groups()
                for k, v in copies.items():
                    if re.search(rf'\b{k}\b', rhs):
                        rhs = re.sub(rf'\b{k}\b', v, rhs)
                        logs.append(f"[Copy Propagation] Replaced '{k}' with '{v}' in '{lhs}'")

                if re.search(r'[\+\-\*\/<<>>]', rhs) and rhs in available_exprs:
                    prev_var = available_exprs[rhs]
                    logs.append(f"[Common Subexpression Elimination] Replaced '{rhs}' with '{prev_var}'")
                    rhs = prev_var

                available_exprs = {e: v for e, v in available_exprs.items() if v != lhs and not re.search(rf'\b{lhs}\b', e)}
                copies = {k: v for k, v in copies.items() if k != lhs and v != lhs}

                if re.match(r'^[a-zA-Z_]\w*$', rhs):
                    copies[lhs] = rhs
                elif re.search(r'[\+\-\*\/<<>>]', rhs) and not re.search(rf'\b{lhs}\b', rhs):
                    available_exprs[rhs] = lhs

                new_lines.append(f"{lbl_prefix}{indent}{lhs}{op}{rhs}{suffix}")
            else:
                new_lines.append(line)
        return new_lines

    def pass_dead_and_unreachable_code(self, lines: List[str], logs: List[str]) -> List[str]:
        known_vals: Dict[str, str] = {}
        new_lines = []
        skip_block = False
        for line in lines:
            if skip_block:
                if '}' in line:
                    skip_block = False
                continue
            m_assign = re.match(r'^\s*([a-zA-Z_]\w*)\s*:?=\s*(\d+)\s*;?\s*$', line)
            if m_assign:
                known_vals[m_assign.group(1)] = m_assign.group(2)
            m_if = re.match(r'^\s*if\s*\(\s*([a-zA-Z_]\w*)\s*==\s*(\d+)\s*\)', line)
            if m_if:
                var, val = m_if.groups()
                if var in known_vals and known_vals[var] != val:
                    logs.append(f"[Unreachable Code Elimination] Removed 'if({var} == {val})' since {var}={known_vals[var]}")
                    skip_block = True
                    continue
            new_lines.append(line)
        return new_lines

    def pass_loop_optimization(self, lines: List[str], logs: List[str]) -> List[str]:
        code = "\n".join(lines)
        pattern_while = re.compile(r'while\s*\(\s*([a-zA-Z_]\w*)\s*(<=|<|>=|>)\s*([a-zA-Z_]\w*\s*[\+\-]\s*\d+)\s*\)')
        m_while = pattern_while.search(code)
        if m_while:
            idx_var, cond_op, inv_expr = m_while.groups()
            code = pattern_while.sub(f"N = {inv_expr};\nwhile({idx_var} {cond_op} N)", code)
            logs.append(f"[Loop Code Motion] Hoisted invariant '{inv_expr}' outside loop")

        pattern_for = re.compile(
            r'for\s*\(\s*([a-zA-Z_]\w*)\s*=\s*1\s*;\s*\1\s*<=\s*(\d+)\s*;\s*(?:\+\+\1|\1\+\+)\s*\)\s*\{\s*([a-zA-Z_]\w*)\s*=\s*\1\s*\*\s*(\d+)\s*;\s*\}',
            re.DOTALL
        )
        m_for = pattern_for.search(code)
        if m_for:
            idx, bound, target_var, factor = m_for.groups()
            replacement = (
                f"temp = {factor};\n"
                f"for({idx}=1; {idx}<={bound}; {idx}++) {{\n"
                f"    {target_var} = temp;\n"
                f"    temp = temp + {factor};\n"
                f"}}"
            )
            code = pattern_for.sub(replacement, code)
            logs.append(f"[Induction Variable Elimination] Converted '{target_var} = {idx} * {factor}' to addition")
        return code.split('\n')

    def pass_peephole_optimization(self, lines: List[str], logs: List[str]) -> List[str]:
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if i + 1 < len(lines):
                m1 = re.match(r'^\s*MOV\s+(\w+)\s*,\s*(\w+)\s*$', line, re.IGNORECASE)
                m2 = re.match(r'^\s*MOV\s+(\w+)\s*,\s*(\w+)\s*$', lines[i + 1], re.IGNORECASE)
                if m1 and m2 and m1.group(1) == m2.group(2) and m1.group(2) == m2.group(1):
                    logs.append(f"[Peephole: Redundant Load/Store] Eliminated '{lines[i+1].strip()}'")
                    new_lines.append(line)
                    i += 2
                    continue
                m_g1 = re.match(r'^\s*goto\s+(\w+)\s*$', line, re.IGNORECASE)
                m_g2 = re.match(r'^\s*(\w+)\s*:\s*goto\s+(\w+)\s*$', lines[i + 1], re.IGNORECASE)
                if m_g1 and m_g2 and m_g1.group(1) == m_g2.group(1):
                    logs.append(f"[Peephole: Flow of Control] Collapsed 'goto {m_g1.group(1)}' -> 'goto {m_g2.group(2)}'")
                    new_lines.append(f"goto {m_g2.group(2)}")
                    i += 2
                    continue

            m_inc = re.match(r'^(\s*)([a-zA-Z_]\w*)\s*:?=\s*\2\s*\+\s*1\s*;?\s*$', line)
            if m_inc:
                logs.append(f"[Peephole: Machine Idiom] '{line.strip()}' -> 'INCR {m_inc.group(2)}'")
                new_lines.append(f"{m_inc.group(1)}INCR {m_inc.group(2)}")
                i += 1
                continue

            m_dec = re.match(r'^(\s*)([a-zA-Z_]\w*)\s*:?=\s*\2\s*\-\s*1\s*;?\s*$', line)
            if m_dec:
                logs.append(f"[Peephole: Machine Idiom] '{line.strip()}' -> 'DECR {m_dec.group(2)}'")
                new_lines.append(f"{m_dec.group(1)}DECR {m_dec.group(2)}")
                i += 1
                continue

            new_lines.append(line)
            i += 1
        return new_lines

    def optimize(self, code: str) -> Dict[str, Any]:
        code = normalize_c_code(code)
        features = np.array([extract_code_features(code)])
        preds = self.ml_model.predict(features)[0]
        predicted_passes = [OPTIMIZATION_LABELS[i] for i, val in enumerate(preds) if val == 1]

        lines = code.split('\n')
        logs: List[str] = []
        lines = self.pass_loop_optimization(lines, logs)
        lines = self.pass_dead_and_unreachable_code(lines, logs)
        lines = self.pass_constant_folding_and_propagation(lines, logs)
        lines = self.pass_algebraic_and_strength_reduction(lines, logs)
        lines = self.pass_cse_and_copy_propagation(lines, logs)
        lines = self.pass_peephole_optimization(lines, logs)

        return {
            "ml_predicted_passes": predicted_passes,
            "transformation_logs": logs,
            "optimized_code": "\n".join(lines),
            "cfg_analysis": cfg_analyzer.analyze(code)
        }

app = FastAPI(title="IntelliEdit & ML Code Optimizer API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
optimizer = CompilerOptimizer(ml_model)

class CodeRequest(BaseModel):
    code: str
    cursor_line: int = 0
    cursor_column: int = 0

@app.post("/api/optimize")
async def optimize_endpoint(req: CodeRequest):
    result = optimizer.optimize(req.code)
    try:
        result["optimizations"] = await ai_engine.get_optimizations(req.code)
    except Exception:
        result["optimizations"] = []
    return result

@app.post("/api/autocomplete")
async def autocomplete(req: CodeRequest):
    suggestions = ast_engine.get_completions(req.code, req.cursor_line, req.cursor_column)
    return {"suggestions": suggestions}

@app.post("/api/ast")
async def get_ast(req: CodeRequest):
    tree_data = ast_engine.parse_code_to_json(req.code)
    return {"ast": tree_data}

@app.post("/api/compiler-processes")
async def compiler_processes(req: CodeRequest):
    tokens = ast_engine.get_lexical_tokens(req.code)
    ast_tree = ast_engine.parse_code_to_json(req.code)
    phases_data = await ai_engine.get_compiler_phases(req.code)
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)