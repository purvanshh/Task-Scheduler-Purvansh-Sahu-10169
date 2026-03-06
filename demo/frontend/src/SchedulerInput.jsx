import React, { useState } from 'react';

const EXAMPLES = [
  {
    name: 'Simple DAG',
    program: `TASK a 2 10
TASK b 1 5
DEPEND b a
RUN
END`,
  },
  {
    name: 'Resource Contention',
    program: `TASK a 3 10
TASK b 2 5
TASK c 1 0
RESOURCE cpu 1
REQUIRE a cpu 1
REQUIRE b cpu 1
REQUIRE c cpu 1
RUN
END`,
  },
  {
    name: 'Failure + Retry',
    program: `TASK a 2 10
TASK b 1 5
TASK c 1 0
DEPEND b a
DEPEND c b
FAIL a
RETRY a 1
RUN
END`,
  },
  {
    name: 'Diamond DAG + Resources',
    program: `TASK a 2 10
TASK b 3 5
TASK c 2 5
TASK d 1 0
DEPEND b a
DEPEND c a
DEPEND d b
DEPEND d c
RESOURCE cpu 2
RESOURCE mem 1
REQUIRE a cpu 1
REQUIRE b cpu 1 
REQUIRE b mem 1
REQUIRE c cpu 1
REQUIRE d cpu 2
RUN
END`,
  },
  {
    name: 'Cascade Failure',
    program: `TASK root 1
TASK mid1 1
TASK mid2 1
TASK leaf1 1
TASK leaf2 1
TASK leaf3 1
DEPEND mid1 root
DEPEND mid2 root
DEPEND leaf1 mid1
DEPEND leaf2 mid1
DEPEND leaf3 mid2
FAIL root
RUN
END`,
  },
];

export default function SchedulerInput({ onRun, loading }) {
  const [program, setProgram] = useState(EXAMPLES[0].program);

  const handleRun = () => {
    if (program.trim()) onRun(program.trim());
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Scheduler Input</h2>
        <div style={styles.examples}>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.name}
              onClick={() => setProgram(ex.program)}
              style={styles.exampleBtn}
            >
              {ex.name}
            </button>
          ))}
        </div>
      </div>
      <textarea
        value={program}
        onChange={(e) => setProgram(e.target.value)}
        style={styles.textarea}
        spellCheck={false}
        placeholder="Enter scheduler commands..."
      />
      <button
        onClick={handleRun}
        disabled={loading}
        style={{
          ...styles.runBtn,
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? 'Running...' : 'Run Scheduler'}
      </button>
    </div>
  );
}

const styles = {
  container: {
    background: '#161b22',
    borderRadius: 12,
    padding: 24,
    border: '1px solid #30363d',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    flexWrap: 'wrap',
    gap: 12,
  },
  title: {
    fontSize: 18,
    fontWeight: 600,
    color: '#f0f6fc',
    margin: 0,
  },
  examples: {
    display: 'flex',
    gap: 8,
    flexWrap: 'wrap',
  },
  exampleBtn: {
    background: '#21262d',
    color: '#8b949e',
    border: '1px solid #30363d',
    borderRadius: 6,
    padding: '6px 12px',
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  textarea: {
    width: '100%',
    height: 200,
    background: '#0d1117',
    color: '#c9d1d9',
    border: '1px solid #30363d',
    borderRadius: 8,
    padding: 16,
    fontSize: 14,
    fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', monospace",
    lineHeight: 1.6,
    resize: 'vertical',
    outline: 'none',
  },
  runBtn: {
    marginTop: 16,
    width: '100%',
    padding: '12px 24px',
    background: '#238636',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background 0.15s',
    letterSpacing: 0.3,
  },
};
