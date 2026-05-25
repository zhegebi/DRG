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
            <span class="run-name" :title="run.task_title || run.doc_type">{{ displayTaskTitle(run) }}</span>
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
            @keydown="handlePromptKeydown"
          ></textarea>

          <div class="composer-actions">
            <input
              ref="sourceInputRef"
              class="file-input"
              type="file"
              multiple
              accept=".md,.txt,text/markdown,text/plain"
              @change="onSourceFileChange"
            />
            <button
              class="composer-tool-button"
              type="button"
              :title="sourceFiles.length ? sourceFiles.map((file) => file.name).join('、') : '添加文件'"
              @click="sourceInputRef?.click()"
            >
              <SvgIcon type="mdi" :path="mdiFilePlusOutline" class="button-icon" />
            </button>
            <button
              v-if="sourceFiles.length"
              class="icon-button"
              type="button"
              aria-label="移除文件"
              @click="clearSourceFiles"
            >
              <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
            </button>

            <div class="doc-type-dropdown">
              <button
                class="doc-type-control doc-type-trigger"
                type="button"
                :aria-expanded="docTypeMenuOpen"
                :title="selectedDocTypeLabel"
                aria-label="文档类型"
                @click="docTypeMenuOpen = !docTypeMenuOpen"
              >
                <SvgIcon type="mdi" :path="mdiFormatListBulletedType" class="button-icon" />
              </button>
              <div v-if="docTypeMenuOpen" class="doc-type-menu">
                <label
                  v-for="dt in docTypes"
                  :key="dt"
                  class="doc-type-option"
                  :class="{ checked: selectedDocTypes.includes(dt) }"
                >
                  <input v-model="selectedDocTypes" type="checkbox" :value="dt" />
                  <span>{{ dt }}</span>
                </label>
              </div>
            </div>

            <button
              ref="docSubmitButtonRef"
              class="submit-button"
              type="button"
              :disabled="isSubmitting || selectedDocTypes.length === 0"
              @click="submitGeneration"
            >
              <SvgIcon
                type="mdi"
                :path="isSubmitting ? mdiLoading : mdiSend"
                :class="['button-icon', { 'loading-icon': isSubmitting }]"
              />
            </button>
          </div>

          <div v-if="sourceFiles.length" class="composer-file-hint">
            已添加：{{ sourceFiles.map((file) => file.name).join('、') }}
          </div>

          <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        </div>
      </section>

      <section v-else class="run-detail-view">
        <header class="run-detail-header">
          <div class="run-title-block">
            <div class="run-detail-label">当前任务</div>
            <div class="run-title-line">
              <h1 class="run-detail-title">{{ selectedRun ? displayTaskTitle(selectedRun) : '文档生成任务' }}</h1>
              <span
                v-if="statusRun"
                class="run-state-icon"
                :class="`run-state-${statusRun.status}`"
                :title="runStatusLabelMap[statusRun.status] || statusRun.status"
              >
                <SvgIcon type="mdi" :path="headerRunStatusIcon" class="button-icon" />
              </span>
            </div>
            <div class="run-detail-meta">{{ selectedRunId }}</div>
          </div>
          <div class="run-title-side">
            <div class="header-progress-actions">
              <div
                v-if="chapterProgressItems.length"
                class="header-progress-rail"
                :class="{
                  'progress-flowing': headerProgressRatio > 0,
                  'progress-completed': isHeaderProgressCompleted,
                }"
                :style="headerProgressStyle"
                aria-label="章节进度"
              >
                <span
                  v-for="item in chapterProgressItems"
                  :key="item.title"
                  class="header-progress-step"
                  :class="[`chapter-status-${item.status}`, { active: activeChapterTitle === item.title }]"
                  :aria-label="`第 ${item.index} 章：${item.title}`"
                  :title="item.title"
                >
                  <span class="header-progress-dot"></span>
                  <span class="header-progress-label">{{ truncateTitle(item.title, 5) }}</span>
                </span>
              </div>
              <button
                class="icon-button action-preview header-preview-button"
                type="button"
                aria-label="结果预览"
                title="结果预览"
                :disabled="!selectedRun"
                @click="previewDrawerOpen = true"
              >
                <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
              </button>
            </div>
          </div>
        </header>

        <div class="run-detail-scroll">
          <section v-if="selectedRun" class="run-insight-panel">
            <section class="chapter-menu-list">
              <template
                v-for="task in conversationTaskItems"
                :key="task.run.run_id"
              >
                <div class="chapter-process-list">
                  <div v-if="task.messages.length" class="conversation-message-list">
                    <article
                      v-for="message in task.messages"
                      :key="message.key"
                      class="conversation-message"
                    >
                      <div class="conversation-message-meta">
                        <span>{{ message.label }}</span>
                        <time>{{ formatTime(message.time) }}</time>
                      </div>
                      <p>{{ message.content }}</p>
                    </article>
                  </div>

                  <article
                    v-for="group in task.groups"
                    :key="`${task.run.run_id}-${group.key}`"
                    class="chapter-process-card"
                    :class="{
                      active: group.title === task.activeChapterTitle,
                      expanded: isChapterGroupExpanded(task.run.run_id, group),
                    }"
                  >
                    <button
                      class="chapter-process-header"
                      type="button"
                      :aria-expanded="isChapterGroupExpanded(task.run.run_id, group)"
                      @click="toggleChapterGroupExpansion(task.run.run_id, group)"
                    >
                      <div>
                        <span>第 {{ group.index }} 章</span>
                        <h2>{{ group.title }}</h2>
                      </div>
                      <span class="chapter-process-side">
                        <strong
                          class="chapter-process-status"
                          :class="`chapter-process-status-${group.status}`"
                          :title="chapterStatusLabel(group.status)"
                          :aria-label="chapterStatusLabel(group.status)"
                        >
                          <SvgIcon
                            type="mdi"
                            :path="chapterStatusIcon(group.status)"
                            class="chapter-process-status-icon"
                          />
                        </strong>
                        <span class="chapter-event-count">{{ group.events.length }} 条</span>
                        <SvgIcon
                          type="mdi"
                          :path="isChapterGroupExpanded(task.run.run_id, group) ? mdiChevronUp : mdiChevronDown"
                          class="chapter-process-chevron"
                        />
                      </span>
                    </button>
                    <div v-if="isChapterGroupExpanded(task.run.run_id, group)" class="chapter-process-body">
                    <article
                      v-for="finalEvt in chapterFinalEvents(group)"
                      :key="`${task.run.run_id}-${group.key}-final-${finalEvt.id}`"
                      class="chapter-final-result"
                    >
                      <header>
                        <div>
                          <span>章节最终结果</span>
                          <h3>{{ group.title }}</h3>
                        </div>
                        <time>{{ formatTime(finalEvt.time) }}</time>
                      </header>
                      <pre>{{ chapterFinalBody(finalEvt) }}</pre>
                    </article>
                    <div
                      v-if="group.events.length"
                      class="process-event-list unified"
                      @scroll="onProcessEventListScroll($event, task.run.run_id, group)"
                    >
                      <article
                        v-for="eventGroup in visibleProcessEventGroups(task.run.run_id, group)"
                        :key="`${task.run.run_id}-${group.key}-${eventGroup.key}`"
                        class="process-event-card"
                        :class="[
                          `process-event-${eventGroup.kind}`,
                          `process-event-state-${eventGroup.state}`,
                          {
                            'is-open': isProcessEventExpanded(task.run.run_id, group, eventGroup),
                            'stream-active': isStreamingEventGroup(task.run, eventGroup),
                            'process-event-error': eventGroup.kind === 'error',
                          },
                        ]"
                      >
                        <button
                          class="process-event-heading"
                          type="button"
                          :aria-expanded="isProcessEventExpanded(task.run.run_id, group, eventGroup)"
                          @click="toggleProcessEventExpansion(task.run.run_id, group, eventGroup)"
                        >
                          <div class="process-event-title-block">
                            <span
                              class="process-event-kind-label"
                              :class="`process-event-kind-${eventGroup.kind}`"
                            >
                              {{ processEventKindLabelMap[eventGroup.kind] }}
                            </span>
                            <h3>{{ eventGroup.title }}</h3>
                            <p v-if="processEventSummary(eventGroup)" class="process-event-summary">
                              {{ processEventSummary(eventGroup) }}
                            </p>
                          </div>
                          <div class="process-event-meta">
                            <SvgIcon
                              v-if="isStreamingEventGroup(task.run, eventGroup)"
                              type="mdi"
                              :path="mdiLoading"
                              class="process-event-loading loading-icon"
                            />
                            <time>{{ formatTime(lastProcessEvent(eventGroup).time) }}</time>
                            <span v-if="lastProcessEvent(eventGroup).turn" class="process-event-turn">
                              Turn {{ lastProcessEvent(eventGroup).turn }}
                            </span>
                            <span
                              class="process-event-current-status"
                              :class="`process-event-current-${eventGroup.state}`"
                              :title="processEventGroupStatusText(eventGroup)"
                              :aria-label="processEventGroupStatusText(eventGroup)"
                            >
                              <SvgIcon
                                type="mdi"
                                :path="processExecutionStatusIcon(eventGroup.state)"
                                :class="['process-status-icon', { 'loading-icon': eventGroup.state === 'running' }]"
                              />
                            </span>
                            <SvgIcon
                              type="mdi"
                              :path="isProcessEventExpanded(task.run.run_id, group, eventGroup) ? mdiChevronUp : mdiChevronDown"
                              class="process-event-chevron"
                            />
                          </div>
                        </button>
                        <div
                          v-if="isProcessEventExpanded(task.run.run_id, group, eventGroup)
                            && visibleProcessEntries(task.run.run_id, group, eventGroup).length"
                          class="process-event-entry-list"
                          @scroll="onProcessEntryListScroll($event, task.run.run_id, group, eventGroup)"
                        >
                          <div class="process-event-entry-panel">
                            <div
                              v-for="evt in visibleProcessEntries(task.run.run_id, group, eventGroup)"
                              :key="`${eventGroup.key}-${evt.id}`"
                              class="process-event-entry"
                              :class="`process-event-entry-${processEventKind(evt)}`"
                            >
                              <div class="process-event-entry-head">
                                <span class="process-event-entry-title">
                                  <strong>{{ processEventEntryTitle(evt, group) }}</strong>
                                  <span
                                    class="process-event-entry-status"
                                    :class="`process-event-current-${processEventEntryState(evt, eventGroup)}`"
                                    :title="processEventEntryStatusText(evt, eventGroup)"
                                    :aria-label="processEventEntryStatusText(evt, eventGroup)"
                                  >
                                    <SvgIcon
                                      type="mdi"
                                      :path="processExecutionStatusIcon(processEventEntryState(evt, eventGroup))"
                                      :class="[
                                        'process-status-icon',
                                        { 'loading-icon': processEventEntryState(evt, eventGroup) === 'running' },
                                      ]"
                                    />
                                  </span>
                                </span>
                                <time>{{ formatTime(evt.time) }}</time>
                              </div>
                              <pre
                                v-if="eventHasBody(evt)"
                                class="process-event-body"
                                :class="{ streaming: isStreamingEventForRun(task.run, evt), prose: processEventKind(evt) !== 'tool' }"
                              >{{ processEventBody(evt) }}</pre>
                            </div>
                          </div>
                          <button
                            v-if="hasMoreProcessEntries(task.run.run_id, group, eventGroup)"
                            class="process-virtual-footer process-entry-footer"
                            type="button"
                            @click="loadMoreProcessEntries(task.run.run_id, group, eventGroup)"
                          >
                            <SvgIcon
                              v-if="isProcessEntryGroupLoading(task.run.run_id, group, eventGroup)"
                              type="mdi"
                              :path="mdiLoading"
                              class="button-icon loading-icon"
                            />
                            <span>
                              {{ isProcessEntryGroupLoading(task.run.run_id, group, eventGroup)
                                ? '正在加载更多细节'
                                : `继续加载 ${visibleProcessEntryCount(task.run.run_id, group, eventGroup)} / ${eventGroup.events.length}` }}
                            </span>
                          </button>
                        </div>
                      </article>
                      <button
                        v-if="hasMoreProcessEvents(task.run.run_id, group)"
                        class="process-virtual-footer"
                        type="button"
                        @click="loadMoreProcessEvents(task.run.run_id, group)"
                      >
                        <SvgIcon
                          v-if="isProcessGroupLoading(task.run.run_id, group)"
                          type="mdi"
                          :path="mdiLoading"
                          class="button-icon loading-icon"
                        />
                        <span>
                          {{ isProcessGroupLoading(task.run.run_id, group)
                            ? '正在加载更多过程'
                            : `继续加载 ${visibleProcessCount(task.run.run_id, group)} / ${processEventGroupTotalCount(group)}` }}
                        </span>
                      </button>
                    </div>
                    <div
                      v-else
                      class="result-empty"
                      :class="{ waiting: shouldShowGroupLoading(task.run, group) }"
                    >
                      <SvgIcon
                        v-if="shouldShowGroupLoading(task.run, group)"
                        type="mdi"
                        :path="mdiLoading"
                        class="button-icon loading-icon"
                      />
                      <span>{{ group.emptyText }}</span>
                    </div>
                    </div>
                  </article>
                </div>
              </template>
            </section>
          </section>
        </div>

        <div v-if="selectedRun && isSelectedRunActive" class="bottom-operation-bar">
          <div class="bottom-operation-card generation-control-card">
            <div class="generation-control-main">
              <div class="generation-control-text">
                <SvgIcon type="mdi" :path="mdiLoading" class="button-icon loading-icon" />
                <span>{{ isTerminating ? '正在终止当前任务' : '任务正在生成' }}</span>
              </div>
              <button
                class="action-btn action-terminate"
                type="button"
                :disabled="!canTerminateRun"
                @click="handleTerminate"
              >
                <SvgIcon
                  type="mdi"
                  :path="isTerminating ? mdiLoading : mdiStopCircleOutline"
                  :class="['button-icon', { 'loading-icon': isTerminating }]"
                />
                {{ isTerminating ? '终止中' : '终止' }}
              </button>
            </div>
            <div v-if="errorMessage" class="composer-error-inline">{{ errorMessage }}</div>
          </div>
        </div>
      </section>
    </main>

    <div
      v-if="previewDrawerOpen"
      class="preview-backdrop"
      role="presentation"
      @click="closePreviewDrawer"
    ></div>

    <aside
      class="result-drawer"
      :class="{ 'result-drawer-open': previewDrawerOpen, 'result-drawer-previewing': Boolean(previewFileKind) }"
      aria-label="结果展示和预览"
    >
      <header class="drawer-header">
        <button
          v-if="previewFileKind"
          class="icon-button drawer-back-button"
          type="button"
          aria-label="返回文件列表"
          @click="backToPreviewList"
        >
          <SvgIcon type="mdi" :path="mdiChevronRight" class="button-icon drawer-back-icon" />
        </button>
        <div>
          <div class="drawer-kicker">结果展示</div>
          <h2 class="drawer-title">{{ previewFileKind ? previewFileTitle : selectedRun ? displayTaskTitle(selectedRun) : '文档生成任务' }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="关闭预览" @click="closePreviewDrawer">
          <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
        </button>
      </header>

      <div v-if="selectedRun" class="drawer-body">
        <section v-if="previewFileKind" class="drawer-preview-panel drawer-preview-full">
          <div v-if="previewError" class="drawer-preview-error">{{ previewError }}</div>
          <div v-else-if="isPreviewLoading" class="drawer-preview-empty">
            <SvgIcon type="mdi" :path="mdiLoading" class="button-icon loading-icon" />
            <span>正在加载预览</span>
          </div>
          <iframe
            v-else-if="previewFileKind === 'pdf' && previewFileUrl"
            class="drawer-pdf-preview"
            :src="previewFileUrl"
            title="PDF 预览"
          ></iframe>
          <div
            v-else-if="previewFileKind === 'markdown'"
            class="drawer-markdown-preview"
            v-html="previewMarkdownHtml"
          ></div>
        </section>

        <div v-else class="final-output-card">
          <span class="preview-status-value" :class="`status-${selectedRun.status}`">
            {{ runStatusLabelMap[selectedRun.status] || selectedRun.status }}
          </span>

          <div class="preview-file-row">
            <div>
              <span>Markdown</span>
              <strong>{{ basename(selectedRun.output_path) || '生成完成后可用' }}</strong>
            </div>
            <div class="preview-file-actions">
              <button
                class="action-btn action-preview"
                type="button"
                :disabled="!canPreviewRunFile('markdown') || isPreviewLoading"
                @click="handlePreviewFile('markdown')"
              >
                <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
                预览
              </button>
              <button
                class="action-btn action-download"
                type="button"
                :disabled="selectedRun.status !== 'completed'"
                @click="handleDownload('markdown')"
              >
                <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="button-icon" />
                下载
              </button>
            </div>
          </div>
          <div class="preview-file-row">
            <div>
              <span>PDF</span>
              <strong>{{ basename(selectedRun.pdf_path) || '生成完成后可用' }}</strong>
            </div>
            <div class="preview-file-actions">
              <button
                class="action-btn action-preview"
                type="button"
                :disabled="!canPreviewRunFile('pdf') || isPreviewLoading"
                @click="handlePreviewFile('pdf')"
              >
                <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
                预览
              </button>
              <button
                class="action-btn action-download"
                type="button"
                :disabled="selectedRun.status !== 'completed'"
                @click="handleDownload('pdf')"
              >
                <SvgIcon type="mdi" :path="mdiFilePdfBox" class="button-icon" />
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import { marked } from 'marked'
import {
  mdiAlertCircleOutline,
  mdiChartLine,
  mdiCheckCircleOutline,
  mdiChevronDown,
  mdiChevronRight,
  mdiChevronUp,
  mdiClockOutline,
  mdiClose,
  mdiFileDocumentOutline,
  mdiFileEyeOutline,
  mdiFilePdfBox,
  mdiFilePlusOutline,
  mdiFormatListBulletedType,
  mdiLoading,
  mdiPlus,
  mdiSend,
  mdiStopCircleOutline,
} from '@mdi/js'
import {
  activeRunStatusSet,
  downloadMarkdown,
  downloadPdf,
  eventTypeLabelMap,
  fetchRunFile,
  getDocTypes,
  getRunTrace,
  listRunHistory,
  phaseLabelMap,
  runStatusLabelMap,
  startGeneration,
  streamRunTrace,
  terminalRunStatusSet,
  terminateRun,
  type AgentTraceEvent,
  type DocType,
  type RunTrace,
} from './dogen_utils'

type ProcessEventKind = 'thought' | 'tool' | 'result' | 'status' | 'error'
type ProcessExecutionState = 'started' | 'running' | 'completed' | 'failed'
type ChapterProgressStatus = 'pending' | 'running' | 'completed'

interface ChapterProgressItem {
  index: number
  title: string
  status: ChapterProgressStatus
}

interface ChapterProcessGroup {
  key: string
  title: string
  index: number
  status: ChapterProgressStatus
  events: AgentTraceEvent[]
  emptyText: string
}

interface ProcessEventDisplayGroup {
  key: string
  title: string
  kind: ProcessEventKind
  state: ProcessExecutionState
  events: AgentTraceEvent[]
}

interface ConversationMessageItem {
  key: string
  label: string
  content: string
  time: string
}

interface ConversationTaskItem {
  run: RunTrace
  messages: ConversationMessageItem[]
  activeChapterTitle: string
  groups: ChapterProcessGroup[]
}

const docTypes = ref<DocType[]>(['需求规格说明书', '架构设计文档', '测试文档'])
const selectedDocTypes = ref<DocType[]>(['需求规格说明书'])
const promptInput = ref('')
const sourceFiles = ref<File[]>([])
const isSubmitting = ref(false)
const isTerminating = ref(false)
const errorMessage = ref('')
const selectedRunId = ref<string | null>(null)
const selectedRun = ref<RunTrace | null>(null)
const runHistory = ref<RunTrace[]>([])
const sourceInputRef = ref<HTMLInputElement | null>(null)
const docSubmitButtonRef = ref<HTMLButtonElement | null>(null)
const previewDrawerOpen = ref(false)
const docTypeMenuOpen = ref(false)
const previewFileKind = ref<'markdown' | 'pdf' | ''>('')
const previewFileUrl = ref('')
const previewFileText = ref('')
const isPreviewLoading = ref(false)
const previewError = ref('')
const expandedChapterIds = ref<string[]>([])
const expandedProcessEventIds = ref<string[]>([])
const processEventVisibleCounts = ref<Record<string, number>>({})
const processEventLoadingKeys = ref<Record<string, boolean>>({})
const processEntryVisibleCounts = ref<Record<string, number>>({})
const processEntryLoadingKeys = ref<Record<string, boolean>>({})

let pollTimer: ReturnType<typeof setInterval> | null = null
let traceStreamController: AbortController | null = null
let previewObjectUrl: string | null = null

const LOCAL_KEY = 'docgen_run_ids'
const PROMPT_KEY = 'docgen_run_prompts'
const PROCESS_EVENT_INITIAL_COUNT = 14
const PROCESS_EVENT_BATCH_COUNT = 12
const PROCESS_ENTRY_INITIAL_COUNT = 8
const PROCESS_ENTRY_BATCH_COUNT = 8
const processEventKindLabelMap: Record<ProcessEventKind, string> = {
  thought: '思考过程',
  tool: '工具调用',
  result: '中间结果',
  status: '执行状态',
  error: '异常信息',
}
const chapterStatusLabelMap: Record<ChapterProgressStatus, string> = {
  pending: '等待中',
  running: '生成中',
  completed: '已完成',
}

const isSelectedRunActive = computed(() => {
  return selectedRun.value ? activeRunStatusSet.has(selectedRun.value.status) : false
})

const canTerminateRun = computed(() => {
  return isSelectedRunActive.value
    && selectedRun.value?.status !== 'terminate_requested'
    && !isTerminating.value
})

const selectedDocTypeLabel = computed(() => {
  if (selectedDocTypes.value.length === 0) return '文档类型'
  if (selectedDocTypes.value.length === 1) return selectedDocTypes.value[0]
  return `已选择 ${selectedDocTypes.value.length} 类文档`
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

const loadLocalRunTraces = async (knownIds = new Set<string>()) => {
  const ids = loadLocalRunIds()
  const traces: RunTrace[] = []
  for (const id of ids) {
    if (knownIds.has(id)) continue
    try {
      traces.push(await getRunTrace(id))
    } catch {
      removeMissingRunId(id)
    }
  }
  return traces
}

const restoreRunHistory = async () => {
  let persistedRuns: RunTrace[] = []
  try {
    persistedRuns = await listRunHistory()
  } catch {
    // 兼容旧版本本地记录；数据库历史接口不可用时继续使用 localStorage。
  }

  const knownIds = new Set(persistedRuns.map((run) => run.run_id))
  const localRuns = await loadLocalRunTraces(knownIds)
  const mergedRuns = [...persistedRuns, ...localRuns].sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at || 0).getTime()
    const bTime = new Date(b.updated_at || b.created_at || 0).getTime()
    return bTime - aTime
  })

  runHistory.value = mergedRuns
  for (const run of [...mergedRuns].reverse()) saveLocalRunId(run.run_id)

  const active = mergedRuns.find((run) => activeRunStatusSet.has(run.status))
  if (active) {
    await selectRun(active.run_id)
  }
}

