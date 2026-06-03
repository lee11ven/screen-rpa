<script setup lang="ts">
import LogicFlow from '@logicflow/core'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { defaultNodeConfig } from '../../dsl/defaults'
import {
  editorToLoopSubGraphPayload,
  normalizeLoopSubGraphEditorWorkflow,
  subGraphPayloadToEditor,
} from '../../dsl/loop-subgraph-model'
import { NODE_PRESENT } from '../../dsl/node-present'
import type { EditorNode, RuntimeEdge, RuntimeNode, WfNodeType } from '../../dsl/types'
import {
  canvasNodeTextForType,
  editorWorkflowToLfData,
  mergeLfIntoEditor,
  parseWfType,
  type LfRawGraph,
} from '../../logicflow/adapters'
import { validateConnection } from '../../logicflow/edge-rules'
import { registerWorkflowNodes } from '../../logicflow/register-nodes'
import { useWorkflowEditorStore } from '../../stores/workflow-editor.store'
import * as workflowApi from '../../services/workflow.api'
import LoopSubgraphInspectorPanel from './LoopSubgraphInspectorPanel.vue'
import NodePalette from './NodePalette.vue'

const props = defineProps<{
  modelValue: boolean
  loopNodeId: string | null
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const store = useWorkflowEditorStore()
const NODE_DRAG_DATA_TYPE = 'application/x-wf-node-type'

const canvasWrapRef = ref<HTMLElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)
const localWf = shallowRef<ReturnType<typeof subGraphPayloadToEditor> | null>(null)
const selectedNodeId = ref<string | null>(null)
const selectedEdgeId = ref<string | null>(null)
const lfRef = shallowRef<LogicFlow | null>(null)
let overlayObserver: MutationObserver | null = null

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  targetType: null as 'node' | 'edge' | null,
  targetId: null as string | null,
})

const selectedNode = computed(() => {
  const id = selectedNodeId.value
  const wf = localWf.value
  if (!id || !wf) return null
  return wf.nodes.find((n) => n.id === id) ?? null
})

const selectedEdge = computed(() => {
  const id = selectedEdgeId.value
  const wf = localWf.value
  const lf = lfRef.value
  if (!id || !wf || !lf) return null
  const edgeModel = lf.getEdgeModelById(id)
  if (!edgeModel) return null
  const sourceNode = wf.nodes.find((n) => n.id === edgeModel.sourceNodeId) ?? null
  const editorEdge =
    wf.edges.find(
      (e) =>
        e.from === edgeModel.sourceNodeId &&
        e.to === edgeModel.targetNodeId &&
        (e.ui?.source_anchor_id ?? '') === (edgeModel.sourceAnchorId ?? '') &&
        (e.ui?.target_anchor_id ?? '') === (edgeModel.targetAnchorId ?? ''),
    ) ??
    wf.edges.find((e) => e.from === edgeModel.sourceNodeId && e.to === edgeModel.targetNodeId) ??
    null
  const edgeText = edgeModel.text
  const label = editorEdge?.label ?? (typeof edgeText === 'string' ? edgeText : String(edgeText?.value ?? ''))
  return {
    id,
    from: edgeModel.sourceNodeId,
    to: edgeModel.targetNodeId,
    label,
    sourceType: sourceNode?.type ?? null,
    condition: editorEdge?.condition as { kind?: string; params?: Record<string, unknown> } | undefined,
  }
})

function removeModificationOverlay(root: HTMLElement | null) {
  if (!root) return
  root.querySelectorAll('svg.modification-overlay').forEach((el) => el.remove())
}

function watchAndRemoveModificationOverlay(root: HTMLElement | null) {
  if (!root) return
  const observer = new MutationObserver(() => removeModificationOverlay(root))
  observer.observe(root, { childList: true, subtree: true })
  if (overlayObserver) overlayObserver.disconnect()
  overlayObserver = observer
}

function rawGraph(): LfRawGraph {
  return lfRef.value!.getGraphRawData() as unknown as LfRawGraph
}

function syncFromLf() {
  const w = localWf.value
  const lf = lfRef.value
  if (!lf || !w) return
  localWf.value = mergeLfIntoEditor(rawGraph(), w)
}

