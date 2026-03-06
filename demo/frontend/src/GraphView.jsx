import React, { useRef, useEffect, useCallback } from 'react';

const STATE_COLORS = {
  pending: '#484f58',
  running: '#1f6feb',
  completed: '#238636',
  failed: '#da3633',
};

const NODE_RADIUS = 24;

function layoutDAG(nodes, edges) {
  const adj = {};
  const inDeg = {};
  for (const n of nodes) {
    adj[n.id] = [];
    inDeg[n.id] = 0;
  }
  for (const e of edges) {
    if (adj[e.source]) adj[e.source].push(e.target);
    if (inDeg[e.target] !== undefined) inDeg[e.target]++;
  }

  const layers = [];
  const assigned = new Set();
  let remaining = nodes.map((n) => n.id);

  while (remaining.length > 0) {
    const layer = remaining.filter(
      (id) =>
        !assigned.has(id) &&
        Object.entries(adj).every(
          ([src, targets]) =>
            !targets.includes(id) || assigned.has(src) || !nodes.find((n) => n.id === src)
        ) &&
        inDeg[id] === 0
    );

    if (layer.length === 0) {
      const unassigned = remaining.filter((id) => !assigned.has(id));
      layer.push(...unassigned);
    }

    layer.sort();
    layers.push(layer);
    for (const id of layer) assigned.add(id);

    for (const id of layer) {
      for (const t of adj[id] || []) {
        inDeg[t]--;
      }
    }

    remaining = remaining.filter((id) => !assigned.has(id));
  }

  const positions = {};
  const layerGap = 80;
  const nodeGap = 90;

  for (let li = 0; li < layers.length; li++) {
    const layer = layers[li];
    const totalWidth = (layer.length - 1) * nodeGap;
    const startX = -totalWidth / 2;
    for (let ni = 0; ni < layer.length; ni++) {
      positions[layer[ni]] = {
        x: startX + ni * nodeGap,
        y: li * layerGap,
      };
    }
  }

  return positions;
}

export default function GraphView({ graphData, taskStates }) {
  const canvasRef = useRef(null);
  const { nodes, edges } = graphData;

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const positions = layoutDAG(nodes, edges);
    const allPos = Object.values(positions);
    const minX = Math.min(...allPos.map((p) => p.x));
    const maxX = Math.max(...allPos.map((p) => p.x));
    const minY = Math.min(...allPos.map((p) => p.y));
    const maxY = Math.max(...allPos.map((p) => p.y));

    const padX = 80;
    const padY = 60;
    const w = Math.max(400, maxX - minX + padX * 2);
    const h = Math.max(200, maxY - minY + padY * 2);

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);

    const offsetX = padX - minX;
    const offsetY = padY - minY;

    ctx.clearRect(0, 0, w, h);

    for (const edge of edges) {
      const from = positions[edge.source];
      const to = positions[edge.target];
      if (!from || !to) continue;

      const fx = from.x + offsetX;
      const fy = from.y + offsetY;
      const tx = to.x + offsetX;
      const ty = to.y + offsetY;

      const dx = tx - fx;
      const dy = ty - fy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const ux = dx / dist;
      const uy = dy / dist;

      const startX = fx + ux * NODE_RADIUS;
      const startY = fy + uy * NODE_RADIUS;
      const endX = tx - ux * (NODE_RADIUS + 8);
      const endY = ty - uy * (NODE_RADIUS + 8);

      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.strokeStyle = '#484f58';
      ctx.lineWidth = 2;
      ctx.stroke();

      const arrowLen = 10;
      const angle = Math.atan2(endY - startY, endX - startX);
      ctx.beginPath();
      ctx.moveTo(endX, endY);
      ctx.lineTo(
        endX - arrowLen * Math.cos(angle - Math.PI / 6),
        endY - arrowLen * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        endX - arrowLen * Math.cos(angle + Math.PI / 6),
        endY - arrowLen * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fillStyle = '#484f58';
      ctx.fill();
    }

    for (const node of nodes) {
      const pos = positions[node.id];
      if (!pos) continue;

      const x = pos.x + offsetX;
      const y = pos.y + offsetY;
      const state = taskStates[node.id] || 'pending';
      const color = STATE_COLORS[state];

      ctx.beginPath();
      ctx.arc(x, y, NODE_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#f0f6fc';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 13px -apple-system, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(node.id, x, y);

      ctx.fillStyle = '#8b949e';
      ctx.font = '10px -apple-system, sans-serif';
      ctx.fillText(`d=${node.duration} p=${node.priority}`, x, y + NODE_RADIUS + 14);
    }
  }, [nodes, edges, taskStates]);

  useEffect(() => {
    draw();
  }, [draw]);

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Dependency Graph</h3>
      <div style={styles.legend}>
        {Object.entries(STATE_COLORS).map(([state, color]) => (
          <span key={state} style={styles.legendItem}>
            <span style={{ ...styles.dot, background: color }} />
            {state}
          </span>
        ))}
      </div>
      <div style={styles.canvasWrap}>
        <canvas ref={canvasRef} style={{ display: 'block' }} />
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
    margin: '0 0 12px 0',
  },
  legend: {
    display: 'flex',
    gap: 16,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    color: '#8b949e',
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    display: 'inline-block',
  },
  canvasWrap: {
    overflow: 'auto',
    background: '#0d1117',
    borderRadius: 8,
    padding: 16,
    display: 'flex',
    justifyContent: 'center',
  },
};
