function PerformanceChart({ indexStats }) {
  // Mock data for demonstration
  const data = [
    { day: 'Mon', build: 1.8, test: 2.1 },
    { day: 'Tue', build: 1.4, test: 1.9 },
    { day: 'Wed', build: 2.4, test: 2.3 },
    { day: 'Thu', build: 1.2, test: 1.5 },
    { day: 'Fri', build: 1.9, test: 2.0 },
    { day: 'Sat', build: 1.0, test: 1.3 },
    { day: 'Sun', build: 1.5, test: 1.7 },
  ];

  const maxValue = 2.5;

  return (
    <section className="section performance-section">
      <div className="section-header">
        <span className="section-icon">📈</span>
        <h2>PERFORMANCE</h2>
        <div className="chart-tabs">
          <button className="tab-btn active">Bar</button>
          <button className="tab-btn">Line</button>
        </div>
      </div>

      <div className="chart-legend">
        <span className="legend-item">
          <span className="legend-dot build"></span>
          Build (s)
        </span>
        <span className="legend-item">
          <span className="legend-dot test"></span>
          Test (s)
        </span>
      </div>

      <div className="chart-container">
        <div className="y-axis">
          <span>2.4</span>
          <span>1.8</span>
          <span>1.2</span>
          <span>0.6</span>
          <span>0</span>
        </div>

        <div className="chart-bars">
          {data.map((d, idx) => (
            <div key={idx} className="bar-group">
              <div className="bars">
                <div
                  className="bar build-bar"
                  style={{ height: `${(d.build / maxValue) * 100}%` }}
                />
                <div
                  className="bar test-bar"
                  style={{ height: `${(d.test / maxValue) * 100}%` }}
                />
              </div>
              <div className="bar-label">{d.day}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="chart-caption">
        Build & test duration — last 7 days
      </div>
    </section>
  );
}

export default PerformanceChart;