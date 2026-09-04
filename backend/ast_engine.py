import tree_sitter_c as tsc
from tree_sitter import Language, Parser

# Initialize C parser
try:
    C_LANGUAGE = Language(tsc.language())
except TypeError:
    C_LANGUAGE = Language(tsc.language(), "c")

try:
    parser = Parser(C_LANGUAGE)
except TypeError:
    parser = Parser()
    if hasattr(parser, "set_language"):
        parser.set_language(C_LANGUAGE)
    else:
        parser.language = C_LANGUAGE

def parse_code(code: str):
    tree = parser.parse(bytes(code, "utf8"))
    return tree

def get_completions(code: str, line: int, column: int):
    # Dummy logic to simulate AST-driven autocomplete
    tree = parse_code(code)
    
    # Ideally, we would traverse to the cursor position and find context
    # Let's provide some mock basic C suggestions 
    return [
        {"label": "printf", "kind": "Function", "detail": "Print formatted output", "insertText": "printf(\"${1:format}\", ${2:args});"},
        {"label": "scanf", "kind": "Function", "detail": "Read formatted input", "insertText": "scanf(\"${1:format}\", &${2:args});"},
        {"label": "malloc", "kind": "Function", "detail": "Memory allocation", "insertText": "malloc(${1:size});"},
        {"label": "free", "kind": "Function", "detail": "Deallocate memory", "insertText": "free(${1:ptr});"},
        {"label": "for", "kind": "Snippet", "detail": "For loop", "insertText": "for (int ${1:i} = 0; ${1:i} < ${2:count}; ${1:i}++) {\n\t${3}\n}"},
    ]

def traverse_tree(node):
    result = {
        "type": node.type,
        "start_point": [node.start_point[0], node.start_point[1]],
        "end_point": [node.end_point[0], node.end_point[1]],
        "children": []
    }
    for child in node.children:
        result["children"].append(traverse_tree(child))
    return result

def parse_code_to_json(code: str):
    tree = parse_code(code)
    return traverse_tree(tree.root_node)

def get_lexical_tokens(code: str):
    tree = parse_code(code)
    tokens = []
    
    def walk(node):
        if len(node.children) == 0:
            if node.type != "comment": # Usually we might skip comments in lexical phase, but keeping simple
                text = code.encode("utf8")[node.start_byte:node.end_byte].decode("utf8")
                tokens.append({"type": node.type, "value": text})
        for child in node.children:
            walk(child)
            
    walk(tree.root_node)
    return tokens
