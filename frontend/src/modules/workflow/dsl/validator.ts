import { compileToRuntime } from './compiler'
import type { EditorWorkflow, RuntimeWorkflow, ValidateIssue } from './types'

function outgoingMap(edges: { from: string; to: string }[]): Map<string, string[]> {
  const m = new Map<string, string[]>()
  for (const e of edges) {
    const arr = m.get(e.from) ?? []
    arr.push(e.to)
    m.set(e.from, arr)
  }
  return m
}

function incomingMap(edges: { from: string; to: string }[]): Map<string, string[]> {
  const m = new Map<string, string[]>()
  for (const e of edges) {
    const arr = m.get(e.to) ?? []
    arr.push(e.from)
    m.set(e.to, arr)
  }
  return m
}

/** 从 start 出发可达节点集合 */
function reachableFromStart(
  startId: string,
  outgoing: Map<string, string[]>,
): Set<string> {
  const seen = new Set<string>()
  const q = [startId]
  while (q.length) {
    const id = q.pop()!
    if (seen.has(id)) continue
    seen.add(id)
    for (const t of outgoing.get(id) ?? []) q.push(t)
  }
  return seen
}

/** 能到达任意 end 的节点集合（反向 BFS） */
function canReachEnd(endIds: string[], incoming: Map<string, string[]>): Set<string> {
  const seen = new Set<string>()
  const q = [...endIds]
  while (q.length) {
    const id = q.pop()!
    if (seen.has(id)) continue
    seen.add(id)
    for (const f of incoming.get(id) ?? []) q.push(f)
  }
  return seen
}

/**
 * 图结构校验（与后端分层思路一致的前端兜底）
 */
export function validateGraphStructure(wf: RuntimeWorkflow): ValidateIssue[] {
  const issues: ValidateIssue[] = []
  const nodes = wf.nodes
  const edges = wf.edges

  const byId = new Map(nodes.map((n) => [n.id, n]))
  for (const e of edges) {
    if (!byId.has(e.from)) {
      issues.push({ path: `edges`, message: `边的 from 不存在: ${e.from}` })
    }
    if (!byId.has(e.to)) {
      issues.push({ path: `edges`, message: `边的 to 不存在: ${e.to}` })
    }
  }

  const starts = nodes.filter((n) => n.type === 'start')
  if (starts.length !== 1) {
    issues.push({
      path: 'nodes',
      message: `必须且仅有一个 start 节点，当前 ${starts.length} 个`,
    })
  }
  const ends = nodes.filter((n) => n.type === 'end')
  if (ends.length < 1) {
    issues.push({ path: 'nodes', message: '至少需要一个 end 节点' })
  }

  const out = outgoingMap(edges)
  const inc = incomingMap(edges)

  if (starts.length === 1) {
    const sid = starts[0]!.id
    const outs = out.get(sid) ?? []
    if (outs.length > 1) {
      issues.push({
        path: `nodes[${sid}]`,
        message: 'start 节点最多一条出边',
        node_id: sid,
      })
    }
    if ((inc.get(sid) ?? []).length > 0) {
      issues.push({ path: `nodes[${sid}]`, message: 'start 不允许入边', node_id: sid })
    }
  }

  for (const n of nodes) {
    if (n.type === 'end') {
      if ((out.get(n.id) ?? []).length > 0) {
        issues.push({ path: `nodes[${n.id}]`, message: 'end 不允许出边', node_id: n.id })
      }
    }
  }

  for (const n of nodes) {
    const outs = out.get(n.id) ?? []
    if (n.type !== 'if' && n.type !== 'end') {
      if (outs.length > 1) {
        issues.push({
          path: `nodes[${n.id}]`,
          message: `${n.type} 节点最多一条出边`,
          node_id: n.id,
        })
      }
    }
  }

  if (starts.length === 1 && ends.length >= 1) {
    const startId = starts[0]!.id
    const endIds = ends.map((e) => e.id)
    const fwd = reachableFromStart(startId, out)
    const bwd = canReachEnd(endIds, inc)
    for (const n of nodes) {
      if (!fwd.has(n.id)) {
        issues.push({
          path: `nodes[${n.id}]`,
          message: '节点从 start 不可达',
          node_id: n.id,
        })
      } else if (!bwd.has(n.id)) {
        issues.push({
          path: `nodes[${n.id}]`,
          message: '节点无法到达任一 end',
          node_id: n.id,
        })
      }
    }
  }

  return issues
}

