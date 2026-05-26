import { useState } from 'react';

const COMMAND_CATALOG = [
  {
    id: 'explain',
    name: 'explain',
    category: 'Analysis',
    description: 'Get high-level project overview',
    args: [],
    example: '$ explain'
  },
  {
    id: 'entry',
    name: 'entry',
    category: 'Analysis',
    description: 'List execution entry points',
    args: [],
    example: '$ entry'
  },
  {
    id: 'find',
    name: 'find',
    category: 'Search',
    description: 'Find symbol definitions and usage',
    args: [
      { name: 'symbol', required: true, description: 'Symbol or function name to search for' }
    ],
    example: '$ find AnimatePresence'
  },
  {
    id: 'lint',
    name: 'lint',
    category: 'Analysis',
    description: 'Detect bugs and code quality issues',
    args: [
      { name: 'path', required: false, default: '.', description: 'Directory to analyze' }
    ],
    example: '$ lint src/'
  },
  {
    id: 'optimize',
    name: 'optimize',
    category: 'Analysis',
    description: 'Find performance optimization opportunities',
    args: [
      { name: 'path', required: false, default: '.', description: 'Directory to analyze' }
    ],
    example: '$ optimize .'
  },
  {
    id: 'fix',
    name: 'fix',
    category: 'Code Generation',
    description: 'Generate copy-pasteable code fixes',
    args: [
      { name: 'path', required: false, default: '.', description: 'Directory to fix' },
      { name: 'allow_refactor', required: false, default: false, description: 'Allow refactoring' }
    ],
    example: '$ fix --allow-refactor'
  },
  {
    id: 'explain-file',
    name: 'explain-file',
    category: 'Analysis',
    description: 'Explain specific file purpose and responsibilities',
    args: [
      { name: 'path', required: true, description: 'File path to explain' }
    ],
    example: '$ explain-file src/app.js'
  },
  {
    id: 'explain-flow',
    name: 'explain-flow',
    category: 'Analysis',
    description: 'Explain execution flow inside a file',
    args: [
      { name: 'path', required: true, description: 'File path to analyze' }
    ],
    example: '$ explain-flow src/main.py'
  },
];

function CommandReference({ onClose, onSelectCommand }) {
  const [search, setSearch] = useState('');
  const [selectedCmd, setSelectedCmd] = useState(null);

  const filteredCommands = COMMAND_CATALOG.filter(cmd =>
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
          <button className="back-btn" onClick={() => setSelectedCmd(null)}>
            ‹ Back to list
          </button>

          <div className="command-detail">
            <div className="command-name-header">
              <h3 className="cmd-name">{selectedCmd.name}</h3>
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
                        {arg.default && (
                          <span className="arg-default">default: {arg.default}</span>
                        )}
                      </div>
                      <div className="arg-description">{arg.description}</div>
                      {arg.required && <div className="required-badge">Required</div>}
                    </div>
                  ))}
                </div>
              </>
            )}

            <h4 className="example-header">EXAMPLE</h4>
            <div className="example-code">
              <span className="prompt">$ </span>
              <span className="cmd-text">{selectedCmd.example.replace('$ ', '')}</span>
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
          <input
            type="text"
            placeholder="Search commands..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="command-list">
          {filteredCommands.map(cmd => (
            <div
              key={cmd.id}
              className="command-item"
              onClick={() => setSelectedCmd(cmd)}
            >
              <div className="cmd-badge">{cmd.category.substring(0, 1)}</div>
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

export default CommandReference;