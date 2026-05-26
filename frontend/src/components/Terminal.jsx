import { useState } from 'react';

const COMMANDS = [
  { value: 'explain', label: 'Explain Project', args: [] },
  { value: 'entry', label: 'Entry Points', args: [] },
  { value: 'find', label: 'Find Symbol', args: ['symbol'] },
  { value: 'lint', label: 'Lint (Find Bugs)', args: ['path'] },
  { value: 'optimize', label: 'Optimize', args: ['path'] },
  { value: 'fix', label: 'Generate Fixes', args: ['path'] },
  { value: 'explain-file', label: 'Explain File', args: ['path'] },
  { value: 'explain-flow', label: 'Explain Flow', args: ['path'] },
];

function TerminalSection({ onExecute, loading }) {
  const [selectedCmd, setSelectedCmd] = useState('');
  const [cmdInput, setCmdInput] = useState('');
  const [argValue, setArgValue] = useState('');

  const handleExecute = () => {
    if (!selectedCmd) {
      alert('Please select a command');
      return;
    }

    const cmd = COMMANDS.find(c => c.value === selectedCmd);
    const args = {};

    if (cmd.args.includes('symbol')) {
      if (!argValue.trim()) {
        alert('Please enter a symbol to find');
        return;
      }
      args.symbol = argValue;
    } else if (cmd.args.includes('path')) {
      args.path = argValue || '.';
    }

    onExecute(selectedCmd, args);
  };

  const currentCmd = COMMANDS.find(c => c.value === selectedCmd);

  return (
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
        <div className="terminal-prompt">
          # Ready. Select a command or type below.
        </div>

        {/* Command Selection */}
        <div className="command-select-wrapper">
          <input
            type="text"
            className="command-select-display"
            placeholder="Select command..."
            value={currentCmd ? currentCmd.label : ''}
            readOnly
            onClick={() => {/* Could show dropdown */}}
          />
          <select
            className="command-select-hidden"
            value={selectedCmd}
            onChange={(e) => {
              setSelectedCmd(e.target.value);
              setArgValue('');
            }}
          >
            <option value="">Select command...</option>
            {COMMANDS.map(cmd => (
              <option key={cmd.value} value={cmd.value}>
                {cmd.label}
              </option>
            ))}
          </select>
        </div>

        {/* Argument Input if needed */}
        {currentCmd && currentCmd.args.length > 0 && (
          <input
            type="text"
            className="arg-input"
            placeholder={
              currentCmd.args.includes('symbol') 
                ? 'Enter symbol name...' 
                : 'Enter path (default: .)'
            }
            value={argValue}
            onChange={(e) => setArgValue(e.target.value)}
          />
        )}

        {/* Execute Command Line */}
        <div className="terminal-execute">
          <span className="prompt-symbol">$</span>
          <input
            type="text"
            className="terminal-input"
            value={cmdInput}
            onChange={(e) => setCmdInput(e.target.value)}
            placeholder={selectedCmd || 'ls -la'}
            readOnly
          />
          <button
            className="execute-btn"
            onClick={handleExecute}
            disabled={loading || !selectedCmd}
          >
            ▶
          </button>
        </div>
      </div>
    </section>
  );
}

export default TerminalSection;