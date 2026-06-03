import type { RuntimeWorkflow } from './types'

/**
 * 与 `outgoingMap` 一致：同一起点的出边按 `edges` 数组中的出现顺序排列。
 */
function buildOutgoingInEdgeOrder(edges: { from: string; to: string }[]): Map<string, string[]> {
  const m = new Map<string, string[]>()
  for (const e of edges) {
    const arr = m.get(e.from) ?? []
    arr.push(e.to)
    m.set(e.from, arr)
  }
  return m
}

/**
 * 从 `start` 沿出边（边表顺序 = 连接顺序）前序 DFS，得到时间线等使用的稳定节点顺序。
 * 与后端 `runtime_executor._out_edges` 的迭代顺序一致。
 */
export function computeNodeDisplayOrder(wf: RuntimeWorkflow): string[] {
  const start = wf.nodes.find((n) => n.type === 'start')
  if (!start) {
    return wf.nodes.map((n) => n.id)
  }
  const out = buildOutgoingInEdgeOrder(wf.edges)
  const outList: string[] = []
  const seen = new Set<string>()

  function visit(id: string) {
    if (seen.has(id)) return
    seen.add(id)
    outList.push(id)
    for (const to of out.get(id) ?? []) {
      visit(to)
    }
  }
  visit(start.id)

  for (const n of wf.nodes) {
    if (!seen.has(n.id)) {
      outList.push(n.id)
    }
  }
  return outList
}
