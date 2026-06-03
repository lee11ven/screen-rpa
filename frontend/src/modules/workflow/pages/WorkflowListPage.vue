<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as workflowApi from '../services/workflow.api'

const router = useRouter()
const state = reactive({
  items: [] as workflowApi.WorkflowListItem[],
  loading: false,
  q: '',
  status: '' as string,
})

const configNameMap = reactive<Record<number, string>>({})
const allConfigs = ref<workflowApi.GlobalObjectConfigListItem[]>([])
const createDialogVisible = ref(false)
const createForm = reactive({
  name: '新流程',
  globalObjectConfigId: null as number | null,
})
const bindDialog = reactive({
  visible: false,
  workflowId: '',
  workflowName: '',
  selectedConfigId: null as number | null,
})
const creatingDisabled = computed(() => !createForm.name.trim() || createForm.globalObjectConfigId == null)

async function loadConfigs() {
  const r = await workflowApi.listGlobalObjectConfigs()
  allConfigs.value = r.items
  for (const item of r.items) configNameMap[item.id] = item.name
}

async function load() {
  state.loading = true
  try {
    const r = await workflowApi.listWorkflows({
      q: state.q || undefined,
      status: state.status || undefined,
    })
    state.items = r.items
    await loadConfigs()
  } finally {
    state.loading = false
  }
}

onMounted(load)

async function onCreate() {
  if (allConfigs.value.length === 0) {
    ElMessage.warning('请先在“全局对象配置”页面创建配置')
    return
  }
  createForm.name = '新流程'
  createForm.globalObjectConfigId = allConfigs.value[0]?.id ?? null
  createDialogVisible.value = true
}

async function submitCreate() {
  if (creatingDisabled.value) return
  try {
    const r = await workflowApi.createWorkflow({
      name: createForm.name.trim(),
      global_object_config_id: createForm.globalObjectConfigId!,
    })
    createDialogVisible.value = false
    ElMessage.success('已创建')
    await load()
    void router.push({ name: 'workflow-editor', params: { id: r.workflow_id } })
  } catch {
    /* http 提示 */
  }
}

async function openEditor(id: string) {
  void router.push({ name: 'workflow-editor', params: { id } })
}

function openVersions(id: string) {
  void router.push({ name: 'workflow-versions', params: { id } })
}

async function onArchive(row: workflowApi.WorkflowListItem) {
  try {
    await ElMessageBox.confirm(`归档流程 ${row.workflow_id}？`, '确认', { type: 'warning' })
    await workflowApi.updateWorkflow({ workflow_id: row.workflow_id, status: 'archived' })
    ElMessage.success('已归档')
    await load()
  } catch {
    /* */
  }
}

async function onCopy(row: workflowApi.WorkflowListItem) {
  try {
    const { value: name } = await ElMessageBox.prompt('新流程名称', '复制', {
      inputValue: `${row.name} 副本`,
    })
    if (row.global_object_config_id == null) {
      ElMessage.warning('源流程未绑定全局对象配置，无法复制')
      return
    }
    const detail = await workflowApi.getWorkflow(row.workflow_id)
    const r = await workflowApi.createWorkflow({ name, global_object_config_id: row.global_object_config_id })
    await workflowApi.updateWorkflow({
      workflow_id: r.workflow_id,
      draft_runtime: { ...detail.draft_runtime, workflow_id: r.workflow_id, name },
      global_object_config_id: row.global_object_config_id ?? undefined,
    })
    ElMessage.success('已复制')
    await load()
    void router.push({ name: 'workflow-editor', params: { id: r.workflow_id } })
  } catch {
    /* */
  }
}

async function onRename(row: workflowApi.WorkflowListItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的流程名称', '修改名称', {
      inputValue: row.name,
      inputValidator: (v) => {
        if (!String(v ?? '').trim()) return '流程名称不能为空'
        return true
      },
    })
    const name = String(value ?? '').trim()
    if (!name || name === row.name) return
    await workflowApi.updateWorkflow({
      workflow_id: row.workflow_id,
      name,
    })
    ElMessage.success('流程名称已更新')
    await load()
  } catch {
    /* cancel or http */
  }
}

