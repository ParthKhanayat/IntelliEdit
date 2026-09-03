import React, { useState } from 'react';
import CodeEditor from './components/CodeEditor';
import SuggestionsPanel from './components/SuggestionsPanel';
import CompilerProcesses from './components/CompilerProcesses';
import { motion } from 'framer-motion';
import { Code2, Wand2, Network } from 'lucide-react';
import './App.css';

function App() {
  const [code, setCode] = useState('#include <stdio.h>\n\nint main() {\n    printf("Hello IntelliEdit!\\n");\n    return 0;\n}');
  const [activeTab, setActiveTab] = useState('suggestions');
  
  return (
    <div className="app-container">
      <motion.div 
        className="main-content"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="editor-container glass-panel">
          <div className="editor-header">
            <Code2 size={18} color="var(--accent-primary)" />
            <span className="file-name">main.c</span>
          </div>
          <CodeEditor code={code} setCode={setCode} />
        </div>
      </motion.div>
      
      <motion.div 
        className="right-panel"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <div className="panel-tabs">
          <button 
            className={`tab-btn ${activeTab === 'suggestions' ? 'active' : ''}`}
            onClick={() => setActiveTab('suggestions')}
          >
            <Wand2 size={16} /> AI Suggestions
          </button>
          <button 
            className={`tab-btn ${activeTab === 'compiler' ? 'active' : ''}`}
            onClick={() => setActiveTab('compiler')}
          >
            <Network size={16} /> Compiler Processes
          </button>
        </div>
        
        <div className="tab-content glass-panel">
          {activeTab === 'suggestions' ? (
            <SuggestionsPanel code={code} />
          ) : (
            <CompilerProcesses code={code} />
          )}
        </div>
      </motion.div>
    </div>
  );
}

export default App;
