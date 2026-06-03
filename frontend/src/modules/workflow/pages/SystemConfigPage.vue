<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as workflowApi from '../services/workflow.api'

const state = reactive({
  loading: false,
  saving: false,
  killingBackend: false,
  form: {
    sub_image_dir: '',
    fullscreen_screenshot_dir: '',
  },
})

async function load() {
  state.loading = true
  try {
    const data = await workflowApi.getSystemConfig()
    state.form.sub_image_dir = data.sub_image_dir || ''
    state.form.fullscreen_screenshot_dir = data.fullscreen_screenshot_dir || ''
  } finally {
    state.loading = false
  }
}

async function onSave() {
  state.saving = true
  try {
    const data = await workflowApi.updateSystemConfig({
      sub_image_dir: state.form.sub_image_dir.trim(),
      fullscreen_screenshot_dir: state.form.fullscreen_screenshot_dir.trim(),
    })
    state.form.sub_image_dir = data.sub_image_dir || ''
    state.form.fullscreen_screenshot_dir = data.fullscreen_screenshot_dir || ''
    ElMessage.success('系统配置已保存')
  } finally {
    state.saving = false
  }
}

async function onKillBackend() {
  try {
    await ElMessageBox.confirm(
      '确认要关闭后端进程吗？执行后桌面应用后端会立即退出，页面将无法继续请求。',
      '危险操作确认',
      {
        type: 'warning',
        confirmButtonText: '确认关闭',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }
  state.killingBackend = true
  try {
    await workflowApi.killBackendProcess()
    ElMessage.success('已下发关闭后端指令，后端将退出')
  } finally {
    state.killingBackend = false
  }
}

async function pickDir(target: 'sub_image_dir' | 'fullscreen_screenshot_dir') {
  try {
    const current = state.form[target].trim()
    const data = await workflowApi.selectDirectory(current)
    if (!data.selected || !data.path) {
      return
    }
    state.form[target] = data.path
  } catch {
    ElMessage.warning('打开目录选择器失败，请手动输入绝对路径')
  }
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="state.loading">
    <el-card>
      <template #header>
        <div class="card-header">系统配置</div>
      </template>

      <el-form label-position="top">
        <el-form-item label="子图保存绝对地址">
          <div class="path-row">
            <el-input
              style="flex: 1 1 auto; width: 100%;"
              v-model="state.form.sub_image_dir"
              placeholder="例如：D:\\works\\screen-rpa\\assets\\sub-images"
              clearable
            />
            <el-button @click="pickDir('sub_image_dir')">选择文件夹</el-button>
          </div>
        </el-form-item>

        <el-form-item label="全屏截图保存绝对地址">
          <div class="path-row">
            <el-input
              style="flex: 1 1 auto; width: 100%;"
              v-model="state.form.fullscreen_screenshot_dir"
              placeholder="例如：D:\\works\\screen-rpa\\assets\\screenshots"
              clearable
            />
            <el-button @click="pickDir('fullscreen_screenshot_dir')">选择文件夹</el-button>
          </div>
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button type="primary" :loading="state.saving" @click="onSave">保存配置</el-button>
        <el-button
          type="danger"
          plain
          :loading="state.killingBackend"
          @click="onKillBackend"
        >
          关闭后端进程
        </el-button>
      </div>
    </el-card>
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

.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.path-row {
  width: 100%;
  display: flex;
  gap: 8px;
}


</style>
