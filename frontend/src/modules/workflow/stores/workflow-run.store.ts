import { defineStore } from 'pinia'
import { ref } from 'vue'
import { RUN_POLL_HIDDEN_MS, RUN_POLL_MS } from '@/config'
import { computeNodeDisplayOrder } from '../dsl/graph-order'
import * as workflowApi from '../services/workflow.api'
import type { RuntimeNode } from '../dsl/types'

const TERMINAL = new Set(['SUCCESS', 'FAILED', 'CANCELLED', 'TIMEOUT'])

function collectNodeMeta(
  nodes: RuntimeNode[],
  nodeNameMap: Record<string, string>,
  nodeTypeMap: Record<string, string>,
) {
  for (const node of nodes) {
    if (!node?.id) continue
    nodeNameMap[node.id] = node.name || node.id
    nodeTypeMap[node.id] = node.type

    if (node.type !== 'loop-container') continue
    const cfg = (node.config ?? {}) as Record<string, unknown>
    const subGraph = cfg.subGraph as { nodes?: unknown } | undefined
    const subNodes = Array.isArray(subGraph?.nodes) ? (subGraph.nodes as RuntimeNode[]) : []
    if (!subNodes.length) continue
    collectNodeMeta(subNodes, nodeNameMap, nodeTypeMap)
  }
}

export const useWorkflowRunStore = defineStore('workflowRun', () => {
  const runId = ref<string | null>(null)
  const status = ref<workflowApi.RunStatusData | null>(null)
  const logs = ref<workflowApi.RunLogsData['items']>([])
  const nextCursor = ref<number | null>(null)
  const nodeNameMap = ref<Record<string, string>>({})
  const nodeTypeMap = ref<Record<string, string>>({})
  /** 自 start 经边表顺序的节点顺序；轮询时固定，不随各节点时间戳变 */
  const graphNodeOrder = ref<string[] | null>(null)
  const polling = ref(false)
  const terminating = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null
  let nodeNameMapVersionKey: string | null = null

  function pollIntervalMs() {
    if (typeof document !== 'undefined' && document.hidden) return RUN_POLL_HIDDEN_MS
    return RUN_POLL_MS
  }

  function stopPolling() {
    if (timer) clearInterval(timer)
    timer = null
    polling.value = false
  }

  async function refresh() {
    if (!runId.value) return
    const st = await workflowApi.getRunStatus(runId.value)
    status.value = st
    const versionKey = `${st.workflow_id}@${st.workflow_version}`
    if (nodeNameMapVersionKey !== versionKey) {
      const verDsl = await workflowApi.getVersionDsl(st.workflow_id, st.workflow_version)
      const nextMap: Record<string, string> = {}
      const nextTypeMap: Record<string, string> = {}
      collectNodeMeta(verDsl.runtime.nodes ?? [], nextMap, nextTypeMap)
      nodeNameMap.value = nextMap
      nodeTypeMap.value = nextTypeMap
      nodeNameMapVersionKey = versionKey
      graphNodeOrder.value = computeNodeDisplayOrder(verDsl.runtime)
    }
    const lg = await workflowApi.getRunLogs(runId.value, 100)
    logs.value = lg.items
    nextCursor.value = lg.next_cursor
    if (TERMINAL.has(st.status)) stopPolling()
  }

  function startPolling() {
    stopPolling()
    polling.value = true
    const loop = () => {
      void refresh()
    }
    timer = setInterval(loop, pollIntervalMs())
    void refresh()
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVis)
    }
  }

  function onVis() {
    if (!polling.value || !timer) return
    clearInterval(timer)
    timer = setInterval(() => void refresh(), pollIntervalMs())
  }

  function teardownListeners() {
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', onVis)
    }
  }

  async function initRunDetail(id: string) {
    runId.value = id
    nodeNameMap.value = {}
    nodeTypeMap.value = {}
    nodeNameMapVersionKey = null
    graphNodeOrder.value = null
    startPolling()
  }

  async function fetchMoreLogs() {
    if (!runId.value || nextCursor.value == null) return
    const lg = await workflowApi.getRunLogs(runId.value, 100, nextCursor.value)
    logs.value = [...logs.value, ...lg.items]
    nextCursor.value = lg.next_cursor
  }

  async function terminateRun() {
    if (!runId.value || terminating.value) return
    terminating.value = true
    try {
      await workflowApi.cancelRun(runId.value)
      await refresh()
    } finally {
      terminating.value = false
    }
  }

  function dispose() {
    teardownListeners()
    stopPolling()
  }

  return {
    runId,
    status,
    logs,
    nextCursor,
    nodeNameMap,
    nodeTypeMap,
    graphNodeOrder,
    polling,
    terminating,
    initRunDetail,
    refresh,
    fetchMoreLogs,
    terminateRun,
    dispose,
  }
})
