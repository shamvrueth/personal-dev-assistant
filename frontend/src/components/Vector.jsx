import { useEffect, useRef } from 'react';

function VectorVisualization({ data }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!data || !data.points || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

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
      
      ctx.strokeStyle = '#0d1117';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

  }, [data]);

  if (!data) return null;

  return (
    <section className="section">
      <div className="section-header">
        <span className="section-icon">📊</span>
        <h2>VECTOR SPACE</h2>
      </div>
      <div className="viz-container">
        <canvas
          ref={canvasRef}
          width={600}
          height={400}
          className="viz-canvas"
        />
        <div className="viz-stats">
          <span>{data.total_points} points</span>
          <span>•</span>
          <span>{data.total_files} files</span>
          <span>•</span>
          <span>{data.dimensions_original}D → {data.dimensions_reduced}D</span>
        </div>
        {data.file_colors && Object.keys(data.file_colors).length > 0 && (
          <div className="viz-legend">
            <div className="legend-title">FILE COLORS</div>
            <div className="legend-list">
              {Object.entries(data.file_colors).map(([file, colorInfo]) => (
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
  );
}

export default VectorVisualization;