function ensureSingleLoopStart() {
  const lf = lfRef.value
  if (!lf) return
  const raw = rawGraph()
  const starts = raw.nodes.filter((n) => parseWfType(n) === 'loop_start')
  if (starts.length > 1) {
    const drop = starts[starts.length - 1]!
    lf.deleteNode(drop.id)
    ElMessage.warning('仅允许一个「循环开始」节点')
  }
}

/** 任意删除后若子图中没有「循环开始」，则补回（防止绕过 UI 的删除） */
function restoreMissingLoopStartIfNeeded() {
  const lf = lfRef.value
  if (!lf) return
  const raw = rawGraph()
  if (raw.nodes.some((n) => parseWfType(n) === 'loop_start')) return
  const id = `loop_start_${Math.random().toString(36).slice(2, 9)}`
  lf.addNode({
    id,
    type: 'wf-loop_start',
    x: 220,
    y: 200,
    text: NODE_PRESENT.loop_start.label,
    properties: {
      wfType: 'loop_start' as const,
      config: defaultNodeConfig('loop_start'),
    },
  })
  ElMessage.warning('「循环开始」不可删除，已自动恢复')
}

function lfNodeIsLoopStart(nodeId: string): boolean {
  const lf = lfRef.value
  if (!lf) return false
  const n = rawGraph().nodes.find((x) => x.id === nodeId)
  return n ? parseWfType(n) === 'loop_start' : false
}

const contextTargetIsLoopStart = computed(() => {
  if (!contextMenu.visible || contextMenu.targetType !== 'node' || !contextMenu.targetId) return false
  return lfNodeIsLoopStart(contextMenu.targetId)
})

function onEdgeAdd(data: {
  id: string
  sourceNodeId: string
  targetNodeId: string
  sourceAnchorId?: string
  targetAnchorId?: string
}) {
  const lf = lfRef.value
  if (!lf) return
  const raw = rawGraph()
  const v = validateConnection(
    raw,
    data.sourceNodeId,
    data.targetNodeId,
    data.id,
    data.sourceAnchorId,
    data.targetAnchorId,
    'loop-inner',
  )
  if (!v.ok) {
    ElMessage.warning(v.message)
    lf.deleteEdge(data.id)
    return
  }
  const sourceNode = raw.nodes.find((n) => n.id === data.sourceNodeId)
  if (sourceNode && parseWfType(sourceNode) === 'if') {
    const edgeModel = lf.getEdgeModelById(data.id)
    if (edgeModel) {
      const conditionExpr = `\${ctx.branch_${Math.random().toString(36).slice(2, 5)}} == true`
      edgeModel.updateText('表达式')
      const currentProps = ((edgeModel as unknown as { properties?: Record<string, unknown> }).properties ?? {}) as Record<
        string,
        unknown
      >
      ;(edgeModel as unknown as { setProperties?: (props: Record<string, unknown>) => void }).setProperties?.({
        ...currentProps,
        condition: {
          kind: 'expression',
          params: { expr: conditionExpr },
        },
      })
    }
  }
  syncFromLf()
}

function hideContextMenu() {
  contextMenu.visible = false
  contextMenu.targetType = null
  contextMenu.targetId = null
}

function showContextMenu(mouseEvent: MouseEvent | undefined, targetType: 'node' | 'edge', targetId: string) {
  const wrap = canvasWrapRef.value
  if (!wrap) return
  const rect = wrap.getBoundingClientRect()
  const x = mouseEvent ? mouseEvent.clientX - rect.left : 20
  const y = mouseEvent ? mouseEvent.clientY - rect.top : 20
  contextMenu.visible = true
  contextMenu.x = x
  contextMenu.y = y
  contextMenu.targetType = targetType
  contextMenu.targetId = targetId
}

function onNodeContextMenu(payload: { data?: { id?: string }; e?: MouseEvent }) {
  payload.e?.preventDefault()
  payload.e?.stopPropagation()
  const id = payload.data?.id
  if (!id) return
  showContextMenu(payload.e, 'node', id)
}

function onEdgeContextMenu(payload: { data?: { id?: string }; e?: MouseEvent }) {
  payload.e?.preventDefault()
  payload.e?.stopPropagation()
  const id = payload.data?.id
  if (!id) return
  showContextMenu(payload.e, 'edge', id)
}

