<script setup lang="ts">
import LogicFlow from '@logicflow/core'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import type { EditorNode, OnErrorPolicy, RuntimeWorkflow } from '../../dsl/types'
import * as workflowApi from '../../services/workflow.api'
import type { ActionParamDef, ActionParamGroup } from './system-action-defs'
import {
  ACTION_DEF_MAP,
  SYSTEM_ACTIONS,
  mergeActionParams,
  normalizeActionParams,
  shouldDisableActionParamInput as shouldDisableActionParamInputForForm,
} from './system-action-defs'

const props = defineProps<{
  workflowId: string | undefined
  selectedNode: EditorNode | null
  selectedEdge: {
    id: string
    from: string
    to: string
    label: string
    sourceType: string | null
    condition?: { kind?: string; params?: Record<string, unknown> }
  } | null
  selectedEdgeId: string | null
  lf: LogicFlow | null
}>()

const emit = defineEmits<{
  'close-node': []
  'close-edge': []
  'apply-node': [nodeId: string, partial: Partial<EditorNode>]
  'sync': []
}>()

function shouldDisableActionParamInput(paramKey: string): boolean {
  return shouldDisableActionParamInputForForm(form, paramKey)
}


const edgeForm = reactive({
  label: '',
  condition_kind: 'expression',
  expr: '',
  template_path: '',
  threshold: 0.85,
})

const wfList = reactive<{ items: workflowApi.WorkflowListItem[] }>({ items: [] })
const workflowContainsLoopMap = reactive<Record<string, boolean>>({})
const loadingLoopCheck = ref(false)

watch(
  () => props.selectedNode?.id,
  async (id) => {
    if (!id) return
    try {
      const r = await workflowApi.listWorkflows()
      wfList.items = r.items
      const ids = r.items.map((w) => w.workflow_id)
      for (const key of Object.keys(workflowContainsLoopMap)) {
        if (!ids.includes(key)) delete workflowContainsLoopMap[key]
      }
      loadingLoopCheck.value = true
      const details = await Promise.all(
        r.items.map(async (w) => {
          try {
            const detail = await workflowApi.getWorkflow(w.workflow_id)
            const hasLoop = detail.draft_runtime.nodes.some((node) => node.type === 'loop-container')
            return { workflowId: w.workflow_id, hasLoop }
          } catch {
            return { workflowId: w.workflow_id, hasLoop: false }
          }
        }),
      )
      for (const item of details) {
        workflowContainsLoopMap[item.workflowId] = item.hasLoop
      }
    } catch {
      wfList.items = []
    } finally {
      loadingLoopCheck.value = false
    }
  },
)

const form = reactive({
  name: '',
  subflowId: '',
  action_key: 'system.mouse_click',
  action_params: {} as Record<string, unknown>,
  action_timeout_ms: 3000,
  action_poll_interval_ms: 150,
  action_retry_times: 1,
  action_retry_interval_ms: 200,
  action_post_delay_ms: 120,
  action_jitter_ms: 30,
  action_success_condition_kind: 'none',
  action_success_condition_params: {} as Record<string, unknown>,
  wait_timeout_ms: 5000,
  wait_poll_interval_ms: 150,
  wait_condition_kind: 'image_exists',
  wait_condition_params: {} as Record<string, unknown>,
  lowcode_code_body: "return {'ok': True, 'data': {}}",
  lowcode_timeout_ms: 3000,
  lowcode_retry_times: 0,
  lowcode_enabled: true,
  loop_id: '',
  loop_max_iterations: 100,
  /** continue：进入下一轮迭代前等待（ms） */
  continue_sleep_ms: 200,
  timeout_sec: undefined as number | undefined,
  on_error: 'fail' as OnErrorPolicy,
})

const lowcodeTestLoading = ref(false)
const lowcodeTestPassed = ref<boolean | null>(null)
const lowcodeTestMessage = ref('')
const lowcodeTestErrors = ref<string[]>([])
const lowcodeTestReturnJson = ref('')

const selectedActionDef = computed(() => ACTION_DEF_MAP.get(form.action_key) ?? null)
const ACTION_PARAM_GROUP_LABELS: Record<string, string> = {
  pre_start: '起点前置定位',
  pre_end: '终点前置定位',
  pre: '前置定位',
  coordinate: '坐标与位移',
  input: '输入内容',
  execute: '执行控制',
  window: '窗口参数',
  template: '模板与匹配',
  other: '其他参数',
}

function actionParamGroupKey(actionKey: string, paramKey: string): string {
  if (paramKey === 'text_source' || paramKey === 'text_var_key') return 'input'
  if (paramKey.startsWith('pre_start_')) return 'pre_start'
  if (paramKey.startsWith('pre_end_')) return 'pre_end'
  if (paramKey.startsWith('pre_')) return 'pre'
  if (paramKey === 'x' || paramKey === 'y' || paramKey.startsWith('start_') || paramKey.startsWith('end_')) return 'coordinate'
  if (paramKey === 'delta' || paramKey.startsWith('logical_')) return 'coordinate'
  if (paramKey === 'text' || paramKey === 'key' || paramKey === 'keys' || paramKey === 'use_clipboard') return 'input'
  if (
    paramKey === 'button' ||
    paramKey === 'clicks' ||
    paramKey.endsWith('_ms') ||
    paramKey === 'jitter_px' ||
    paramKey === 'relative'
  ) {
    return 'execute'
  }
  if (paramKey === 'title' || paramKey === 'class_name' || paramKey === 'process_name' || paramKey === 'hwnd') return 'window'
  if (paramKey.includes('template') || paramKey === 'threshold' || paramKey === 'multi_scale') return 'template'
  if (actionKey === 'system.exec_command') return 'execute'
  return 'other'
}

