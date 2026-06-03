<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { useWorkflowEditorStore } from '../../stores/workflow-editor.store'
import * as workflowApi from '../../services/workflow.api'

const props = defineProps<{ workflowId: string }>()
const store = useWorkflowEditorStore()
const router = useRouter()

async function onSave() {
  try {
    await store.saveDraft()
    ElMessage.success('已保存草稿')
  } catch {
    /* http 已提示 */
  }
}

async function onValidate() {
  try {
    await store.validateRemote()
    store.revalidateLocal()
    if (store.allIssues.length === 0) ElMessage.success('校验通过')
    else ElMessage.warning(`发现 ${store.allIssues.length} 条问题`)
  } catch {
    /* */
  }
}

async function onPublish() {
  try {
    await ElMessageBox.confirm('将校验当前草稿并发布为新版本，是否继续？', '发布', { type: 'warning' })
  } catch {
    return
  }
  const res = await workflowApi.publishWorkflow(props.workflowId)
  if (!res.success) {
    const errs = (res.data as { errors?: unknown[] } | null)?.errors
    ElMessage.error(res.message || '发布失败')
    if (errs) console.warn(errs)
    return
  }
  ElMessage.success(`已发布版本 ${res.data?.version}`)
}

function onUndo() {
  store.lfInstance?.undo()
}

function onRedo() {
  store.lfInstance?.redo()
}

function onVersions() {
  void router.push({ name: 'workflow-versions', params: { id: props.workflowId } })
}

async function onRun() {
  try {
    const detail = await workflowApi.getWorkflow(props.workflowId)
    if (detail.global_object_config_id == null) {
      ElMessage.warning('当前流程未绑定全局对象配置，请返回列表重选')
      return
    }
    // 运行编辑器流程时，确保当前画布修改先落盘并发布，避免执行旧版本。
    if (store.dirty) {
      await store.saveDraft()
    }
    const publishRes = await workflowApi.publishWorkflow(props.workflowId)
    if (!publishRes.success) {
      ElMessage.error(publishRes.message || '发布失败，无法运行')
      return
    }

    const { value } = await ElMessageBox.prompt('运行输入 JSON', '发起运行', {
      inputType: 'textarea',
      inputValue: '{}',
    })
    const input = JSON.parse(value || '{}') as Record<string, unknown>
    const r = await workflowApi.runWorkflow(props.workflowId, {
      input,
      version: publishRes.data?.version ?? undefined,
    })
    void router.push({ name: 'workflow-run', params: { runId: r.run_id } })
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('请输入合法 JSON')
  }
}
</script>

<template>
  <div class="toolbar">
    <el-space wrap>
      <el-button type="primary" :disabled="!store.dirty" @click="onSave">保存草稿</el-button>
      <el-button @click="onValidate">校验</el-button>
      <el-button type="success" @click="onPublish">发布</el-button>
      <el-button @click="onRun">运行</el-button>
      <el-button @click="onVersions">版本</el-button>
      <el-divider direction="vertical" />
      <el-button @click="onUndo">撤销</el-button>
      <el-button @click="onRedo">重做</el-button>
      <el-tag v-if="!store.protocolOk" type="warning">协议版本不一致</el-tag>
      <el-tag v-if="store.dirty" type="info">未保存</el-tag>
    </el-space>
  </div>
</template>

<style scoped>
.toolbar {
  margin-bottom: 12px;
}
</style>
