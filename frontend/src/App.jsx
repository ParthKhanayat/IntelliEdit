import React, { useState, useEffect, useRef } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import mermaid from 'mermaid';
import { Cpu, FileCode, Zap, Layers, Activity, GitCompare, CheckCircle2, RefreshCw } from 'lucide-react';

import CodeEditor from './components/CodeEditor';
import CompilerProcesses from './components/CompilerProcesses';
import './App.css';

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

const PRESETS = {
  slide_cfg: `prod := 0
i := 1
L1: t1 := 4 * i
t2 := a[t1]
t3 := 4 * i
t4 := b[t3]
t5 := t2 * t4
t6 := prod + t5
prod := t6
i := i + 1
if i <= 20 goto L1`,
  const_prop: `length = (22 / 7) * d;
pi = 3.14;
r = 5;
Area = pi * r * r;
a := b + c
b := a - d
c := b + c
d := a - d`,
  loop_opt: `while(i <= max - 1) {
    sum = sum + a[i];
}
for(i=1; i<=50; i++) {
    count = i * 7;
}`,
  peephole: `x = 0;
if(x == 1) {
    a = b + 5;
}
y = x + 0;
z = a ^ 2;
w = b * 8;
MOV R0, x
MOV x, R0
goto L1
L1: goto L2
i = i + 1`
};

const DEFAULT_C_CODE = `#include <stdio.h>

int main() {
    printf("Hello IntelliEdit!\\n");
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        sum += i;
    }
    return 0;
}`;

