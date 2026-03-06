/**
 * Convert raw scheduler API response into visualization-ready data structures.
 */

export function parseGraphData(tasks, dependencies) {
  const nodes = Object.entries(tasks).map(([id, info]) => ({
    id,
    duration: info.duration,
    priority: info.priority,
    state: 'pending',
  }));

  const edges = [];
  for (const [task, deps] of Object.entries(dependencies)) {
    for (const dep of deps) {
      edges.push({ source: dep, target: task });
    }
  }

  return { nodes, edges };
}

export function computeTaskStates(events) {
  const states = {};
  for (const e of events) {
    if (e.type === 'STARTED') states[e.task] = 'running';
    if (e.type === 'COMPLETED') states[e.task] = 'completed';
    if (e.type === 'FAILED') states[e.task] = 'failed';
  }
  return states;
}

export function computeTaskStatesAtTick(events, tick) {
  const states = {};
  for (const e of events) {
    if (e.tick > tick) break;
    if (e.type === 'STARTED') states[e.task] = 'running';
    if (e.type === 'COMPLETED') states[e.task] = 'completed';
    if (e.type === 'FAILED') states[e.task] = 'failed';
  }
  return states;
}

export function parseTimelineData(events, tasks) {
  const intervals = [];
  const activeStarts = {};

  for (const e of events) {
    if (e.type === 'STARTED') {
      activeStarts[e.task] = e.tick;
    } else if (e.type === 'COMPLETED') {
      const start = activeStarts[e.task];
      if (start !== undefined) {
        intervals.push({
          task: e.task,
          start,
          end: e.tick,
          status: 'completed',
          priority: tasks[e.task]?.priority ?? 0,
        });
        delete activeStarts[e.task];
      }
    } else if (e.type === 'FAILED') {
      const start = activeStarts[e.task];
      if (start !== undefined) {
        intervals.push({
          task: e.task,
          start,
          end: e.tick,
          status: 'failed',
          reason: e.reason,
          priority: tasks[e.task]?.priority ?? 0,
        });
        delete activeStarts[e.task];
      }
    }
  }

  return intervals;
}

export function parseResourceData(events, resources, requirements) {
  if (!resources || Object.keys(resources).length === 0) return [];

  const maxTick = events.reduce((m, e) => Math.max(m, e.tick), 0) + 1;

  const intervals = [];
  const starts = {};
  for (const e of events) {
    if (e.type === 'STARTED') starts[e.task] = e.tick;
    else if (e.type === 'COMPLETED') {
      if (starts[e.task] !== undefined) {
        intervals.push({ task: e.task, start: starts[e.task], end: e.tick });
        delete starts[e.task];
      }
    }
  }

  const series = {};
  for (const rname of Object.keys(resources)) {
    series[rname] = { capacity: resources[rname], data: [] };
    for (let t = 0; t < maxTick; t++) {
      let used = 0;
      for (const iv of intervals) {
        if (iv.start <= t && t < iv.end) {
          const req = requirements[iv.task];
          if (req && req[rname]) used += req[rname];
        }
      }
      series[rname].data.push({ tick: t, used, capacity: resources[rname] });
    }
  }

  return series;
}

export function getMaxTick(events) {
  if (!events || events.length === 0) return 0;
  return events.reduce((m, e) => Math.max(m, e.tick), 0);
}
