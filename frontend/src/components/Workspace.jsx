import { useState } from 'react';

function WorkspaceSection({ workspace, onSetWorkspace, onBuildIndex, loading }) {
  const [path, setPath] = useState('');

  const handleSetClick = () => {
    if (!path.trim()) {
      alert('Please enter a workspace path');
      return;
    }
    onSetWorkspace(path);
  };

  return (
    <section className="section workspace-section">
      <div className="section-header">
        <span className="section-icon">📁</span>
        <h2>WORKSPACE</h2>
      </div>

      <div className="workspace-status">
        <span className="chevron-right">›</span>
        <span className="status-text">
          {workspace || 'No workspace set'}
        </span>
      </div>

      <input
        type="text"
        className="workspace-input"
        placeholder="📁 /path/to/project"
        value={path}
        onChange={(e) => setPath(e.target.value)}
        disabled={loading}
      />

      <button
        className="btn btn-primary"
        onClick={handleSetClick}
        disabled={loading}
      >
        Set Workspace
      </button>

      <button
        className="btn btn-secondary"
        onClick={onBuildIndex}
        disabled={loading || !workspace}
      >
        Build Index
      </button>
    </section>
  );
}

export default WorkspaceSection;