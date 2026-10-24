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
        f"Could not find '{MODEL_PATH}'. Please place the .pkl file into the backend/ folder."
    )

ml_model = joblib.load(MODEL_PATH)
cfg_analyzer = BasicBlockCFGAnalyzer()

# Regex pattern matching optional C type declarations while preserving indentation
C_ASSIGN_PATTERN = re.compile(
    r'^(\s*(?:[a-zA-Z_]\w*\s*:\s*)?(?:(?:int|float|double|long|short|char|unsigned)\s+)?)'
    r'([a-zA-Z_]\w*)'
    r'(\s*:?=\s*)'
    r'(.+?)'
    r'(;?\s*)$'
)

class CompilerOptimizer:
    def __init__(self, model):
        self.ml_model = model

    def pass_constant_folding_and_propagation(self, lines: List[str], logs: List[str]) -> List[str]:
        constants: Dict[str, Any] = {}
        new_lines = []

        # Pre-scan to find variables modified inside loops or via +=, ++, --
        full_code = "\n".join(lines)
        loop_modified_vars = set(re.findall(r'\b([a-zA-Z_]\w*)\s*(?:\+\+|\-\-|[\+\-\*\/]=)', full_code))

        in_loop = False
        for line in lines:
            stripped = line.strip()

            # Track loop entry and kill any constants modified inside the loop
            if re.match(r'^(for|while)\b', stripped):
                in_loop = True
                for v in list(constants.keys()):
                    if re.search(rf'\b{v}\b\s*(?:=|\+=|\-=|\*=|\+\+|\-\-)', full_code):
                        del constants[v]
                new_lines.append(line)
                continue

            # If a line uses +=, -=, *=, /=, ++, or --, kill that variable's constant status
            m_compound = re.match(r'^\s*([a-zA-Z_]\w*)\s*(?:[\+\-\*\/]=|\+\+|\-\-)', stripped)
            if m_compound:
                var_mod = m_compound.group(1)
                if var_mod in constants:
                    del constants[var_mod]
                new_lines.append(line)
                continue

            lhs_match = C_ASSIGN_PATTERN.match(line)
            if lhs_match and not stripped.startswith(("if", "for", "while", "return", "printf")):
                prefix, lhs_var, op, rhs, suffix = lhs_match.groups()

                # Do not propagate a variable into its own re-assignment inside a loop (e.g., sum = sum + 8)
                for const_var, const_val in list(constants.items()):
                    if const_var == lhs_var and in_loop:
                        continue
                    if const_var in loop_modified_vars and in_loop:
                        continue
                    if re.search(rf'\b{const_var}\b', rhs):
                        rhs = re.sub(rf'\b{const_var}\b', str(const_val), rhs)
                        logs.append(f"[Constant Propagation] Replaced '{const_var}' with {const_val}")

                # Evaluate pure numeric expressions (Constant Folding)
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

                # Record constant only if not inside a loop and not modified by loop
                if re.match(r'^\d+(?:\.\d+)?$', rhs.strip()) and not in_loop and lhs_var not in loop_modified_vars:
                    constants[lhs_var] = float(rhs.strip()) if '.' in rhs else int(rhs.strip())
                elif lhs_var in constants:
                    del constants[lhs_var]

                new_lines.append(f"{prefix}{lhs_var}{op}{rhs}{suffix}")
            else:
                new_lines.append(line)
        return new_lines

    def pass_algebraic_and_strength_reduction(self, lines: List[str], logs: List[str]) -> List[str]:
        new_lines = []
        for line in lines:
            orig = line
            # Eliminate self-identity statement `x = x + 0;` or `x = x * 1;`
            if re.match(r'^\s*([a-zA-Z_]\w*)\s*:?=\s*\1\s*(\+\s*0|\*\s*1)\s*;?\s*$', line):
                logs.append(f"[Algebraic Simplification] Eliminated identity '{line.strip()}'")
                continue

            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\+\s*0\b', r'\1', line)
            line = re.sub(r'\b0\s*\+\s*([a-zA-Z_]\w*)\b', r'\1', line)
            line = re.sub(r'\b([a-zA-Z_]\w*)\s*\*\s*1\b', r'\1', line)
            line = re.sub(r'\b1\s*\*\s*([a-zA-Z_]\w*)\b', r'\1', line)
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
            stripped = line.strip()
            if stripped.startswith(("if", "for", "while", "return", "printf", "}")):
                if stripped.startswith(("for", "while")):
                    available_exprs.clear()
                    copies.clear()
                new_lines.append(line)
                continue

            assign_match = C_ASSIGN_PATTERN.match(line)
            if assign_match:
                prefix, lhs, op, rhs, suffix = assign_match.groups()
                for k, v in copies.items():
                    if k != lhs and re.search(rf'\b{k}\b', rhs):
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

                new_lines.append(f"{prefix}{lhs}{op}{rhs}{suffix}")
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
            m_assign = C_ASSIGN_PATTERN.match(line)
            if m_assign and re.match(r'^\d+$', m_assign.group(4).strip()):
                known_vals[m_assign.group(2)] = m_assign.group(4).strip()

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

        # 1. Code Motion in while condition: while(i <= max - 1)
        pattern_while = re.compile(r'(\s*)while\s*\(\s*([a-zA-Z_]\w*)\s*(<=\vert{}<\vert{}>=\vert{}>)\s*([a-zA-Z_]\w*\s*[\+\-]\s*\d+)\s*\)')
        m_while = pattern_while.search(code)
        if m_while:
            indent, idx_var, cond_op, inv_expr = m_while.groups()
            code = pattern_while.sub(f"{indent}int N = {inv_expr};\n{indent}while ({idx_var} {cond_op} N)", code)
            logs.append(f"[Loop Code Motion] Hoisted invariant '{inv_expr}' outside loop")

        # 2. Induction Variable Strength Reduction in for loops: count = i * 7
        pattern_for = re.compile(
            r'(\s*)for\s*\(\s*(?:int\s+)?([a-zA-Z_]\w*)\s*=\s*1\s*;\s*\2\s*<=\s*(\d+)\s*;\s*(?:\+\+\2\vert{}\2\+\+)\s*\)\s*\{\s*(?:int\s+)?([a-zA-Z_]\w*)\s*=\s*\2\s*\*\s*(\d+)\s*;\s*\}',
            re.DOTALL
        )
        m_for = pattern_for.search(code)
        if m_for:
            indent, idx, bound, target_var, factor = m_for.groups()
            replacement = (
                f"{indent}int temp = {factor};\n"
                f"{indent}for (int {idx} = 1; {idx} <= {bound}; {idx}++) {{\n"
                f"{indent}    int {target_var} = temp;\n"
                f"{indent}    temp = temp + {factor};\n"
                f"{indent}}}"
            )
            code = pattern_for.sub(replacement, code)
            logs.append(f"[Induction Variable Elimination] Converted '{target_var} = {idx} * {factor}' to addition")

        # 3. Hoist loop-invariant assignments out of for/while loop bodies (Slide 12)
        loop_body_pattern = re.compile(
            r'(\s*)((?:for|while)\s*\([^\)]+\)\s*\{\n)'
            r'((?:.*\n)*?)'
            r'(\s+)((?:int\s+)?[a-zA-Z_]\w*\s*=\s*[a-zA-Z0-9_]+\s*[\+\-\*\/]\s*[a-zA-Z0-9_]+\s*;)\n',
            re.MULTILINE
        )
        m_inv = loop_body_pattern.search(code)
        if m_inv:
            indent, loop_header, before_stmts, body_indent, inv_stmt = m_inv.groups()
            if not re.search(r'\b(i|j|sum|count)\b', inv_stmt):
                code = loop_body_pattern.sub(
                    f"{indent}{inv_stmt}\n{indent}{loop_header}{before_stmts}",
                    code,
                    count=1
                )
                logs.append(f"[Loop Code Motion] Hoisted loop-invariant statement '{inv_stmt.strip()}' outside loop")

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

            # Only convert i = i + 1 to INCR i if it is TAC/Assembly (no trailing C semicolon)
            m_inc = re.match(r'^(\s*)([a-zA-Z_]\w*)\s*:?=\s*\2\s*\+\s*1\s*$', line)
            if m_inc:
                logs.append(f"[Peephole: Machine Idiom] '{line.strip()}' -> 'INCR {m_inc.group(2)}'")
                new_lines.append(f"{m_inc.group(1)}INCR {m_inc.group(2)}")
                i += 1
                continue

            m_dec = re.match(r'^(\s*)([a-zA-Z_]\w*)\s*:?=\s*\2\s*\-\s*1\s*$', line)
            if m_dec:
                logs.append(f"[Peephole: Machine Idiom] '{line.strip()}' -> 'DECR {m_dec.group(2)}'")
                new_lines.append(f"{m_dec.group(1)}DECR {m_dec.group(2)}")
                i += 1
                continue

            new_lines.append(line)
            i += 1
        return new_lines

    def optimize(self, code: str) -> Dict[str, Any]:
        # 1. Extract 10 features and ask the Random Forest ML model which passes to run
        features = np.array([extract_code_features(code)])
        preds = self.ml_model.predict(features)[0]
        predicted_passes = [OPTIMIZATION_LABELS[i] for i, val in enumerate(preds) if val == 1]

        lines = code.split('\n')
        logs: List[str] = []

        # 2. ML-GATED EXECUTION: Only run passes that the ML Model predicted (preds[i] == 1)
        if preds[4] == 1:
            lines = self.pass_loop_optimization(lines, logs)
        if preds[3] == 1:
            lines = self.pass_dead_and_unreachable_code(lines, logs)
        if preds[0] == 1:
            lines = self.pass_constant_folding_and_propagation(lines, logs)
        if preds[1] == 1 or features[0][1] > 0 or features[0][2] > 0:
            lines = self.pass_algebraic_and_strength_reduction(lines, logs)
        if preds[2] == 1:
            lines = self.pass_cse_and_copy_propagation(lines, logs)
        if preds[5] == 1:
            lines = self.pass_peephole_optimization(lines, logs)

        return {
            "ml_predicted_passes": predicted_passes,
            "transformation_logs": logs,
            "optimized_code": "\n".join(lines),
            "cfg_analysis": cfg_analyzer.analyze(code)
        }