export default function App() {
  // Navigation State: 'ml-optimizer' or 'ide'
  const [activeMode, setActiveMode] = useState('ml-optimizer');

  // ML Optimizer Workbench State
  const [originalCode, setOriginalCode] = useState(PRESETS.slide_cfg);
  const [optimizedCode, setOptimizedCode] = useState("// Click 'Run ML Optimizer & Generate CFG' to view results...");
  const [mlPasses, setMlPasses] = useState([]);
  const [logs, setLogs] = useState([]);
  const [cfgSvg, setCfgSvg] = useState("");
  const [blocks, setBlocks] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const diffEditorRef = useRef(null);

  // IntelliEdit C IDE State (Original 30% Milestone)
  const [ideCode, setIdeCode] = useState(DEFAULT_C_CODE);
  const [selectedPreset, setSelectedPreset] = useState('slide_cfg');

  function handleEditorMount(editor) {
    diffEditorRef.current = editor;
    const originalEditor = editor.getOriginalEditor();
    if (originalEditor) {
      originalEditor.onDidChangeModelContent(() => {
        handleOriginalChange(originalEditor.getValue());
      });
    }
  }

  function handleOriginalChange(value) {
    setOriginalCode(value || "");
  }

  function handlePresetChange(presetKey) {
    setSelectedPreset(presetKey);
    let code = "";
    if (presetKey === "ide_code") {
      code = ideCode;
    } else {
      code = PRESETS[presetKey];
    }
    if (code) {
      setOriginalCode(code);
      if (diffEditorRef.current) {
        const originalEditor = diffEditorRef.current.getOriginalEditor();
        if (originalEditor && originalEditor.getValue() !== code) {
          originalEditor.setValue(code);
        }
      }
    }
  }

  async function runOptimizationWithCode(codeToSend) {
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: codeToSend })
      });
      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }
      const data = await response.json();

      setOptimizedCode(data.optimized_code);
      setMlPasses(data.ml_predicted_passes || []);
      setLogs(data.transformation_logs || []);
      setBlocks(data.cfg_analysis?.blocks || []);

      // Render Mermaid CFG SVG
      if (data.cfg_analysis?.mermaid_cfg) {
        const uniqueId = "cfgSvg_" + Math.random().toString(36).substring(2, 9);
        const { svg } = await mermaid.render(uniqueId, data.cfg_analysis.mermaid_cfg);
        setCfgSvg(svg);
      }
    } catch (err) {
      alert("Make sure your unified FastAPI server is running on http://localhost:8000");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }

  async function runOptimization() {
    const codeToSend = diffEditorRef.current?.getOriginalEditor()?.getValue() ?? originalCode;
    await runOptimizationWithCode(codeToSend);
  }

  async function handleSendToMlOptimizer(autoRun = true) {
    setSelectedPreset("ide_code");
    setOriginalCode(ideCode);
    setActiveMode("ml-optimizer");
    if (diffEditorRef.current) {
      const originalEditor = diffEditorRef.current.getOriginalEditor();
      if (originalEditor) {
        originalEditor.setValue(ideCode);
      }
    }
    if (autoRun) {
      await runOptimizationWithCode(ideCode);
    }
  }

  return (
    <div style={{ background: '#0f172a', color: '#e2e8f0', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      
      {/* Top Header / Mode Switcher */}
      <header className="top-navbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className="nav-brand">
            <Zap size={20} color="#3b82f6" />
            <span>IntelliEdit</span>
          </div>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="mode-switcher">
          <button 
            className={`mode-btn ${activeMode === 'ml-optimizer' ? 'active' : ''}`}
            onClick={() => setActiveMode('ml-optimizer')}
            title="Module 5 ML Optimization, Basic Blocks & CFG"
          >
            <GitCompare size={16} />
            <span>ML Optimizer & CFG</span>
          </button>
          
          <button 
            className={`mode-btn ${activeMode === 'ide' ? 'active' : ''}`}
            onClick={() => setActiveMode('ide')}
            title="IntelliEdit C IDE, AST Parsing & Compiler Pipeline"
          >
            <CodeEditorIcon size={16} />
            <span>IntelliEdit C IDE</span>
          </button>
        </div>

        {/* Backend Status indicator */}
        <div className="nav-status">
          <div className="status-dot"></div>
          <span>API :8000 Online</span>
        </div>
      </header>

      {/* VIEW 1: ML Optimizer & CFG Workbench */}
      {activeMode === 'ml-optimizer' && (
        <div className="ml-wrapper">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 14px', background: '#1e293b', borderRadius: '8px', border: '1px solid #334155', marginBottom: '10px' }}>
            <div style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>
              <strong>Module 5:</strong> ML-Driven Code Optimizer & Control Flow Graph Workbench
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <select 
                value={selectedPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                style={{ background: '#0f172a', color: '#f8fafc', padding: '6px 10px', borderRadius: '6px', border: '1px solid #475569', cursor: 'pointer', fontSize: '0.85rem' }}
              >
                <option value="ide_code">📄 Current C Code from IDE (main.c)</option>
                <option value="slide_cfg">Preset 1: Basic Block Loop & CSE (M5-P1 Slide 38)</option>
                <option value="const_prop">Preset 2: Constant Folding & Propagation</option>
                <option value="loop_opt">Preset 3: Loop Code Motion & Induction Var</option>
                <option value="peephole">Preset 4: Peephole & Strength Reduction</option>
              </select>
              <button 
                onClick={() => handlePresetChange("ide_code")}
                style={{
                  background: '#334155',
                  color: '#e2e8f0',
                  border: '1px solid #475569',
                  padding: '6px 11px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: '500',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
                title="Pull and load current code from the C IDE (main.c)"
              >
                <RefreshCw size={13} />
                <span>Pull from C IDE</span>
              </button>
              <button 
                onClick={runOptimization}
                disabled={isLoading}
                style={{ 
                  background: isLoading ? '#1d4ed8' : '#2563eb', 
                  color: '#fff', 
                  border: 'none', 
                  padding: '7px 16px', 
                  borderRadius: '6px', 
                  fontWeight: '600', 
                  fontSize: '0.85rem',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.8 : 1,
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Zap size={15} />
                {isLoading ? 'Running Optimizer...' : 'Run ML Optimizer & Generate CFG'}
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.25fr 1fr', gridTemplateRows: '400px 1fr', gap: '10px', flex: 1, overflow: 'hidden' }}>
            
            {/* Top Left: Monaco Diff Editor */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '10px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px' }}>Source Code (Left) vs Optimized Target Code (Right)</h3>
              <div style={{ flex: 1, borderRadius: '4px', overflow: 'hidden' }}>
                <DiffEditor
                  height="100%"
                  language="c"
                  theme="vs-dark"
                  original={originalCode}
                  modified={optimizedCode}
                  onMount={handleEditorMount}
                  onChange={(value) => handleOriginalChange(value)}
                  options={{ originalEditable: true, automaticLayout: true }}
                />
              </div>
            </div>

            {/* Top Right: Control Flow Graph */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '10px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px' }}>Control Flow Graph (Basic Blocks & Leaders)</h3>
              <div 
                style={{ background: '#ffffff', color: '#000', borderRadius: '6px', padding: '10px', flex: 1, overflow: 'auto', display: 'flex', alignItems: cfgSvg ? 'flex-start' : 'center', justifyContent: cfgSvg ? 'center' : 'center' }} 
              >
                {cfgSvg ? (
                  <div 
                    dangerouslySetInnerHTML={{ __html: cfgSvg }} 
                    style={{ width: '100%', display: 'flex', justifyContent: 'center' }} 
                  />
                ) : (
                  <span style={{ color: '#64748b', fontSize: '13px' }}>
                    Click &apos;Run ML Optimizer &amp; Generate CFG&apos; to view the control flow graph.
                  </span>
                )}
              </div>
            </div>

            {/* Bottom Left: ML Predictions & Audit Logs */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '10px', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
              <h3 style={{ margin: '0 0 6px 0', fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px' }}>Random Forest ML Predicted Passes</h3>
              <div>
                {mlPasses.length > 0 ? mlPasses.map((p, idx) => (
                  <span key={idx} style={{ display: 'inline-block', background: '#1d4ed8', color: '#dbeafe', padding: '3px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: '500', margin: '2px' }}>{p}</span>
                )) : <span style={{ fontSize: '12px', color: '#94a3b8' }}>No ML passes triggered yet.</span>}
              </div>
              <h3 style={{ margin: '10px 0 6px 0', fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px' }}>Compiler Transformation Audit Log</h3>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {logs.length > 0 ? logs.map((l, idx) => (
                  <div key={idx} style={{ fontFamily: 'monospace', fontSize: '11px', padding: '4px 0', borderBottom: '1px solid #334155', color: '#4ade80' }}>{l}</div>
                )) : <div style={{ fontSize: '12px', color: '#94a3b8' }}>No transformations logged.</div>}
              </div>
            </div>

            {/* Bottom Right: Data Flow Table */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '10px', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
              <h3 style={{ margin: '0 0 6px 0', fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.5px' }}>Basic Blocks & Reaching Definitions Data Flow</h3>
              <div style={{ flex: 1, overflow: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ background: '#0f172a' }}>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>Block</th>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>Leader Statement</th>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>gen[B]</th>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>kill[B]</th>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>in[B]</th>
                      <th style={{ border: '1px solid #334155', padding: '5px' }}>out[B]</th>
                    </tr>
                  </thead>
                  <tbody>
                    {blocks.map((b) => (
                      <tr key={b.id}>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><b>{b.id}</b></td>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><code>{b.leader_statement}</code></td>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><code>{`{${b.gen.join(", ")}}`}</code></td>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><code>{`{${b.kill.join(", ")}}`}</code></td>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><code>{`{${b.in.join(", ")}}`}</code></td>
                        <td style={{ border: '1px solid #334155', padding: '5px' }}><code>{`{${b.out.join(", ")}}`}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* VIEW 2: Original IntelliEdit C IDE (30% Milestone) */}
      {activeMode === 'ide' && (
        <div className="app-container">
          {/* Main Monaco Editor */}
          <div className="main-content">
            <div className="editor-container glass-panel">
              <div className="editor-header">
                <FileCode size={18} color="var(--accent-primary)" />
                <span className="file-name">main.c</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '10px' }}>
                  Tree-Sitter C Autocomplete Enabled
                </span>
                <button
                  onClick={() => handleSendToMlOptimizer(true)}
                  style={{
                    marginLeft: 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                    color: '#fff',
                    border: 'none',
                    padding: '6px 14px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: '600',
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(37,99,235,0.3)',
                    transition: 'all 0.2s'
                  }}
                  title="Copy this C code to ML Optimizer & CFG Workbench and run analysis immediately"
                >
                  <Zap size={14} />
                  <span>Send to ML Optimizer & Run CFG →</span>
                </button>
              </div>
              <CodeEditor code={ideCode} setCode={setIdeCode} />
            </div>
          </div>

          {/* Right Inspection Panel */}
          <div className="right-panel">
            <div className="panel-tabs">
              <div className="tab-btn active" style={{ cursor: 'default' }}>
                <Cpu size={16} />
                Compiler Processes
              </div>
            </div>
            <div className="tab-content glass-panel">
              <CompilerProcesses code={ideCode} />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

function CodeEditorIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6"></polyline>
      <polyline points="8 6 2 12 8 18"></polyline>
    </svg>
  );
}