const loadRecord = (key: string): Record<string, string> => {
  try {
    const value = JSON.parse(localStorage.getItem(key) || '{}')
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  } catch {
    return {}
  }
}

const saveRecordValue = (key: string, id: string, value: string) => {
  const record = loadRecord(key)
  record[id] = value
  localStorage.setItem(key, JSON.stringify(record))
}

const saveRunPrompt = (runId: string, prompt: string) => {
  const clean = prompt.trim()
  if (clean) saveRecordValue(PROMPT_KEY, runId, clean)
}

const runConversationMessages = (run: RunTrace): ConversationMessageItem[] => {
  const messages: ConversationMessageItem[] = []
  const started = run.events.find((event) => event.type === 'run_started')
  const startedHint = typeof started?.user_hint === 'string' ? started.user_hint.trim() : ''
  const stored = loadRecord(PROMPT_KEY)[run.run_id]
  const firstPrompt = stored || startedHint
  if (firstPrompt) {
    messages.push({
      key: `${run.run_id}-start`,
      label: '用户提示',
      content: firstPrompt,
      time: started?.time || run.created_at,
    })
  }

  return messages
}

const stopPolling = () => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (traceStreamController !== null) {
    traceStreamController.abort()
    traceStreamController = null
  }
}

const pollRun = async (runId: string) => {
  try {
    const trace = await getRunTrace(runId)
    selectedRun.value = trace
    updateRunInHistory(trace)
    ensureExpandedChaptersForRun(trace)
    if (terminalRunStatusSet.has(trace.status)) stopPolling()
  } catch (error) {
    errorMessage.value = `获取任务状态失败：${error}`
    stopPolling()
  }
}

