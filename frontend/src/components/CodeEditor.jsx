import React, { useRef, useEffect } from 'react';
import Editor, { useMonaco } from '@monaco-editor/react';
import axios from 'axios';

const CodeEditor = ({ code, setCode }) => {
  const monaco = useMonaco();
  const editorRef = useRef(null);

  useEffect(() => {
    if (monaco) {
      monaco.editor.defineTheme('intelliDark', {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': '#0f111a00', // Transparent for glassmorphism
          'editor.lineHighlightBackground': '#ffffff10',
        }
      });
      monaco.editor.setTheme('intelliDark');
      
      // Register custom autocomplete provider for C
      const provider = monaco.languages.registerCompletionItemProvider('c', {
        provideCompletionItems: async (model, position) => {
          try {
            // Fetch completions from backend
            const response = await axios.post('http://localhost:8000/api/autocomplete', {
              code: model.getValue(),
              cursor_line: position.lineNumber,
              cursor_column: position.column
            });
            
            const suggestions = response.data.suggestions.map(s => ({
              label: s.label,
              kind: monaco.languages.CompletionItemKind[s.kind] || monaco.languages.CompletionItemKind.Function,
              insertText: s.insertText || s.label,
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              detail: s.detail
            }));
            
            return { suggestions };
          } catch (e) {
            console.error("Autocomplete error:", e);
            return { suggestions: [] };
          }
        }
      });

      return () => {
        provider.dispose();
      }
    }
  }, [monaco]);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
  };

  return (
    <Editor
      height="100%"
      language="c"
      value={code}
      theme="intelliDark"
      onChange={(value) => setCode(value)}
      onMount={handleEditorDidMount}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', monospace",
        fontLigatures: true,
        smoothScrolling: true,
        cursorBlinking: "smooth",
        cursorSmoothCaretAnimation: true,
        formatOnPaste: true,
        padding: { top: 20 }
      }}
    />
  );
};

export default CodeEditor;
