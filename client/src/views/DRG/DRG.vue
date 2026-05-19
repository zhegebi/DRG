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

        <div class="agent-tabs">
          <button
            class="agent-tab"
            :class="{ active: agentType === 'notest' }"
            @click="switchAgent('notest')"
          >
            DRG入组
          </button>
          <button
            class="agent-tab"
            :class="{ active: agentType === 'test' }"
            @click="switchAgent('test')"
          >
            测试用例生成
          </button>
        </div>

        <div class="task-composer">
          <div v-if="fileList.length > 0" class="file-cards">
            <div v-for="(file, index) in fileList" :key="index" class="file-card">
              <span class="file-card-name">{{ file.name }}</span>
              <button class="file-card-remove" @click="removeFile(index)">
                <SvgIcon type="mdi" :path="mdiCloseCircle" class="file-card-remove-icon" />
              </button>
            </div>
          </div>

          <label v-if="agentType === 'notest'" class="file-upload-btn" title="上传电子病历文件">
            <SvgIcon type="mdi" :path="mdiFileUpload" class="button-icon" />
            <span>上传病历文件</span>
            <input
              type="file"
              accept=".txt,.md,.pdf"
              class="file-input-hidden"
              @change="handleFileUpload"
            />
          </label>

          <div class="task-input-row">
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

        <div v-if="selectedTask" class="task-flow-panels">
          <template v-if="viewMode === 'progress'">
            <template v-if="selectedTask.should_generate_test">
              <DropDownMenu
                title="生成测试用例"
                panel-type="menu"
                :status="getGroupStatus(testCaseSteps)"
                :default-open="true"
              >
                <DropDownMenu
                  v-for="step in testCaseSteps"
                  :key="step"
                  :title="stepNameMap[step]"
                  :content="getStepContent(step)"
                  :status="getStepStatus(step, testCaseSteps)"
                />
              </DropDownMenu>

              <DropDownMenu
                title="将测试用例DRG入组"
                panel-type="menu"
                :status="getGroupStatus(drgGroupingSteps)"
                :default-open="true"
              >
                <DropDownMenu
                  v-for="step in drgGroupingSteps"
                  :key="step"
                  :title="stepNameMap[step]"
                  :content="getStepContent(step)"
                  :status="getStepStatus(step, drgGroupingSteps)"
                />
              </DropDownMenu>
            </template>

            <template v-else>
              <DropDownMenu
                title="将电子病历DRG入组"
                panel-type="menu"
                :status="getGroupStatus(drgGroupingSteps)"
                :default-open="true"
              >
                <DropDownMenu
                  v-for="step in drgGroupingSteps"
                  :key="step"
                  :title="stepNameMap[step]"
                  :content="getStepContent(step)"
                  :status="getStepStatus(step, drgGroupingSteps)"
                />
              </DropDownMenu>
            </template>
          </template>

          <template v-else>
            <div class="result-panel">
              <div v-if="resultContent" class="result-markdown" v-html="renderedResult"></div>
              <div v-else-if="isLoadingResult" class="result-loading">加载结果中...</div>
              <div v-else class="result-empty">暂无结果</div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiClockOutline,
  mdiCloseCircle,
  mdiFileUpload,
  mdiPlus,
  mdiProgressClock,
  mdiSend,
} from '@mdi/js'
import DropDownMenu from '@/components/DropDownMenu.vue'
import {
  createTask,
  getTaskList,
  getTaskStatus,
  getTaskResultStream,
  getTaskResult,
  getTaskProgress,
} from '@/views/DRG/drg_utils'
import type { TaskStep } from '@/api'
import { marked } from 'marked'
import * as pdfjsLib from 'pdfjs-dist'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString()

type TaskStatus = 'pending' | 'running' | 'success' | 'failed'

interface TaskItem {
  task_id: string
  task_name: string
  task_status: TaskStatus
  should_generate_test: boolean
}

const stepNameMap: Record<TaskStep, string> = {
  extract_medical_record: '提取病历信息',
  get_mdc_code: '获取MDC编码',
  get_adrg_code: '获取ADRG编码',
  get_mcc_cc_level: '获取并发症等级',
  get_drg: '获取DRG信息',
  get_final_result: '获取最终结果',
  select_test_case_type: '选择测试用例类型',
  generate_test_case: '根据测试用例类型生成测试用例',
}