function deleteByContextMenu() {
  const lf = lfRef.value
  if (!lf || !contextMenu.targetType || !contextMenu.targetId) return
  if (contextMenu.targetType === 'node') {
    if (lfNodeIsLoopStart(contextMenu.targetId)) {
      ElMessage.warning('「循环开始」不可删除')
      hideContextMenu()
      return
    }
    lf.deleteNode(contextMenu.targetId)
    selectedNodeId.value = null
  } else {
    lf.deleteEdge(contextMenu.targetId)
    selectedEdgeId.value = null
  }
  hideContextMenu()
  syncFromLf()
}

function onGlobalPointerDown() {
  hideContextMenu()
}

function bindEvents() {
  const lf = lfRef.value
  if (!lf) return
  lf.on('node:dragend', () => syncFromLf())
  lf.on('node:add', () => {
    ensureSingleLoopStart()
    syncFromLf()
  })
  lf.on('node:delete', () => {
    ensureSingleLoopStart()
    restoreMissingLoopStartIfNeeded()
    syncFromLf()
  })
  lf.on(
    'edge:add',
    (e: unknown) =>
      onEdgeAdd(
        (e as { data: Parameters<typeof onEdgeAdd>[0] }).data,
      ),
  )
  lf.on('edge:delete', () => syncFromLf())
  lf.on('node:click', ({ data }) => {
    selectedNodeId.value = data?.id ?? null
    selectedEdgeId.value = null
    hideContextMenu()
  })
  lf.on('edge:click', ({ data }) => {
    selectedEdgeId.value = data?.id ?? null
    selectedNodeId.value = null
    hideContextMenu()
  })
  lf.on('blank:click', () => {
    selectedNodeId.value = null
    selectedEdgeId.value = null
    hideContextMenu()
  })
  lf.on('node:contextmenu', (e: unknown) => onNodeContextMenu(e as { data?: { id?: string }; e?: MouseEvent }))
  lf.on('edge:contextmenu', (e: unknown) => onEdgeContextMenu(e as { data?: { id?: string }; e?: MouseEvent }))
}

function mountLf() {
  if (!containerRef.value) return
  const lf = new LogicFlow({
    container: containerRef.value,
    grid: false,
    snapline: true,
    history: true,
    edgeType: 'bezier',
    stopScrollGraph: false,
  })
  lf.updateEditConfig({
    hoverOutline: false,
    nodeSelectedOutline: false,
    edgeSelectedOutline: false,
  })
  registerWorkflowNodes(lf)
  lfRef.value = lf
  bindEvents()
  removeModificationOverlay(containerRef.value)
  watchAndRemoveModificationOverlay(containerRef.value)
}

function renderWorkflow() {
  const lf = lfRef.value
  if (!lf || !localWf.value) return
  const data = editorWorkflowToLfData(localWf.value)
  lf.render(data as unknown as Parameters<LogicFlow['render']>[0])
  removeModificationOverlay(containerRef.value)
}

function destroyLf() {
  if (overlayObserver) {
    overlayObserver.disconnect()
    overlayObserver = null
  }
  if (lfRef.value) {
    ;(lfRef.value as unknown as { destroy?: () => void }).destroy?.()
    lfRef.value = null
  }
  if (containerRef.value) containerRef.value.innerHTML = ''
}

function loadFromStore() {
  const wf = store.currentWorkflow
  const lid = props.loopNodeId
  if (!wf || !lid) return
  const node = wf.nodes.find((n) => n.id === lid && n.type === 'loop-container')
  if (!node) {
    ElMessage.error('未找到循环体节点')
    emit('update:modelValue', false)
    return
  }
  const cfg = (node.config ?? {}) as Record<string, unknown>
  const subGraph = cfg.subGraph as { nodes?: unknown; edges?: unknown } | undefined
  const nodes = Array.isArray(subGraph?.nodes) ? (subGraph!.nodes as RuntimeNode[]) : []
  const edges = Array.isArray(subGraph?.edges) ? (subGraph!.edges as RuntimeEdge[]) : []
  const subGraphEditorUi = cfg.subGraph_editor_ui as Record<string, unknown> | undefined
  localWf.value = normalizeLoopSubGraphEditorWorkflow(
    subGraphPayloadToEditor({ nodes, edges }, wf.settings, subGraphEditorUi),
  )
}