const selectedActionParamGroups = computed<ActionParamGroup[]>(() => {
  const def = selectedActionDef.value
  if (!def) return []
  const groups = new Map<string, ActionParamDef[]>()
  for (const p of def.params) {
    const groupKey = actionParamGroupKey(def.key, p.key)
    const list = groups.get(groupKey) ?? []
    list.push(p)
    groups.set(groupKey, list)
  }
  return Array.from(groups.entries()).map(([key, params]) => ({
    key,
    label: ACTION_PARAM_GROUP_LABELS[key] ?? ACTION_PARAM_GROUP_LABELS.other,
    params,
  }))
})

watch(
  () => props.selectedNode,
  (n) => {
    clearLowcodeTestResult()
    if (!n) return
    form.name = n.name
    form.timeout_sec = n.timeout_sec
    form.on_error = n.on_error ?? 'fail'
    const c = n.config
    form.subflowId = String(c.workflow_id ?? '')
    form.action_key = String(c.action_key ?? 'system.mouse_click')
    form.action_params = mergeActionParams(form.action_key, c.params)
    form.action_timeout_ms = Number(c.timeout_ms ?? 3000)
    form.action_poll_interval_ms = Number(c.poll_interval_ms ?? 150)
    form.action_retry_times = Number(c.retry_times ?? 1)
    form.action_retry_interval_ms = Number(c.retry_interval_ms ?? 200)
    form.action_post_delay_ms = Number(c.post_delay_ms ?? 120)
    form.action_jitter_ms = Number(c.jitter_ms ?? 30)
    const successCondition = (c.success_condition as Record<string, unknown> | undefined) ?? { kind: 'none', params: {} }
    form.action_success_condition_kind = String(successCondition.kind ?? 'none')
    form.action_success_condition_params = normalizeImageConditionParams(
      form.action_success_condition_kind,
      (successCondition.params as Record<string, unknown> | undefined) ?? {},
    )
    form.wait_timeout_ms = Number(c.timeout_ms ?? 5000)
    form.wait_poll_interval_ms = Number(c.poll_interval_ms ?? 150)
    const waitCondition = (c.condition as Record<string, unknown> | undefined) ?? {
      kind: 'image_exists',
      params: { template_path: '', threshold: 0.85 },
    }
    form.wait_condition_kind = String(waitCondition.kind ?? 'image_exists')
    form.wait_condition_params = normalizeImageConditionParams(
      form.wait_condition_kind,
      (waitCondition.params as Record<string, unknown> | undefined) ?? {},
    )
    form.lowcode_code_body = String(c.code_body ?? "return {'ok': True, 'data': {}}")
    form.lowcode_timeout_ms = Number(c.timeout_ms ?? 3000)
    form.lowcode_retry_times = Number(c.retry_times ?? 0)
    form.lowcode_enabled = Boolean(c.enabled ?? true)
    form.loop_id = String(c.loopId ?? '')
    form.loop_max_iterations = Number(c.maxIterations ?? 100)
    if (n.type === 'continue') {
      const raw = (c as { sleep_ms?: unknown }).sleep_ms
      const explicit =
        typeof raw === 'number' ||
        (typeof raw === 'string' && String(raw).trim() !== '' && !Number.isNaN(Number(raw)))
      form.continue_sleep_ms = explicit ? Math.max(0, Math.round(Number(raw))) : 200
      if (!explicit) {
        nextTick(() => {
          if (props.selectedNode?.id === n.id && props.selectedNode?.type === 'continue') applyNodeConfig()
        })
      }
    }
  },
  { immediate: true },
)
watch(
  () => props.selectedEdge,
  (e) => {
    edgeForm.label = e?.label ?? ''
    if (e?.sourceType === 'if') {
      const condition = (e.condition ?? {}) as { kind?: unknown; params?: Record<string, unknown> }
      const kind = String(condition.kind ?? 'expression')
      const params = (condition.params ?? {}) as Record<string, unknown>
      const parsed =
        kind === 'sub_image_exists' || kind === 'sub_image_not_exists'
          ? {
              condition_kind: kind,
              expr: '',
              template_path: String(params.template_path ?? ''),
              threshold: Number(params.threshold ?? 0.85),
            }
          : parseIfEdgeLabel(String(params.expr ?? e?.label ?? ''))
      edgeForm.condition_kind = parsed.condition_kind
      edgeForm.expr = parsed.expr
      edgeForm.template_path = parsed.template_path
      edgeForm.threshold = parsed.threshold
    } else {
      edgeForm.condition_kind = 'expression'
      edgeForm.expr = ''
      edgeForm.template_path = ''
      edgeForm.threshold = 0.85
    }
  },
  { immediate: true },
)

function onActionKeyChange(actionKey: string) {
  form.action_key = actionKey
  form.action_params = mergeActionParams(actionKey, {})
  applyNodeConfig()
}

function subflowHasLoop(workflowId: string): boolean {
  const id = String(workflowId || '').trim()
  if (!id) return false
  return workflowContainsLoopMap[id] === true
}

function isSelfWorkflowSelection(workflowId: string): boolean {
  const selectedId = String(workflowId || '').trim()
  const currentWorkflowId = String(props.workflowId || '').trim()
  if (!selectedId || !currentWorkflowId) return false
  return selectedId === currentWorkflowId
}

function onSubflowChange(nextWorkflowId: string) {
  if (isSelfWorkflowSelection(nextWorkflowId)) {
    ElMessage.warning('硬门禁：子流程节点不能选择当前流程本身，防止无限递归')
    form.subflowId = ''
    applyNodeConfig()
    return
  }
  if (subflowHasLoop(nextWorkflowId)) {
    ElMessage.warning('硬门禁：已包含循环体的子流程，不能作为新循环体内部流程的子节点')
    form.subflowId = ''
    applyNodeConfig()
    return
  }
  applyNodeConfig()
}

