import { defineStore } from 'pinia'
import { computed, ref, shallowRef, watch } from 'vue'
import LogicFlow from '@logicflow/core'
import { AUTO_SAVE_MS, EXPECTED_PROTOCOL_VERSION } from '@/config'
import { compileToRuntime } from '../dsl/compiler'
import { editorFromRuntime } from '../dsl/defaults'
import { validateRuntimeSchema } from '../dsl/schema'
import type { EditorNode, EditorWorkflow, ValidateIssue } from '../dsl/types'
import { validateEditorWorkflow } from '../dsl/validator'
import type { LfRawGraph } from '../logicflow/adapters'
import { mergeLfIntoEditor } from '../logicflow/adapters'
import { canvasNodeTextForType } from '../logicflow/adapters'
import * as workflowApi from '../services/workflow.api'

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T
}

export const useWorkflowEditorStore = defineStore('workflowEditor', () => {
  const currentWorkflow = ref<EditorWorkflow | null>(null)
  const selectedNodeId = ref<string | null>(null)
  const dirty = ref(false)
  const localIssues = ref<ValidateIssue[]>([])
  const remoteIssues = ref<ValidateIssue[]>([])
  const lfInstance = shallowRef<LogicFlow | null>(null)
  const loading = ref(false)
  const protocolOk = ref(true)
  /** 仅用于触发 LogicFlow 全量重绘（初始化 / 撤销重做） */
  const canvasGeneration = ref(0)

  const historyStack = ref<EditorWorkflow[]>([])
  const futureStack = ref<EditorWorkflow[]>([])

  const allIssues = computed(() => [...localIssues.value, ...remoteIssues.value])

  function pushHistory() {
    if (!currentWorkflow.value) return
    historyStack.value.push(clone(currentWorkflow.value))
    futureStack.value = []
    if (historyStack.value.length > 60) historyStack.value.shift()
  }

  function setLf(lf: LogicFlow | null) {
    lfInstance.value = lf
  }

  function revalidateLocal() {
    if (!currentWorkflow.value) {
      localIssues.value = []
      return
    }
    const graph = validateEditorWorkflow(currentWorkflow.value)
    const rt = compileToRuntime(currentWorkflow.value)
    const schema = validateRuntimeSchema(rt)
    localIssues.value = [...graph, ...schema]
  }

  function applyGraphFromLf(raw: LfRawGraph, opts?: { recordHistory?: boolean }) {
    if (!currentWorkflow.value) return
    if (opts?.recordHistory !== false) pushHistory()
    currentWorkflow.value = mergeLfIntoEditor(raw, currentWorkflow.value)
    dirty.value = true
    revalidateLocal()
  }

  function bumpCanvas() {
    canvasGeneration.value += 1
  }

  function updateSelectedNodeConfig(partial: Partial<EditorNode>) {
    const id = selectedNodeId.value
    if (!id) return
    updateNodeById(id, partial)
  }

  function updateNodeById(nodeId: string, partial: Partial<EditorNode>) {
    if (!currentWorkflow.value) return
    const idx = currentWorkflow.value.nodes.findIndex((n) => n.id === nodeId)
    if (idx < 0) return
    const n = currentWorkflow.value.nodes[idx]!
    currentWorkflow.value.nodes.splice(idx, 1, { ...n, ...partial })
    dirty.value = true
    revalidateLocal()
    const lf = lfInstance.value
    if (lf) {
      const m = lf.getNodeModelById(nodeId)
      if (m) {
        if (partial.name != null) {
          const canvasText = canvasNodeTextForType(n.type, partial.name)
          m.updateText(canvasText)
        }
        const p = (m.properties as Record<string, unknown>) ?? {}
        if (partial.name != null) p.node_name = partial.name
        if (partial.config) p.config = partial.config
        if (partial.timeout_sec !== undefined) p.timeout_sec = partial.timeout_sec
        if (partial.on_error !== undefined) p.on_error = partial.on_error
        if (partial.retry_policy !== undefined) p.retry_policy = partial.retry_policy
        m.setProperties(p)
      }
    }
  }

  async function initEditor(workflowId: string) {
    loading.value = true
    try {
      const pv = await workflowApi.fetchProtocolVersion()
      protocolOk.value = pv === EXPECTED_PROTOCOL_VERSION
      const data = await workflowApi.getWorkflow(workflowId)
      currentWorkflow.value = editorFromRuntime(data.draft_runtime)
      dirty.value = false
      historyStack.value = []
      futureStack.value = []
      localIssues.value = []
      remoteIssues.value = []
      revalidateLocal()
      bumpCanvas()
    } finally {
      loading.value = false
    }
  }

  async function saveDraft() {
    if (!currentWorkflow.value) return
    const rt = compileToRuntime(currentWorkflow.value)
    await workflowApi.updateWorkflow({
      workflow_id: currentWorkflow.value.workflow_id,
      draft_runtime: rt,
    })
    dirty.value = false
  }

  async function validateRemote() {
    if (!currentWorkflow.value) return
    const rt = compileToRuntime(currentWorkflow.value)
    const res = await workflowApi.validateRemote(rt)
    remoteIssues.value = (res.errors ?? []).map((e) => ({
      path: e.path,
      message: e.message,
      node_id: e.node_id,
    }))
  }

  function compileRuntimeDsl() {
    if (!currentWorkflow.value) return null
    return compileToRuntime(currentWorkflow.value)
  }

  function undoWorkflow() {
    const prev = historyStack.value.pop()
    if (!prev || !currentWorkflow.value) return
    futureStack.value.push(clone(currentWorkflow.value))
    currentWorkflow.value = prev
    dirty.value = true
    revalidateLocal()
    bumpCanvas()
  }

  function redoWorkflow() {
    const next = futureStack.value.pop()
    if (!next || !currentWorkflow.value) return
    historyStack.value.push(clone(currentWorkflow.value))
    currentWorkflow.value = next
    dirty.value = true
    revalidateLocal()
    bumpCanvas()
  }

  function focusIssue(issue: ValidateIssue) {
    if (!issue.node_id) return
    selectedNodeId.value = issue.node_id
    lfInstance.value?.selectElementById(issue.node_id)
  }

  let autosaveTimer: ReturnType<typeof setTimeout> | null = null
  watch(
    () => currentWorkflow.value,
    () => {
      if (!dirty.value) return
      if (autosaveTimer) clearTimeout(autosaveTimer)
      autosaveTimer = setTimeout(() => {
        autosaveTimer = null
        void saveDraft().catch(() => {})
      }, AUTO_SAVE_MS)
    },
    { deep: true },
  )

  return {
    currentWorkflow,
    selectedNodeId,
    dirty,
    localIssues,
    remoteIssues,
    allIssues,
    lfInstance,
    loading,
    protocolOk,
    canvasGeneration,
    setLf,
    initEditor,
    applyGraphFromLf,
    updateSelectedNodeConfig,
    updateNodeById,
    saveDraft,
    validateRemote,
    compileRuntimeDsl,
    revalidateLocal,
    undoWorkflow,
    redoWorkflow,
    focusIssue,
  }
})