function addNode(wfType: WfNodeType, at?: { x: number; y: number }) {
  const lf = lfRef.value
  if (!lf) return
  if (wfType === 'loop_start') {
    ElMessage.warning('循环体内已有「循环开始」，不可再添加')
    return
  }
  const id = `n_${wfType}_${Math.random().toString(36).slice(2, 9)}`
  const position = at ?? {
    x: 280 + Math.random() * 120,
    y: 200 + Math.random() * 120,
  }
  lf.addNode({
    id,
    type: `wf-${wfType}`,
    x: position.x,
    y: position.y,
    text: NODE_PRESENT[wfType].label,
    properties: {
      wfType,
      config: defaultNodeConfig(wfType),
    },
  })
}

function onCanvasDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes(NODE_DRAG_DATA_TYPE)) return
  e.preventDefault()
  e.dataTransfer.dropEffect = 'copy'
}

function onCanvasDrop(e: DragEvent) {
  const canvas = containerRef.value
  const lf = lfRef.value
  const wfType = e.dataTransfer?.getData(NODE_DRAG_DATA_TYPE) as WfNodeType | ''
  if (!canvas || !wfType || !lf) return
  e.preventDefault()
  const rect = canvas.getBoundingClientRect()
  const htmlPoint: [number, number] = [e.clientX - rect.left, e.clientY - rect.top]
  const [x, y] = lf.graphModel.transformModel.HtmlPointToCanvasPoint(htmlPoint)
  addNode(wfType, { x, y })
}

