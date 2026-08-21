import React, { useState } from 'react';
import CodeEditor from './components/CodeEditor';
import SuggestionsPanel from './components/SuggestionsPanel';
import { motion } from 'framer-motion';
import { Code2 } from 'lucide-react';
import './App.css';

function App() {
  const [code, setCode] = useState('#include <stdio.h>\n\nint main() {\n    printf("Hello IntelliEdit!\\n");\n    return 0;\n}');
  
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
        className="ai-panel glass-panel"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <SuggestionsPanel code={code} />
      </motion.div>
    </div>
  );
}

export default App;
