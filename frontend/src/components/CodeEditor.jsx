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

      // Register a Code Action Provider for inline ML-driven optimization hints
      const codeActionProvider = monaco.languages.registerCodeActionProvider('c', {
        provideCodeActions: async (model, range) => {
          const lineContent = model.getLineContent(range.startLineNumber);

          // Try the backend ML model first for a richer prediction
          try {
            const response = await axios.post('http://localhost:8000/api/inline-hint', {
              code: lineContent
            });
            const { predicted_passes, suggestion } = response.data;

            if (suggestion) {
              const passLabel = predicted_passes.length > 0
                ? predicted_passes.join(', ')
                : 'Optimization';
              return {
                actions: [
                  {
                    title: `🔧 ML Hint (${passLabel}): apply suggested optimization`,
                    diagnostics: [],
                    kind: 'quickfix',
                    isPreferred: true,
                    edit: {
                      edits: [
                        {
                          resource: model.uri,
                          textEdit: {
                            range: new monaco.Range(
                              range.startLineNumber,
                              1,
                              range.startLineNumber,
                              lineContent.length + 1
                            ),
                            text: suggestion
                          }
                        }
                      ]
                    }
                  }
                ],
                dispose: () => {}
              };
            }
          } catch (err) {
            // Backend unavailable – fall through to client-side heuristics
            console.warn("Inline-hint API unavailable, using client-side fallback:", err.message);
          }

          // Client-side fallback: quick pattern-match for common optimizations
          if (lineContent.includes('* 8') || lineContent.includes('* 4') || lineContent.includes('+ 0')) {
            let suggestedText = lineContent;
            let diagnosticMessage = '';

            if (lineContent.includes('* 8')) {
              suggestedText = lineContent.replace(/\*\s*8/, '<< 3');
              diagnosticMessage = 'Optimize: Replace multiplication by 8 with bitwise shift (Strength Reduction)';
            } else if (lineContent.includes('* 4')) {
              suggestedText = lineContent.replace(/\*\s*4/, '<< 2');
              diagnosticMessage = 'Optimize: Replace multiplication by 4 with bitwise shift (Strength Reduction)';
            } else if (lineContent.includes('+ 0')) {
              suggestedText = lineContent.replace(/\+\s*0/, '').replace(/;\s*$/, ';');
              diagnosticMessage = 'Optimize: Remove redundant addition (Algebraic Simplification)';
            }

            return {
              actions: [
                {
                  title: diagnosticMessage,
                  diagnostics: [],
                  kind: 'quickfix',
                  isPreferred: true,
                  edit: {
                    edits: [
                      {
                        resource: model.uri,
                        textEdit: {
                          range: new monaco.Range(
                            range.startLineNumber,
                            1,
                            range.startLineNumber,
                            lineContent.length + 1
                          ),
                          text: suggestedText
                        }
                      }
                    ]
                  }
                }
              ],
              dispose: () => {}
            };
          }

          return { actions: [], dispose: () => {} };
        }
      });

      return () => {
        provider.dispose();
        codeActionProvider.dispose();
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