const testCaseSteps: TaskStep[] = ['select_test_case_type', 'generate_test_case']
const drgGroupingSteps: TaskStep[] = [
  'extract_medical_record',
  'get_mdc_code',
  'get_adrg_code',
  'get_mcc_cc_level',
  'get_drg',
  'get_final_result',
]

type AgentType = 'notest' | 'test'

const agentType = ref<AgentType>('notest')
const taskList = ref<TaskItem[]>([])
const selectedTaskId = ref<string | null>(null)
interface FileItem {
  name: string
  content: string
}

const taskInput = ref('')
const fileList = ref<FileItem[]>([])
const stepStates = ref<Record<string, { lines: string[] }>>({})
const viewMode = ref<'progress' | 'result'>('progress')
const resultContent = ref('')
const isLoadingResult = ref(false)

let progressTimer: ReturnType<typeof setInterval> | null = null
let statusTimer: ReturnType<typeof setInterval> | null = null
let pollingFlag = false

const terminalTaskStatusSet = new Set<TaskStatus>(['success', 'failed'])

const isUnfinishedTask = (task: TaskItem) => {
  return !terminalTaskStatusSet.has(task.task_status)
}

const unfinishedTaskIdSet = computed(() => {
  return new Set(
    taskList.value.filter(isUnfinishedTask).map((task) => task.task_id),
  )
})

const selectedTask = computed(() => {
  return taskList.value.find((task) => task.task_id === selectedTaskId.value)
})

const taskInputPlaceholder = computed(() => {
  return agentType.value === 'test' ? '请输入您想要的测试用例类型' : '请输入电子病历'
})

