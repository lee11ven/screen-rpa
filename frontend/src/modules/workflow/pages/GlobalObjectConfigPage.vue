<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import TypedDynamicForm from '../components/shared/TypedDynamicForm.vue'
import * as workflowApi from '../services/workflow.api'

const state = reactive({
  loading: false,
  q: '',
  items: [] as workflowApi.GlobalObjectConfigListItem[],
})

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  id: null as number | null,
  loading: false,
  form: {
    name: '',
    config: {} as Record<string, unknown>,
  },
})
const importJsonText = ref('')
const MAX_DEPTH = 5

const submitDisabled = computed(
  () => !dialog.form.name.trim() || Object.keys(dialog.form.config ?? {}).length === 0 || dialog.loading,
)

function hasInvalidConfigKeys(v: unknown): boolean {
  if (Array.isArray(v)) {
    return v.some((item) => hasInvalidConfigKeys(item))
  }
  if (!v || typeof v !== 'object') return false
  const obj = v as Record<string, unknown>
  for (const key of Object.keys(obj)) {
    if (!key.trim()) return true
    if (hasInvalidConfigKeys(obj[key])) return true
  }
  return false
}

function exceedsMaxDepth(v: unknown, depth = 1): boolean {
  if (Array.isArray(v)) {
    if (depth > MAX_DEPTH) return true
    return v.some((item) => exceedsMaxDepth(item, depth + 1))
  }
  if (v && typeof v === 'object') {
    if (depth > MAX_DEPTH) return true
    return Object.values(v as Record<string, unknown>).some((child) => exceedsMaxDepth(child, depth + 1))
  }
  return false
}

async function load() {
  state.loading = true
  try {
    const r = await workflowApi.listGlobalObjectConfigs({ q: state.q || undefined })
    state.items = r.items
  } finally {
    state.loading = false
  }
}

onMounted(load)

function onCreate() {
  dialog.visible = true
  dialog.mode = 'create'
  dialog.id = null
  dialog.form.name = ''
  dialog.form.config = {}
  importJsonText.value = ''
}

async function onEdit(row: workflowApi.GlobalObjectConfigListItem) {
  dialog.visible = true
  dialog.mode = 'edit'
  dialog.id = row.id
  dialog.loading = true
  try {
    const detail = await workflowApi.getGlobalObjectConfig(row.id)
    dialog.form.name = detail.name
    dialog.form.config = detail.config ?? {}
    importJsonText.value = JSON.stringify(detail.config ?? {}, null, 2)
  } finally {
    dialog.loading = false
  }
}

function applyImportedObject(raw: unknown) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    ElMessage.warning('仅支持导入 JSON Object')
    return
  }
  if (exceedsMaxDepth(raw, 1)) {
    ElMessage.warning(`嵌套层级不能超过 ${MAX_DEPTH} 层`)
    return
  }
  dialog.form.config = raw as Record<string, unknown>
  importJsonText.value = JSON.stringify(raw, null, 2)
  ElMessage.success('JSON 导入成功')
}

function importFromText() {
  try {
    const parsed = JSON.parse(importJsonText.value || '{}')
    applyImportedObject(parsed)
  } catch {
    ElMessage.error('JSON 格式不合法')
  }
}

function importFromFile(file: File) {
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result ?? '{}'))
      applyImportedObject(parsed)
    } catch {
      ElMessage.error('文件 JSON 格式不合法')
    }
  }
  reader.onerror = () => {
    ElMessage.error('读取文件失败')
  }
  reader.readAsText(file, 'utf-8')
}

function onJsonFileChange(uploadFile: { raw?: File }) {
  if (!uploadFile.raw) return
  importFromFile(uploadFile.raw)
}

async function onSubmit() {
  if (submitDisabled.value) return
  if (hasInvalidConfigKeys(dialog.form.config)) {
    ElMessage.warning('存在空字段名，请修正后再保存')
    return
  }
  if (exceedsMaxDepth(dialog.form.config, 1)) {
    ElMessage.warning(`嵌套层级不能超过 ${MAX_DEPTH} 层`)
    return
  }
  dialog.loading = true
  try {
    if (dialog.mode === 'create') {
      await workflowApi.createGlobalObjectConfig({
        name: dialog.form.name.trim(),
        config: dialog.form.config,
      })
      ElMessage.success('已创建')
    } else if (dialog.id != null) {
      await workflowApi.updateGlobalObjectConfig(dialog.id, {
        name: dialog.form.name.trim(),
        config: dialog.form.config,
      })
      ElMessage.success('已更新')
    }
    dialog.visible = false
    await load()
  } finally {
    dialog.loading = false
  }
}

async function onDelete(row: workflowApi.GlobalObjectConfigListItem) {
  try {
    await ElMessageBox.confirm(`删除配置 ${row.name}？`, '确认', { type: 'warning' })
    await workflowApi.deleteGlobalObjectConfig(row.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    /* cancel */
  }
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">全局对象配置</div>
      </template>
      <div class="bar">
        <el-input
          v-model="state.q"
          placeholder="搜索配置名称"
          clearable
          style="width: 240px"
          @clear="load"
          @keyup.enter="load"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button type="success" @click="onCreate">新建配置</el-button>
      </div>
      <el-table v-loading="state.loading" border :data="state.items" max-height="650" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="配置名称" min-width="220" />
        <el-table-column prop="updated_at" label="更新时间" min-width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="onEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialog.visible"
      :title="dialog.mode === 'create' ? '新建全局对象配置' : '编辑全局对象配置'"
      fullscreen
    >
      <el-form v-loading="dialog.loading" label-position="top">
        <el-form-item label="配置名称">
          <el-input v-model="dialog.form.name" />
        </el-form-item>
        <el-form-item label="导入 JSON（可选）">
          <el-input
            v-model="importJsonText"
            type="textarea"
            :rows="6"
            placeholder='粘贴 JSON Object，例如：{"env":"prod","retry":3}'
          />
          <div class="import-actions">
            <el-button @click="importFromText">从文本导入</el-button>
            <el-upload
              accept=".json,application/json"
              :show-file-list="false"
              :auto-upload="false"
              :on-change="onJsonFileChange"
            >
              <el-button>选择 JSON 文件导入</el-button>
            </el-upload>
          </div>
        </el-form-item>
        <el-form-item label="配置对象 Object（必填）">
          <TypedDynamicForm v-model="dialog.form.config" mode="object" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :disabled="submitDisabled" :loading="dialog.loading" @click="onSubmit">
          保存
        </el-button>
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

.import-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}
</style>