const startPolling = (runId: string) => {
  stopPolling()
  void pollRun(runId)
  traceStreamController = new AbortController()
  void streamRunTrace(
    runId,
    (trace) => {
      if (selectedRunId.value !== runId) return
      selectedRun.value = trace
      updateRunInHistory(trace)
      ensureExpandedChaptersForRun(trace)
      if (terminalRunStatusSet.has(trace.status)) stopPolling()
    },
    traceStreamController.signal,
  ).catch((error) => {
    if (error instanceof DOMException && error.name === 'AbortError') return
    if (selectedRunId.value !== runId) return
    pollTimer = setInterval(() => void pollRun(runId), 1000)
  })
}

const openNewDoc = () => {
  selectedRunId.value = null
  selectedRun.value = null
  expandedChapterIds.value = []
  errorMessage.value = ''
  closePreviewDrawer()
  docTypeMenuOpen.value = false
  stopPolling()
}

const submitGeneration = async () => {
  if (isSubmitting.value) return
  isSubmitting.value = true
  errorMessage.value = ''
  try {
    if (selectedDocTypes.value.length === 0) {
      throw new Error('请至少选择一种文档类型')
    }
    docTypeMenuOpen.value = false
    const initialPrompt = promptInput.value.trim()
    const startedRuns: RunTrace[] = []
    for (const docType of selectedDocTypes.value) {
      const response = await startGeneration(initialPrompt, docType, sourceFiles.value)
      saveLocalRunId(response.task_id)
      saveRunPrompt(response.task_id, initialPrompt || docType)
      const stub: RunTrace = {
        run_id: response.task_id,
        status: 'running',
        doc_type: response.doc_type,
        task_title: response.task_title || response.doc_type,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        output_path: null,
        pdf_path: null,
        error: null,
        terminated: false,
        events: [],
      }
      updateRunInHistory(stub)
      startedRuns.push(stub)
    }
    const firstRun = startedRuns[0]
    if (!firstRun) throw new Error('后台生成接口未返回运行任务')
    selectedRunId.value = firstRun.run_id
    selectedRun.value = firstRun
    expandedChapterIds.value = defaultExpandedChapterKeys(firstRun)
    promptInput.value = ''
    clearSourceFiles()
    startPolling(firstRun.run_id)
  } catch (error) {
    errorMessage.value = `启动失败：${error}`
  } finally {
    isSubmitting.value = false
  }
}

const insertTextareaLineBreak = (event: KeyboardEvent) => {
  const target = event.target
  if (!(target instanceof HTMLTextAreaElement)) return
  const start = target.selectionStart
  const end = target.selectionEnd
  target.value = `${target.value.slice(0, start)}\n${target.value.slice(end)}`
  target.selectionStart = start + 1
  target.selectionEnd = start + 1
  target.dispatchEvent(new Event('input', { bubbles: true }))
}

const handlePromptKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Enter' || event.isComposing) return
  event.preventDefault()
  if (event.ctrlKey || event.shiftKey) {
    insertTextareaLineBreak(event)
    return
  }
  if (isSubmitting.value || selectedDocTypes.value.length === 0) return
  docSubmitButtonRef.value?.click()
}

