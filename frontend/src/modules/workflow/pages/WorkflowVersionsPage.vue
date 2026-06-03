<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import * as workflowApi from '../services/workflow.api'

const props = defineProps<{ id: string }>()
const router = useRouter()
const state = reactive({
  items: [] as { version: number; state: string; published_at: string | null }[],
  loading: false,
  dialog: false,
  dslText: '',
  viewing: 0,
})

async function load() {
  state.loading = true
  try {
    const r = await workflowApi.listVersions(props.id)
    state.items = r.items
  } finally {
    state.loading = false
  }
}

onMounted(load)

async function view(v: number) {
  try {
    const r = await workflowApi.getVersionDsl(props.id, v)
    state.dslText = JSON.stringify(r.runtime, null, 2)
    state.viewing = v
    state.dialog = true
  } catch {
    ElMessage.error('加载版本失败')
  }
}
</script>

<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-button text @click="router.push({ name: 'workflow-list' })">
            <el-icon size="16" style="margin-right: 4px;"><ArrowLeft /></el-icon>
            列表
          </el-button>
          <el-button text @click="router.push({ name: 'workflow-editor', params: { id } })">编辑</el-button>
          <span class="muted">{{ id }}</span>

          <div class="card-title">
            流程版本
          </div>
        </div>
      </template>
      
      <el-table v-loading="state.loading" :data="state.items" stripe>
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="state" label="状态" width="120" />
        <el-table-column prop="published_at" label="发布时间" min-width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="view(row.version)">查看 DSL</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="state.dialog" :title="`Runtime DSL v${state.viewing}`" width="800px">
      <el-input v-model="state.dslText" type="textarea" :rows="22" readonly />
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
}
.head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-header {
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.muted {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.card-title {
  margin-left: auto;
  font-size: 16px;
  font-weight: 600;
}
</style>
