import re
from typing import List, Dict, Set, Tuple, Any

class BasicBlockCFGAnalyzer:
    """
    Implements Module 5 Part 1:
    1. Partition into Basic Blocks using Leader Rules (Slide 37)
    2. Construct Flow Graph edges (Slide 40)
    3. Compute Global Data Flow Analysis: gen[B], kill[B], in[B], out[B] (Slides 24-35)
    """
    def analyze(self, code: str) -> Dict[str, Any]:
        raw_lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('//')]
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

        # STEP 1: Determine Leaders
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
                        "label": "true/jump" if is_conditional else "jump"
                    })

            if not is_unconditional_goto and b_idx + 1 < len(blocks):
                edges.append({
                    "from": b_id,
                    "to": blocks[b_idx + 1]["id"],
                    "label": "fallthrough"
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