const selectRun = async (runId: string) => {
  selectedRunId.value = runId
  expandedChapterIds.value = []
  errorMessage.value = ''
  previewFileKind.value = ''
  clearPreviewFile()
  docTypeMenuOpen.value = false
  stopPolling()
  try {
    const trace = await getRunTrace(runId)
    selectedRun.value = trace
    updateRunInHistory(trace)
    expandedChapterIds.value = defaultExpandedChapterKeys(trace)
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

const handleTerminate = async () => {
  if (!selectedRunId.value || !canTerminateRun.value) return
  isTerminating.value = true
  errorMessage.value = ''
  try {
    await terminateRun(selectedRunId.value)
    await refreshSelectedRun()
  } catch (error) {
    errorMessage.value = `终止失败：${error}`
  } finally {
    isTerminating.value = false
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

const clearPreviewFile = () => {
  if (previewObjectUrl) {
    URL.revokeObjectURL(previewObjectUrl)
    previewObjectUrl = null
  }
  previewFileUrl.value = ''
  previewFileText.value = ''
  previewError.value = ''
}

const backToPreviewList = () => {
  previewFileKind.value = ''
  clearPreviewFile()
}

const closePreviewDrawer = () => {
  previewDrawerOpen.value = false
  previewFileKind.value = ''
  clearPreviewFile()
}

const canPreviewRunFile = (kind: 'markdown' | 'pdf') => {
  if (!selectedRun.value || selectedRun.value.status !== 'completed') return false
  return kind === 'pdf'
    ? Boolean(selectedRun.value.pdf_path || selectedRun.value.output_path)
    : Boolean(selectedRun.value.output_path)
}

const previewFileTitle = computed(() => {
  if (previewFileKind.value === 'pdf') return basename(selectedRun.value?.pdf_path) || 'PDF 预览'
  if (previewFileKind.value === 'markdown') return basename(selectedRun.value?.output_path) || 'Markdown 预览'
  return '未选择文件'
})

const previewMarkdownHtml = computed(() => {
  return marked.parse(previewFileText.value || '', { async: false }) as string
})

const handlePreviewFile = async (kind: 'markdown' | 'pdf') => {
  if (!selectedRunId.value || !canPreviewRunFile(kind)) return
  isPreviewLoading.value = true
  previewError.value = ''
  clearPreviewFile()
  previewFileKind.value = kind
  try {
    const blob = await fetchRunFile(selectedRunId.value, kind)
    if (kind === 'pdf') {
      previewObjectUrl = URL.createObjectURL(blob)
      previewFileUrl.value = previewObjectUrl
    } else {
      previewFileText.value = await blob.text()
    }
  } catch (error) {
    previewError.value = `预览失败：${error}`
  } finally {
    isPreviewLoading.value = false
  }
}

const onSourceFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  sourceFiles.value = Array.from(input.files || [])
}

const clearSourceFiles = () => {
  sourceFiles.value = []
  if (sourceInputRef.value) sourceInputRef.value.value = ''
}

const normalizedPhase = (phase: string) => {
  if (phase.startsWith('generate_section:')) return 'generate_sections'
  return phase || 'run'
}

const eventSectionTitle = (event: AgentTraceEvent) => {
  if (event.phase?.startsWith('generate_section:')) return event.phase.slice('generate_section:'.length)
  return ''
}

const truncateTitle = (value: string, max = 10) => {
  const clean = (value || '文档生成任务').trim()
  return clean.length > max ? `${clean.slice(0, max)}…` : clean
}

const displayTaskTitle = (run: RunTrace) => {
  return run.task_title || run.doc_type || '文档生成任务'
}

const processEventTypes = new Set([
  'reasoning',
  'phase_started',
  'llm_request',
  'tool_calls_planned',
  'tool_call',
  'tool_result',
  'assistant_message',
  'section_started',
  'section_completed',
  'section_saved_in_memory',
  'document_stitched',
  'format_repaired',
  'phase_completed',
  'error',
])

const conversationRuns = computed(() => {
  return selectedRun.value ? [selectedRun.value] : []
})

const statusRun = computed(() => {
  const runs = conversationRuns.value
  return runs.length ? runs[runs.length - 1] : selectedRun.value
})

const processEventsForRun = (run?: RunTrace | null) => {
  if (!run) return []
  return run.events
    .filter((event) => {
      if (event.type === 'tool_calls_planned') return false
      return (
        processEventTypes.has(event.type)
        || event.type.includes('tool')
        || event.type.includes('section')
        || Boolean(event.result || event.content || event.message || event.error)
      )
    })
}

const chapterTitlesForRun = (run?: RunTrace | null) => {
  if (!run) return []
  const splitEvent = run.events.find((event) => {
    return event.phase === 'split_sections' && Array.isArray(event.sections)
  })
  if (Array.isArray(splitEvent?.sections)) {
    return (splitEvent.sections as string[]).filter(Boolean)
  }
  const titles: string[] = []
  for (const event of run.events) {
    const title = event.title || eventSectionTitle(event)
    if (title && !titles.includes(title)) {
      titles.push(title)
    }
  }
  return titles
}

const eventBelongsToChapter = (event: AgentTraceEvent, title: string) => {
  return event.title === title || eventSectionTitle(event) === title
}

const chapterProgressItemsForRun = (run?: RunTrace | null): ChapterProgressItem[] => {
  if (!run) return []
  return chapterTitlesForRun(run).map((title, index) => {
    const events = run.events.filter((event) => eventBelongsToChapter(event, title))
    const completed = events.some((event) => {
      return event.type === 'section_completed'
        || event.type === 'section_saved_in_memory'
    })
    const status: ChapterProgressStatus = completed ? 'completed' : events.length > 0 ? 'running' : 'pending'
    return { index: index + 1, title, status }
  })
}

const chapterProgressItems = computed<ChapterProgressItem[]>(() => chapterProgressItemsForRun(statusRun.value))

const activeChapterTitleForRun = (run?: RunTrace | null) => {
  const items = chapterProgressItemsForRun(run)
  const running = [...items].reverse().find((item) => item.status === 'running')
  if (running) return running.title
  const latest = [...items].reverse().find((item) => item.status === 'completed')
  return latest?.title || items[0]?.title || ''
}

const activeChapterTitle = computed(() => activeChapterTitleForRun(statusRun.value))

const lastCompletedChapterIndex = (items: ChapterProgressItem[]) => {
  return items.reduce((latest, item, index) => item.status === 'completed' ? index : latest, -1)
}

const runningChapterIndex = (items: ChapterProgressItem[]) => {
  return items.findIndex((item) => item.status === 'running')
}

const headerCompletedRatio = computed(() => {
  const items = chapterProgressItems.value
  if (items.length <= 1) return items[0]?.status === 'completed' ? 1 : 0
  const completedIndex = lastCompletedChapterIndex(items)
  return completedIndex < 0 ? 0 : Math.max(0, Math.min(1, completedIndex / (items.length - 1)))
})

const headerProgressRatio = computed(() => {
  const items = chapterProgressItems.value
  if (items.length <= 1) return items[0]?.status === 'completed' ? 1 : 0
  let index = runningChapterIndex(items)
  if (index >= 0) {
    if (index >= items.length - 1) return 0.94
    return Math.max(0, Math.min(1, (index + 0.35) / (items.length - 1)))
  }
  index = lastCompletedChapterIndex(items)
  if (index < 0) return 0
  return Math.max(0, Math.min(1, index / (items.length - 1)))
})

const headerProgressStyle = computed<Record<string, string>>(() => ({
  '--progress-ratio': String(headerProgressRatio.value),
  '--completed-ratio': String(headerCompletedRatio.value),
}))

const isHeaderProgressCompleted = computed(() => {
  return chapterProgressItems.value.length > 0
    && chapterProgressItems.value.every((item) => item.status === 'completed')
})

const chapterProcessGroupsForRun = (run?: RunTrace | null): ChapterProcessGroup[] => {
  if (!run) return []

  const items = chapterProgressItemsForRun(run)
  const events = processEventsForRun(run)

  return items.map((item) => {
    const groupEvents = events.filter((event) => eventBelongsToChapter(event, item.title))
    return {
      key: `chapter-${item.index}-${item.title}`,
      title: item.title,
      index: item.index,
      status: item.status,
      events: groupEvents,
      emptyText: item.status === 'pending'
        ? '等待本章节开始'
        : item.status === 'running'
          ? '正在进入本章节'
          : '本章节暂无过程记录',
    }
  })
}

const shouldShowGroupLoading = (run: RunTrace, group: ChapterProcessGroup) => {
  return activeRunStatusSet.has(run.status) && group.status !== 'pending'
}

const chapterFinalEvents = (group: ChapterProcessGroup) => {
  if (!group.index) return []
  const finalEvent = [...group.events].reverse().find((event) => {
    return event.type === 'section_completed' && typeof event.content === 'string' && event.content.trim()
  })
  return finalEvent ? [finalEvent] : []
}

const chapterFinalBody = (event: AgentTraceEvent) => {
  return typeof event.content === 'string' ? event.content : ''
}

const chapterStatusLabel = (status: ChapterProgressStatus) => {
  return chapterStatusLabelMap[status] || status
}

const chapterStatusIcon = (status: ChapterProgressStatus) => {
  if (status === 'completed') return mdiCheckCircleOutline
  if (status === 'running') return mdiLoading
  return mdiClockOutline
}

const chapterGroupExpansionKey = (runId: string, group: ChapterProcessGroup) => {
  return `${runId}::chapter::${group.key}`
}

const defaultExpandedChapterKeys = (run: RunTrace) => {
  const groups = chapterProcessGroupsForRun(run)
  const activeTitle = activeChapterTitleForRun(run)
  const defaultGroups = groups.filter((group) => {
    return group.status === 'running' || group.title === activeTitle
  })
  const targets = defaultGroups.length ? defaultGroups : groups.slice(0, 1)
  return targets.map((group) => chapterGroupExpansionKey(run.run_id, group))
}

const ensureExpandedChaptersForRun = (run: RunTrace) => {
  const prefix = `${run.run_id}::chapter::`
  if (expandedChapterIds.value.some((key) => key.startsWith(prefix))) return
  expandedChapterIds.value = [
    ...expandedChapterIds.value,
    ...defaultExpandedChapterKeys(run),
  ]
}

const isChapterGroupExpanded = (runId: string, group: ChapterProcessGroup) => {
  return expandedChapterIds.value.includes(chapterGroupExpansionKey(runId, group))
}

const toggleChapterGroupExpansion = (runId: string, group: ChapterProcessGroup) => {
  const key = chapterGroupExpansionKey(runId, group)
  if (expandedChapterIds.value.includes(key)) {
    expandedChapterIds.value = expandedChapterIds.value.filter((item) => item !== key)
  } else {
    expandedChapterIds.value = [...expandedChapterIds.value, key]
  }
}

const processGroupVirtualKey = (runId: string, group: ChapterProcessGroup) => {
  return `${runId}::${group.key}`
}

const visibleProcessCount = (runId: string, group: ChapterProcessGroup) => {
  const key = processGroupVirtualKey(runId, group)
  const count = processEventVisibleCounts.value[key] ?? PROCESS_EVENT_INITIAL_COUNT
  return Math.min(count, processEventDisplayGroups(group).length)
}

const visibleProcessEventGroups = (runId: string, group: ChapterProcessGroup) => {
  return processEventDisplayGroups(group).slice(0, visibleProcessCount(runId, group))
}

const hasMoreProcessEvents = (runId: string, group: ChapterProcessGroup) => {
  return visibleProcessCount(runId, group) < processEventDisplayGroups(group).length
}

const processEventGroupTotalCount = (group: ChapterProcessGroup) => {
  return processEventDisplayGroups(group).length
}

const isProcessGroupLoading = (runId: string, group: ChapterProcessGroup) => {
  return Boolean(processEventLoadingKeys.value[processGroupVirtualKey(runId, group)])
}

const loadMoreProcessEvents = (runId: string, group: ChapterProcessGroup) => {
  if (!hasMoreProcessEvents(runId, group) || isProcessGroupLoading(runId, group)) return
  const key = processGroupVirtualKey(runId, group)
  processEventLoadingKeys.value = { ...processEventLoadingKeys.value, [key]: true }
  window.setTimeout(() => {
    processEventVisibleCounts.value = {
      ...processEventVisibleCounts.value,
      [key]: Math.min(
        visibleProcessCount(runId, group) + PROCESS_EVENT_BATCH_COUNT,
        processEventDisplayGroups(group).length,
      ),
    }
    processEventLoadingKeys.value = { ...processEventLoadingKeys.value, [key]: false }
  }, 80)
}

const onProcessEventListScroll = (event: Event, runId: string, group: ChapterProcessGroup) => {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const nearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 96
  if (nearBottom) loadMoreProcessEvents(runId, group)
}

const processEventGroupKey = (event: AgentTraceEvent, group: ChapterProcessGroup) => {
  const phase = normalizedPhase(event.phase || (group.index ? `generate_section:${group.title}` : 'run'))
  return `phase:${phase}:kind:${processEventKind(event)}`
}

const processEventExpansionKey = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  return `${runId}::${group.key}::${eventGroup.key}`
}

const isProcessEventExpanded = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  return expandedProcessEventIds.value.includes(processEventExpansionKey(runId, group, eventGroup))
}

const toggleProcessEventExpansion = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  const key = processEventExpansionKey(runId, group, eventGroup)
  if (expandedProcessEventIds.value.includes(key)) {
    expandedProcessEventIds.value = expandedProcessEventIds.value.filter((id) => id !== key)
  } else {
    expandedProcessEventIds.value = [...expandedProcessEventIds.value, key]
  }
}

