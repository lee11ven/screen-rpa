import { getData, http, postData, type ApiEnvelope } from '@/api/http'
import type { RuntimeWorkflow } from '../dsl/types'

export type WorkflowListItem = {
  workflow_id: string
  name: string
  status: string
  global_object_config_id: number | null
  protocol_version: number
  published_version: number | null
  updated_at: string | null
}

export type WorkflowGetData = {
  workflow_id: string
  name: string
  status: string
  global_object_config_id: number | null
  protocol_version: number
  draft_runtime: RuntimeWorkflow
  published_version: number | null
}

export type GlobalObjectConfigListItem = {
  id: number
  name: string
  updated_at: string | null
}

export type GlobalObjectConfigDetail = {
  id: number
  name: string
  config: Record<string, unknown>
  updated_at: string | null
}

export type SystemConfig = {
  sub_image_dir: string
  fullscreen_screenshot_dir: string
}

export type SelectDirectoryResult = {
  selected: boolean
  path: string
}

export type UploadSubImageTemplateData = {
  filename: string
  saved_path: string
}

export type ValidateResult = {
  valid: boolean
  errors: { path: string; message: string; node_id?: string }[]
  lowcode_return?: Record<string, unknown> | null
}

export type RunStatusData = {
  run_id: string
  workflow_id: string
  workflow_version: number
  status: string
  cancelled?: boolean
  started_at: string | null
  finished_at: string | null
  error_message: string | null
  nodes: {
    node_id: string
    node_name?: string | null
    status: string
    started_at: string | null
    finished_at: string | null
    error_code: string | null
  }[]
}

export type RunLogsData = {
  items: {
    id: number
    level: string
    node_id: string | null
    message: string
    context_json: Record<string, unknown>
    created_at: string
  }[]
  next_cursor: number | null
}

export type QueueListItem = {
  id: number
  message_id: string
  queue_status: string
  workflow_id: string
  workflow_name: string
  run_id: string
  run_status: string
  idempotency_key: string
  retry_count: number
  available_at: string | null
  dequeued_at: string | null
  done_at: string | null
  dead_at: string | null
  lease_until: string | null
  fail_reason: string | null
  updated_at: string | null
}

export async function fetchProtocolVersion(): Promise<number> {
  const d = await getData<{ protocol_version: number }>('/workflow/meta/protocol')
  return d.protocol_version
}

export async function listWorkflows(params?: {
  status?: string
  q?: string
}): Promise<{ items: WorkflowListItem[] }> {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.q) search.set('q', params.q)
  const q = search.toString()
  return getData(`/workflow/list${q ? `?${q}` : ''}`)
}

export async function createWorkflow(body: {
  name: string
  global_object_config_id: number
  workflow_id?: string | null
  draft_runtime?: RuntimeWorkflow | null
}): Promise<{ workflow_id: string; name: string }> {
  return postData('/workflow/create', body)
}

export async function updateWorkflow(body: {
  workflow_id: string
  name?: string | null
  global_object_config_id?: number | null
  draft_runtime?: RuntimeWorkflow | null
  status?: string | null
}): Promise<{ workflow_id: string; updated: boolean }> {
  return postData('/workflow/update', body)
}

export async function listGlobalObjectConfigs(params?: {
  q?: string
}): Promise<{ items: GlobalObjectConfigListItem[] }> {
  const search = new URLSearchParams()
  if (params?.q) search.set('q', params.q)
  const q = search.toString()
  return getData(`/workflow/global-config/list${q ? `?${q}` : ''}`)
}

export async function getGlobalObjectConfig(configId: number): Promise<GlobalObjectConfigDetail> {
  return getData(`/workflow/global-config/${encodeURIComponent(String(configId))}`)
}

export async function createGlobalObjectConfig(body: {
  name: string
  config: Record<string, unknown>
}): Promise<{ id: number; name: string }> {
  return postData('/workflow/global-config/create', body)
}

