import re
from typing import List, Dict, Set, Tuple, Any

class BasicBlockCFGAnalyzer:
    """
    Upgraded Analyzer:
    1. Automatically lowers high-level C (for, while, if, +=, ++) into Three-Address Code (TAC)
       matching Module 5 Part 1 Slides 42-46.
    2. Partitions into Basic Blocks using Leader Rules (Slide 37).
    3. Constructs Flow Graph edges (Slide 40) & Reaching Definitions (gen/kill/in/out).
    """

    def _lower_c_to_tac(self, raw_code: str) -> List[str]:
        """
        If the input is high-level C code (contains for/while/main/#include),
        automatically translates it into Three-Address Code (TAC) with explicit labels and gotos.
        If the input is already TAC, leaves it untouched.
        """
        # If code already has explicit 'goto', treat it as Three-Address Code directly
        if re.search(r'\bgoto\b', raw_code, re.IGNORECASE):
            return [l.strip() for l in raw_code.split('\n') if l.strip() and not l.strip().startswith('//')]

        tac_lines: List[str] = []
        block_stack: List[Tuple[str, str, str]] = [] # (type, start_label, exit_label, step_stmt)
        loop_id = 1
        if_id = 1

        for raw_line in raw_code.split('\n'):
            line = raw_line.strip()
            if not line or line.startswith('//') or line.startswith('#include'):
                continue

            # Skip function signature headers like 'int main() {'
            if re.match(r'^(?:int|void|float|double|char)?\s*main\s*\([^)]*\)\s*\{?$', line):
                continue
            if line == '{':
                continue

            # Handle closing brace '}' for loops/conditionals
            if line == '}':
                if block_stack:
                    b_type, start_lbl, exit_lbl, step_stmt = block_stack.pop()
                    if b_type == 'for':
                        if step_stmt:
                            tac_lines.append(step_stmt)
                        tac_lines.append(f"goto {start_lbl}")
                        tac_lines.append(f"{exit_lbl}:")
                    elif b_type == 'while':
                        tac_lines.append(f"goto {start_lbl}")
                        tac_lines.append(f"{exit_lbl}:")
                    elif b_type == 'if':
                        tac_lines.append(f"{exit_lbl}:")
                continue

            # 1. Convert C `for (init; cond; step) {` -> TAC (Matches Slide 46)
            m_for = re.match(r'^for\s*\(\s*([^;]+);\s*([^;]+);\s*([^\)]+)\)\s*\{?$', line)
            if m_for:
                init_s, cond_s, step_s = [s.strip() for s in m_for.groups()]
                # Clean C types like 'int i = 0' -> 'i = 0'
                init_s = re.sub(r'^(?:int|float|double|long|char)\s+', '', init_s)
                # Normalize step 'i++' or '++i' -> 'i = i + 1'
                step_s = re.sub(r'^([a-zA-Z_]\w*)\+\+$\vert{}^\+\+([a-zA-Z_]\w*)$', lambda m: f"{m.group(1) or m.group(2)} = {m.group(1) or m.group(2)} + 1", step_s)
                step_s = re.sub(r'^([a-zA-Z_]\w*)\-\-$\vert{}^\-\-([a-zA-Z_]\w*)$', lambda m: f"{m.group(1) or m.group(2)} = {m.group(1) or m.group(2)} - 1", step_s)

                loop_lbl = f"LOOP_FOR_{loop_id}"
                body_lbl = f"L_BODY_{loop_id}"
                exit_lbl = f"L_EXIT_{loop_id}"
                loop_id += 1

                tac_lines.append(init_s)
                tac_lines.append(f"{loop_lbl}: if {cond_s} goto {body_lbl}")
                tac_lines.append(f"goto {exit_lbl}")
                tac_lines.append(f"{body_lbl}:")
                block_stack.append(('for', loop_lbl, exit_lbl, step_s))
                continue

            # 2. Convert C `while (cond) {` -> TAC (Matches Slide 42 & 44)
            m_while = re.match(r'^while\s*\(\s*([^\)]+)\)\s*\{?$', line)
            if m_while:
                cond_s = m_while.group(1).strip()
                loop_lbl = f"LOOP_WHILE_{loop_id}"
                body_lbl = f"L_BODY_{loop_id}"
                exit_lbl = f"L_EXIT_{loop_id}"
                loop_id += 1

                tac_lines.append(f"{loop_lbl}: if {cond_s} goto {body_lbl}")
                tac_lines.append(f"goto {exit_lbl}")
                tac_lines.append(f"{body_lbl}:")
                block_stack.append(('while', loop_lbl, exit_lbl, ""))
                continue

            # 3. Convert C `if (cond) {` -> TAC
            m_if = re.match(r'^if\s*\(\s*([^\)]+)\)\s*\{?$', line)
            if m_if and 'goto' not in line:
                cond_s = m_if.group(1).strip()
                true_lbl = f"L_TRUE_{if_id}"
                exit_lbl = f"L_ENDIF_{if_id}"
                if_id += 1

                tac_lines.append(f"if {cond_s} goto {true_lbl}")
                tac_lines.append(f"goto {exit_lbl}")
                tac_lines.append(f"{true_lbl}:")
                block_stack.append(('if', true_lbl, exit_lbl, ""))
                continue

            # 4. Clean regular C statements (strip types, semicolons, expand +=, ++)
            stmt = line.rstrip(';').strip()
            stmt = re.sub(r'^(?:int|float|double|long|char)\s+', '', stmt)

            # Expand compound assignments: `sum += i` -> `sum = sum + i`
            m_comp = re.match(r'^([a-zA-Z_]\w*)\s*([\+\-\*\/])=\s*(.+)$', stmt)
            if m_comp:
                v, op, rhs = m_comp.groups()
                stmt = f"{v} = {v} {op} {rhs}"

            # Expand `i++` or `i--`
            stmt = re.sub(r'^([a-zA-Z_]\w*)\+\+$\vert{}^\+\+([a-zA-Z_]\w*)$', lambda m: f"{m.group(1) or m.group(2)} = {m.group(1) or m.group(2)} + 1", stmt)
            stmt = re.sub(r'^([a-zA-Z_]\w*)\-\-$\vert{}^\-\-([a-zA-Z_]\w*)$', lambda m: f"{m.group(1) or m.group(2)} = {m.group(1) or m.group(2)} - 1", stmt)

            if stmt:
                tac_lines.append(stmt)

        return tac_lines

    def analyze(self, code: str) -> Dict[str, Any]:
        raw_lines = self._lower_c_to_tac(code)
        if not raw_lines:
            return {"blocks": [], "edges": [], "mermaid_cfg": "graph TD;"}

        statements: List[str] = []
        label_to_index: Dict[str, int] = {}

        pending_label = None
        for line in raw_lines:
            m_only_label = re.match(r'^([a-zA-Z_]\w*)\s*:\s*$', line)
            if m_only_label:
                pending_label = m_only_label.group(1)
                continue

            m_inline_label = re.match(r'^([a-zA-Z_]\w*)\s*:\s*(.+)$', line)
            if m_inline_label:
                lbl, stmt = m_inline_label.groups()
                label_to_index[lbl] = len(statements)
                statements.append(f"{lbl}: {stmt}")
                pending_label = None
            else:
                if pending_label:
                    label_to_index[pending_label] = len(statements)
                    statements.append(f"{pending_label}: {line}")
                    pending_label = None
                else:
                    statements.append(line)

        n = len(statements)
        if n == 0:
            return {"blocks": [], "edges": [], "mermaid_cfg": "graph TD;"}

        # STEP 1: Determine Leaders (Slide 37)
        leaders: Set[int] = {0}
        for i, stmt in enumerate(statements):
            m_goto = re.search(r'\bgoto\s+\(?([a-zA-Z0-9_]+)\)?', stmt, re.IGNORECASE)
            if m_goto:
                target = m_goto.group(1)
                if target in label_to_index:
                    leaders.add(label_to_index[target])
                elif target.isdigit():
                    idx = int(target) - 1
                    if 0 <= idx < n:
                        leaders.add(idx)
                if i + 1 < n:
                    leaders.add(i + 1)

        sorted_leaders = sorted(leaders)

        # STEP 2: Partition into Basic Blocks
        blocks: List[Dict[str, Any]] = []
        stmt_to_block: Dict[int, str] = {}

        for b_idx, start in enumerate(sorted_leaders):
            end = sorted_leaders[b_idx + 1] if b_idx + 1 < len(sorted_leaders) else n
            b_id = f"B{b_idx + 1}"
            b_stmts = statements[start:end]
            for s_i in range(start, end):
                stmt_to_block[s_i] = b_id

            blocks.append({
                "id": b_id,
                "leader_statement": statements[start],
                "start_line": start + 1,
                "end_line": end,
                "statements": b_stmts
            })

        # STEP 3: Construct Control Flow Graph Edges
        edges: List[Dict[str, str]] = []
        for b_idx, block in enumerate(blocks):
            last_stmt = block["statements"][-1]
            b_id = block["id"]

            m_goto = re.search(r'\bgoto\s+\(?([a-zA-Z0-9_]+)\)?', last_stmt, re.IGNORECASE)
            is_conditional = bool(re.search(r'\bif\b', last_stmt, re.IGNORECASE))
            is_unconditional_goto = bool(m_goto and not is_conditional)

            if m_goto:
                target = m_goto.group(1)
                target_block = None
                if target in label_to_index:
                    target_block = stmt_to_block[label_to_index[target]]
                elif target.isdigit() and (int(target) - 1) in stmt_to_block:
                    target_block = stmt_to_block[int(target) - 1]

                if target_block:
                    edges.append({
                        "from": b_id,
                        "to": target_block,
                        "label": "true" if is_conditional else "jump"
                    })

            if not is_unconditional_goto and b_idx + 1 < len(blocks):
                edges.append({
                    "from": b_id,
                    "to": blocks[b_idx + 1]["id"],
                    "label": "false" if is_conditional else "fallthrough"
                })

        # STEP 4: Reaching Definitions Data Flow (gen, kill, in, out)
        all_defs: Dict[str, Tuple[str, str]] = {}
        var_to_defs: Dict[str, Set[str]] = {}
        def_counter = 1

        for block in blocks:
            block["defs"] = []
            for stmt in block["statements"]:
                clean_stmt = re.sub(r'^[a-zA-Z_]\w*\s*:\s*', '', stmt)
                m_def = re.match(r'^([a-zA-Z_]\w*)\s*:?=\s*(.+)$', clean_stmt)
                if m_def and not clean_stmt.startswith("if"):
                    var = m_def.group(1)
                    d_id = f"d{def_counter}"
                    def_counter += 1
                    all_defs[d_id] = (var, block["id"])
                    var_to_defs.setdefault(var, set()).add(d_id)
                    block["defs"].append((d_id, var, stmt))

        for block in blocks:
            gen_b: Set[str] = set()
            kill_b: Set[str] = set()
            for d_id, var, _ in block["defs"]:
                other_defs = var_to_defs[var] - {d_id}
                kill_b.update(other_defs)
                gen_b = (gen_b - other_defs) | {d_id}

            block["gen"] = sorted(gen_b)
            block["kill"] = sorted(kill_b)
            block["in"] = set()
            block["out"] = set(gen_b)

        block_map = {b["id"]: b for b in blocks}
        changed = True
        while changed:
            changed = False
            for block in blocks:
                b_id = block["id"]
                preds = [e["from"] for e in edges if e["to"] == b_id]
                new_in = set()
                for p in preds:
                    new_in.update(block_map[p]["out"])
                new_out = set(block["gen"]) | (new_in - set(block["kill"]))
                if new_in != block["in"] or new_out != block["out"]:
                    block["in"] = new_in
                    block["out"] = new_out
                    changed = True

        for block in blocks:
            block["in"] = sorted(block["in"])
            block["out"] = sorted(block["out"])
            block["defs"] = [f"{d_id}: {stmt}" for d_id, _, stmt in block["defs"]]

        # STEP 5: Build Mermaid.js Flowchart String
        mermaid_lines = ["graph TD"]
        for block in blocks:
            escaped_stmts = "<br/>".join(s.replace('"', "'") for s in block["statements"])
            mermaid_lines.append(f'    {block["id"]}["<b>{block["id"]} (Leader: Line {block["start_line"]})</b><br/>{escaped_stmts}"]')
        for edge in edges:
            mermaid_lines.append(f'    {edge["from"]} -->|{edge["label"]}| {edge["to"]}')

        return {
            "blocks": blocks,
            "edges": edges,
            "mermaid_cfg": "\n".join(mermaid_lines)
        }