async function onRun(row: workflowApi.WorkflowListItem) {
  try {
    const detail = await workflowApi.getWorkflow(row.workflow_id)
    if (detail.global_object_config_id == null) {
      ElMessage.warning('当前流程未绑定全局对象配置，请先重选配置')
      return
    }
    const { value } = await ElMessageBox.prompt('运行输入 JSON', '发起运行', {
      inputType: 'textarea',
      inputValue: '{}',
    })
    const input = JSON.parse(value || '{}') as Record<string, unknown>
    const r = await workflowApi.runWorkflow(row.workflow_id, { input })
    void router.push({ name: 'workflow-run', params: { runId: r.run_id } })
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('请输入合法 JSON')
  }
}

async function openConfigDialog(workflowId: string) {
  const detail = await workflowApi.getWorkflow(workflowId)
  bindDialog.visible = true
  bindDialog.workflowId = workflowId
  bindDialog.workflowName = detail.name
  bindDialog.selectedConfigId = detail.global_object_config_id
}

async function submitConfigDialog() {
  if (!bindDialog.workflowId) return
  if (bindDialog.selectedConfigId == null) {
    ElMessage.warning('请选择全局对象配置')
    return
  }
  try {
    await workflowApi.updateWorkflow({
      workflow_id: bindDialog.workflowId,
      global_object_config_id: bindDialog.selectedConfigId,
    })
    bindDialog.visible = false
    ElMessage.success('全局对象配置已更新')
    await load()
  } catch {
    /* http */
  }
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">流程列表</div>
      </template>
      <div class="bar">
        <el-input v-model="state.q" placeholder="搜索 id / 名称" clearable style="width: 220px" @clear="load" @keyup.enter="load" />
        <el-select v-model="state.status" placeholder="状态" clearable style="width: 140px" @change="load">
          <el-option label="活跃" value="active" />
          <el-option label="归档" value="archived" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button type="success" @click="onCreate">新建</el-button>
      </div>
      <el-table v-loading="state.loading" border :data="state.items" max-height="650" stripe>
        <el-table-column prop="workflow_id" label="ID" min-width="160" />
        <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '活跃' : '归档' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="published_version" label="已发布版本" width="120" />
        <el-table-column label="全局对象配置" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.global_object_config_id != null" type="success">
              {{ configNameMap[row.global_object_config_id] || `#${row.global_object_config_id}` }}
            </el-tag>
            <el-tag v-else type="danger">未指定</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="160" />
        <el-table-column label="操作" width="430" fixed="right">
          <template #default="{ row }">
            <el-button :disabled="row.status === 'archived'" link type="primary" @click="openEditor(row.workflow_id)">编辑</el-button>
            <el-button link @click="onRename(row)">改名</el-button>
            <el-button link type="success" @click="onRun(row)">运行</el-button>
            <el-button link @click="openConfigDialog(row.workflow_id)">重选配置</el-button>
            <el-button link @click="openVersions(row.workflow_id)">版本</el-button>
            <el-button link @click="onCopy(row)">复制</el-button>
            <el-button v-if="row.status === 'active'" link type="danger" @click="onArchive(row)">归档</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新建流程" width="760px">
      <el-form label-position="top">
        <el-form-item label="流程名称">
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item label="全局对象配置（必选）">
          <el-select v-model="createForm.globalObjectConfigId" filterable placeholder="选择全局对象配置">
            <el-option v-for="c in allConfigs" :key="c.id" :label="`${c.name} (#${c.id})`" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="creatingDisabled" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="bindDialog.visible" :title="`重选全局对象配置 - ${bindDialog.workflowName}`" width="620px">
      <el-form label-position="top">
        <el-form-item label="全局对象配置">
          <el-select v-model="bindDialog.selectedConfigId" filterable placeholder="选择全局对象配置">
            <el-option v-for="c in allConfigs" :key="c.id" :label="`${c.name} (#${c.id})`" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitConfigDialog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}
.bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
