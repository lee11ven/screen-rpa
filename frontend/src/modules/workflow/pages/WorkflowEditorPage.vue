<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import CanvasPanel from '../components/editor/CanvasPanel.vue'
import TopToolbar from '../components/editor/TopToolbar.vue'
import ValidationPanel from '../components/editor/ValidationPanel.vue'
import { useWorkflowEditorStore } from '../stores/workflow-editor.store'
import { ElMessageBox } from 'element-plus'
import * as workflowApi from '../services/workflow.api'

const props = defineProps<{ id: string }>()
const router = useRouter()
const store = useWorkflowEditorStore()

onMounted(async () => {
  try {
    await store.initEditor(props.id)
  } catch {
    void router.push({ name: 'workflow-list' })
  }
})

async function editName(id: string) {
  const { value } = await ElMessageBox.prompt('请输入新的流程名称', '修改名称', {
    inputValue: store.currentWorkflow?.name,
    inputValidator: (v) => {
      if (!String(v ?? '').trim()) return '流程名称不能为空'
      return true
    },
  })
  if (value) {
    await workflowApi.updateWorkflow({
      workflow_id: id,
      name: value,
    })
    store.currentWorkflow!.name = value
    await store.saveDraft()
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
          <span class="muted">{{ id }}</span>
          
          <span style="margin-left: auto;" v-if="store.currentWorkflow" @click="() => editName(id)">{{ store.currentWorkflow.name }}</span>
        </div>
      </template>
      
      <TopToolbar v-if="store.currentWorkflow" :workflow-id="id" />
      <div v-loading="store.loading" class="body">
        <CanvasPanel />
        <ValidationPanel />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.page {
  padding: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}
.body {
  display: flex;
  gap: 12px;
  align-items: stretch;
}
.muted {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