const processEntryChapterKey = (event: AgentTraceEvent) => {
  return event.title || eventSectionTitle(event) || ''
}

const shouldShowProcessEventEntry = (event: AgentTraceEvent) => {
  const isPhaseStatus = event.type === 'phase_started'
    || event.type === 'phase_completed'
    || event.type === 'llm_request'
  return !isPhaseStatus || eventHasBody(event)
}

const processEventDisplayEntries = (eventGroup: ProcessEventDisplayGroup) => {
  const completedChapters = new Set(
    eventGroup.events
      .filter((event) => event.type === 'section_completed')
      .map(processEntryChapterKey)
      .filter(Boolean),
  )
  let entries = eventGroup.events
  if (completedChapters.size) {
    entries = eventGroup.events.filter((event) => {
      return event.type !== 'section_saved_in_memory'
      || !completedChapters.has(processEntryChapterKey(event))
    })
  }
  return entries.filter(shouldShowProcessEventEntry)
}

const visibleProcessEntryCount = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  const key = processEventExpansionKey(runId, group, eventGroup)
  const count = processEntryVisibleCounts.value[key] ?? PROCESS_ENTRY_INITIAL_COUNT
  return Math.min(count, processEventDisplayEntries(eventGroup).length)
}

const visibleProcessEntries = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  return processEventDisplayEntries(eventGroup).slice(0, visibleProcessEntryCount(runId, group, eventGroup))
}

const hasMoreProcessEntries = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  return visibleProcessEntryCount(runId, group, eventGroup) < processEventDisplayEntries(eventGroup).length
}

const isProcessEntryGroupLoading = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  return Boolean(processEntryLoadingKeys.value[processEventExpansionKey(runId, group, eventGroup)])
}

const loadMoreProcessEntries = (
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  if (!hasMoreProcessEntries(runId, group, eventGroup) || isProcessEntryGroupLoading(runId, group, eventGroup)) return
  const key = processEventExpansionKey(runId, group, eventGroup)
  processEntryLoadingKeys.value = { ...processEntryLoadingKeys.value, [key]: true }
  window.setTimeout(() => {
    processEntryVisibleCounts.value = {
      ...processEntryVisibleCounts.value,
      [key]: Math.min(
        visibleProcessEntryCount(runId, group, eventGroup) + PROCESS_ENTRY_BATCH_COUNT,
        processEventDisplayEntries(eventGroup).length,
      ),
    }
    processEntryLoadingKeys.value = { ...processEntryLoadingKeys.value, [key]: false }
  }, 80)
}

const onProcessEntryListScroll = (
  event: Event,
  runId: string,
  group: ChapterProcessGroup,
  eventGroup: ProcessEventDisplayGroup,
) => {
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const nearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 96
  if (nearBottom) loadMoreProcessEntries(runId, group, eventGroup)
}

const processEventDisplayGroups = (group: ChapterProcessGroup): ProcessEventDisplayGroup[] => {
  const groups: ProcessEventDisplayGroup[] = []
  const indexByKey = new Map<string, ProcessEventDisplayGroup>()
  const latestChapterEvent = group.events[group.events.length - 1]
  for (const event of group.events) {
    if (event.type === 'tool_calls_planned') continue
    const key = processEventGroupKey(event, group)
    let item = indexByKey.get(key)
    if (!item) {
      item = {
        key,
        title: phaseEventTitle(event),
        kind: processEventKind(event),
        state: processEventState(event),
        events: [],
      }
      indexByKey.set(key, item)
      groups.push(item)
    }
    item.events.push(event)
    item.state = processEventState(event)
    if (item.kind !== 'error' && processEventKind(event) === 'error') item.kind = 'error'
    if (item.kind === 'status' && processEventKind(event) !== 'status') item.kind = processEventKind(event)
  }
  const chapterCompleted = group.status === 'completed'
  for (const item of groups) {
    const latest = lastProcessEvent(item)
    if (!latest || item.state === 'failed') continue
    const isLatestChapterEvent = latestChapterEvent && latest.id === latestChapterEvent.id
    if (chapterCompleted || (item.state === 'running' && latestChapterEvent && !isLatestChapterEvent)) {
      item.state = 'completed'
    }
  }
  return groups
}

const lastProcessEvent = (group: ProcessEventDisplayGroup) => {
  return group.events[group.events.length - 1] as AgentTraceEvent
}

const isStreamingEventGroup = (run: RunTrace, group: ProcessEventDisplayGroup) => {
  return group.events.some((event) => isStreamingEventForRun(run, event))
}

const conversationTaskItems = computed<ConversationTaskItem[]>(() => {
  return conversationRuns.value.map((run) => ({
    run,
    messages: runConversationMessages(run),
    activeChapterTitle: activeChapterTitleForRun(run),
    groups: chapterProcessGroupsForRun(run),
  }))
})

const headerRunStatusIcon = computed(() => {
  if (!statusRun.value) return mdiClockOutline
  if (statusRun.value.status === 'completed') return mdiCheckCircleOutline
  if (statusRun.value.status === 'failed'
    || statusRun.value.status === 'terminated') {
    return mdiAlertCircleOutline
  }
  if (statusRun.value.status === 'running'
    || statusRun.value.status === 'terminate_requested') {
    return mdiChartLine
  }
  return mdiClockOutline
})

const isStreamingEventForRun = (run: RunTrace, event: AgentTraceEvent) => {
  if (!activeRunStatusSet.has(run.status)) return false
  const latest = run.events[run.events.length - 1]
  return Boolean(event.streaming && latest?.id === event.id)
}