function applyNodeConfig() {
  const n = props.selectedNode
  if (!n) return
  const base: Partial<EditorNode> = {
    name: form.name,
    timeout_sec: form.timeout_sec,
    on_error: form.on_error,
  }
  let config = { ...n.config }
  switch (n.type) {
    case 'subflow':
      if (isSelfWorkflowSelection(form.subflowId)) {
        ElMessage.warning('硬门禁：子流程节点不能选择当前流程本身，防止无限递归')
        return
      }
      if (subflowHasLoop(form.subflowId)) {
        ElMessage.warning('硬门禁：已包含循环体的子流程，不能作为新循环体内部流程的子节点')
        return
      }
      config = {
        ...config,
        workflow_id: form.subflowId,
        input_mapping: (config.input_mapping as object) ?? {},
        output_mapping: (config.output_mapping as object) ?? {},
      }
      break
    case 'action':
      config = {
        ...config,
        action_key: form.action_key,
        params: normalizeActionParams(form.action_key, form.action_params),
        timeout_ms: form.action_timeout_ms,
        poll_interval_ms: form.action_poll_interval_ms,
        retry_times: form.action_retry_times,
        retry_interval_ms: form.action_retry_interval_ms,
        post_delay_ms: form.action_post_delay_ms,
        jitter_ms: form.action_jitter_ms,
        success_condition: {
          kind: form.action_success_condition_kind,
          params: { ...form.action_success_condition_params },
        },
      }
      break
    case 'wait':
      config = {
        ...config,
        timeout_ms: form.wait_timeout_ms,
        poll_interval_ms: form.wait_poll_interval_ms,
        condition: {
          kind: form.wait_condition_kind,
          params: { ...form.wait_condition_params },
        },
      }
      break
    case 'lowcode_function':
      config = {
        ...config,
        code_body: form.lowcode_code_body,
        timeout_ms: form.lowcode_timeout_ms,
        retry_times: form.lowcode_retry_times,
        enabled: form.lowcode_enabled,
      }
      break
    case 'loop-container': {
      config = {
        ...config,
        loopId: String(form.loop_id || '').trim(),
        maxIterations: Number(form.loop_max_iterations || 0),
        subGraph: (config.subGraph as Record<string, unknown>) ?? { nodes: [], edges: [] },
      }
      break
    }
    case 'continue':
      config = {
        ...config,
        sleep_ms: Math.max(0, Math.round(Number(form.continue_sleep_ms) || 0)),
      }
      break
    default:
      break
  }
  emit('apply-node', n.id, { ...base, config })
}

const uploadingActionParamKey = ref<string | null>(null)

function isTemplatePathParam(paramKey: string): boolean {
  return paramKey.includes('template_path')
}

function normalizeImageConditionParams(kind: string, params: Record<string, unknown> | undefined): Record<string, unknown> {
  const next = { ...(params ?? {}) }
  if (kind === 'image_exists' || kind === 'image_not_exists') {
    next.template_path = String(next.template_path ?? '')
    next.threshold = Number(next.threshold ?? 0.85)
  }
  return next
}

