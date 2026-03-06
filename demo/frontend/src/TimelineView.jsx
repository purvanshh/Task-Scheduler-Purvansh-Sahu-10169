import React from 'react';

const STATUS_COLORS = {
  completed: '#238636',
  failed: '#da3633',
};

export default function TimelineView({ intervals, maxTick, currentTick }) {
  if (!intervals || intervals.length === 0) return null;

  const taskNames = [...new Set(intervals.map((iv) => iv.task))].sort();
  const rowHeight = 40;
  const labelWidth = 100;
  const tickWidth = Math.max(30, Math.min(60, 600 / (maxTick + 1)));
  const totalWidth = labelWidth + (maxTick + 1) * tickWidth + 20;
  const totalHeight = taskNames.length * rowHeight + 60;

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Execution Timeline</h3>
      <div style={styles.scrollWrap}>
        <svg width={totalWidth} height={totalHeight} style={{ display: 'block' }}>
          {/* Tick labels */}
          {Array.from({ length: maxTick + 1 }, (_, t) => (
            <text
              key={`tick-${t}`}
              x={labelWidth + t * tickWidth + tickWidth / 2}
              y={16}
              textAnchor="middle"
              fill="#484f58"
              fontSize={11}
              fontFamily="monospace"
            >
              {t}
            </text>
          ))}

          {/* Grid lines */}
          {Array.from({ length: maxTick + 2 }, (_, t) => (
            <line
              key={`grid-${t}`}
              x1={labelWidth + t * tickWidth}
              y1={24}
              x2={labelWidth + t * tickWidth}
              y2={totalHeight}
              stroke="#21262d"
              strokeWidth={1}
            />
          ))}

          {/* Current tick marker */}
          {currentTick !== null && currentTick !== undefined && (
            <rect
              x={labelWidth + currentTick * tickWidth}
              y={24}
              width={tickWidth}
              height={totalHeight - 24}
              fill="#1f6feb"
              opacity={0.08}
            />
          )}

          {/* Task rows */}
          {taskNames.map((taskName, rowIdx) => {
            const y = 30 + rowIdx * rowHeight;
            const taskIntervals = intervals.filter((iv) => iv.task === taskName);

            return (
              <g key={taskName}>
                {/* Row background */}
                <rect
                  x={0}
                  y={y}
                  width={totalWidth}
                  height={rowHeight}
                  fill={rowIdx % 2 === 0 ? '#0d1117' : '#161b22'}
                />

                {/* Task label */}
                <text
                  x={labelWidth - 12}
                  y={y + rowHeight / 2}
                  textAnchor="end"
                  dominantBaseline="central"
                  fill="#c9d1d9"
                  fontSize={13}
                  fontWeight="500"
                  fontFamily="monospace"
                >
                  {taskName}
                </text>

                {/* Bars */}
                {taskIntervals.map((iv, i) => {
                  const barX = labelWidth + iv.start * tickWidth + 2;
                  const barW = Math.max((iv.end - iv.start) * tickWidth - 4, 4);
                  const color = STATUS_COLORS[iv.status] || '#484f58';

                  return (
                    <g key={i}>
                      <rect
                        x={barX}
                        y={y + 6}
                        width={barW}
                        height={rowHeight - 12}
                        rx={4}
                        fill={color}
                        opacity={0.85}
                      />
                      {barW > 40 && (
                        <text
                          x={barX + barW / 2}
                          y={y + rowHeight / 2}
                          textAnchor="middle"
                          dominantBaseline="central"
                          fill="#fff"
                          fontSize={10}
                          fontWeight="bold"
                        >
                          {iv.start}–{iv.end}
                        </text>
                      )}
                      {iv.status === 'failed' && (
                        <text
                          x={barX + barW / 2}
                          y={y + rowHeight - 4}
                          textAnchor="middle"
                          fill="#ff7b72"
                          fontSize={8}
                        >
                          {iv.reason || 'failed'}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
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
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#f0f6fc',
    margin: '0 0 16px 0',
  },
  scrollWrap: {
    overflowX: 'auto',
    background: '#0d1117',
    borderRadius: 8,
    padding: 12,
  },
};