function deleteCurrentSelection() {
  const lf = lfRef.value
  if (!lf) return
  if (selectedNodeId.value) {
    if (lfNodeIsLoopStart(selectedNodeId.value)) {
      ElMessage.warning('「循环开始」不可删除')
      return
    }
    lf.deleteNode(selectedNodeId.value)
    selectedNodeId.value = null
    return
  }
  if (selectedEdgeId.value) {
    lf.deleteEdge(selectedEdgeId.value)
    selectedEdgeId.value = null
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Delete' && e.key !== 'Backspace') return
  const target = e.target as HTMLElement | null
  const tag = target?.tagName?.toLowerCase()
  if (tag === 'input' || tag === 'textarea' || target?.isContentEditable) return
  e.preventDefault()
  deleteCurrentSelection()
}

function applyLocalNode(nodeId: string, partial: Partial<EditorNode>) {
  const wf = localWf.value
  if (!wf) return
  const idx = wf.nodes.findIndex((n) => n.id === nodeId)
  if (idx < 0) return
  const n = wf.nodes[idx]!
  const next: EditorNode = { ...n, ...partial }
  const nodes = wf.nodes.slice()
  nodes[idx] = next
  localWf.value = { ...wf, nodes }
  const lf = lfRef.value
  const m = lf?.getNodeModelById(nodeId)
  if (m) {
    if (partial.name != null) {
      m.updateText(canvasNodeTextForType(next.type, partial.name))
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

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      loadFromStore()
      await nextTick()
      mountLf()
      renderWorkflow()
      ensureSingleLoopStart()
      restoreMissingLoopStartIfNeeded()
      syncFromLf()
      window.addEventListener('keydown', onKeydown)
      window.addEventListener('mousedown', onGlobalPointerDown)
    } else {
      window.removeEventListener('keydown', onKeydown)
      window.removeEventListener('mousedown', onGlobalPointerDown)
      destroyLf()
      localWf.value = null
      selectedNodeId.value = null
      selectedEdgeId.value = null
      hideContextMenu()
    }
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('mousedown', onGlobalPointerDown)
  destroyLf()
})

function onCancel() {
  emit('update:modelValue', false)
}

async function hasNestedLoopInSubflows() {
  const wf = localWf.value
  if (!wf) return false
  const subflowWorkflowIds = Array.from(
    new Set(
      wf.nodes
        .filter((n) => n.type === 'subflow')
        .map((n) => String((n.config as Record<string, unknown>)?.workflow_id ?? '').trim())
        .filter((id) => id.length > 0),
    ),
  )
  if (!subflowWorkflowIds.length) return false
  const details = await Promise.all(
    subflowWorkflowIds.map(async (workflowId) => {
      try {
        const detail = await workflowApi.getWorkflow(workflowId)
        return detail.draft_runtime.nodes.some((node) => node.type === 'loop-container')
      } catch {
        return false
      }
    }),
  )
  return details.some(Boolean)
}

async function onConfirm() {
  const wf = localWf.value
  const lid = props.loopNodeId
  if (!wf || !lid) {
    emit('update:modelValue', false)
    return
  }
  try {
    if (await hasNestedLoopInSubflows()) {
      ElMessage.error('硬门禁：检测到子流程已包含循环体，禁止在新循环体内部引用该子流程')
      return
    }
  } catch {
    ElMessage.error('子流程循环体校验失败，请稍后重试')
    return
  }
  const parent = store.currentWorkflow?.nodes.find((n) => n.id === lid)
  if (!parent || parent.type !== 'loop-container') {
    ElMessage.error('循环体节点已不存在，已关闭编辑器')
    emit('update:modelValue', false)
    return
  }
  const { subGraph, subGraph_editor_ui } = editorToLoopSubGraphPayload(wf)
  const prevCfg = { ...(parent.config ?? {}) } as Record<string, unknown>
  prevCfg.subGraph = subGraph
  if (subGraph_editor_ui != null) prevCfg.subGraph_editor_ui = subGraph_editor_ui
  else delete prevCfg.subGraph_editor_ui
  store.updateNodeById(lid, { config: prevCfg })
  emit('update:modelValue', false)
  ElMessage.success('已保存循环体内流程')
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    class="loop-subgraph-editor-dialog"
    fullscreen
    destroy-on-close
    :append-to-body="true"
    :close-on-click-modal="false"
    title="流程控制 · 循环体内流程"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="modelValue" class="loop-dialog-body">
      <div ref="canvasWrapRef" class="canvas-wrap">
        <div ref="containerRef" class="lf-canvas" @dragover="onCanvasDragOver" @drop="onCanvasDrop" />
        <div class="node-palette-panel">
          <NodePalette variant="loop-inner" @add="(t) => addNode(t)" />
        </div>
        <LoopSubgraphInspectorPanel
          :workflow-id="store.currentWorkflow?.workflow_id"
          :selected-node="selectedNode"
          :selected-edge="selectedEdge"
          :selected-edge-id="selectedEdgeId"
          :lf="lfRef"
          @close-node="selectedNodeId = null"
          @close-edge="selectedEdgeId = null"
          @apply-node="(nodeId, partial) => applyLocalNode(nodeId, partial)"
          @sync="syncFromLf"
        />
        <div
          v-if="contextMenu.visible"
          class="canvas-context-menu"
          :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
          @mousedown.stop
          @contextmenu.prevent
        >
          <el-button v-if="!contextTargetIsLoopStart" text type="danger" @click="deleteByContextMenu">删除</el-button>
          <span v-else class="ctx-menu-hint">「循环开始」不可删除</span>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="onCancel">取消</el-button>
      <el-button type="primary" @click="onConfirm">保存并关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.loop-dialog-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
}

.canvas-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
}

.lf-canvas {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  z-index: 10 !important;
}

.lf-canvas :deep(.lf-graph) {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 10 !important;
}

.lf-canvas :deep(svg.lf-canvas-overlay) {
  position: relative;
  z-index: 1 !important;
}

.lf-canvas :deep(.lf-grid) {
  position: absolute;
  inset: 0;
  width: 100% !important;
  height: 100% !important;
  z-index: 0 !important;
  pointer-events: none;
}

.lf-canvas :deep(.lf-grid svg) {
  width: 100% !important;
  height: 100% !important;
  z-index: 0 !important;
  pointer-events: none;
}

.lf-canvas :deep(.modification-overlay) {
  display: none !important;
}

.lf-canvas :deep(.lf-bezier-adjust),
.lf-canvas :deep(.lf-bezier-adjust-anchor),
.lf-canvas :deep(.lf-edge-adjust-point) {
  display: none !important;
}

.node-palette-panel {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
}

.canvas-context-menu {
  position: absolute;
  z-index: 20;
  min-width: 88px;
  padding: 4px 6px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
.ctx-menu-hint {
  display: block;
  padding: 4px 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>

<style>
.loop-subgraph-editor-dialog.el-dialog.is-fullscreen {
  display: flex;
  flex-direction: column;
  margin: 0;
}
.loop-subgraph-editor-dialog .el-dialog__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 12px 16px;
}
</style>
