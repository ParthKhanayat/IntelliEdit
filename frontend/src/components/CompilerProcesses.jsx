import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Code, Cpu, Layers, Zap, CheckCircle2 } from 'lucide-react';
import './CompilerProcesses.css';

const CompilerProcesses = ({ code }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProcesses = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://localhost:8000/api/compiler-processes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code })
        });
        if (!response.ok) throw new Error('Failed to fetch compiler processes');
        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    if (code) {
      // Add a small debounce so it doesn't fetch on every keystroke immediately
      const timer = setTimeout(() => {
        fetchProcesses();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [code]);

  if (loading && !data) return <div className="loading-state glass-panel">Analyzing code phases...</div>;
  if (error) return <div className="error-state glass-panel">Error: {error}</div>;
  if (!data) return <div className="empty-state glass-panel">Write some code to see compiler processes.</div>;

  const phases = [
    {
      id: 'lexical',
      title: '1. Lexical Analysis',
      icon: <Layers size={18} />,
      content: (
        <div className="token-list">
          {data.lexical_analysis?.map((token, i) => (
            <span key={i} className={`token token-${token.type.replace(/[^a-zA-Z0-9]/g, '-')}`}>
              {token.value}
            </span>
          ))}
        </div>
      )
    },
    {
      id: 'syntax',
      title: '2. Syntax Analysis (AST)',
      icon: <Activity size={18} />,
      content: (
        <pre className="code-block json">
          {JSON.stringify(data.syntax_analysis, null, 2)}
        </pre>
      )
    },
    {
      id: 'semantic',
      title: '3. Semantic Analysis',
      icon: <CheckCircle2 size={18} />,
      content: (
        <ul className="semantic-list">
          {data.semantic_analysis?.map((msg, i) => (
            <li key={i}>{msg.message}</li>
          ))}
        </ul>
      )
    },
    {
      id: 'ir',
      title: '4. Intermediate Code',
      icon: <Code size={18} />,
      content: (
        <pre className="code-block">
          {data.intermediate_code}
        </pre>
      )
    },
    {
      id: 'optimization',
      title: '5. Code Optimization',
      icon: <Zap size={18} />,
      content: (
        <ul className="optimization-list">
          {data.code_optimization?.map((opt, i) => (
            <li key={i}>{opt}</li>
          ))}
        </ul>
      )
    },
    {
      id: 'target',
      title: '6. Target Code Generation',
      icon: <Cpu size={18} />,
      content: (
        <pre className="code-block assembly">
          {data.target_code}
        </pre>
      )
    }
  ];

  return (
    <div className="compiler-processes-container">
      <div className="processes-header">
        <h2>Compiler Design Processes</h2>
        <p className="subtitle">Real-time breakdown of the compilation pipeline</p>
      </div>
      
      <div className="phases-timeline">
        {phases.map((phase, index) => (
          <motion.div 
            key={phase.id} 
            className="phase-card glass-panel"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <div className="phase-header">
              {phase.icon}
              <h3>{phase.title}</h3>
            </div>
            <div className="phase-body">
              {phase.content}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default CompilerProcesses;
