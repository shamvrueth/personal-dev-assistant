import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = 'http://localhost:8000';

// Command Reference Component
function CommandReference({ onClose }) {
  const [search, setSearch] = useState('');
  const [selectedCmd, setSelectedCmd] = useState(null);

  const COMMANDS = [
    { id: 'explain', name: 'explain', category: 'Analysis', description: 'Get high-level project overview', args: [], example: 'explain' },
    { id: 'entry', name: 'entry', category: 'Analysis', description: 'List execution entry points', args: [], example: 'entry' },
    { id: 'find', name: 'find', category: 'Search', description: 'Find symbol definitions and usage', args: [{ name: 'symbol', required: true }], example: 'find AnimatePresence' },
    { id: 'lint', name: 'lint', category: 'Analysis', description: 'Detect bugs and code quality issues', args: [{ name: 'path', required: false, default: '.' }], example: 'lint src/' },
    { id: 'optimize', name: 'optimize', category: 'Analysis', description: 'Find performance optimization opportunities', args: [{ name: 'path', required: false, default: '.' }], example: 'optimize .' },
    { id: 'fix', name: 'fix', category: 'Code Generation', description: 'Generate copy-pasteable code fixes', args: [{ name: 'path', required: false, default: '.' }], example: 'fix .' },
    { id: 'explain-file', name: 'explain-file', category: 'Analysis', description: 'Explain specific file purpose', args: [{ name: 'path', required: true }], example: 'explain-file src/app.js' },
    { id: 'explain-flow', name: 'explain-flow', category: 'Analysis', description: 'Explain execution flow inside a file', args: [{ name: 'path', required: true }], example: 'explain-flow src/main.py' },
  ];

  const filteredCommands = COMMANDS.filter(cmd =>
    cmd.name.toLowerCase().includes(search.toLowerCase()) ||
    cmd.description.toLowerCase().includes(search.toLowerCase())
  );

  if (selectedCmd) {
    return (
      <div className="command-reference">
        <div className="ref-header">
          <div className="ref-title-section">
            <span className="ref-icon">📖</span>
            <h2>Command Reference</h2>
          </div>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="ref-content">
          <button className="back-btn" onClick={() => setSelectedCmd(null)}>‹ Back to list</button>
          <div className="command-detail">
            <div className="command-name-header">
              <h3 className="cmd-name-header">{selectedCmd.name}</h3>
              <span className="cmd-category">{selectedCmd.category}</span>
            </div>
            <p className="cmd-description">{selectedCmd.description}</p>
            {selectedCmd.args.length > 0 && (
              <>
                <h4 className="args-header">ARGUMENTS</h4>
                <div className="args-list">
                  {selectedCmd.args.map((arg, idx) => (
                    <div key={idx} className="arg-item">
                      <div className="arg-name-line">
                        <span className="arg-tag">🏷️</span>
                        <span className="arg-name">{arg.name}</span>
                        {arg.default && <span className="arg-default">default: {arg.default}</span>}
                      </div>
                      {arg.required && <div className="required-badge">Required</div>}
                    </div>
                  ))}
                </div>
              </>
            )}
            <h4 className="example-header">EXAMPLE</h4>
            <div className="example-code">
              <span className="prompt">$ </span>
              <span className="cmd-text">{selectedCmd.example}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="command-reference">
      <div className="ref-header">
        <div className="ref-title-section">
          <span className="ref-icon">📖</span>
          <h2>Command Reference</h2>
        </div>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>
      <div className="ref-content">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input type="text" placeholder="Search commands..." value={search} onChange={(e) => setSearch(e.target.value)} className="search-input" />
        </div>
        <div className="command-list">
          {filteredCommands.map(cmd => (
            <div key={cmd.id} className="command-item" onClick={() => setSelectedCmd(cmd)}>
              <div className="cmd-badge">{cmd.category[0]}</div>
              <div className="cmd-info">
                <div className="cmd-name">{cmd.name}</div>
                <div className="cmd-desc">{cmd.description}</div>
              </div>
              <span className="cmd-chevron">›</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Main App
function App() {
  const [workspace, setWorkspace] = useState('');
  const [workspacePath, setWorkspacePath] = useState('');
  const [indexStats, setIndexStats] = useState(null);
  const [commandInput, setCommandInput] = useState('');
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCommandRef, setShowCommandRef] = useState(false);
  const [vizData, setVizData] = useState(null);

  useEffect(() => {
    loadCurrentWorkspace();
    loadIndexStats();
  }, []);

  const loadCurrentWorkspace = async () => {
    try {
      const res = await axios.get(`${API_URL}/workspace/current`);
      setWorkspace(res.data.workspace || '');
    } catch (err) {
      console.error('Load workspace error:', err);
    }
  };

  const loadIndexStats = async () => {
    try {
      const res = await axios.get(`${API_URL}/index/stats`);
      setIndexStats(res.data.stats);
      
      // Auto-load visualization if index exists
      if (res.data.stats.indexed_chunks > 0) {
        loadVisualization();
      }
    } catch (err) {
      console.error('Load stats error:', err);
    }
  };

  const loadVisualization = async () => {
    try {
      const res = await axios.get(`${API_URL}/index/visualize?max_points=500`);
      setVizData(res.data);
    } catch (err) {
      console.error('Load viz error:', err);
    }
  };

  const handleSetWorkspace = async () => {
    if (!workspacePath.trim()) {
      setOutput('❌ Please enter a workspace path');
      return;
    }

    setLoading(true);
    setOutput('⏳ Setting workspace...');

    try {
      await axios.post(`${API_URL}/workspace/set`, { workspace: workspacePath });
      await axios.post(`${API_URL}/config/git`, { has_git: true, is_local: true });
      
      setOutput('✅ Workspace set! Now build the index.');
      setVizData(null);
      await loadCurrentWorkspace();
    } catch (err) {
      setOutput(`❌ Error: ${err.response?.data?.detail || err.message}`);
      console.error('Set workspace error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleBuildIndex = async () => {
    setLoading(true);
    setOutput('⏳ Building index... This may take 30-120 seconds...');

    try {
      const res = await axios.post(`${API_URL}/index/build`);
      setOutput(`✅ Index built!\n${res.data.stats.indexed_chunks} chunks indexed.`);
      await loadIndexStats();
      await loadVisualization();
    } catch (err) {
      setOutput(`❌ Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const parseCommand = (input) => {
    const parts = input.trim().split(/\s+/);
    const cmd = parts[0];
    const rest = parts.slice(1).join(' ');

    const validCommands = ['explain', 'entry', 'find', 'lint', 'optimize', 'fix', 'explain-file', 'explain-flow', 'git-summary'];
    
    if (!validCommands.includes(cmd)) {
      return { error: `Unknown command: ${cmd}. Try: ${validCommands.join(', ')}` };
    }

    const args = {};
    if (['find'].includes(cmd)) {
      args.symbol = rest || '';
    } else if (['lint', 'optimize', 'fix', 'explain-file', 'explain-flow'].includes(cmd)) {
      args.path = rest || '.';
    }

    return { command: cmd, args };
  };

  const handleExecute = async () => {
    if (!commandInput.trim()) {
      setOutput('❌ Please enter a command');
      return;
    }

    const parsed = parseCommand(commandInput);
    if (parsed.error) {
      setOutput(`❌ ${parsed.error}`);
      return;
    }

    setLoading(true);
    setOutput(`⏳ Executing ${parsed.command}...`);

    try {
      const res = await axios.post(`${API_URL}/execute`, {
        command: parsed.command,
        args: parsed.args
      });
      setOutput(res.data.response);
    } catch (err) {
      setOutput(`❌ Error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading) {
      handleExecute();
    }
  };

  if (showCommandRef) {
    return <CommandReference onClose={() => setShowCommandRef(false)} />;
  }

  return (
    <div className="app">
      {/* Fixed Header */}
      <header className="header">
        <div className="logo">
          <div className="logo-icon">{'>'}_</div>
          <div className="title-section">
            <h1>Dev Assistant</h1>
            <p className="subtitle">{workspace ? '● Workspace set' : '● No workspace'}</p>
          </div>
        </div>
      </header>

      {/* Scrollable Content */}
      <div className="main-content">
        {/* Workspace */}
        <section className="section">
          <div className="section-header">
            <span className="section-icon">📁</span>
            <h2>WORKSPACE</h2>
          </div>
          <div className="workspace-status">
            <span className="chevron-right">›</span>
            <span className="status-text">{workspace || 'No workspace set'}</span>
          </div>
          <input
            type="text"
            className="workspace-input"
            placeholder="📁 /path/to/project"
            value={workspacePath}
            onChange={(e) => setWorkspacePath(e.target.value)}
            disabled={loading}
          />
          <button className="btn btn-primary" onClick={handleSetWorkspace} disabled={loading}>
            Set Workspace
          </button>
          <button className="btn btn-secondary" onClick={handleBuildIndex} disabled={loading || !workspace}>
            Build Index
          </button>
        </section>

        {/* Command Reference Button */}
        <button className="command-ref-btn" onClick={() => setShowCommandRef(true)}>
          <span className="icon">📖</span>
          <div className="ref-text">
            <div className="ref-title">Command Reference</div>
            <div className="ref-subtitle">8 commands with args & examples</div>
          </div>
          <span className="chevron">›</span>
        </button>

        {/* Terminal */}
        <section className="section terminal-section">
          <div className="terminal-header">
            <div className="traffic-lights">
              <span className="light red"></span>
              <span className="light yellow"></span>
              <span className="light green"></span>
            </div>
            <span className="terminal-title">terminal — bash</span>
          </div>
          <div className="terminal-body">
            <div className="terminal-prompt"># Ready. Select a command or type below.</div>
            <div className="command-hint">
              <p>Available: explain, entry, find, lint, optimize, fix, explain-file, explain-flow</p>
            </div>
            <div className="terminal-execute">
              <span className="prompt-symbol">$</span>
              <input
                type="text"
                className="terminal-input"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type command (e.g., lint . or find MyComponent)"
                disabled={loading}
                autoFocus
              />
              <button className="execute-btn" onClick={handleExecute} disabled={loading || !commandInput.trim()}>
                ▶
              </button>
            </div>
          </div>
        </section>

        {/* Output */}
        <section className="section">
          <div className="section-header">
            <span className="section-icon">📄</span>
            <h2>OUTPUT</h2>
          </div>
          <div className="output-container">
            {output ? (
              <pre className="output-text">{output}</pre>
            ) : (
              <div className="output-placeholder">
                <div className="chevron-up">^</div>
                <p>Run a command to see output</p>
              </div>
            )}
          </div>
        </section>

        {/* Vector Visualization */}
        {/* {console.log(vizData.visualization)} */}
        {workspace.length != 0 && vizData && vizData.visualization && !vizData.error && vizData.visualization.points && vizData.visualization.points.length > 0 && (
          <section className="section">
            <div className="section-header">
              <span className="section-icon">📊</span>
              <h2>VECTOR SPACE</h2>
            </div>
            <div className="viz-container">
              <VectorCanvas data={vizData.visualization} />
              <div className="viz-stats">
                <span>{vizData.visualization.total_points} points</span>
                <span>•</span>
                <span>{vizData.visualization.total_files} files</span>
                <span>•</span>
                <span>{vizData.visualization.dimensions_original}D → {vizData.visualization.dimensions_reduced}D</span>
              </div>
              {vizData.visualization.file_colors && Object.keys(vizData.visualization.file_colors).length > 0 && (
                <div className="viz-legend">
                  <div className="legend-title">FILE COLORS</div>
                  <div className="legend-list">
                    {Object.entries(vizData.visualization.file_colors).map(([file, colorInfo]) => (
                      <div key={file} className="legend-item">
                        <span className="legend-dot" style={{ backgroundColor: colorInfo.hex }} />
                        <span className="legend-label" title={file}>
                          {file.replace(/\\/g, '/').split('/').pop()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// Vector Visualization Canvas
function VectorCanvas({ data }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!data || !data.points || data.points.length === 0 || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = 380;
    const height = 300;
    
    canvas.width = width;
    canvas.height = height;

    // Clear canvas
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, width, height);

    // Draw grid
    ctx.strokeStyle = '#21262d';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const x = (width / 10) * i;
      const y = (height / 10) * i;
      
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
      
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Draw points
    data.points.forEach(point => {
      const x = point.x * width;
      const y = point.y * height;
      
      ctx.fillStyle = point.color;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
      
      // Add border
      ctx.strokeStyle = '#0d1117';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

  }, [data]);

  return <canvas ref={canvasRef} className="viz-canvas" />;
}

export default App;