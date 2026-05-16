<template>
  <div class="drg-agent-layout">
    <div class="task-sidebar">
      <button class="new-task-button" type="button" @click="openNewTask">
        <SvgIcon type="mdi" :path="mdiPlus" class="button-icon" />
        <span>新建任务</span>
      </button>

      <div class="task-list">
        <button
          v-for="task in taskList"
          :key="task.task_id"
          class="task-card"
          :class="{ active: selectedTaskId === task.task_id }"
          type="button"
          @click="selectTask(task.task_id)"
        >
          <span class="task-name">{{ task.task_name }}</span>
          <SvgIcon
            type="mdi"
            :path="statusIconMap[task.task_status]"
            class="task-status-icon"
            :class="`status-${task.task_status}`"
            :title="statusLabelMap[task.task_status]"
          />
        </button>
      </div>
    </div>

    <div class="agent-main">
      <div v-if="!selectedTaskId" class="new-task-view">
        <div class="agent-title-area">
          <div class="agent-title">DRG智能体</div>
        </div>

        <div class="task-composer">
          <div class="testcase-option" @click="toggleGenerateTestCase">
            <input v-model="shouldGenerateTestCase" type="checkbox" @click.stop />
            <span>生成测试用例</span>
          </div>

          <textarea
            v-model="taskInput"
            class="task-input"
            rows="1"
            :placeholder="taskInputPlaceholder"
          ></textarea>

          <button class="submit-button" type="button" aria-label="提交任务" @click="submitNewTask">
            <SvgIcon type="mdi" :path="mdiSend" class="button-icon" />
          </button>
        </div>
      </div>

      <div v-else class="task-detail-view">
        <div class="task-detail-header">
          <div>
            <div class="task-detail-label">当前任务</div>
            <div class="task-detail-title">{{ selectedTask?.task_name }}</div>
          </div>
          <span
            v-if="selectedTask"
            class="task-detail-status"
            :class="`status-${selectedTask.task_status}`"
          >
            {{ statusLabelMap[selectedTask.task_status] }}
          </span>
        </div>

        <DropDownMenu
          title="任务执行面板"
          panel-type="menu"
          :status="selectedTask?.task_status"
          :default-open="true"
        >
          <DropDownMenu title="title1" :content="content" status="pending" />
          <DropDownMenu title="title2" :content="content" status="running" />
          <DropDownMenu title="title3" :content="content" status="success" />
          <DropDownMenu title="title4" :content="content" status="failed" />
          <DropDownMenu title="title5" :content="content" status="pending" />
          <DropDownMenu title="title6" :content="content" status="running" />
        </DropDownMenu>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiClockOutline,
  mdiPlus,
  mdiProgressClock,
  mdiSend,
} from '@mdi/js'
import DropDownMenu from '@/components/DropDownMenu.vue'

type TaskStatus = 'pending' | 'running' | 'success' | 'failed'

interface TaskItem {
  task_id: string
  task_name: string
  task_status: TaskStatus
}

const taskList = ref<TaskItem[]>([
  {
    task_id: 'task-001',
    task_name: '医保结算病例分析',
    task_status: 'pending',
  },
  {
    task_id: 'task-002',
    task_name: 'DRG入组校验',
    task_status: 'running',
  },
  {
    task_id: 'task-003',
    task_name: '测试用例生成',
    task_status: 'success',
  },
  {
    task_id: 'task-004',
    task_name: '异常病案复核',
    task_status: 'failed',
  },
])

const selectedTaskId = ref<string | null>(null)
const taskInput = ref('')
const shouldGenerateTestCase = ref(false)
const content = ref('这是任务执行进度消息')

const selectedTask = computed(() => {
  return taskList.value.find((task) => task.task_id === selectedTaskId.value)
})

const taskInputPlaceholder = computed(() => {
  return shouldGenerateTestCase.value ? '请输入您想要的测试用例类型' : '请输入电子病历'
})

const statusIconMap: Record<TaskStatus, string> = {
  pending: mdiClockOutline,
  running: mdiProgressClock,
  success: mdiCheckCircleOutline,
  failed: mdiAlertCircleOutline,
}

const statusLabelMap: Record<TaskStatus, string> = {
  pending: '等待中',
  running: '运行中',
  success: '已成功',
  failed: '已失败',
}

const openNewTask = () => {
  selectedTaskId.value = null
}

const selectTask = (taskId: string) => {
  selectedTaskId.value = taskId
}

const toggleGenerateTestCase = () => {
  shouldGenerateTestCase.value = !shouldGenerateTestCase.value
}

const submitNewTask = () => {
  const taskName = taskInput.value.trim()
  if (!taskName) return

  const newTask: TaskItem = {
    task_id: `task-${Date.now()}`,
    task_name: shouldGenerateTestCase.value ? `${taskName}（生成测试用例）` : taskName,
    task_status: 'pending',
  }

  taskList.value = [newTask, ...taskList.value]
  selectedTaskId.value = newTask.task_id
  taskInput.value = ''
  shouldGenerateTestCase.value = false
}
</script>

<style lang="scss" scoped>
.drg-agent-layout {
  min-height: calc(100vh - 64px);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  color: #1e293b;
}

.task-sidebar {
  padding: 16px;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 127, 212, 0.12);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.new-task-button {
  height: 44px;
  border: none;
  border-radius: 8px;
  background: #007fd4;
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.button-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.task-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card {
  width: 100%;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}

.task-card:hover {
  border-color: rgba(0, 127, 212, 0.28);
  background: #f8fbff;
}

.task-card.active {
  border-color: rgba(0, 127, 212, 0.56);
  background: #eef8ff;
}

.task-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
}

.task-status-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: currentColor;
}

.status-pending {
  color: #64748b;
}

.status-running {
  color: #007fd4;
}

.status-success {
  color: #16a34a;
}

.status-failed {
  color: #dc2626;
}

.agent-main {
  min-height: calc(100vh - 64px);
}

.new-task-view {
  min-height: calc(100vh - 64px);
  padding: 32px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.agent-title-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.agent-title {
  margin: 0;
  color: #007fd4;
  font-size: 52px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: 0;
}

.task-composer {
  width: min(920px, 100%);
  margin: 0 auto;
  padding: 10px;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  gap: 10px;
}

.testcase-option {
  height: 42px;
  padding: 0 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.testcase-option input {
  width: 16px;
  height: 16px;
  accent-color: #007fd4;
}

.task-input {
  height: 42px;
  flex: 1;
  resize: none;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  color: #1e293b;
  font-size: 14px;
  line-height: 20px;
  outline: none;
}

.task-input:focus {
  border-color: rgba(0, 127, 212, 0.5);
}

.submit-button {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border: none;
  border-radius: 8px;
  background: #007fd4;
  color: #ffffff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.task-detail-view {
  min-height: calc(100vh - 64px);
  padding: 28px 32px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.task-detail-header {
  width: min(960px, 100%);
  max-width: 960px;
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.task-detail-label {
  margin: 0 0 4px;
  color: #64748b;
  font-size: 13px;
}

.task-detail-title {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
  line-height: 1.25;
}

.task-detail-status {
  padding: 6px 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 820px) {
  .drg-agent-layout {
    grid-template-columns: 1fr;
  }

  .task-sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(0, 127, 212, 0.12);
  }

  .task-list {
    max-height: 220px;
  }

  .task-composer {
    align-items: stretch;
    flex-direction: column;
  }

  .testcase-option,
  .submit-button {
    width: 100%;
  }

  .agent-title {
    font-size: 40px;
  }
}
</style>