export async function updateGlobalObjectConfig(
  configId: number,
  body: { name?: string | null; config?: Record<string, unknown> | null },
): Promise<{ id: number; updated: boolean }> {
  return postData(`/workflow/global-config/${encodeURIComponent(String(configId))}/update`, body)
}

export async function deleteGlobalObjectConfig(configId: number): Promise<{ id: number; deleted: boolean }> {
  return postData(`/workflow/global-config/${encodeURIComponent(String(configId))}/delete`, {})
}

export async function getSystemConfig(): Promise<SystemConfig> {
  return getData('/workflow/system-config')
}

export async function updateSystemConfig(body: Partial<SystemConfig>): Promise<SystemConfig> {
  return postData('/workflow/system-config/update', body)
}

export async function selectDirectory(initialDir?: string): Promise<SelectDirectoryResult> {
  return postData('/workflow/system/select-directory', { initial_dir: initialDir || '' })
}

export async function killBackendProcess(): Promise<{ scheduled: boolean }> {
  return postData('/workflow/system/kill-backend', {})
}

export async function uploadSubImageTemplate(file: File): Promise<UploadSubImageTemplateData> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await http.post<ApiEnvelope<UploadSubImageTemplateData>>('/workflow/sub-image-template/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  if (!res.data.success) {
    throw new Error(res.data.message || `错误码 ${res.data.code}`)
  }
  return res.data.data
}

export async function getWorkflow(workflowId: string): Promise<WorkflowGetData> {
  return getData(`/workflow/${encodeURIComponent(workflowId)}`)
}

export async function validateRemote(runtime: RuntimeWorkflow): Promise<ValidateResult> {
  return postData('/workflow/validate', { runtime })
}

export async function publishWorkflow(
  workflowId: string,
): Promise<ApiEnvelope<{ workflow_id: string; version: number }>> {
  const res = await http.post<ApiEnvelope<{ workflow_id: string; version: number }>>(
    `/workflow/${encodeURIComponent(workflowId)}/publish`,
  )
  return res.data
}

export async function runWorkflow(
  workflowId: string,
  body: { input: Record<string, unknown>; version?: number | null },
): Promise<{ run_id: string; status: string }> {
  return postData(`/workflow/${encodeURIComponent(workflowId)}/run`, body)
}

export async function getRunStatus(runId: string): Promise<RunStatusData> {
  return getData(`/workflow/run/${encodeURIComponent(runId)}/status`)
}

export async function getRunLogs(
  runId: string,
  limit = 100,
  cursor?: number | null,
): Promise<RunLogsData> {
  const sp = new URLSearchParams({ limit: String(limit) })
  if (cursor != null) sp.set('cursor', String(cursor))
  return getData(`/workflow/run/${encodeURIComponent(runId)}/logs?${sp}`)
}

export async function cancelRun(
  runId: string,
): Promise<{ run_id: string; status: string; cancelled: boolean }> {
  return postData(`/workflow/run/${encodeURIComponent(runId)}/cancel`, {})
}

export async function listQueueRecords(params?: {
  queue_status?: string
  workflow_id?: string
  run_id?: string
  limit?: number
}): Promise<{ items: QueueListItem[] }> {
  const search = new URLSearchParams()
  if (params?.queue_status) search.set('queue_status', params.queue_status)
  if (params?.workflow_id) search.set('workflow_id', params.workflow_id)
  if (params?.run_id) search.set('run_id', params.run_id)
  if (params?.limit != null) search.set('limit', String(params.limit))
  const q = search.toString()
  return getData(`/workflow/queue/list${q ? `?${q}` : ''}`)
}

export async function listVersions(workflowId: string): Promise<{
  items: { version: number; state: string; published_at: string | null }[]
}> {
  return getData(`/workflow/${encodeURIComponent(workflowId)}/versions`)
}

export async function getVersionDsl(
  workflowId: string,
  version: number,
): Promise<{ version: number; state: string; runtime: RuntimeWorkflow }> {
  return getData(
    `/workflow/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(String(version))}`,
  )
}
