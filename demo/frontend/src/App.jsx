import React, { useState, useCallback } from 'react';
import SchedulerInput from './SchedulerInput';
import GraphView from './GraphView';
import TimelineView from './TimelineView';
import ResourceChart from './ResourceChart';
import {
  parseGraphData,
  computeTaskStates,
  computeTaskStatesAtTick,
  parseTimelineData,
  parseResourceData,
  getMaxTick,
} from './TraceParser';

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentTick, setCurrentTick] = useState(null);

  const handleRun = useCallback(async (program) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentTick(null);

    try {
      const resp = await fetch('/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ program }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${resp.status}`);
      }

      const data = await resp.json();
      setResult(data);

      const max = getMaxTick(data.events);
      setCurrentTick(max);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const graphData = result ? parseGraphData(result.tasks, result.dependencies) : null;
  const maxTick = result ? getMaxTick(result.events) : 0;
  const taskStates = result
    ? currentTick !== null && currentTick < maxTick
      ? computeTaskStatesAtTick(result.events, currentTick)
      : computeTaskStates(result.events)
    : {};
  const intervals = result ? parseTimelineData(result.events, result.tasks) : [];
  const resourceData = result
    ? parseResourceData(result.events, result.resources, result.requirements)
    : {};

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.h1}>DAG Task Scheduler</h1>
          <span style={styles.subtitle}>Interactive Visualization</span>
        </div>
      </header>

      <main style={styles.main}>
        <SchedulerInput onRun={handleRun} loading={loading} />

        {error && <div style={styles.error}>{error}</div>}

        {result && (
          <>
            {/* Tick slider */}
            {maxTick > 0 && (
              <div style={styles.sliderContainer}>
                <label style={styles.sliderLabel}>
                  Replay tick: <strong>{currentTick ?? maxTick}</strong> / {maxTick}
                </label>
                <input
                  type="range"
                  min={0}
                  max={maxTick}
                  value={currentTick ?? maxTick}
                  onChange={(e) => setCurrentTick(Number(e.target.value))}
                  style={styles.slider}
                />
              </div>
            )}

            {/* Metrics bar */}
            {result.metrics && Object.keys(result.metrics).length > 0 && (
              <div style={styles.metricsBar}>
                <MetricPill label="Ticks" value={result.metrics.total_ticks} />
                <MetricPill label="Completed" value={result.metrics.tasks_completed} color="#238636" />
                <MetricPill label="Failed" value={result.metrics.tasks_failed} color="#da3633" />
                <MetricPill label="Retries" value={result.metrics.retry_attempts} color="#a371f7" />
                <MetricPill label="Decisions" value={result.metrics.scheduler_decisions} color="#1f6feb" />
                {Object.entries(result.metrics.peak_resource_usage || {}).map(([r, v]) => (
                  <MetricPill key={r} label={`Peak ${r}`} value={v} color="#f0883e" />
                ))}
              </div>
            )}

            {/* Visualizations */}
            <div style={styles.vizGrid}>
              {graphData && graphData.nodes.length > 0 && (
                <GraphView graphData={graphData} taskStates={taskStates} />
              )}
              <TimelineView intervals={intervals} maxTick={maxTick} currentTick={currentTick} />
            </div>

            <ResourceChart resourceData={resourceData} />

            {/* Console output */}
            <div style={styles.console}>
              <h3 style={styles.consoleTitle}>Console Output</h3>
              <pre style={styles.consolePre}>{result.stdout || '(no output)'}</pre>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function MetricPill({ label, value, color = '#8b949e' }) {
  return (
    <div style={styles.pill}>
      <span style={{ color: '#8b949e', fontSize: 11 }}>{label}</span>
      <span style={{ color, fontSize: 18, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </span>
    </div>
  );
}

const styles = {
  app: {
    minHeight: '100vh',
    background: '#0f1117',
  },
  header: {
    borderBottom: '1px solid #21262d',
    padding: '20px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#161b22',
  },
  h1: {
    fontSize: 22,
    fontWeight: 700,
    color: '#f0f6fc',
    margin: 0,
    letterSpacing: -0.5,
  },
  subtitle: {
    color: '#484f58',
    fontSize: 13,
  },
  main: {
    maxWidth: 1100,
    margin: '0 auto',
    padding: '24px 24px 80px',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  error: {
    background: '#3d1114',
    border: '1px solid #da3633',
    color: '#ff7b72',
    padding: '12px 16px',
    borderRadius: 8,
    fontSize: 14,
  },
  sliderContainer: {
    background: '#161b22',
    borderRadius: 12,
    padding: '16px 24px',
    border: '1px solid #30363d',
  },
  sliderLabel: {
    color: '#c9d1d9',
    fontSize: 13,
    display: 'block',
    marginBottom: 8,
  },
  slider: {
    width: '100%',
    accentColor: '#1f6feb',
    cursor: 'pointer',
  },
  metricsBar: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
  },
  pill: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: 10,
    padding: '10px 18px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
    minWidth: 80,
  },
  vizGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: 20,
  },
  console: {
    background: '#161b22',
    borderRadius: 12,
    padding: 24,
    border: '1px solid #30363d',
  },
  consoleTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: '#f0f6fc',
    margin: '0 0 12px 0',
  },
  consolePre: {
    background: '#0d1117',
    color: '#7ee787',
    padding: 16,
    borderRadius: 8,
    fontSize: 13,
    fontFamily: "'SF Mono', 'Fira Code', monospace",
    lineHeight: 1.6,
    overflow: 'auto',
    maxHeight: 300,
    whiteSpace: 'pre-wrap',
    margin: 0,
  },
};