export function validateIfBranches(wf: RuntimeWorkflow): ValidateIssue[] {
  const issues: ValidateIssue[] = []
  const byId = new Map(wf.nodes.map((n) => [n.id, n]))
  const outEdges = wf.edges.filter((e) => {
    const n = byId.get(e.from)
    return n?.type === 'if'
  })
  const byFrom = new Map<string, typeof wf.edges>()
  for (const e of outEdges) {
    const arr = byFrom.get(e.from) ?? []
    arr.push(e)
    byFrom.set(e.from, arr)
  }
  for (const n of wf.nodes) {
    if (n.type !== 'if') continue
    const arr = byFrom.get(n.id) ?? []
    if (arr.length === 0) {
      issues.push({
        path: `nodes[${n.id}]`,
        message: 'if 节点至少需要一条出边',
        node_id: n.id,
      })
    }
  }
  for (const [from, arr] of byFrom) {
    const normalizedConditions = arr
      .map((e) => {
        const condition = e.condition
        if (!condition || typeof condition !== 'object') {
          const legacyExpr = String(e.label ?? '').trim()
          if (!legacyExpr) return ''
          return JSON.stringify({ kind: 'expression', params: { expr: legacyExpr } })
        }
        const kind = String(condition.kind ?? '').trim()
        if (!kind) return ''
        const params = condition.params && typeof condition.params === 'object' ? condition.params : {}
        return JSON.stringify({ kind, params })
      })
      .filter(Boolean)
    if (normalizedConditions.length !== arr.length) {
      issues.push({
        path: `nodes[${from}]`,
        message: 'if 每条出边都需要配置条件',
        node_id: from,
      })
      continue
    }
    const uniqueConditions = new Set(normalizedConditions)
    if (uniqueConditions.size !== normalizedConditions.length) {
      issues.push({
        path: `nodes[${from}]`,
        message: 'if 出边条件不能重复',
        node_id: from,
      })
    }
  }
  return issues
}

