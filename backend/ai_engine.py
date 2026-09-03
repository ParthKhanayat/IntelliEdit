import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# We would configure the API key here once the user provides it in a .env file
# api_key = os.environ.get("GEMINI_API_KEY")
# if api_key:
#     genai.configure(api_key=api_key)

async def get_optimizations(code: str):
    # Mock response for now. 
    # In a real scenario, we'd pass the AST and code to an LLM like Gemini.
    return [
        {
            "line": 1,
            "suggestion": "Consider using 'const' for read-only variables to improve safety and potential compiler optimizations.",
            "type": "best-practice"
        },
        {
            "line": 5,
            "suggestion": "This loop can be optimized by unrolling it or using SIMD instructions if applicable. A compiler flag like -O3 might handle this automatically.",
            "type": "performance"
        }
    ]

async def get_compiler_phases(code: str):
    # Mock response for Semantic Analysis, IR, Optimization, and Target Assembly
    return {
        "semantic_analysis": [
            {"type": "info", "message": "Type checking passed."},
            {"type": "info", "message": "Symbol table populated successfully."},
            {"type": "info", "message": "No undeclared variables found."}
        ],
        "intermediate_code": "; ModuleID = 'main.c'\n; source_filename = \"main.c\"\n\ndefine dso_local i32 @main() {\n  %1 = alloca i32, align 4\n  store i32 0, i32* %1, align 4\n  %2 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([20 x i8], [20 x i8]* @.str, i64 0, i64 0))\n  ret i32 0\n}\n\ndeclare dso_local i32 @printf(i8*, ...)",
        "code_optimization": [
            "Constant folding performed.",
            "Dead code elimination passed. No unreachable code found.",
            "Register allocation optimized for loop variables."
        ],
        "target_code": "\t.file\t\"main.c\"\n\t.text\n\t.globl\tmain\n\t.type\tmain, @function\nmain:\n.LFB0:\n\tpushq\t%rbp\n\tmovq\t%rsp, %rbp\n\tleaq\t.LC0(%rip), %rdi\n\tmovl\t$0, %eax\n\tcall\tprintf@PLT\n\tmovl\t$0, %eax\n\tpopq\t%rbp\n\tret\n.LFE0:\n\t.size\tmain, .-main\n\t.section\t.rodata\n.LC0:\n\t.string\t\"Hello IntelliEdit!\\n\""
    }