const runStatusIcon = (status: string) => {
  if (status === 'completed') return mdiCheckCircleOutline
  if (status === 'failed' || status === 'terminated') return mdiAlertCircleOutline
  if (status === 'running' || status.endsWith('_requested')) return mdiLoading
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
  const second = `${date.getSeconds()}`.padStart(2, '0')
  return `${month}/${day} ${hour}:${minute}:${second}`
}

const truncateText = (value: unknown, max = 420) => {
  if (value === undefined || value === null) return ''
  const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  return text.length > max ? `${text.slice(0, max)}...` : text
}

const processEventKind = (event: AgentTraceEvent): ProcessEventKind => {
  if (event.type === 'error' || event.error) return 'error'
  if (event.type === 'reasoning') return 'thought'
  if (event.type.includes('tool')) return 'tool'
  if (
    event.type === 'assistant_message'
    || event.type.includes('section')
    || event.type === 'document_stitched'
    || event.type === 'table_repaired'
    || event.type === 'format_repaired'
  ) {
    return 'result'
  }
  return 'status'
}

const processEventState = (event: AgentTraceEvent): ProcessExecutionState => {
  if (event.type === 'error' || event.error || event.type.endsWith('_failed')) return 'failed'
  if (event.type === 'phase_started' || event.type === 'section_started') return 'started'
  if (event.type === 'phase_completed'
    || event.type === 'section_completed'
    || event.type === 'section_saved_in_memory'
    || event.type === 'document_stitched'
    || event.type === 'format_repaired'
    || event.type === 'table_repaired'
    || event.type === 'tool_result'
    || event.type === 'assistant_message') {
    return 'completed'
  }
  return 'running'
}

const processExecutionStatusLabel = (state: ProcessExecutionState) => {
  if (state === 'started') return '开始执行'
  if (state === 'running') return '执行中'
  if (state === 'completed') return '执行完成'
  return '执行失败'
}

const processExecutionStatusIcon = (state: ProcessExecutionState) => {
  if (state === 'started') return mdiClockOutline
  if (state === 'running') return mdiLoading
  if (state === 'completed') return mdiCheckCircleOutline
  return mdiAlertCircleOutline
}

const phaseEventTitle = (event: AgentTraceEvent) => {
  const phase = normalizedPhase(event.phase || 'run')
  return `阶段：${phaseLabelMap[phase] || phase}`
}

const toolEventTitle = (event: AgentTraceEvent) => {
  const tools = Array.isArray(event.tools) ? event.tools.filter(Boolean).join('、') : ''
  return event.name ? `工具：${event.name}` : tools ? `工具：${tools}` : '工具调用'
}

const processEventSectionTitle = (event: AgentTraceEvent, group?: ChapterProcessGroup) => {
  const sectionTitle = event.title || eventSectionTitle(event)
  if (group?.index && sectionTitle === group.title) return ''
  return sectionTitle
}

const processEventTitle = (event: AgentTraceEvent, group?: ChapterProcessGroup) => {
  const sectionTitle = processEventSectionTitle(event, group)
  if (event.type === 'phase_started' || event.type === 'phase_completed' || event.type === 'llm_request') return phaseEventTitle(event)
  if (event.type === 'tool_calls_planned' || event.type === 'tool_call' || event.type === 'tool_result') return toolEventTitle(event)
  if (event.type === 'reasoning') return '模型思考'
  if (event.type === 'assistant_message') return sectionTitle ? `模型输出：${sectionTitle}` : '模型输出'
  if (event.type === 'section_started' || event.type === 'section_completed' || event.type === 'section_saved_in_memory') {
    return sectionTitle ? `章节：${sectionTitle}` : '章节生成'
  }
  if (event.type === 'document_stitched') return '文档拼接'
  if (event.type === 'table_repaired' || event.type === 'format_repaired') return '格式规范化'
  return sectionTitle || eventTypeLabelMap[event.type] || event.type
}

const processEventEntryTitle = (event: AgentTraceEvent, group?: ChapterProcessGroup) => {
  if (event.type === 'phase_started' || event.type === 'phase_completed' || event.type === 'llm_request') return '阶段状态'
  return processEventTitle(event, group)
}

const processEventSummary = (group: ProcessEventDisplayGroup) => {
  const latest = lastProcessEvent(group)
  if (!latest) return ''
  const body = processEventBody(latest)
  return body ? truncateText(body, 220) : ''
}

const processEventGroupStatusText = (group: ProcessEventDisplayGroup) => {
  return processExecutionStatusLabel(group.state)
}

const processEventEntryState = (
  event: AgentTraceEvent,
  group: ProcessEventDisplayGroup,
): ProcessExecutionState => {
  const state = processEventState(event)
  if (state === 'failed') return 'failed'
  if (group.state === 'completed') return 'completed'
  return state
}

const processEventEntryStatusText = (
  event: AgentTraceEvent,
  group: ProcessEventDisplayGroup,
) => {
  return processExecutionStatusLabel(processEventEntryState(event, group))
}

const processEventBodySource = (event: AgentTraceEvent) => {
  if (event.type === 'section_completed') return undefined
  const eventRecord = event as Record<string, unknown>
  const contentKeys = [
    'error',
    'message',
    'result',
    'content',
    'arguments',
    'sections',
    'action',
    'reason',
    'source_files',
    'file_names',
    'output_path',
    'pdf_path',
    'section_count',
  ]
  for (const key of contentKeys) {
    const value = eventRecord[key]
    if (value !== undefined && value !== null && value !== '') return value
  }
  return undefined
}

const eventHasBody = (event: AgentTraceEvent) => {
  const value = processEventBodySource(event)
  return value !== undefined && value !== null && value !== ''
}

const processEventBody = (event: AgentTraceEvent) => {
  const value = processEventBodySource(event)
  if (value === undefined || value === null) return ''
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

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
    if (types.length > 0) {
      docTypes.value = types
      selectedDocTypes.value = selectedDocTypes.value.filter((type) => types.includes(type))
      const firstType = types[0]
      if (selectedDocTypes.value.length === 0 && firstType) selectedDocTypes.value = [firstType]
    }
  } catch {
    docTypes.value = ['需求规格说明书', '架构设计文档', '测试文档']
  }
  await restoreRunHistory()
})

