import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';

const COLORS = ['#1f6feb', '#238636', '#a371f7', '#f0883e', '#da3633', '#56d4dd'];

export default function ResourceChart({ resourceData }) {
  if (!resourceData || Object.keys(resourceData).length === 0) {
    return (
      <div style={styles.container}>
        <h3 style={styles.title}>Resource Usage</h3>
        <div style={styles.empty}>No resources defined in this program</div>
      </div>
    );
  }

  const resourceNames = Object.keys(resourceData).sort();

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Resource Usage</h3>
      <div style={styles.grid}>
        {resourceNames.map((rname, idx) => {
          const { capacity, data } = resourceData[rname];
          const color = COLORS[idx % COLORS.length];

          return (
            <div key={rname} style={styles.chartCard}>
              <div style={styles.chartHeader}>
                <span style={styles.resourceName}>{rname}</span>
                <span style={styles.capacityBadge}>capacity: {capacity}</span>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis
                    dataKey="tick"
                    stroke="#484f58"
                    fontSize={11}
                    tickLine={false}
                    label={{ value: 'Tick', position: 'bottom', fill: '#484f58', fontSize: 11 }}
                  />
                  <YAxis
                    stroke="#484f58"
                    fontSize={11}
                    tickLine={false}
                    domain={[0, capacity + 1]}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#21262d',
                      border: '1px solid #30363d',
                      borderRadius: 8,
                      color: '#c9d1d9',
                      fontSize: 12,
                    }}
                    formatter={(value) => [value, 'Used']}
                    labelFormatter={(label) => `Tick ${label}`}
                  />
                  <ReferenceLine
                    y={capacity}
                    stroke="#da3633"
                    strokeDasharray="4 4"
                    strokeWidth={1.5}
                    label={{
                      value: `max ${capacity}`,
                      position: 'right',
                      fill: '#da3633',
                      fontSize: 10,
                    }}
                  />
                  <Area
                    type="stepAfter"
                    dataKey="used"
                    stroke={color}
                    fill={color}
                    fillOpacity={0.25}
                    strokeWidth={2}
                    dot={false}
                    animationDuration={600}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          );
        })}
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
  empty: {
    color: '#484f58',
    fontSize: 14,
    padding: '24px 0',
    textAlign: 'center',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
    gap: 16,
  },
  chartCard: {
    background: '#0d1117',
    borderRadius: 8,
    padding: 16,
  },
  chartHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  resourceName: {
    color: '#c9d1d9',
    fontSize: 14,
    fontWeight: 600,
    fontFamily: 'monospace',
  },
  capacityBadge: {
    background: '#21262d',
    color: '#8b949e',
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: 11,
  },
};