app = FastAPI(title="BCSE307L ML Code Optimizer API")
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
async def autocomplete_endpoint(request: CodeRequest):
    suggestions = ast_engine.get_completions(request.code, request.cursor_line, request.cursor_column)
    return {"suggestions": suggestions}

@app.post("/api/ast")
async def get_ast_endpoint(request: CodeRequest):
    tree_data = ast_engine.parse_code_to_json(request.code)
    return {"ast": tree_data}

@app.post("/api/compiler-processes")
async def compiler_processes_endpoint(request: CodeRequest):
    tokens = ast_engine.get_lexical_tokens(request.code)
    ast_tree = ast_engine.parse_code_to_json(request.code)
    phases_data = await ai_engine.get_compiler_phases(request.code)
    
    return {
        "lexical_analysis": tokens,
        "syntax_analysis": ast_tree,
        "semantic_analysis": phases_data.get("semantic_analysis", []),
        "intermediate_code": phases_data.get("intermediate_code", ""),
        "code_optimization": phases_data.get("code_optimization", []),
        "target_code": phases_data.get("target_code", "")
    }

class InlineHintRequest(BaseModel):
    code: str

@app.post("/api/inline-hint")
def inline_hint_endpoint(req: InlineHintRequest):
    features = np.array([extract_code_features(req.code)])
    preds = ml_model.predict(features)[0]
    predicted_passes = [OPTIMIZATION_LABELS[i] for i, val in enumerate(preds) if val == 1]
    
    suggestion = None
    if preds[1] == 1 or features[0][1] > 0 or features[0][2] > 0:
        if "* 8" in req.code:
            suggestion = re.sub(r'\*\s*8', '<< 3', req.code)
        elif "+ 0" in req.code:
            suggestion = re.sub(r'\+\s*0', '', req.code)

    return {
        "predicted_passes": predicted_passes,
        "suggestion": suggestion
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)