async function uploadTemplateForParam(options: UploadRequestOptions, applyPath: (savedPath: string) => void) {
  const rawFile = options.file
  if (!rawFile) return
  try {
    const result = await workflowApi.uploadSubImageTemplate(rawFile)
    applyPath(result.saved_path)
    options.onSuccess?.(result)
    ElMessage.success(`上传成功：${result.filename}`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '上传失败'
    options.onError?.({ name: 'UploadError', message, status: 500, method: 'post', url: '' } as never)
    ElMessage.error(message)
  } finally {
    /* noop */
  }
}

async function uploadActionTemplateForParam(options: UploadRequestOptions, paramKey: string) {
  uploadingActionParamKey.value = paramKey
  try {
    await uploadTemplateForParam(options, (savedPath) => {
      form.action_params[paramKey] = savedPath
      applyNodeConfig()
    })
  } finally {
    uploadingActionParamKey.value = null
  }
}

function getPreTemplateUploader(paramKey: string) {
  return (options: UploadRequestOptions) => uploadActionTemplateForParam(options, paramKey)
}

function parseIfEdgeLabel(label: string) {
  const raw = String(label ?? '').trim()
  if (!raw) return { condition_kind: 'expression', expr: '', template_path: '', threshold: 0.85 }
  return { condition_kind: 'expression', expr: raw, template_path: '', threshold: 0.85 }
}

function getIfConditionLabel(kind: string) {
  if (kind === 'sub_image_exists') return '子图存在'
  if (kind === 'sub_image_not_exists') return '子图不存在'
  return '表达式'
}

function buildIfEdgeCondition() {
  if (edgeForm.condition_kind === 'sub_image_exists' || edgeForm.condition_kind === 'sub_image_not_exists') {
    return {
      kind: edgeForm.condition_kind,
      params: {
        template_path: String(edgeForm.template_path ?? '').trim(),
        threshold: Number(edgeForm.threshold ?? 0.85),
      },
    }
  }
  return {
    kind: 'expression',
    params: { expr: String(edgeForm.expr ?? '').trim() },
  }
}

function richTextByIfCondition(
  condition: { kind: string; params?: Record<string, unknown> },
  fallbackLabel = '',
): string {
  const kind = String(condition.kind ?? '').trim()
  if (kind) return getIfConditionLabel(kind)
  return String(fallbackLabel ?? '').trim() || '表达式'
}

const uploadingEdgeTemplate = ref(false)
const uploadingWaitConditionTemplate = ref(false)
const uploadingActionSuccessConditionTemplate = ref(false)
const lowcodeTextareaRef = ref<HTMLTextAreaElement | null>(null)
const lowcodeHighlightRef = ref<HTMLElement | null>(null)
const lowcodeFullscreen = ref(false)

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function highlightPythonCode(code: string): string {
  const escaped = escapeHtml(code)
  const withComments = escaped.replace(/(#.*)$/gm, '<span class="py-comment">$1</span>')
  const withStrings = withComments.replace(
    /(\"[^\"\\]*(?:\\.[^\"\\]*)*\"|\'[^'\\]*(?:\\.[^'\\]*)*\')/g,
    '<span class="py-string">$1</span>',
  )
  const withKeywords = withStrings.replace(
    /\b(def|return|if|elif|else|for|while|in|try|except|finally|with|as|pass|break|continue|and|or|not|True|False|None|from|import)\b/g,
    '<span class="py-keyword">$1</span>',
  )
  const withBuiltins = withKeywords.replace(
    /\b(len|range|min|max|sum|str|int|float|dict|list|bool|enumerate)\b/g,
    '<span class="py-builtin">$1</span>',
  )
  return withBuiltins.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="py-number">$1</span>')
}

const lowcodeHighlightedHtml = computed(() => {
  const content = String(form.lowcode_code_body ?? '')
  return `${highlightPythonCode(content)}\n`
})

function highlightJsonText(jsonText: string): string {
  const escaped = escapeHtml(jsonText)
  return escaped.replace(
    /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"\s*:?)|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (match, stringToken) => {
      if (stringToken) {
        return /:\s*$/.test(stringToken)
          ? `<span class="json-key">${match}</span>`
          : `<span class="json-string">${match}</span>`
      }
      if (/true|false/.test(match)) return `<span class="json-boolean">${match}</span>`
      if (/null/.test(match)) return `<span class="json-null">${match}</span>`
      return `<span class="json-number">${match}</span>`
    },
  )
}

const lowcodeTestReturnHighlightedHtml = computed(() => {
  const content = String(lowcodeTestReturnJson.value ?? '')
  return `${highlightJsonText(content)}\n`
})

function syncLowcodeScroll() {
  const ta = lowcodeTextareaRef.value
  const hl = lowcodeHighlightRef.value
  if (!ta || !hl) return
  hl.scrollTop = ta.scrollTop
  hl.scrollLeft = ta.scrollLeft
}

function onLowcodeInput() {
  applyNodeConfig()
  void nextTick(() => syncLowcodeScroll())
}

function onLowcodeKeydown(e: KeyboardEvent) {
  if (e.key !== 'Tab') return
  const ta = lowcodeTextareaRef.value
  if (!ta) return
  e.preventDefault()
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const src = form.lowcode_code_body
  form.lowcode_code_body = `${src.slice(0, start)}    ${src.slice(end)}`
  void nextTick(() => {
    ta.selectionStart = ta.selectionEnd = start + 4
    onLowcodeInput()
  })
}

function toggleLowcodeFullscreen() {
  lowcodeFullscreen.value = !lowcodeFullscreen.value
  void nextTick(() => syncLowcodeScroll())
}

function clearLowcodeTestResult() {
  lowcodeTestPassed.value = null
  lowcodeTestMessage.value = ''
  lowcodeTestErrors.value = []
  lowcodeTestReturnJson.value = ''
}

function stringifyLowcodeReturn(value: unknown): string {
  if (value == null) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function buildLowcodeFunctionTestRuntime(): RuntimeWorkflow {
  return {
    workflow_id: '__lowcode_test__',
    name: 'Lowcode Function Test',
    settings: {
      default_timeout_sec: 60,
      max_retries: 0,
      max_loop_iterations: 100,
    },
    nodes: [
      { id: 'start_1', type: 'start', name: '开始', config: {} },
      { id: 'lowcode_1', type: 'lowcode_function', name: form.name || '函数体测试', config: {} },
      { id: 'end_1', type: 'end', name: '结束', config: {} },
    ],
    edges: [
      { from: 'start_1', to: 'lowcode_1' },
      { from: 'lowcode_1', to: 'end_1' },
    ],
  }
}

async function loadLowcodeTestCtxFromGlobalConfig(): Promise<Record<string, unknown>> {
  const workflowId = props.workflowId
  if (!workflowId) return {}
  try {
    const detail = await workflowApi.getWorkflow(workflowId)
    const configId = detail.global_object_config_id
    if (configId == null) return {}
    const configDetail = await workflowApi.getGlobalObjectConfig(configId)
    return configDetail.config ?? {}
  } catch {
    return {}
  }
}

async function runLowcodeFunctionTest() {
  if (props.selectedNode?.type !== 'lowcode_function') return
  clearLowcodeTestResult()
  lowcodeTestLoading.value = true
  try {
    const runtime = buildLowcodeFunctionTestRuntime()
    const testCtx = await loadLowcodeTestCtxFromGlobalConfig()
    const testNode = runtime.nodes.find((n) => n.id === 'lowcode_1')
    if (!testNode) throw new Error('测试节点创建失败')
    testNode.config = {
      code_body: form.lowcode_code_body,
      timeout_ms: Number(form.lowcode_timeout_ms ?? 3000),
      retry_times: Number(form.lowcode_retry_times ?? 0),
      enabled: Boolean(form.lowcode_enabled),
      test_ctx: testCtx,
    }
    const result = await workflowApi.validateRemote(runtime)
    if (result.valid) {
      lowcodeTestPassed.value = true
      lowcodeTestMessage.value = '函数体校验通过，可继续保存或发布。'
      lowcodeTestReturnJson.value = stringifyLowcodeReturn(result.lowcode_return)
      return
    }
    const relatedErrors = result.errors
      .filter((err) => err.node_id === 'lowcode_1' || err.path.includes('code_body'))
      .map((err) => err.message)
    lowcodeTestPassed.value = false
    lowcodeTestErrors.value = relatedErrors.length > 0 ? relatedErrors : result.errors.map((err) => err.message)
    lowcodeTestMessage.value = '函数体校验失败，请根据错误信息修正代码。'
  } catch (error) {
    lowcodeTestPassed.value = false
    lowcodeTestMessage.value = error instanceof Error ? error.message : '测试失败，请稍后重试'
    lowcodeTestErrors.value = []
  } finally {
    lowcodeTestLoading.value = false
  }
}

async function uploadEdgeTemplate(options: UploadRequestOptions) {
  const rawFile = options.file
  if (!rawFile) return
  uploadingEdgeTemplate.value = true
  try {
    const result = await workflowApi.uploadSubImageTemplate(rawFile)
    edgeForm.template_path = result.saved_path
    applyEdgeConfig()
    options.onSuccess?.(result)
    ElMessage.success(`上传成功：${result.filename}`)
  } catch (error) {
    const message = error instanceof Error ? error.message : '上传失败'
    options.onError?.({ name: 'UploadError', message, status: 500, method: 'post', url: '' } as never)
    ElMessage.error(message)
  } finally {
    uploadingEdgeTemplate.value = false
  }
}

async function uploadWaitConditionTemplate(options: UploadRequestOptions) {
  uploadingWaitConditionTemplate.value = true
  try {
    await uploadTemplateForParam(options, (savedPath) => {
      form.wait_condition_params.template_path = savedPath
      applyNodeConfig()
    })
  } finally {
    uploadingWaitConditionTemplate.value = false
  }
}

async function uploadActionSuccessConditionTemplate(options: UploadRequestOptions) {
  uploadingActionSuccessConditionTemplate.value = true
  try {
    await uploadTemplateForParam(options, (savedPath) => {
      form.action_success_condition_params.template_path = savedPath
      applyNodeConfig()
    })
  } finally {
    uploadingActionSuccessConditionTemplate.value = false
  }
}

function onWaitConditionKindChange(kind: string) {
  form.wait_condition_kind = kind
  form.wait_condition_params = normalizeImageConditionParams(kind, form.wait_condition_params)
  applyNodeConfig()
}

function onActionSuccessConditionKindChange(kind: string) {
  form.action_success_condition_kind = kind
  form.action_success_condition_params = normalizeImageConditionParams(kind, form.action_success_condition_params)
  applyNodeConfig()
}

function applyEdgeConfig() {
  if (!props.lf || !props.selectedEdgeId) return
  const edgeModel = props.lf.getEdgeModelById(props.selectedEdgeId)
  if (!edgeModel) return
  const isIfEdge = props.selectedEdge?.sourceType === 'if'
  const nextCondition = isIfEdge ? buildIfEdgeCondition() : undefined
  const nextLabel = isIfEdge ? richTextByIfCondition(nextCondition!, edgeForm.label) : String(edgeForm.label ?? '')
  edgeModel.updateText(nextLabel)
  edgeForm.label = nextLabel
  if (isIfEdge) {
    const currentProps = ((edgeModel as unknown as { properties?: Record<string, unknown> }).properties ?? {}) as Record<
      string,
      unknown
    >
    ;(edgeModel as unknown as { setProperties?: (props: Record<string, unknown>) => void }).setProperties?.({
      ...currentProps,
      condition: nextCondition,
    })
  }
  emit('sync')
}
</script>

<template>
  <div v-if="selectedNode" class="node-config-panel">
      <div class="node-config-head">
        <span class="node-config-title">节点配置</span>
        <el-button text @click="emit('close-node')">关闭</el-button>
      </div>
      <el-form label-position="top" @submit.prevent>
        <div class="config-group">
          <div class="config-group-title">基础信息</div>
          <el-form-item label="名称">
            <el-input v-model="form.name" @change="applyNodeConfig" />
          </el-form-item>
        </div>

        <div v-if="selectedNode.type === 'continue'" class="config-group">
          <div class="config-group-title">节点参数</div>
          <el-form-item label="等待下一轮执行的时间（ms）">
            <el-input-number v-model="form.continue_sleep_ms" :min="100" :step="1" @change="applyNodeConfig" />
          </el-form-item>
        </div>

        <div
          v-if="
            selectedNode.type === 'subflow' ||
            selectedNode.type === 'wait' ||
            selectedNode.type === 'lowcode_function'
          "
          class="config-group"
        >
          <div class="config-group-title">节点参数</div>
          <template v-if="selectedNode.type === 'subflow'">
            <el-form-item label="子流程">
              <el-select
                v-model="form.subflowId"
                filterable
                :loading="loadingLoopCheck"
                placeholder="选择 workflow"
                @change="onSubflowChange"
              >
                <el-option
                  v-for="w in wfList.items"
                  :key="w.workflow_id"
                  :label="`${w.name} (${w.workflow_id})${isSelfWorkflowSelection(w.workflow_id) ? ' - 当前流程，禁选' : workflowContainsLoopMap[w.workflow_id] ? ' - 已含循环体，禁选' : ''}`"
                  :value="w.workflow_id"
                  :disabled="isSelfWorkflowSelection(w.workflow_id) || workflowContainsLoopMap[w.workflow_id]"
                />
              </el-select>
            </el-form-item>
          </template>
          <template v-if="selectedNode.type === 'wait'">
            <el-form-item label="超时(ms)">
              <el-input-number v-model="form.wait_timeout_ms" :min="100" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="轮询间隔(ms)">
              <el-input-number v-model="form.wait_poll_interval_ms" :min="20" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="等待条件">
              <el-select v-model="form.wait_condition_kind" @change="onWaitConditionKindChange">
                <el-option label="元素出现" value="image_exists" />
                <el-option label="元素消失" value="image_not_exists" />
                <el-option label="窗口激活" value="window_active" />
                <el-option label="剪贴板变化" value="clipboard_changed" />
                <el-option label="表达式" value="expression" />
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="form.wait_condition_kind === 'image_exists' || form.wait_condition_kind === 'image_not_exists'"
              label="模板路径"
            >
              <div class="template-path-input-row">
                <el-input v-model="form.wait_condition_params.template_path" @change="applyNodeConfig" />
                <el-upload
                  :show-file-list="false"
                  accept="image/*"
                  :http-request="uploadWaitConditionTemplate"
                >
                  <el-button :loading="uploadingWaitConditionTemplate">上传图片</el-button>
                </el-upload>
              </div>
            </el-form-item>
            <el-form-item
              v-if="form.wait_condition_kind === 'image_exists' || form.wait_condition_kind === 'image_not_exists'"
              label="匹配阈值"
            >
              <el-input-number v-model="form.wait_condition_params.threshold" :min="0" :max="1" :step="0.01" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.wait_condition_kind === 'window_active'" label="窗口标题">
              <el-input v-model="form.wait_condition_params.title" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.wait_condition_kind === 'window_active'" label="进程名">
              <el-input v-model="form.wait_condition_params.process_name" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.wait_condition_kind === 'clipboard_changed'" label="期望文本(可选)">
              <el-input v-model="form.wait_condition_params.expected_text" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.wait_condition_kind === 'expression'" label="表达式">
              <el-input
                v-model="form.wait_condition_params.expr"
                type="textarea"
                :rows="2"
                placeholder="${ctx.xxx} == 'ok'"
                @change="applyNodeConfig"
              />
            </el-form-item>
          </template>
          <template v-if="selectedNode.type === 'lowcode_function'">
            <el-form-item>
              <div class="lowcode-editor-wrap" :class="{ 'is-fullscreen': lowcodeFullscreen }">
                <div class="lowcode-editor-header">
                  <div>Python 函数体</div>
                  <div class="lowcode-editor-toolbar">
                    <el-button size="small" type="primary" :loading="lowcodeTestLoading" @click="runLowcodeFunctionTest">
                      测试函数体
                    </el-button>
                    <el-button size="small" @click="toggleLowcodeFullscreen">
                      {{ lowcodeFullscreen ? '退出全屏' : '全屏编辑' }}
                    </el-button>
                  </div>
                </div>
                <div class="lowcode-editor">
                  <pre ref="lowcodeHighlightRef" class="lowcode-highlight-layer" v-html="lowcodeHighlightedHtml" />
                  <textarea
                    ref="lowcodeTextareaRef"
                    v-model="form.lowcode_code_body"
                    class="lowcode-editor-input"
                    rows="10"
                    placeholder="仅填写函数体，不要写 def curr_low(db, ctx):"
                    spellcheck="false"
                    @input="onLowcodeInput"
                    @scroll="syncLowcodeScroll"
                    @keydown="onLowcodeKeydown"
                  />
                </div>
              </div>
            </el-form-item>
            <div v-if="lowcodeTestPassed !== null" class="lowcode-test-result" :class="lowcodeTestPassed ? 'is-pass' : 'is-fail'">
              <div class="lowcode-test-title">{{ lowcodeTestPassed ? '测试通过' : '测试失败' }}</div>
              <div class="lowcode-test-message">{{ lowcodeTestMessage }}</div>
              <div v-if="lowcodeTestPassed && lowcodeTestReturnJson" class="lowcode-test-return">
                <div class="lowcode-test-return-label">return 实际值(JSON)</div>
                <pre class="lowcode-test-return-json" v-html="lowcodeTestReturnHighlightedHtml" />
              </div>
              <ul v-if="!lowcodeTestPassed && lowcodeTestErrors.length" class="lowcode-test-errors">
                <li v-for="(err, idx) in lowcodeTestErrors" :key="`${idx}-${err}`">{{ err }}</li>
              </ul>
            </div>
            <el-form-item label="超时(ms)">
              <el-input-number v-model="form.lowcode_timeout_ms" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="重试次数">
              <el-input-number v-model="form.lowcode_retry_times" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="启用节点">
              <el-switch v-model="form.lowcode_enabled" @change="applyNodeConfig" />
            </el-form-item>
          </template>
        </div>

        <div v-if="selectedNode.type === 'action'" class="config-group">
          <div class="config-group-title">动作配置</div>
          <el-form-item label="action_key">
            <el-select v-model="form.action_key" filterable @change="onActionKeyChange">
              <el-option v-for="a in SYSTEM_ACTIONS" :key="a.key" :label="`${a.label} (${a.key})`" :value="a.key" />
            </el-select>
          </el-form-item>
          <div v-if="selectedActionDef" class="action-hint">{{ selectedActionDef.description }}</div>
          <template v-if="selectedActionDef">
            <div v-for="group in selectedActionParamGroups" :key="group.key" class="action-param-group">
              <div class="action-param-group-title">{{ group.label }}</div>
              <el-form-item v-for="p in group.params" :key="p.key" :label="p.label">
                <el-select
                  v-if="p.key === 'text_source'"
                  v-model="form.action_params[p.key]"
                  :disabled="shouldDisableActionParamInput(p.key)"
                  @change="applyNodeConfig"
                >
                  <el-option label="直接文本" value="literal" />
                  <el-option label="全局变量Key" value="global_var" />
                </el-select>
                <el-switch
                  v-else-if="p.type === 'boolean'"
                  v-model="form.action_params[p.key]"
                  @change="applyNodeConfig"
                />
                <el-input-number
                  v-else-if="p.type === 'number'"
                  v-model="form.action_params[p.key]"
                  :min="p.min"
                  :disabled="shouldDisableActionParamInput(p.key)"
                  @change="applyNodeConfig"
                />
                <div v-else-if="isTemplatePathParam(p.key)" class="template-path-input-row">
                  <el-input
                    v-model="form.action_params[p.key]"
                    :placeholder="p.placeholder"
                    :disabled="shouldDisableActionParamInput(p.key)"
                    @change="applyNodeConfig"
                  />
                  <el-upload
                    :show-file-list="false"
                    accept="image/*"
                    :disabled="shouldDisableActionParamInput(p.key)"
                    :http-request="getPreTemplateUploader(p.key)"
                  >
                    <el-button
                      :loading="uploadingActionParamKey === p.key"
                      :disabled="shouldDisableActionParamInput(p.key)"
                    >
                      上传图片
                    </el-button>
                  </el-upload>
                </div>
                <el-input
                  v-else
                  v-model="form.action_params[p.key]"
                  :placeholder="p.placeholder"
                  :disabled="shouldDisableActionParamInput(p.key)"
                  @change="applyNodeConfig"
                />
              </el-form-item>
            </div>
          </template>
          <div class="action-param-group">
            <div class="action-param-group-title">执行等待策略</div>
            <el-form-item label="动作超时(ms)">
              <el-input-number v-model="form.action_timeout_ms" :min="100" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="轮询间隔(ms)">
              <el-input-number v-model="form.action_poll_interval_ms" :min="20" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="自动重试次数">
              <el-input-number v-model="form.action_retry_times" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="重试间隔(ms)">
              <el-input-number v-model="form.action_retry_interval_ms" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="动作后延时(ms)">
              <el-input-number v-model="form.action_post_delay_ms" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="随机抖动(ms)">
              <el-input-number v-model="form.action_jitter_ms" :min="0" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item label="成功条件">
              <el-select v-model="form.action_success_condition_kind" @change="onActionSuccessConditionKindChange">
                <el-option label="不检查" value="none" />
                <el-option label="元素出现" value="image_exists" />
                <el-option label="元素消失" value="image_not_exists" />
                <el-option label="窗口激活" value="window_active" />
                <el-option label="剪贴板变化" value="clipboard_changed" />
                <el-option label="表达式" value="expression" />
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="form.action_success_condition_kind === 'image_exists' || form.action_success_condition_kind === 'image_not_exists'"
              label="模板路径"
            >
              <div class="template-path-input-row">
                <el-input v-model="form.action_success_condition_params.template_path" @change="applyNodeConfig" />
                <el-upload
                  :show-file-list="false"
                  accept="image/*"
                  :http-request="uploadActionSuccessConditionTemplate"
                >
                  <el-button :loading="uploadingActionSuccessConditionTemplate">上传图片</el-button>
                </el-upload>
              </div>
            </el-form-item>
            <el-form-item
              v-if="form.action_success_condition_kind === 'image_exists' || form.action_success_condition_kind === 'image_not_exists'"
              label="匹配阈值"
            >
              <el-input-number
                v-model="form.action_success_condition_params.threshold"
                :min="0"
                :max="1"
                :step="0.01"
                @change="applyNodeConfig"
              />
            </el-form-item>
            <el-form-item v-if="form.action_success_condition_kind === 'window_active'" label="窗口标题">
              <el-input v-model="form.action_success_condition_params.title" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.action_success_condition_kind === 'window_active'" label="进程名">
              <el-input v-model="form.action_success_condition_params.process_name" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.action_success_condition_kind === 'clipboard_changed'" label="期望文本(可选)">
              <el-input v-model="form.action_success_condition_params.expected_text" @change="applyNodeConfig" />
            </el-form-item>
            <el-form-item v-if="form.action_success_condition_kind === 'expression'" label="表达式">
              <el-input
                v-model="form.action_success_condition_params.expr"
                type="textarea"
                :rows="2"
                placeholder="${ctx.xxx} == 'ok'"
                @change="applyNodeConfig"
              />
            </el-form-item>
          </div>
        </div>

        <div v-if="selectedNode.type !== 'start' && selectedNode.type !== 'end'" class="config-group">
          <div class="config-group-title">运行策略</div>
          <el-form-item label="超时(秒)">
            <el-input-number v-model="form.timeout_sec" :min="0" @change="applyNodeConfig" />
          </el-form-item>
          <el-form-item label="错误策略">
            <el-select v-model="form.on_error" @change="applyNodeConfig">
              <el-option label="失败" value="fail" />
              <el-option label="重试" value="retry" />
              <el-option label="跳过" value="skip" />
              <el-option label="跳转节点" value="to_node" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
    </div>
    <div v-else-if="selectedEdge" class="node-config-panel">
      <div class="node-config-head">
        <span class="node-config-title">连线配置</span>
        <el-button text @click="emit('close-edge')">关闭</el-button>
      </div>
      <el-form label-position="top" @submit.prevent>
        <div class="config-group">
          <div class="config-group-title">基础信息</div>
          <el-form-item label="起点">
            <el-input :model-value="selectedEdge.from" disabled />
          </el-form-item>
          <el-form-item label="终点">
            <el-input :model-value="selectedEdge.to" disabled />
          </el-form-item>
        </div>
        <div class="config-group">
          <div class="config-group-title">
            {{ selectedEdge.sourceType === 'if' ? '分支条件（多条件边）' : '连线标签' }}
          </div>
          <el-form-item
            :label="
              selectedEdge.sourceType === 'if'
                ? '条件配置'
                : '标签'
            "
          >
            <el-input
              v-if="selectedEdge.sourceType !== 'if'"
              v-model="edgeForm.label"
              type="textarea"
              :rows="2"
              placeholder="示例：${ctx.order.amount} >= 1000 and ${ctx.user.level} == 'vip'"
              @change="applyEdgeConfig"
            />
            <template v-else>
              <el-select v-model="edgeForm.condition_kind" @change="applyEdgeConfig">
                <el-option label="表达式" value="expression" />
                <el-option label="子图存在" value="sub_image_exists" />
                <el-option label="子图不存在" value="sub_image_not_exists" />
              </el-select>
              
              <el-input
                v-if="edgeForm.condition_kind === 'expression'"
                style="margin-top: 8px"
                v-model="edgeForm.expr"
                type="textarea"
                :rows="2"
                placeholder="示例：${ctx.order.amount} >= 1000 and ${ctx.user.level} == 'vip'"
                @change="applyEdgeConfig"
              />
              
              <template v-else>
                <div class="template-path-input-row" style="margin-top: 8px">
                  <el-input
                    v-model="edgeForm.template_path"
                    placeholder="子图模板路径"
                    @change="applyEdgeConfig"
                  />
                  <el-upload
                    :show-file-list="false"
                    accept="image/*"
                    :http-request="uploadEdgeTemplate"
                  >
                    <el-button :loading="uploadingEdgeTemplate">上传图片</el-button>
                  </el-upload>
                </div>
                <el-input-number
                  v-model="edgeForm.threshold"
                  style="margin-top: 8px"
                  :min="0"
                  :max="1"
                  :step="0.01"
                  @change="applyEdgeConfig"
                />
              </template>
            </template>
          </el-form-item>
          <div v-if="selectedEdge.sourceType === 'if'" class="action-hint">
            条件边支持任意数量；支持表达式和子图检查。表达式可直接引用任务上下文全局变量对象，如 <code>${ctx.xxx}</code>。
          </div>
        </div>
      </el-form>
    </div>
</template>

<style scoped>
.node-config-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 360px;
  max-height: calc(100% - 24px);
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 10;
}

.node-config-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.node-config-title {
  font-size: 14px;
  font-weight: 600;
}

.config-group {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: #fff;
}

.config-group-title {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.action-hint {
  margin: -2px 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.action-param-group {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.action-param-group:first-of-type {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

.action-param-group-title {
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.template-path-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-path-input-row .el-input {
  flex: 1;
}

.lowcode-editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.lowcode-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.lowcode-editor-wrap.is-fullscreen .lowcode-editor-header {
  color: #fff;
}

.lowcode-editor-wrap.is-fullscreen {
  position: fixed;
  inset: 16px;
  z-index: 5000;
  background: #0b1220;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}

.lowcode-editor-wrap.is-fullscreen .lowcode-editor {
  height: calc(100% - 40px);
}

.lowcode-editor-wrap:not(.is-fullscreen) {
  width: 100%;
}

.lowcode-editor {
  position: relative;
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: #0f172a;
  overflow: hidden;
}

.lowcode-highlight-layer {
  margin: 0;
  padding: 10px;
  min-height: 220px;
  max-height: 360px;
  overflow: auto;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #e2e8f0;
}

.lowcode-editor-input {
  position: absolute;
  inset: 0;
  width: 100%;
  min-height: 220px;
  max-height: 360px;
  border: 0;
  margin: 0;
  padding: 10px;
  resize: vertical;
  background: transparent;
  color: transparent;
  caret-color: #f8fafc;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  outline: none;
}

.lowcode-editor-input::selection {
  background: rgba(96, 165, 250, 0.35);
}

.lowcode-editor-input::placeholder {
  color: rgba(226, 232, 240, 0.55);
}

.lowcode-highlight-layer :deep(.py-keyword) {
  color: #c084fc;
}

.lowcode-highlight-layer :deep(.py-string) {
  color: #86efac;
}

.lowcode-highlight-layer :deep(.py-comment) {
  color: #94a3b8;
}

.lowcode-highlight-layer :deep(.py-number) {
  color: #fcd34d;
}

.lowcode-highlight-layer :deep(.py-builtin) {
  color: #60a5fa;
}

.lowcode-editor-wrap.is-fullscreen .lowcode-highlight-layer {
  min-height: 100%;
  max-height: 100%;
}

.lowcode-editor-wrap.is-fullscreen .lowcode-editor-input {
  min-height: 100%;
  max-height: 100%;
  resize: none;
}

.lowcode-test-result {
  margin: 4px 0 10px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
}

.lowcode-test-result.is-pass {
  border-color: rgba(16, 185, 129, 0.45);
  background: rgba(16, 185, 129, 0.08);
}

.lowcode-test-result.is-fail {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.08);
}

.lowcode-test-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.lowcode-test-message {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

.lowcode-test-errors {
  margin: 6px 0 0;
  padding-left: 16px;
  color: var(--el-color-danger);
  font-size: 12px;
}

.lowcode-test-return {
  margin-top: 8px;
}

.lowcode-test-return-label {
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--el-text-color-primary);
}

.lowcode-test-return-json {
  margin: 0;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid var(--el-border-color);
  background: rgba(15, 23, 42, 0.95);
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.lowcode-test-return-json :deep(.json-key) {
  color: #93c5fd;
}

.lowcode-test-return-json :deep(.json-string) {
  color: #86efac;
}

.lowcode-test-return-json :deep(.json-number) {
  color: #fca5a5;
}

.lowcode-test-return-json :deep(.json-boolean) {
  color: #fcd34d;
}

.lowcode-test-return-json :deep(.json-null) {
  color: #c4b5fd;
}
</style>
