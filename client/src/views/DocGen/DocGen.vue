<template>
  <div class="docgen-layout">
    <aside class="run-sidebar">
      <button class="new-doc-button" type="button" @click="openNewDoc">
        <SvgIcon type="mdi" :path="mdiPlus" class="button-icon" />
        <span>新建任务</span>
      </button>

      <div class="run-list">
        <button
          v-for="run in runHistory"
          :key="run.run_id"
          class="run-card"
          :class="{ active: selectedRunId === run.run_id }"
          type="button"
          @click="selectRun(run.run_id)"
        >
          <span class="run-card-main">
            <span class="run-name">{{ run.doc_type || '文档生成任务' }}</span>
            <span class="run-time">{{ formatTime(run.created_at || run.updated_at) }}</span>
          </span>
          <SvgIcon
            type="mdi"
            :path="runStatusIcon(run.status)"
            class="run-status-icon"
            :class="`status-${run.status}`"
            :title="runStatusLabelMap[run.status] || run.status"
          />
        </button>
        <div v-if="runHistory.length === 0" class="run-empty">暂无任务</div>
      </div>
    </aside>

    <main class="docgen-main">
      <section v-if="!selectedRunId" class="new-doc-view">
        <div class="agent-title-area">
          <h1 class="agent-title">文档生成智能体</h1>
        </div>

        <div class="doc-composer">
          <textarea
            v-model="promptInput"
            class="prompt-input"
            rows="5"
            placeholder="补充生成重点，例如：突出接口定义、模块职责、测试边界和部署视图"
          ></textarea>

          <div class="composer-actions">
            <input
              ref="sourceInputRef"
              class="file-input"
              type="file"
              accept=".md,.txt,text/markdown,text/plain"
              @change="onSourceFileChange"
            />
            <button
              class="composer-tool-button"
              type="button"
              :title="sourceFile ? sourceFile.name : '添加文件'"
              @click="sourceInputRef?.click()"
            >
              <SvgIcon type="mdi" :path="mdiFilePlusOutline" class="button-icon" />
            </button>
            <button
              v-if="sourceFile"
              class="icon-button"
              type="button"
              aria-label="移除文件"
              @click="clearSourceFile"
            >
              <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
            </button>

            <label class="doc-type-control" for="doc-type">
              <SvgIcon type="mdi" :path="mdiFormatListBulletedType" class="button-icon" />
              <select id="doc-type" v-model="selectedDocType" class="doc-type-select">
                <option v-for="dt in docTypes" :key="dt" :value="dt">{{ dt }}</option>
              </select>
            </label>

            <button
              class="submit-button"
              type="button"
              :disabled="isSubmitting"
              @click="submitGeneration"
            >
              <SvgIcon type="mdi" :path="isSubmitting ? mdiProgressClock : mdiSend" class="button-icon" />
            </button>
          </div>

          <div v-if="sourceFile" class="composer-file-hint">
            已添加：{{ sourceFile.name }}
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>
      </section>

      <section v-else class="run-detail-view">
        <header class="run-detail-header">
          <div class="run-title-block">
            <div class="run-detail-label">当前任务</div>
            <h1 class="run-detail-title">{{ selectedRun?.doc_type || '文档生成任务' }}</h1>
            <div class="run-detail-meta">{{ selectedRunId }}</div>
          </div>
          <div class="header-actions">
            <button class="action-btn" type="button" @click="refreshSelectedRun">
              <SvgIcon type="mdi" :path="mdiRefresh" class="button-icon" />
              刷新
            </button>
            <button
              class="action-btn action-preview"
              type="button"
              :disabled="!selectedRun"
              @click="previewDrawerOpen = true"
            >
              <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
              预览
            </button>
            <button
              v-if="isSelectedRunActive"
              class="action-btn action-interrupt"
              type="button"
              @click="handleInterrupt"
            >
              中断
            </button>
            <button
              v-if="isSelectedRunActive"
              class="action-btn action-terminate"
              type="button"
              @click="handleTerminate"
            >
              终止
            </button>
            <button
              v-if="selectedRun?.status === 'completed'"
              class="action-btn action-download"
              type="button"
              @click="handleDownload('markdown')"
            >
              <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="button-icon" />
              Markdown
            </button>
            <button
              v-if="selectedRun?.status === 'completed'"
              class="action-btn action-download"
              type="button"
              @click="handleDownload('pdf')"
            >
              <SvgIcon type="mdi" :path="mdiFilePdfBox" class="button-icon" />
              PDF
            </button>
            <span
              v-if="selectedRun"
              class="run-detail-status"
              :class="`status-${selectedRun.status}`"
            >
              {{ runStatusLabelMap[selectedRun.status] || selectedRun.status }}
            </span>
          </div>
        </header>

        <div v-if="selectedRun?.error" class="error-message">{{ selectedRun.error }}</div>

        <section v-if="selectedRun" class="process-stream">
          <header class="process-stream-header">
            <div>
              <span>智能体过程</span>
              <h2>思考、工具调用和中间结果</h2>
            </div>
            <button class="action-btn action-preview" type="button" @click="previewDrawerOpen = true">
              <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
              结果预览
            </button>
          </header>

          <div v-if="processEvents.length" class="process-event-list">
            <article
              v-for="(evt, idx) in processEvents"
              :key="`${evt.id}-${idx}`"
              class="process-event-card"
              :class="`process-event-${processEventKind(evt)}`"
            >
              <div class="process-event-meta">
                <span class="process-event-badge">{{ processEventKindLabel(evt) }}</span>
                <span>{{ eventTypeLabelMap[evt.type] || evt.type }}</span>
                <time>{{ formatTime(evt.time) }}</time>
                <span v-if="evt.turn" class="process-event-turn">Turn {{ evt.turn }}</span>
              </div>
              <h3>{{ processEventTitle(evt) }}</h3>
              <div v-if="evt.tools" class="event-tools">{{ evt.tools.join(', ') }}</div>
              <pre v-if="processEventBody(evt)" class="process-event-body">{{ processEventBody(evt) }}</pre>
            </article>
          </div>
          <div v-else class="result-empty">暂无智能体过程事件</div>
        </section>

        <div v-if="selectedRun" class="phase-panels">
          <DropDownMenu
            v-for="phase in phaseGroups"
            :key="phase.key"
            :title="`${phase.label} (${phase.events.length})`"
            panel-type="menu"
            :status="phase.status"
            :default-open="phase.status === 'running' || phase.key === 'run'"
          >
            <div class="phase-event-list">
              <div
                v-for="(evt, idx) in phase.events"
                :key="`${evt.id}-${idx}`"
                class="event-row"
                :class="{ 'event-row-error': evt.type === 'error' }"
              >
                <div class="event-head">
                  <span class="event-type">{{ eventTypeLabelMap[evt.type] || evt.type }}</span>
                  <span class="event-time">{{ formatTime(evt.time) }}</span>
                  <span v-if="evt.title || eventSectionTitle(evt)" class="event-title">
                    {{ evt.title || eventSectionTitle(evt) }}
                  </span>
                  <span v-if="evt.name" class="event-tool-name">{{ evt.name }}</span>
                </div>
                <div v-if="evt.tools" class="event-tools">{{ evt.tools.join(', ') }}</div>
                <div v-if="evt.message" class="event-text">{{ evt.message }}</div>
                <div v-if="evt.error" class="event-error-text">{{ evt.error }}</div>
                <pre v-if="eventPreview(evt)" class="event-preview">{{ eventPreview(evt) }}</pre>
              </div>
            </div>
          </DropDownMenu>
        </div>

        <div v-if="isSelectedRunActive" class="bottom-operation-bar">
          <div class="bottom-operation-card">
            <textarea
              v-model="hintInput"
              class="hint-input"
              rows="2"
              placeholder="继续补充提示词，智能体会在下一轮生成中参考"
            ></textarea>
            <div class="bottom-operation-actions">
              <input
                ref="hintInputRef"
                class="file-input"
                type="file"
                accept=".md,.txt,text/markdown,text/plain"
                @change="onHintFileChange"
              />
              <button class="composer-tool-button" type="button" @click="hintInputRef?.click()">
                <SvgIcon type="mdi" :path="mdiFilePlusOutline" class="button-icon" />
                <span>{{ hintFile ? hintFile.name : '添加文件' }}</span>
              </button>
              <button
                v-if="hintFile"
                class="icon-button"
                type="button"
                aria-label="移除参考文件"
                @click="clearHintFile"
              >
                <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
              </button>
              <button
                class="action-btn action-primary"
                type="button"
                :disabled="isAppendingHint"
                @click="handleAppendHint"
              >
                <SvgIcon type="mdi" :path="mdiMessageTextOutline" class="button-icon" />
                {{ isAppendingHint ? '提交中' : '追加提示' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>

    <button
      v-if="selectedRun"
      class="preview-tab"
      type="button"
      :aria-expanded="previewDrawerOpen"
      @click="previewDrawerOpen = true"
    >
      <SvgIcon type="mdi" :path="mdiChevronRight" class="preview-tab-icon" />
      <span>结果预览</span>
    </button>

    <div
      v-if="previewDrawerOpen"
      class="preview-backdrop"
      role="presentation"
      @click="previewDrawerOpen = false"
    ></div>

    <aside
      class="result-drawer"
      :class="{ 'result-drawer-open': previewDrawerOpen }"
      aria-label="结果展示和预览"
    >
      <header class="drawer-header">
        <div>
          <div class="drawer-kicker">结果展示</div>
          <h2 class="drawer-title">{{ selectedRun?.doc_type || '文档生成任务' }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭预览" @click="previewDrawerOpen = false">
          <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
        </button>
      </header>

      <div v-if="selectedRun" class="drawer-body">
        <div class="preview-status-card">
          <span class="preview-status-label">任务状态</span>
          <span class="preview-status-value" :class="`status-${selectedRun.status}`">
            {{ runStatusLabelMap[selectedRun.status] || selectedRun.status }}
          </span>
          <span class="preview-run-id">{{ selectedRun.run_id }}</span>
        </div>

        <div class="preview-actions">
          <button
            class="action-btn action-download"
            type="button"
            :disabled="selectedRun.status !== 'completed'"
            @click="handleDownload('markdown')"
          >
            <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="button-icon" />
            Markdown
          </button>
          <button
            class="action-btn action-download"
            type="button"
            :disabled="selectedRun.status !== 'completed'"
            @click="handleDownload('pdf')"
          >
            <SvgIcon type="mdi" :path="mdiFilePdfBox" class="button-icon" />
            PDF
          </button>
        </div>

        <div class="preview-file-list">
          <div class="preview-file-row">
            <span>Markdown</span>
            <strong>{{ basename(selectedRun.output_path) || '生成完成后可用' }}</strong>
          </div>
          <div class="preview-file-row">
            <span>PDF</span>
            <strong>{{ basename(selectedRun.pdf_path) || '生成完成后可用' }}</strong>
          </div>
        </div>

        <section class="preview-section">
          <h3>最近输出</h3>
          <div v-if="previewEvents.length" class="preview-event-list">
            <article
              v-for="evt in previewEvents"
              :key="evt.id"
              class="preview-event-card"
            >
              <div class="preview-event-head">
                <span>{{ eventTypeLabelMap[evt.type] || evt.type }}</span>
                <time>{{ formatTime(evt.time) }}</time>
              </div>
              <p v-if="evt.title || eventSectionTitle(evt)">
                {{ evt.title || eventSectionTitle(evt) }}
              </p>
              <pre v-if="eventPreview(evt)">{{ eventPreview(evt) }}</pre>
            </article>
          </div>
          <div v-else class="result-empty">暂无可预览内容</div>
        </section>
      </div>
    </aside>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiChevronRight,
  mdiClockOutline,
  mdiClose,
  mdiFileDocumentOutline,
  mdiFileEyeOutline,
  mdiFilePdfBox,
  mdiFilePlusOutline,
  mdiFormatListBulletedType,
  mdiMessageTextOutline,
  mdiPlus,
  mdiProgressClock,
  mdiRefresh,
  mdiSend,
} from '@mdi/js'
import DropDownMenu from '@/components/DropDownMenu.vue'
import type { DropDownStatus } from '@/components/DropDownMenu.vue'
import {
  activeRunStatusSet,
  appendRunHint,
  downloadMarkdown,
  downloadPdf,
  eventTypeLabelMap,
  getDocTypes,
  getRunTrace,
  interruptRun,
  phaseLabelMap,
  runStatusLabelMap,
  startGeneration,
  terminalRunStatusSet,
  terminateRun,
  type AgentTraceEvent,
  type DocType,
  type RunTrace,
} from './dogen_utils'

interface PhaseGroup {
  key: string
  label: string
  status: DropDownStatus
  events: AgentTraceEvent[]
}

type ProcessEventKind = 'thought' | 'tool' | 'result' | 'status' | 'error'

const docTypes = ref<DocType[]>(['需求规格说明书', '架构设计文档', '测试文档'])
const selectedDocType = ref<DocType>('需求规格说明书')
const promptInput = ref('')
const sourceFile = ref<File | null>(null)
const hintInput = ref('')
const hintFile = ref<File | null>(null)
const isSubmitting = ref(false)
const isAppendingHint = ref(false)
const errorMessage = ref('')
const selectedRunId = ref<string | null>(null)
const selectedRun = ref<RunTrace | null>(null)
const runHistory = ref<RunTrace[]>([])
const sourceInputRef = ref<HTMLInputElement | null>(null)
const hintInputRef = ref<HTMLInputElement | null>(null)
const previewDrawerOpen = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const LOCAL_KEY = 'docgen_run_ids'
const phaseOrder = ['run', 'read_files', 'split_sections', 'generate_sections', 'validate', 'stitch', 'save', 'convert_pdf']

const isSelectedRunActive = computed(() => {
  return selectedRun.value ? activeRunStatusSet.has(selectedRun.value.status) : false
})

const loadLocalRunIds = (): string[] => {
  try {
    const value = JSON.parse(localStorage.getItem(LOCAL_KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

const saveLocalRunId = (id: string) => {
  const ids = loadLocalRunIds().filter((item) => item !== id)
  ids.unshift(id)
  localStorage.setItem(LOCAL_KEY, JSON.stringify(ids.slice(0, 40)))
}

const removeMissingRunId = (id: string) => {
  const ids = loadLocalRunIds().filter((item) => item !== id)
  localStorage.setItem(LOCAL_KEY, JSON.stringify(ids))
}

const updateRunInHistory = (trace: RunTrace) => {
  const index = runHistory.value.findIndex((run) => run.run_id === trace.run_id)
  if (index >= 0) {
    runHistory.value[index] = trace
  } else {
    runHistory.value.unshift(trace)
  }
}

const restoreRunHistory = async () => {
  const ids = loadLocalRunIds()
  const traces: RunTrace[] = []
  for (const id of ids) {
    try {
      traces.push(await getRunTrace(id))
    } catch {
      removeMissingRunId(id)
    }
  }
  runHistory.value = traces
  const active = traces.find((run) => activeRunStatusSet.has(run.status))
  if (active) {
    await selectRun(active.run_id)
  }
}

const stopPolling = () => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const pollRun = async (runId: string) => {
  try {
    const trace = await getRunTrace(runId)
    selectedRun.value = trace
    updateRunInHistory(trace)
    if (terminalRunStatusSet.has(trace.status)) stopPolling()
  } catch (error) {
    errorMessage.value = `获取任务状态失败：${error}`
    stopPolling()
  }
}

const startPolling = (runId: string) => {
  stopPolling()
  void pollRun(runId)
  pollTimer = setInterval(() => void pollRun(runId), 2500)
}

const openNewDoc = () => {
  selectedRunId.value = null
  selectedRun.value = null
  errorMessage.value = ''
  hintInput.value = ''
  previewDrawerOpen.value = false
  clearHintFile()
  stopPolling()
}

const submitGeneration = async () => {
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    const response = await startGeneration(promptInput.value.trim(), selectedDocType.value, sourceFile.value)
    saveLocalRunId(response.run_id)
    const stub: RunTrace = {
      run_id: response.run_id,
      status: 'running',
      doc_type: response.doc_type,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      output_path: null,
      pdf_path: null,
      error: null,
      interrupted: false,
      terminated: false,
      events: [],
    }
    selectedRunId.value = response.run_id
    selectedRun.value = stub
    updateRunInHistory(stub)
    promptInput.value = ''
    clearSourceFile()
    startPolling(response.run_id)
  } catch (error) {
    errorMessage.value = `启动失败：${error}`
  } finally {
    isSubmitting.value = false
  }
}

const selectRun = async (runId: string) => {
  selectedRunId.value = runId
  errorMessage.value = ''
  stopPolling()
  try {
    const trace = await getRunTrace(runId)
    selectedRun.value = trace
    updateRunInHistory(trace)
    if (activeRunStatusSet.has(trace.status)) startPolling(runId)
  } catch (error) {
    selectedRun.value = null
    errorMessage.value = `读取任务失败：${error}`
  }
}

const refreshSelectedRun = async () => {
  if (!selectedRunId.value) return
  await pollRun(selectedRunId.value)
}

const handleInterrupt = async () => {
  if (!selectedRunId.value) return
  await interruptRun(selectedRunId.value)
  await refreshSelectedRun()
}

const handleTerminate = async () => {
  if (!selectedRunId.value) return
  await terminateRun(selectedRunId.value)
  await refreshSelectedRun()
}

const handleAppendHint = async () => {
  if (!selectedRunId.value) return
  const trimmed = hintInput.value.trim()
  if (!trimmed && !hintFile.value) return
  isAppendingHint.value = true
  errorMessage.value = ''
  try {
    await appendRunHint(
      selectedRunId.value,
      trimmed || '请参考追加文件内容调整后续生成。',
      hintFile.value,
    )
    hintInput.value = ''
    clearHintFile()
    await refreshSelectedRun()
  } catch (error) {
    errorMessage.value = `追加失败：${error}`
  } finally {
    isAppendingHint.value = false
  }
}

const handleDownload = async (kind: 'markdown' | 'pdf') => {
  if (!selectedRunId.value || !selectedRun.value) return
  const extension = kind === 'pdf' ? 'pdf' : 'md'
  const fileName = fileNameFromRun(selectedRun.value, extension)
  if (kind === 'pdf') {
    await downloadPdf(selectedRunId.value, fileName)
  } else {
    await downloadMarkdown(selectedRunId.value, fileName)
  }
}

const onSourceFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  sourceFile.value = input.files?.[0] || null
}

const onHintFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  hintFile.value = input.files?.[0] || null
}

const clearSourceFile = () => {
  sourceFile.value = null
  if (sourceInputRef.value) sourceInputRef.value.value = ''
}

const clearHintFile = () => {
  hintFile.value = null
  if (hintInputRef.value) hintInputRef.value.value = ''
}

const normalizedPhase = (phase: string) => {
  if (phase.startsWith('generate_section:')) return 'generate_sections'
  return phase || 'run'
}

const eventSectionTitle = (event: AgentTraceEvent) => {
  return event.phase?.startsWith('generate_section:') ? event.phase.slice('generate_section:'.length) : ''
}

const phaseStatusFromEvents = (events: AgentTraceEvent[]): DropDownStatus => {
  if (events.some((event) => event.type === 'error')) return 'failed'
  if (events.some((event) => event.type === 'phase_completed')) return 'success'
  if (events.length > 0) return 'running'
  return 'pending'
}

const phaseGroups = computed<PhaseGroup[]>(() => {
  if (!selectedRun.value) return []
  const groups = new Map<string, PhaseGroup>()
  for (const event of selectedRun.value.events) {
    const key = normalizedPhase(event.phase)
    const existing = groups.get(key)
    if (existing) {
      existing.events.push(event)
    } else {
      groups.set(key, {
        key,
        label: phaseLabelMap[key] || key,
        status: 'pending',
        events: [event],
      })
    }
  }
  return [...groups.values()]
    .map((group) => ({ ...group, status: phaseStatusFromEvents(group.events) }))
    .sort((a, b) => {
      const ai = phaseOrder.indexOf(a.key)
      const bi = phaseOrder.indexOf(b.key)
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi)
    })
})

const runStatusIcon = (status: string) => {
  if (status === 'completed') return mdiCheckCircleOutline
  if (status === 'failed' || status === 'interrupted' || status === 'terminated') return mdiAlertCircleOutline
  if (status === 'running' || status.endsWith('_requested')) return mdiProgressClock
  return mdiClockOutline
}

const formatTime = (iso?: string) => {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  const hour = `${date.getHours()}`.padStart(2, '0')
  const minute = `${date.getMinutes()}`.padStart(2, '0')
  return `${month}/${day} ${hour}:${minute}`
}

const truncateText = (value: unknown, max = 420) => {
  if (value === undefined || value === null) return ''
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return text.length > max ? `${text.slice(0, max)}...` : text
}

const eventPreview = (event: AgentTraceEvent) => {
  return truncateText(event.result || event.content || event.arguments, 600)
}

const processEventTypes = new Set([
  'reasoning',
  'tool_calls_planned',
  'tool_call',
  'tool_result',
  'assistant_message',
  'section_completed',
  'section_saved_in_memory',
  'document_stitched',
  'table_repaired',
  'phase_completed',
  'hint_appended',
  'error',
])

const processEvents = computed(() => {
  if (!selectedRun.value) return []
  return selectedRun.value.events
    .filter((event) => {
      return (
        processEventTypes.has(event.type)
        || event.type.includes('tool')
        || event.type.includes('section')
        || Boolean(event.result || event.content || event.message || event.error)
      )
    })
    .slice(-80)
})

const processEventKind = (event: AgentTraceEvent): ProcessEventKind => {
  if (event.type === 'error' || event.error) return 'error'
  if (event.type === 'reasoning') return 'thought'
  if (event.type.includes('tool')) return 'tool'
  if (
    event.type === 'assistant_message'
    || event.type.includes('section')
    || event.type === 'document_stitched'
    || event.type === 'table_repaired'
  ) {
    return 'result'
  }
  return 'status'
}

const processEventKindLabel = (event: AgentTraceEvent) => {
  const kind = processEventKind(event)
  if (kind === 'thought') return '思考过程'
  if (kind === 'tool') return '工具调用'
  if (kind === 'result') return '中间结果'
  if (kind === 'error') return '异常'
  return '状态'
}

const processEventTitle = (event: AgentTraceEvent) => {
  const sectionTitle = event.title || eventSectionTitle(event)
  if (event.type === 'tool_calls_planned') {
    return `计划调用工具：${event.tools?.join(', ') || '待确认'}`
  }
  if (event.type === 'tool_call') return `调用工具：${event.name || 'tool'}`
  if (event.type === 'tool_result') return `工具返回：${event.name || 'tool'}`
  if (event.type === 'assistant_message') return sectionTitle || '模型中间输出'
  if (event.type === 'section_completed') return sectionTitle ? `章节完成：${sectionTitle}` : '章节完成'
  if (event.type === 'section_saved_in_memory') return sectionTitle ? `章节暂存：${sectionTitle}` : '章节暂存'
  if (event.type === 'phase_completed') {
    const phase = normalizedPhase(event.phase)
    return `阶段完成：${phaseLabelMap[phase] || phase}`
  }
  if (event.type === 'document_stitched') return '文档拼接完成'
  if (event.type === 'table_repaired') return '表格已规范化'
  if (event.type === 'hint_appended') return '已追加用户提示'
  return sectionTitle || eventTypeLabelMap[event.type] || event.type
}

const processEventBody = (event: AgentTraceEvent) => {
  return truncateText(
    event.error
      || event.message
      || event.result
      || event.content
      || event.arguments
      || event.sections
      || event.output_path
      || event.pdf_path,
    900,
  )
}

const previewEvents = computed(() => {
  if (!selectedRun.value) return []
  return selectedRun.value.events
    .filter((event) => {
      return Boolean(eventPreview(event) || event.title || eventSectionTitle(event) || event.message || event.error)
    })
    .slice(-8)
    .reverse()
})

const basename = (path?: string | null) => {
  if (!path) return ''
  return path.split(/[\\/]/).pop() || ''
}

const fileNameFromRun = (run: RunTrace, extension: 'md' | 'pdf') => {
  const fromPath = basename(extension === 'pdf' ? run.pdf_path : run.output_path)
  if (fromPath) return fromPath
  const stamp = (run.created_at || new Date().toISOString()).replace(/[:T-]/g, '').slice(0, 12)
  return `${run.doc_type || '文档'}_${stamp}.${extension}`
}

onMounted(async () => {
  try {
    const types = await getDocTypes()
    if (types.length > 0) docTypes.value = types
  } catch {
    docTypes.value = ['需求规格说明书', '架构设计文档', '测试文档']
  }
  await restoreRunHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.docgen-layout {
  min-height: calc(100vh - $control-bar-height);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  color: #1e293b;
  position: relative;
}

.run-sidebar {
  padding: 16px;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 127, 212, 0.12);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.new-doc-button,
.submit-button {
  min-height: 44px;
  border: none;
  border-radius: 8px;
  background: #007fd4;
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.submit-button:disabled,
.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.button-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.run-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.run-card {
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

.run-card:hover {
  border-color: rgba(0, 127, 212, 0.28);
  background: #f8fbff;
}

.run-card.active {
  border-color: rgba(0, 127, 212, 0.56);
  background: #eef8ff;
}

.run-card-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.run-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 700;
}

.run-time,
.run-empty {
  color: #64748b;
  font-size: 12px;
}

.run-empty {
  padding: 8px 4px;
}

.run-status-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: currentColor;
}

.status-running,
.status-interrupt_requested,
.status-terminate_requested {
  color: #007fd4;
}

.status-completed {
  color: #16a34a;
}

.status-failed {
  color: #dc2626;
}

.status-interrupted,
.status-terminated {
  color: #f59e0b;
}

.docgen-main {
  min-height: calc(100vh - $control-bar-height);
  padding: 28px 32px;
  box-sizing: border-box;
  overflow-y: auto;
}

.new-doc-view {
  min-height: calc(100vh - $control-bar-height - 56px);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.agent-title-area {
  width: min(920px, 100%);
  margin: 0 auto 24px;
}

.agent-title {
  margin: 0;
  color: #007fd4;
  font-size: 48px;
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: 0;
  text-align: center;
}

.doc-composer,
.bottom-operation-card {
  width: min(920px, 100%);
  margin: 0 auto;
  padding: 12px;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  gap: 10px;
}

.doc-composer {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.bottom-operation-card {
  box-sizing: border-box;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.composer-file-hint {
  max-width: 100%;
  align-self: flex-end;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-type-select,
.prompt-input,
.hint-input {
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  font-family: inherit;
  font-size: 14px;
  outline: none;
}

.doc-type-select {
  width: 168px;
  height: 38px;
  min-width: 0;
  padding: 0 28px 0 8px;
  border: none;
  background: transparent;
  color: #334155;
  font-weight: 700;
  cursor: pointer;
}

.prompt-input,
.hint-input {
  resize: vertical;
  padding: 10px 12px;
  line-height: 20px;
}

.prompt-input {
  min-height: 116px;
  resize: vertical;
}

.hint-input {
  min-width: 220px;
  flex: 1;
}

.bottom-operation-card .hint-input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.file-input {
  display: none;
}

.file-button,
.action-btn,
.icon-button,
.composer-tool-button,
.doc-type-control {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.composer-tool-button,
.doc-type-control {
  height: 38px;
  background: #f8fafc;
}

.doc-type-control {
  padding-right: 4px;
  cursor: pointer;
}

.file-button {
  min-width: 180px;
  max-width: 100%;
  overflow: hidden;
}

.icon-button {
  width: 38px;
  padding: 0;
}

.action-primary,
.action-download,
.action-preview {
  color: #007fd4;
  border-color: rgba(0, 127, 212, 0.32);
}

.action-interrupt {
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.32);
}

.action-terminate {
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.32);
}

.run-detail-view {
  width: min(980px, 100%);
  margin: 0 auto;
  padding-bottom: 8px;
}

.run-detail-header {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.run-title-block {
  min-width: 0;
}

.run-detail-label {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 13px;
}

.run-detail-title {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
  line-height: 1.25;
}

.run-detail-meta {
  margin-top: 5px;
  color: #94a3b8;
  font-family: Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.run-detail-status {
  min-height: 38px;
  padding: 0 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.error-message {
  width: min(920px, 100%);
  margin: 10px auto 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

.process-stream {
  width: min(920px, 100%);
  margin: 14px auto;
  padding: 14px;
  box-sizing: border-box;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.process-stream-header {
  margin-bottom: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.process-stream-header span {
  color: #007fd4;
  font-size: 13px;
  font-weight: 800;
}

.process-stream-header h2 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 18px;
  line-height: 1.3;
}

.process-event-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.process-event-card {
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-left-width: 4px;
  border-radius: 8px;
  background: #f8fafc;
}

.process-event-thought {
  border-left-color: #007fd4;
}

.process-event-tool {
  border-left-color: #7c3aed;
}

.process-event-result {
  border-left-color: #16a34a;
}

.process-event-status {
  border-left-color: #64748b;
}

.process-event-error {
  border-left-color: #dc2626;
  background: #fef2f2;
}

.process-event-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.process-event-badge {
  padding: 3px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #007fd4;
}

.process-event-tool .process-event-badge {
  background: #ede9fe;
  color: #7c3aed;
}

.process-event-result .process-event-badge {
  background: #dcfce7;
  color: #15803d;
}

.process-event-error .process-event-badge {
  background: #fee2e2;
  color: #dc2626;
}

.process-event-card h3 {
  margin: 8px 0 0;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.45;
}

.process-event-body {
  max-height: 260px;
  margin: 8px 0 0;
  padding: 10px;
  overflow: auto;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.phase-panels {
  width: min(920px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bottom-operation-bar {
  position: sticky;
  bottom: 0;
  z-index: 8;
  width: min(920px, 100%);
  margin: 18px auto 0;
  padding: 18px 0 0;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0), #f8fafc 32%);
}

.bottom-operation-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.phase-event-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-row {
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
}

.event-row-error {
  background: #fef2f2;
}

.event-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.event-type {
  color: #007fd4;
  font-size: 13px;
  font-weight: 800;
}

.event-time {
  color: #94a3b8;
  font-size: 12px;
}

.event-title,
.event-tool-name {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.event-tools {
  margin-top: 6px;
  color: #475569;
  font-family: Consolas, monospace;
  font-size: 12px;
}

.event-text,
.event-error-text {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.event-error-text {
  color: #dc2626;
  font-weight: 700;
}

.event-preview {
  margin: 8px 0 0;
  max-height: 180px;
  padding: 8px;
  overflow: auto;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.preview-tab {
  position: fixed;
  right: 0;
  top: 50%;
  z-index: 25;
  min-height: 112px;
  padding: 12px 8px;
  border: 1px solid rgba(0, 127, 212, 0.2);
  border-right: none;
  border-radius: 8px 0 0 8px;
  background: #ffffff;
  color: #007fd4;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.14);
  cursor: pointer;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transform: translateY(-50%);
}

.preview-tab span {
  writing-mode: vertical-rl;
  letter-spacing: 0;
  font-size: 13px;
  font-weight: 800;
}

.preview-tab-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.preview-backdrop {
  position: fixed;
  inset: $control-bar-height 0 0 0;
  z-index: 35;
  background: rgba(15, 23, 42, 0.18);
}

.result-drawer {
  position: fixed;
  top: $control-bar-height;
  right: 0;
  bottom: 0;
  z-index: 40;
  width: min(460px, 92vw);
  background: #ffffff;
  border-left: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: -20px 0 40px rgba(15, 23, 42, 0.16);
  transform: translateX(100%);
  transition: transform 0.22s ease;
  display: flex;
  flex-direction: column;
}

.result-drawer-open {
  transform: translateX(0);
}

.drawer-header {
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.drawer-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.drawer-title {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 20px;
  line-height: 1.25;
}

.drawer-body {
  padding: 16px 18px 22px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-status-card {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 6px;
}

.preview-status-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.preview-status-value {
  font-size: 15px;
  font-weight: 800;
}

.preview-run-id {
  color: #94a3b8;
  font-family: Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.preview-actions .action-btn {
  flex: 1;
}

.preview-file-list {
  display: grid;
  gap: 8px;
}

.preview-file-row {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 4px;
}

.preview-file-row span {
  color: #64748b;
  font-size: 12px;
}

.preview-file-row strong {
  color: #1e293b;
  font-size: 13px;
  word-break: break-all;
}

.preview-section h3 {
  margin: 0 0 10px;
  color: #0f172a;
  font-size: 16px;
}

.preview-event-list {
  display: grid;
  gap: 10px;
}

.preview-event-card {
  padding: 10px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.preview-event-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
}

.preview-event-head time {
  color: #94a3b8;
  font-weight: 600;
}

.preview-event-card p {
  margin: 8px 0 0;
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
}

.preview-event-card pre {
  max-height: 220px;
  margin: 8px 0 0;
  padding: 8px;
  overflow: auto;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

@media (max-width: 860px) {
  .docgen-layout {
    grid-template-columns: 1fr;
  }

  .run-sidebar {
    border-right: none;
    border-bottom: 1px solid rgba(0, 127, 212, 0.12);
  }

  .run-list {
    max-height: 220px;
  }

  .docgen-main {
    padding: 22px 18px;
  }

  .agent-title {
    font-size: 36px;
  }

  .run-detail-header,
  .composer-actions,
  .bottom-operation-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .file-button,
  .action-btn,
  .submit-button,
  .composer-tool-button,
  .doc-type-control,
  .doc-type-select {
    width: 100%;
  }

  .composer-file-hint {
    align-self: stretch;
  }
}
</style>