function validateLoopSubgraphStructure(loopNodeId: string, cfg: Record<string, unknown>): ValidateIssue[] {
  const issues: ValidateIssue[] = []
  const maxIterations = Number(cfg.maxIterations)
  if (!Number.isInteger(maxIterations) || maxIterations <= 0) {
    issues.push({
      path: `nodes[${loopNodeId}].config.maxIterations`,
      message: 'loop-container.maxIterations 必须是正整数',
      node_id: loopNodeId,
    })
  }
  const loopId = String(cfg.loopId ?? '').trim()
  if (!loopId) {
    issues.push({
      path: `nodes[${loopNodeId}].config.loopId`,
      message: 'loop-container.loopId 不能为空',
      node_id: loopNodeId,
    })
  }
  const subGraph = cfg.subGraph as { nodes?: unknown; edges?: unknown } | undefined
  if (!subGraph || typeof subGraph !== 'object') {
    issues.push({
      path: `nodes[${loopNodeId}].config.subGraph`,
      message: 'loop-container.subGraph 必须是对象',
      node_id: loopNodeId,
    })
    return issues
  }
  const nodes = Array.isArray(subGraph.nodes) ? (subGraph.nodes as RuntimeWorkflow['nodes']) : []
  const edges = Array.isArray(subGraph.edges) ? (subGraph.edges as RuntimeWorkflow['edges']) : []
  if (nodes.length === 0) {
    issues.push({
      path: `nodes[${loopNodeId}].config.subGraph.nodes`,
      message: 'loop-container.subGraph.nodes 不能为空',
      node_id: loopNodeId,
    })
    return issues
  }
  const wf: RuntimeWorkflow = {
    workflow_id: `__loop_${loopNodeId}__`,
    name: `loop-${loopNodeId}`,
    settings: { default_timeout_sec: 60, max_retries: 0, max_loop_iterations: 1000 },
    nodes,
    edges,
  }
  const byId = new Map(nodes.map((n) => [n.id, n]))
  const starts = nodes.filter((n) => n.type === 'loop_start')
  if (starts.length !== 1) {
    issues.push({
      path: `nodes[${loopNodeId}].config.subGraph.nodes`,
      message: `loop 子图必须且仅有一个 loop_start，当前 ${starts.length} 个`,
      node_id: loopNodeId,
    })
  }
  const hasContinueOrBreak = nodes.some((n) => n.type === 'continue' || n.type === 'break')
  if (!hasContinueOrBreak) {
    issues.push({
      path: `nodes[${loopNodeId}].config.subGraph.nodes`,
      message: 'loop 子图至少包含一个 continue 或 break 节点',
      node_id: loopNodeId,
    })
  }
  const disallowed = nodes.filter((n) => n.type === 'start' || n.type === 'end' || n.type === 'loop-container')
  for (const n of disallowed) {
    issues.push({
      path: `nodes[${loopNodeId}].config.subGraph.nodes`,
      message: `loop 子图不允许节点类型: ${n.type}`,
      node_id: n.id,
    })
  }
  const outgoing = outgoingMap(edges)
  for (const n of nodes) {
    if (n.type !== 'if' && n.type !== 'break' && n.type !== 'continue') {
      if ((outgoing.get(n.id) ?? []).length > 1) {
        issues.push({
          path: `nodes[${loopNodeId}].config.subGraph.nodes[${n.id}]`,
          message: `${n.type} 节点最多一条出边`,
          node_id: n.id,
        })
      }
    }
    if ((n.type === 'continue' || n.type === 'break') && (outgoing.get(n.id) ?? []).length > 0) {
      issues.push({
        path: `nodes[${loopNodeId}].config.subGraph.nodes[${n.id}]`,
        message: `${n.type} 节点不允许出边`,
        node_id: n.id,
      })
    }
  }
  if (starts.length === 1) {
    const reachable = reachableFromStart(starts[0]!.id, outgoing)
    for (const nid of reachable) {
      const node = byId.get(nid)
      if (!node) continue
      if ((node.type === 'if' ? false : true) && (outgoing.get(nid) ?? []).length === 0 && node.type !== 'continue' && node.type !== 'break') {
        issues.push({
          path: `nodes[${loopNodeId}].config.subGraph`,
          message: `存在自然结束路径（未落到 continue/break）：${nid}`,
          node_id: nid,
        })
      }
    }
  }
  // reuse if-condition rule for subgraph
  issues.push(...validateIfBranches(wf).map((i) => ({ ...i, path: `nodes[${loopNodeId}].config.subGraph.${i.path}` })))
  return issues
}

export function validateEditorWorkflow(wf: EditorWorkflow): ValidateIssue[] {
  const runtime = compileToRuntime(wf)
  const lowcodeIssues: ValidateIssue[] = []
  for (const node of runtime.nodes) {
    if (node.type !== 'lowcode_function') continue
    const cfg = (node.config ?? {}) as Record<string, unknown>
    const codeBody = String(cfg.code_body ?? '').trim()
    if (!codeBody) {
      lowcodeIssues.push({
        path: `nodes[${node.id}].config.code_body`,
        message: 'lowcode_function 必须填写 code_body',
        node_id: node.id,
      })
    }
    const timeoutMs = Number(cfg.timeout_ms ?? 3000)
    if (!Number.isInteger(timeoutMs) || timeoutMs < 0) {
      lowcodeIssues.push({
        path: `nodes[${node.id}].config.timeout_ms`,
        message: 'timeout_ms 必须是非负整数',
        node_id: node.id,
      })
    }
    const retryTimes = Number(cfg.retry_times ?? 0)
    if (!Number.isInteger(retryTimes) || retryTimes < 0) {
      lowcodeIssues.push({
        path: `nodes[${node.id}].config.retry_times`,
        message: 'retry_times 必须是非负整数',
        node_id: node.id,
      })
    }
  }
  const loopIssues: ValidateIssue[] = []
  for (const node of runtime.nodes) {
    if (node.type === 'loop-container') {
      loopIssues.push(...validateLoopSubgraphStructure(node.id, (node.config ?? {}) as Record<string, unknown>))
    }
    if (node.type === 'loop_start' || node.type === 'continue' || node.type === 'break') {
      loopIssues.push({
        path: `nodes[${node.id}]`,
        message: `${node.type} 只能在 loop-container.subGraph 内使用`,
        node_id: node.id,
      })
    }
  }
  return [...validateGraphStructure(runtime), ...validateIfBranches(runtime), ...lowcodeIssues, ...loopIssues]
}