const renderedResult = computed(() => {
  if (!resultContent.value) return ''
  return marked(resultContent.value)
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

function getStepContent(step: TaskStep): string {
  const lines = stepStates.value[step]?.lines ?? []
  return lines.join('\n')
}

function drgGroupingHasStarted(): boolean {
  return drgGroupingSteps.some((step) => {
    const lines = stepStates.value[step]?.lines
    return lines && lines.length > 0
  })
}

function getStepStatus(step: TaskStep, group: TaskStep[]): TaskStatus {
  const lines = stepStates.value[step]?.lines ?? []
  if (lines.length === 0) return 'pending'

  // 测试用例生成步骤：一旦 DRG 入组阶段开始，全部算完成
  if (group === testCaseSteps && drgGroupingHasStarted()) {
    return 'success'
  }

  let lastContentIndex = -1
  for (let i = group.length - 1; i >= 0; i--) {
    const key = group[i]
    if (key === undefined) continue
    const s = stepStates.value[key]
    if (s && s.lines.length > 0) {
      lastContentIndex = i
      break
    }
  }

  const myIndex = group.indexOf(step)
  if (myIndex === lastContentIndex) return 'running'
  if (myIndex < lastContentIndex) return 'success'
  return 'pending'
}

function getGroupStatus(group: TaskStep[]): TaskStatus {
  const statuses = group.map((s) => getStepStatus(s, group))
  if (statuses.some((s) => s === 'running')) return 'running'
  if (statuses.every((s) => s === 'success')) return 'success'
  return 'pending'
}

async function fetchTaskList() {
  try {
    const list = await getTaskList()
    if (!list) return
    taskList.value = list.map((item) => ({
      task_id: item.task_id,
      task_name: item.task_name,
      task_status: item.task_status as TaskStatus,
      should_generate_test: item.should_generate_test,
    }))
  } catch (e) {
    console.error('获取任务列表失败:', e)
  }
}

function stopProgressPolling() {
  if (progressTimer !== null) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function initStepStates(task: TaskItem) {
  const steps = task.should_generate_test
    ? [...testCaseSteps, ...drgGroupingSteps]
    : [...drgGroupingSteps]

  const states: Record<string, { lines: string[] }> = {}
  for (const step of steps) {
    states[step] = { lines: [] }
  }
  stepStates.value = states
}

async function pollProgress(taskId: string) {
  if (pollingFlag) return
  pollingFlag = true

  try {
    const task = taskList.value.find((t) => t.task_id === taskId)
    if (!task) return

    const steps = task.should_generate_test
      ? [...testCaseSteps, ...drgGroupingSteps]
      : [...drgGroupingSteps]

    let runningIdx = -1
    for (let i = steps.length - 1; i >= 0; i--) {
      const step = steps[i]
      if (step === undefined) continue
      const lines = stepStates.value[step]?.lines
      if (lines && lines.length > 0) {
        runningIdx = i
        break
      }
    }

    const stepsToPoll: TaskStep[] = []
    if (runningIdx === -1) {
      const first = steps[0]
      if (first !== undefined) stepsToPoll.push(first)
    } else {
      const running = steps[runningIdx]
      if (running !== undefined) stepsToPoll.push(running)
      const next = steps[runningIdx + 1]
      if (next !== undefined) stepsToPoll.push(next)
    }

    for (const step of stepsToPoll) {
      try {
        const { task_progress, is_completed } = await getTaskProgress(taskId, step)
        stepStates.value[step] = { lines: task_progress.step_log_lines }

        if (is_completed) {
          stopProgressPolling()
          await fetchTaskList()
          viewMode.value = 'result'
          loadResultStream(taskId)
          return
        }
      } catch {
        // 单步查询失败静默跳过
      }
    }
  } finally {
    pollingFlag = false
  }
}

function startProgressPolling(taskId: string) {
  stopProgressPolling()
  pollProgress(taskId)
  progressTimer = setInterval(() => pollProgress(taskId), 200)
}

async function loadResult(taskId: string) {
  isLoadingResult.value = true
  resultContent.value = ''
  try {
    const text = await getTaskResult(taskId)
    resultContent.value = text
  } catch (e) {
    resultContent.value = `加载结果失败: ${e}`
  } finally {
    isLoadingResult.value = false
  }
}

async function loadResultStream(taskId: string) {
  isLoadingResult.value = true
  resultContent.value = ''
  try {
    await getTaskResultStream(taskId, (chunk) => {
      resultContent.value += chunk
    })
  } catch (e) {
    resultContent.value = `加载结果失败: ${e}`
  } finally {
    isLoadingResult.value = false
  }
}

function startStatusPolling() {
  statusTimer = setInterval(async () => {
    const ids = [...unfinishedTaskIdSet.value]
    if (ids.length === 0) return

    try {
      const statusList = await getTaskStatus(...ids)
      for (const item of statusList) {
        const task = taskList.value.find((t) => t.task_id === item.task_id)
        if (task) {
          task.task_status = item.task_status as TaskStatus
        }
      }
    } catch {
      // 状态轮询失败静默跳过
    }
  }, 1000)
}

watch(selectedTaskId, (newId) => {
  stopProgressPolling()
  stepStates.value = {}
  resultContent.value = ''
  isLoadingResult.value = false

  if (!newId) {
    viewMode.value = 'progress'
    return
  }

  const task = taskList.value.find((t) => t.task_id === newId)
  if (!task) return

  if (terminalTaskStatusSet.has(task.task_status)) {
    viewMode.value = 'result'
    loadResult(newId)
  } else {
    viewMode.value = 'progress'
    initStepStates(task)
    startProgressPolling(newId)
  }
})

const openNewTask = () => {
  selectedTaskId.value = null
}

const selectTask = (taskId: string) => {
  selectedTaskId.value = taskId
}

const switchAgent = (type: AgentType) => {
  if (agentType.value === type) return
  agentType.value = type
  selectedTaskId.value = null
  taskInput.value = ''
  fileList.value = []
  fetchTaskList()
}

const removeFile = (index: number) => {
  fileList.value.splice(index, 1)
}

const handleFileUpload = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (file.name.endsWith('.pdf')) {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    let text = ''
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const content = await page.getTextContent()
      const pageText = content.items.map((item: any) => item.str).join(' ')
      text += pageText + '\n'
    }
    fileList.value.push({ name: file.name, content: text.trim() })
  } else {
    const text = await file.text()
    fileList.value.push({ name: file.name, content: text })
  }

  input.value = ''
}

const submitNewTask = async () => {
  const input = taskInput.value.trim()
  const fileContents = fileList.value.map((f) => f.content).join('\n')
  const parts: string[] = []
  if (input) parts.push(input)
  if (fileContents) parts.push(fileContents)
  const userInput = parts.join('\n')
  if (!userInput) return

  try {
    const taskId = await createTask(userInput, agentType.value === 'test')
    await fetchTaskList()
    selectedTaskId.value = taskId
    taskInput.value = ''
    fileList.value = []
  } catch (e) {
    console.error('创建任务失败:', e)
  }
}

onMounted(() => {
  fetchTaskList()
  startStatusPolling()
})

onUnmounted(() => {
  stopProgressPolling()
  if (statusTimer !== null) {
    clearInterval(statusTimer)
    statusTimer = null
  }
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;
.drg-agent-layout {
  height: calc(100vh - $control-bar-height);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  color: #1e293b;
  overflow: hidden;
}

.task-sidebar {
  padding: 16px;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 127, 212, 0.12);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
  min-height: 0;
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
  flex: 1;
  min-height: 0;
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
  min-height: 0;
  overflow-y: auto;
}

.new-task-view {
  min-height: 100%;
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

.agent-tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 20px;
}

.agent-tab {
  padding: 8px 24px;
  border: 1px solid rgba(0, 127, 212, 0.2);
  background: #ffffff;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;

  &:first-child {
    border-radius: 8px 0 0 8px;
  }

  &:last-child {
    border-radius: 0 8px 8px 0;
  }

  &:hover {
    background: rgba(0, 127, 212, 0.06);
  }

  &.active {
    background: #007fd4;
    color: #ffffff;
    border-color: #007fd4;
  }
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
  flex-direction: column;
  gap: 10px;
}

.file-upload-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px dashed rgba(0, 127, 212, 0.35);
  border-radius: 8px;
  background: #ffffff;
  color: #007fd4;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 6px;
  position: relative;

  &:hover {
    background: rgba(0, 127, 212, 0.06);
    border-color: rgba(0, 127, 212, 0.55);
  }
}

.file-input-hidden {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.task-input-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.file-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.file-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  border: 1px solid rgba(0, 127, 212, 0.22);
  border-radius: 6px;
  background: rgba(0, 127, 212, 0.05);
  font-size: 13px;
  color: #1e293b;
}

.file-card-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-card-remove {
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;

  &:hover {
    color: #dc2626;
  }
}

.file-card-remove-icon {
  width: 18px;
  height: 18px;
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
  min-height: calc(100vh - $control-bar-height);
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

.task-flow-panels {
  width: min(960px, 100%);
  display: flex;
  flex-direction: column;
  gap: 10px;
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

.result-panel {
  width: 100%;
  min-height: 200px;
  padding: 20px 24px;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  font-size: 14px;
  line-height: 1.8;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 127, 212, 0.35) transparent;
}

.result-panel::-webkit-scrollbar {
  width: 6px;
}

.result-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 127, 212, 0.35);
  border-radius: 999px;
}

.result-panel::-webkit-scrollbar-track {
  background: transparent;
}

.result-loading,
.result-empty {
  color: #64748b;
  font-size: 14px;
}

.result-markdown {
  :deep(h1) {
    margin: 16px 0 8px;
    font-size: 20px;
    color: #0f172a;
  }

  :deep(h2) {
    margin: 14px 0 6px;
    font-size: 17px;
    color: #0f172a;
  }

  :deep(h3) {
    margin: 12px 0 4px;
    font-size: 15px;
    color: #1e293b;
  }

  :deep(p) {
    margin: 4px 0;
    line-height: 1.8;
  }

  :deep(strong) {
    font-weight: 700;
    color: #0f172a;
  }

  :deep(ul),
  :deep(ol) {
    margin: 4px 0;
    padding-left: 20px;
  }

  :deep(li) {
    margin: 2px 0;
  }
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

  .submit-button {
    width: 100%;
  }

  .agent-title {
    font-size: 40px;
  }
}
</style>
