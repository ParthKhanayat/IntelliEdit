import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Sparkles, Loader2, GitCommitHorizontal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const SuggestionsPanel = ({ code }) => {
  const [optimizations, setOptimizations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchOptimizations = async () => {
      setLoading(true);
      try {
        const response = await axios.post('http://localhost:8000/api/optimize', {
          code,
          cursor_line: 0,
          cursor_column: 0
        });
        setOptimizations(response.data.optimizations || []);
      } catch (e) {
        console.error("Error fetching optimizations:", e);
      } finally {
        setLoading(false);
      }
    };

    // Debounce optimization fetching to avoid spamming the backend
    const timer = setTimeout(() => {
      if (code.trim().length > 5) fetchOptimizations();
    }, 1500);

    return () => clearTimeout(timer);
  }, [code]);

  return (
    <>
      <div className="panel-header">
        <Sparkles size={20} color="var(--accent-secondary)" />
        <span className="panel-title">AI Optimizations</span>
        {loading && <Loader2 size={16} className="spinner" style={{marginLeft: 'auto', animation: 'spin 1s linear infinite'}} />}
      </div>
      <div className="panel-content">
        <AnimatePresence>
          {optimizations.length === 0 && !loading && (
             <motion.div 
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
               style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: '40px' }}
             >
               <GitCommitHorizontal size={40} style={{ margin: '0 auto', opacity: 0.5 }} />
               <p style={{ marginTop: '16px' }}>Code looks good! No optimizations to suggest at the moment.</p>
             </motion.div>
          )}
          {optimizations.map((opt, i) => (
            <motion.div 
              key={i}
              className="suggestion-card"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="suggestion-header">
                <span>Line {opt.line}</span>
                <span className={`badge ${opt.type}`}>{opt.type}</span>
              </div>
              <p style={{ fontSize: '0.9rem', lineHeight: '1.5' }}>
                {opt.suggestion}
              </p>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </>
  );
};

export default SuggestionsPanel;