onUnmounted(() => {
  clearPreviewFile()
  stopPolling()
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.docgen-layout {
  height: calc(100vh - $control-bar-height);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  color: #1e293b;
  position: relative;
  overflow: hidden;
}

.run-sidebar {
  padding: 16px;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 127, 212, 0.12);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
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
.action-btn:disabled,
.icon-button:disabled,
.composer-tool-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.button-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.loading-icon {
  animation: icon-spin 0.95s linear infinite;
}

@keyframes icon-spin {
  to {
    transform: rotate(360deg);
  }
}

.run-list {
  flex: 1;
  min-height: 0;
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
.status-terminate_requested {
  color: #007fd4;
}

.status-completed {
  color: #16a34a;
}

.status-failed {
  color: #dc2626;
}

.status-terminated {
  color: #f59e0b;
}

.docgen-main {
  height: 100%;
  min-height: 0;
  padding: 28px 32px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.new-doc-view {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
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
  width: 100%;
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
  width: min(920px, 100%);
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
.prompt-input {
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 12px;
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

.prompt-input {
  resize: vertical;
  padding: 10px 12px;
  line-height: 20px;
}

.doc-type-dropdown {
  position: relative;
  width: 38px;
  min-width: 38px;
}

.doc-type-trigger {
  width: 38px;
  min-width: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
}

.doc-type-chevron {
  width: 16px;
  height: 16px;
  color: #64748b;
}

.doc-type-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 6px);
  z-index: 20;
  min-width: 220px;
  padding: 6px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  display: grid;
  gap: 4px;
}

.prompt-input {
  min-height: 116px;
  resize: vertical;
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

.doc-composer .composer-tool-button,
.doc-composer .submit-button,
.doc-composer .doc-type-trigger,
.icon-button {
  width: 38px;
  min-width: 38px;
  height: 38px;
  min-height: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
  box-shadow: none;
}

.doc-composer .composer-tool-button:hover,
.doc-composer .submit-button:hover,
.doc-composer .doc-type-trigger:hover,
.icon-button:hover {
  background: #eef6ff;
}

.doc-type-control {
  padding-right: 4px;
  cursor: pointer;
}

.doc-type-control.doc-type-trigger {
  padding: 0;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.doc-type-option {
  min-height: 32px;
  padding: 0 10px;
  border-radius: 6px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  user-select: none;
}

.doc-type-option input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #007fd4;
}

.doc-type-option.checked {
  background: #e8f5ff;
  color: #005f9e;
}

.file-button {
  min-width: 180px;
  max-width: 100%;
  overflow: hidden;
}

.icon-button {
  width: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
}

.action-primary,
.action-download,
.action-preview {
  color: #007fd4;
  border-color: rgba(0, 127, 212, 0.32);
}

.action-terminate {
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.32);
}

.icon-button.action-preview,
.icon-button.action-download,
.icon-button.action-primary,
.icon-button.action-terminate {
  border-color: transparent;
  background: transparent;
}

.run-detail-view {
  width: min(1080px, 100%);
  height: 100%;
  min-height: 0;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.run-detail-header {
  flex: 0 0 auto;
  position: relative;
  z-index: 4;
  padding-bottom: 2px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.run-title-block {
  min-width: 0;
  flex: 1 1 auto;
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

.run-title-line {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.run-title-line .run-detail-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-error-inline {
  padding: 8px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

.run-detail-meta {
  margin-top: 5px;
  color: #94a3b8;
  font-family: Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

.run-title-side {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0;
}

.header-progress-actions {
  width: auto;
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.header-progress-rail {
  position: relative;
  min-width: 0;
  max-width: min(560px, 48vw);
  padding: 5px 4px 2px;
  overflow-x: auto;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 0;
  scrollbar-width: none;
}

.header-progress-rail::before,
.header-progress-rail::after {
  content: "";
  position: absolute;
  top: 12px;
  left: 33px;
  height: 2px;
  border-radius: 999px;
}

.header-progress-rail::before {
  right: 33px;
  background: #cbd5e1;
}

.header-progress-rail::after {
  z-index: 0;
  right: 33px;
  background:
    linear-gradient(
      90deg,
      #16a34a 0%,
      #16a34a calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--progress-ratio, 0) * 100%),
      transparent calc(var(--progress-ratio, 0) * 100%),
      transparent 100%
    );
}

.header-progress-rail.progress-completed::after {
  background: #16a34a;
}

.header-progress-rail::-webkit-scrollbar {
  display: none;
}

.header-progress-step {
  position: relative;
  z-index: 1;
  width: 58px;
  min-width: 58px;
  color: #64748b;
  display: grid;
  justify-items: center;
  gap: 4px;
}

.header-progress-dot {
  position: relative;
  z-index: 1;
  width: 13px;
  height: 13px;
  padding: 0;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  background: #ffffff;
}

.header-progress-label {
  max-width: 48px;
  overflow: hidden;
  color: #64748b;
  font-size: 10px;
  line-height: 1.1;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-progress-step.chapter-status-completed .header-progress-dot {
  border-color: #16a34a;
  background: #16a34a;
}

.header-progress-step.chapter-status-running .header-progress-dot {
  border-color: #007fd4;
  background: #007fd4;
}

.header-progress-step.active .header-progress-dot {
  box-shadow: 0 0 0 5px rgba(0, 127, 212, 0.14);
}

.run-state-icon {
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.run-state-icon .button-icon {
  width: 22px;
  height: 22px;
}

.run-state-running,
.run-state-terminate_requested {
  color: #007fd4;
}

.run-state-completed {
  color: #16a34a;
}

.run-state-failed,
.run-state-terminated {
  color: #dc2626;
}

.header-preview-button {
  flex: 0 0 auto;
  background: transparent;
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

.run-insight-panel {
  width: 100%;
  margin: 0 auto;
  display: grid;
  gap: 12px;
}

.run-overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.overview-tile {
  min-height: 72px;
  padding: 12px;
  box-sizing: border-box;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #ffffff;
  display: grid;
  align-content: center;
  gap: 6px;
}

.overview-tile span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.overview-tile strong {
  min-width: 0;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-progress-panel {
  width: 100%;
  margin: 0;
  padding: 14px;
  box-sizing: border-box;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.run-detail-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 4px 4px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 127, 212, 0.35) transparent;
}

.run-detail-scroll::-webkit-scrollbar {
  width: 6px;
}

.run-detail-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 127, 212, 0.35);
  border-radius: 999px;
}

.run-detail-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.chapter-progress-header {
  margin-bottom: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.chapter-progress-header span {
  color: #007fd4;
  font-size: 13px;
  font-weight: 800;
}

.chapter-progress-header h2 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 18px;
  line-height: 1.3;
}

.chapter-progress-rail {
  display: flex;
  align-items: flex-start;
  gap: 0;
  overflow-x: auto;
  padding: 10px 2px 14px;
}

.chapter-progress-step {
  position: relative;
  min-width: 92px;
  padding: 0 18px 0 0;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: grid;
  justify-items: start;
  gap: 6px;
}

.chapter-progress-step::after {
  content: "";
  position: absolute;
  top: 13px;
  left: 28px;
  right: 6px;
  height: 2px;
  background: #cbd5e1;
}

.chapter-progress-step:last-child::after {
  display: none;
}

.chapter-node {
  position: relative;
  z-index: 1;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #cbd5e1;
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.chapter-label {
  max-width: 82px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 700;
}

.chapter-status-completed .chapter-node,
.chapter-status-completed::after {
  background: #16a34a;
}

.chapter-status-running .chapter-node {
  background: #007fd4;
}

.chapter-progress-step.active .chapter-node {
  box-shadow: 0 0 0 4px rgba(0, 127, 212, 0.16);
}

.chapter-detail-panel {
  margin-top: 6px;
  padding-top: 12px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.chapter-detail-header {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chapter-detail-header span {
  color: #0f172a;
  font-size: 15px;
  font-weight: 800;
}

.chapter-detail-header strong {
  color: #64748b;
  font-size: 12px;
}

.chapter-menu-list {
  display: grid;
  gap: 12px;
}

.process-event-heading:focus-visible {
  outline: 3px solid rgba(0, 127, 212, 0.18);
  outline-offset: 3px;
}

.conversation-message-list {
  display: grid;
  gap: 8px;
}

.conversation-message {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.conversation-message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.conversation-message p {
  margin: 6px 0 0;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.chapter-process-list {
  display: grid;
  gap: 8px;
}

.chapter-process-list {
  margin-top: 0;
  padding: 10px;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.chapter-process-card {
  min-width: 0;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.chapter-process-card.active {
  border-color: rgba(0, 127, 212, 0.35);
  box-shadow: 0 0 0 3px rgba(0, 127, 212, 0.06);
}

.chapter-process-card.expanded {
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
}

.chapter-process-header {
  width: 100%;
  min-height: 42px;
  padding: 8px 12px;
  border: none;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: inherit;
  cursor: pointer;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chapter-process-card.expanded > .chapter-process-header {
  border-bottom: 1px solid rgba(0, 127, 212, 0.1);
}

.chapter-process-header:focus-visible {
  outline: 3px solid rgba(0, 127, 212, 0.18);
  outline-offset: 3px;
}

.chapter-process-header > div {
  min-width: 0;
}

.chapter-process-header span {
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
}

.chapter-process-header h2 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.35;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chapter-process-side {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.chapter-process-status,
.chapter-event-count {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.chapter-process-status {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.chapter-process-status-icon {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

.chapter-process-status-running .chapter-process-status-icon {
  animation: icon-spin 0.95s linear infinite;
}

.chapter-process-status-running {
  color: #007fd4;
}

.chapter-process-status-completed {
  color: #16a34a;
}

.chapter-process-status-pending {
  color: #64748b;
}

.chapter-process-chevron {
  width: 17px;
  height: 17px;
  color: #64748b;
}

.chapter-process-body {
  min-width: 0;
}

.chapter-final-result {
  margin: 10px 12px 12px;
  padding: 12px;
  border: 1px solid rgba(14, 116, 144, 0.2);
  border-radius: 8px;
  background: #ecfeff;
}

.chapter-final-result header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.chapter-final-result span {
  color: #0e7490;
  font-size: 12px;
  font-weight: 800;
}

.chapter-final-result h3 {
  margin: 3px 0 0;
  color: #164e63;
  font-size: 15px;
  line-height: 1.35;
}

.chapter-final-result time {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.chapter-final-result pre {
  margin: 10px 0 0;
  padding: 10px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #1e293b;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.detail-feed-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.detail-feed-column {
  min-width: 0;
  min-height: 260px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-feed-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-feed-header span {
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
}

.detail-feed-header h3 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.35;
}

.detail-feed-header strong {
  color: #64748b;
  font-size: 12px;
}

.process-event-list {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.process-event-list.compact {
  overflow: visible;
  padding-right: 0;
}

.process-event-list.unified {
  overflow: visible;
  padding: 10px 12px 12px;
  gap: 6px;
}

.process-event-card {
  border: none;
  border-radius: 8px;
  background: transparent;
  overflow: visible;
}

.process-event-list.unified .process-event-card {
  padding: 0;
  border: none;
  border-radius: 8px;
  background: transparent;
}

.process-event-list.unified .process-event-card.process-event-thought {
  box-shadow: none;
}

.process-event-list.unified .process-event-card.process-event-tool {
  box-shadow: none;
}

.process-event-list.unified .process-event-card.process-event-result {
  box-shadow: none;
}

.process-event-list.unified .process-event-card.process-event-status {
  box-shadow: none;
}

.process-event-list.unified .process-event-card.process-event-error {
  box-shadow: none;
}

.process-event-card.stream-active {
  box-shadow: none;
}

.process-event-list.unified .process-event-card.stream-active {
  box-shadow: none;
}

.process-event-heading {
  width: 100%;
  min-height: 40px;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.process-event-heading:hover {
  background: rgba(0, 127, 212, 0.05);
}

.process-event-card.is-open > .process-event-heading {
  background: rgba(0, 127, 212, 0.06);
}

.process-event-card.process-event-thought > .process-event-heading {
  background: #f0f9ff;
}

.process-event-card.process-event-tool > .process-event-heading {
  background: #f5f3ff;
}

.process-event-card.process-event-result > .process-event-heading {
  background: #f0fdf4;
}

.process-event-card.process-event-status > .process-event-heading {
  background: #f8fafc;
}

.process-event-card.process-event-error > .process-event-heading {
  background: #fef2f2;
}

.process-event-card.process-event-thought > .process-event-heading:hover,
.process-event-card.process-event-thought.is-open > .process-event-heading {
  background: #e0f2fe;
}

.process-event-card.process-event-tool > .process-event-heading:hover,
.process-event-card.process-event-tool.is-open > .process-event-heading {
  background: #ede9fe;
}

.process-event-card.process-event-result > .process-event-heading:hover,
.process-event-card.process-event-result.is-open > .process-event-heading {
  background: #dcfce7;
}

.process-event-card.process-event-status > .process-event-heading:hover,
.process-event-card.process-event-status.is-open > .process-event-heading {
  background: #f1f5f9;
}

.process-event-card.process-event-error > .process-event-heading:hover,
.process-event-card.process-event-error.is-open > .process-event-heading {
  background: #fee2e2;
}

.process-event-title-block {
  min-width: 0;
  flex: 1 1 auto;
}

.process-event-kind-label {
  margin-bottom: 2px;
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  display: inline-flex;
}

.process-event-kind-tool {
  color: #7c3aed;
}

.process-event-kind-result {
  color: #15803d;
}

.process-event-kind-status {
  color: #64748b;
}

.process-event-kind-error {
  color: #dc2626;
}

.process-event-summary {
  margin: 4px 0 0;
  padding: 0;
  overflow: hidden;
  border-radius: 0;
  background: transparent;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.process-event-chevron {
  width: 17px;
  height: 17px;
  color: #64748b;
}

.process-event-entry-list {
  max-height: min(420px, 46vh);
  margin: 4px 0 8px;
  padding: 8px 8px 8px 12px;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 127, 212, 0.35) transparent;
}

.process-event-entry-panel {
  border-radius: 8px;
  background: #f8fafc;
  overflow: hidden;
}

.process-event-entry-list::-webkit-scrollbar {
  width: 6px;
}

.process-event-entry-list::-webkit-scrollbar-thumb {
  background: rgba(0, 127, 212, 0.35);
  border-radius: 999px;
}

.process-event-entry-list::-webkit-scrollbar-track {
  background: transparent;
}

.process-event-entry {
  padding: 9px 10px;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.process-event-entry + .process-event-entry {
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.process-event-entry-thought {
  border-color: rgba(0, 127, 212, 0.18);
  background: rgba(240, 249, 255, 0.72);
}

.process-event-entry-tool {
  border-color: rgba(124, 58, 237, 0.2);
  background: rgba(245, 243, 255, 0.72);
}

.process-event-entry-result {
  border-color: rgba(22, 163, 74, 0.18);
  background: rgba(240, 253, 244, 0.72);
}

.process-event-entry-error {
  border-color: rgba(220, 38, 38, 0.22);
  background: rgba(254, 242, 242, 0.72);
}

.process-event-entry-head {
  min-height: 20px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.process-event-entry-title {
  min-width: 0;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.process-event-entry-title strong {
  color: #0f172a;
}

.process-event-entry-title span {
  color: #64748b;
}

.process-event-entry-head time {
  flex: 0 0 auto;
  font-weight: 700;
}

.process-event-entry .process-event-body {
  margin-top: 8px;
}

.result-empty {
  min-height: 78px;
  margin: 10px 12px 12px;
  padding: 14px;
  box-sizing: border-box;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.result-empty.waiting {
  border-color: rgba(0, 127, 212, 0.22);
  background: #f0f9ff;
  color: #007fd4;
}

.process-event-error {
  background: #fef2f2;
}

.process-event-meta {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.process-event-current-status,
.process-event-entry-status {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.process-status-icon {
  width: 15px;
  height: 15px;
  fill: currentColor;
}

.process-event-current-started {
  color: #64748b;
}

.process-event-current-running {
  color: #007fd4;
}

.process-event-current-completed {
  color: #16a34a;
}

.process-event-current-failed {
  color: #dc2626;
}

.process-event-entry-title .process-event-entry-status.process-event-current-started {
  color: #64748b;
}

.process-event-entry-title .process-event-entry-status.process-event-current-running {
  color: #007fd4;
}

.process-event-entry-title .process-event-entry-status.process-event-current-completed {
  color: #16a34a;
}

.process-event-entry-title .process-event-entry-status.process-event-current-failed {
  color: #dc2626;
}

.process-event-loading {
  width: 15px;
  height: 15px;
  color: #007fd4;
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
  min-width: 0;
  margin: 0;
  color: #0f172a;
  font-size: 14px;
  line-height: 1.45;
  font-weight: 800;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-body {
  margin: 8px 0 0;
  padding: 10px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-body.prose {
  color: #1e293b;
  font-family: inherit;
  font-size: 13px;
}

.process-virtual-footer {
  width: 100%;
  min-height: 42px;
  border: none;
  border-top: 1px dashed rgba(0, 127, 212, 0.18);
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.process-virtual-footer:hover {
  color: #007fd4;
  background: #f0f9ff;
}

.process-event-body.streaming::after {
  content: "";
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 3px;
  vertical-align: -2px;
  background: #007fd4;
  animation: stream-caret 0.9s steps(2, start) infinite;
}

@keyframes stream-caret {
  50% {
    opacity: 0;
  }
}

.bottom-operation-bar {
  position: relative;
  flex: 0 0 auto;
  z-index: 8;
  width: 100%;
  margin: 0;
  padding: 14px 0 0;
  box-sizing: border-box;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
  display: flex;
  justify-content: center;
}

.generation-control-card {
  padding: 10px 12px;
}

.generation-control-main {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.generation-control-text {
  min-width: 0;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.generation-control-text .button-icon {
  color: #007fd4;
}

.bottom-operation-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.bottom-run-finished {
  min-height: 48px;
  padding: 12px;
  box-sizing: border-box;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
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
  padding: 8px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
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
  width: min(760px, 94vw);
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

.drawer-header > div {
  min-width: 0;
  flex: 1;
}

.drawer-back-button {
  flex: 0 0 auto;
}

.drawer-back-icon {
  transform: rotate(180deg);
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
  flex: 1;
  min-height: 0;
  padding: 16px 18px 22px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-drawer-previewing .drawer-body {
  padding: 0;
  overflow: hidden;
}

.final-output-card {
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 10px;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.preview-file-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.preview-file-actions .action-btn {
  min-height: 34px;
  padding: 0 10px;
}

.drawer-preview-panel {
  flex: 1;
  min-height: 0;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.drawer-preview-full {
  height: 100%;
  min-height: 0;
  border: none;
  border-radius: 0;
  background: #ffffff;
}

.drawer-preview-panel header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.drawer-preview-panel header span {
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
}

.drawer-preview-panel header h3 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.35;
  word-break: break-all;
}

.drawer-preview-empty,
.drawer-preview-error {
  flex: 1;
  min-height: 0;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.drawer-preview-error {
  border-color: rgba(220, 38, 38, 0.22);
  color: #dc2626;
}

.drawer-pdf-preview,
.drawer-markdown-preview {
  flex: 1;
  min-height: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #ffffff;
}

.drawer-pdf-preview {
  width: 100%;
}

.drawer-markdown-preview {
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: #1e293b;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.65;
  scrollbar-width: none;
}

.drawer-markdown-preview::-webkit-scrollbar {
  display: none;
}

.drawer-markdown-preview :deep(h1),
.drawer-markdown-preview :deep(h2),
.drawer-markdown-preview :deep(h3) {
  margin: 18px 0 10px;
  color: #0f172a;
  line-height: 1.35;
}

.drawer-markdown-preview :deep(h1:first-child),
.drawer-markdown-preview :deep(h2:first-child),
.drawer-markdown-preview :deep(h3:first-child) {
  margin-top: 0;
}

.drawer-markdown-preview :deep(p),
.drawer-markdown-preview :deep(ul),
.drawer-markdown-preview :deep(ol) {
  margin: 8px 0;
}

.drawer-markdown-preview :deep(table) {
  width: 100%;
  margin: 12px 0;
  border-collapse: collapse;
  font-size: 12px;
}

.drawer-markdown-preview :deep(th),
.drawer-markdown-preview :deep(td) {
  padding: 7px 8px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  vertical-align: top;
}

.drawer-markdown-preview :deep(th) {
  background: #f8fafc;
  font-weight: 800;
}

.drawer-markdown-preview :deep(code) {
  padding: 2px 5px;
  border-radius: 4px;
  background: #f1f5f9;
  font-family: Consolas, monospace;
  font-size: 12px;
}

.drawer-markdown-preview :deep(pre) {
  padding: 10px;
  overflow-x: auto;
  overflow-y: visible;
  border-radius: 6px;
  background: #0f172a;
  color: #e2e8f0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.drawer-markdown-preview :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
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
  margin: 8px 0 0;
  padding: 8px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #475569;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

@media (max-width: 860px) {
  .docgen-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
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

  .run-overview-grid,
  .detail-feed-grid {
    grid-template-columns: 1fr;
  }

  .agent-title {
    font-size: 36px;
  }

  .run-detail-header,
  .composer-actions,
  .bottom-operation-actions,
  .generation-control-main {
    align-items: stretch;
    flex-direction: column;
  }

  .run-title-side {
    width: 100%;
    justify-content: flex-end;
  }

  .header-progress-actions {
    width: 100%;
  }

  .header-progress-rail {
    flex: 1 1 auto;
    max-width: calc(100% - 52px);
    justify-content: flex-start;
  }

  .result-drawer {
    width: 100vw;
  }

  .preview-file-row,
  .preview-file-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .file-button,
  .action-btn,
  .doc-type-select {
    width: 100%;
  }

  .doc-type-dropdown {
    width: 38px;
    min-width: 38px;
    align-self: flex-end;
  }

  .doc-type-menu {
    left: auto;
    right: 0;
    width: auto;
    min-width: 220px;
    box-sizing: border-box;
  }

  .doc-composer .submit-button,
  .doc-composer .composer-tool-button,
  .doc-composer .doc-type-trigger {
    width: 38px;
    align-self: flex-end;
  }

  .composer-file-hint {
    align-self: stretch;
  }
}
</style>
