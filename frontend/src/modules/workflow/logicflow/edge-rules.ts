import { parseWfType, type LfRawGraph } from './adapters'

export type ConnectionGraphScope = 'main' | 'loop-inner'

export function validateConnection(
  graph: LfRawGraph,
  sourceId: string,
  targetId: string,
  creatingEdgeId?: string,
  sourceAnchorId?: string,
  targetAnchorId?: string,
  scope: ConnectionGraphScope = 'main',
): { ok: true } | { ok: false; message: string } {
  if (!sourceAnchorId?.endsWith('_out')) {
    return { ok: false, message: '起点必须使用出边锚点' }
  }
  if (!targetAnchorId?.endsWith('_in')) {
    return { ok: false, message: '终点必须使用入边锚点' }
  }

  if (sourceId === targetId) {
    return { ok: false, message: '不允许自环' }
  }
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]))
  const s = nodes.get(sourceId)
  const t = nodes.get(targetId)
  if (!s || !t) return { ok: false, message: '节点不存在' }

  const st = parseWfType(s)
  const tt = parseWfType(t)
  const innerOnly = new Set(['loop_start', 'continue', 'break'])
  if (scope === 'main') {
    if (innerOnly.has(st)) {
      return { ok: false, message: `${st} 仅允许在循环体子图内使用` }
    }
    if (innerOnly.has(tt)) {
      return { ok: false, message: `${tt} 仅允许在循环体子图内使用` }
    }
  }

  if (tt === 'start') {
    return { ok: false, message: '不能连入 start' }
  }
  if (st === 'end') {
    return { ok: false, message: 'end 不能有出边' }
  }

  const outgoing = graph.edges.filter((e) => {
    if (e.sourceNodeId !== sourceId) return false
    if (!creatingEdgeId) return true
    return e.id !== creatingEdgeId
  })
  if (st === 'if') {
    return { ok: true }
  } else if (outgoing.length >= 1) {
    return { ok: false, message: `${st} 仅允许一条出边` }
  }

  return { ok: true }
}
