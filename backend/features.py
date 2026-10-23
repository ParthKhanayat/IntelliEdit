import re
from typing import List

OPTIMIZATION_LABELS = [
    "Constant Folding & Propagation",
    "Strength Reduction & Algebraic Simplification",
    "Common Subexpression & Copy Propagation",
    "Dead & Unreachable Code Elimination",
    "Loop Optimization (Code Motion & Induction Var)",
    "Peephole Optimization (Machine Idioms & Jumps)"
]

def extract_code_features(code: str) -> List[float]:
    """
    Extracts 10 structural and lexical features from Intermediate/C/Assembly code
    matching the exact feature order trained in Google Colab.
    """
    lines = [line.strip() for line in code.split('\n') if line.strip() and not line.strip().startswith('//')]
    full_text = "\n".join(lines)

    # 0. Constant arithmetic (22/7, 3.14 * 5) -> Constant Folding
    f_const_arith = len(re.findall(r'\b\d+(?:\.\d+)?\s*[\+\-\*\/]\s*\d+(?:\.\d+)?\b', full_text))

    # 1. Algebraic identities (x + 0, x * 1) -> Algebraic Simplification
    f_identities = len(re.findall(r'[\+\-]\s*0\b|\*\s*1\b|\b1\s*\*', full_text))

    # 2. Power-of-2 mult/div or exponentiation (x*2, x*4, x*8, x/2, x^2, 2*x) -> Strength Reduction
    f_strength = len(re.findall(r'\*\s*[248]\b|\b2\s*\*|\/\s*2\b|\^\s*2\b', full_text))

    # 3. Duplicate RHS expressions -> Common Subexpression Elimination
    rhs_list = []
    for l in lines:
        if '=' in l and not re.match(r'^(if|while|for)\b', l):
            parts = re.split(r':?=', l, maxsplit=1)
            if len(parts) == 2:
                rhs = parts[1].rstrip(';').strip()
                if re.search(r'[\+\-\*\/]', rhs):
                    rhs_list.append(rhs)
    f_duplicate_rhs = len(rhs_list) - len(set(rhs_list))

    # 4. Direct variable copies (x = a) -> Copy Propagation
    f_copies = len(re.findall(r'^\s*[a-zA-Z_]\w*\s*:?=\s*[a-zA-Z_]\w*\s*;?\s*$', full_text, re.MULTILINE))

    # 5. Contradictory conditions -> Dead/Unreachable Code
    f_unreachable = len(re.findall(r'if\s*\(\s*[a-zA-Z_]\w*\s*==\s*\d+\s*\)', full_text))

    # 6. Loop constructs (while / for) -> Loop Optimization
    f_loops = len(re.findall(r'\b(while|for)\b', full_text))

    # 7. Loop multiplication with induction var (i * 5, i * 7)
    f_loop_mult = 1 if (f_loops > 0 and re.search(r'\b[ij]\s*\*\s*\d+', full_text)) else 0

    # 8. Assembly MOV or goto jumps -> Peephole Optimization
    f_peephole_asm = len(re.findall(r'\b(MOV|goto)\b', full_text, re.IGNORECASE))

    # 9. Increment/Decrement patterns (i = i + 1, i = i - 1) -> Machine Idioms
    f_inc_dec = len(re.findall(r'\b([a-zA-Z_]\w*)\s*:?=\s*\1\s*[\+\-]\s*1\b', full_text))

    return [
        float(f_const_arith), float(f_identities), float(f_strength),
        float(f_duplicate_rhs), float(f_copies), float(f_unreachable),
        float(f_loops), float(f_loop_mult), float(f_peephole_asm), float(f_inc_dec)
    ]