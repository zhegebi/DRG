import { computed, onMounted, onUnmounted, ref } from 'vue'
import { marked } from 'marked'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiChevronDown,
  mdiChevronRight,
  mdiChevronUp,
  mdiClockOutline,
  mdiClose,
  mdiDownload,
  mdiFileDocumentOutline,
  mdiFileEyeOutline,
  mdiFileImageOutline,
  mdiFilePdfBox,
  mdiFilePlusOutline,
  mdiFormatListBulletedType,
  mdiImageMultipleOutline,
  mdiLoading,
  mdiMenuDown,
  mdiPlus,
  mdiProgressClock,
  mdiSend,
  mdiStopCircleOutline,
} from '@mdi/js'
import {
  activeRunStatusSet,
  deleteRun,
  downloadDocImage,
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
  type GenerationMode,
  type RunTrace,
} from './dogen_utils'

export type ProcessEventKind = 'thought' | 'tool' | 'result' | 'status' | 'error'
export type ProcessExecutionState = 'started' | 'running' | 'completed' | 'failed'
export type ChapterProgressStatus = 'pending' | 'running' | 'completed'
export type RunStatusKind = 'running' | 'completed' | 'stopped' | 'error'

export interface ChapterProgressItem {
  index: number
  title: string
  status: ChapterProgressStatus
}

export interface ChapterProcessGroup {
  key: string
  title: string
  index: number
  status: ChapterProgressStatus
  events: AgentTraceEvent[]
  emptyText: string
}

export interface ProcessEventDisplayGroup {
  key: string
  title: string
  kind: ProcessEventKind
  state: ProcessExecutionState
  events: AgentTraceEvent[]
}

export interface ProcessEventDetailItem {
  label: string
  value: string
  wide?: boolean
}

export interface ConversationMessageItem {
  key: string
  label: string
  content: string
  time: string
}

export interface ConversationTaskItem {
  run: RunTrace
  messages: ConversationMessageItem[]
  activeChapterTitle: string
  groups: ChapterProcessGroup[]
}

// ── Singleton state ──────────────────────────────────────────────
const docTypes = ref<DocType[]>(['需求规格说明书', '架构设计文档', '测试文档'])
const selectedDocTypes = ref<DocType[]>(['需求规格说明书'])
const defaultGenerationModeConfig: { value: GenerationMode, label: string, description: string } = {
  value: 'structured',
  label: '提示词+文件+规范',
  description: '结合预定义 output 规范生成完整文档',
}
const generationModes: Array<{ value: GenerationMode, label: string, description: string }> = [
  defaultGenerationModeConfig,
  { value: 'prompt_only', label: '提示词+文件', description: '只按提示词和上传文件撰写' },
]
const selectedGenerationMode = ref<GenerationMode>('structured')
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
const generationModeMenuOpen = ref(false)
const previewFileKind = ref<'markdown' | 'pdf' | 'image' | ''>('')
const previewFileUrl = ref('')
const previewFileText = ref('')
const isPreviewLoading = ref(false)
const previewError = ref('')
const imageDownloadMenuOpen = ref(false)
const expandedChapterIds = ref<string[]>([])
let userHasToggledChapters = false
const expandedProcessEventIds = ref<string[]>([])
const processEventVisibleCounts = ref<Record<string, number>>({})
const processEventLoadingKeys = ref<Record<string, boolean>>({})
const processEntryVisibleCounts = ref<Record<string, number>>({})
const processEntryLoadingKeys = ref<Record<string, boolean>>({})

let pollTimer: ReturnType<typeof setInterval> | null = null
let traceStreamController: AbortController | null = null
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

// ── Utility functions ────────────────────────────────────────────
const basename = (path?: string | null) => {
  if (!path) return ''
  return path.split(/[\\/]/).pop() || ''
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

const displayTaskTitle = (run: RunTrace) => {
  return run.task_title || run.doc_type || '文档生成任务'
}

const truncateTitle = (value: string, max = 10) => {
  const clean = (value || '文档生成任务').trim()
  return clean.length > max ? `${clean.slice(0, max)}…` : clean
}

const normalizedPhase = (phase: string) => {
  if (phase.startsWith('generate_section:')) return 'generate_sections'
  return phase || 'run'
}

const eventSectionTitle = (event: AgentTraceEvent) => {
  if (event.phase?.startsWith('generate_section:')) return event.phase.slice('generate_section:'.length)
  return ''
}

const phaseDisplayName = (phase: string) => {
  const normalized = normalizedPhase(phase || 'run')
  return phaseLabelMap[normalized] || normalized
}

const formatEventValue = (value: unknown) => {
  if (value === undefined || value === null || value === '') return ''
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value)) return value.filter(Boolean).join('、')
  return String(value)
}

// ── Local storage helpers ────────────────────────────────────────
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

const fileNameFromRun = (run: RunTrace, extension: 'md' | 'pdf') => {
  const fromPath = basename(extension === 'pdf' ? run.pdf_path : run.output_path)
  if (fromPath) return fromPath
  const stamp = (run.created_at || new Date().toISOString()).replace(/[:T-]/g, '').slice(0, 12)
  return `${run.doc_type || '文档'}_${stamp}.${extension}`
}

// ── Event helpers ─────────────────────────────────────────────────
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

const markerOnlyEventTypes = new Set([
  'phase_started',
  'phase_completed',
  'section_started',
  'section_completed',
  'section_saved_in_memory',
  'llm_request',
])

const executionContentEventTypes = new Set([
  'reasoning',
  'assistant_message',
  'tool_calls_planned',
  'tool_call',
  'tool_result',
  'document_stitched',
  'table_repaired',
  'format_repaired',
  'error',
])

const executionPayloadKeys = [
  'error',
  'message',
  'result',
  'content',
  'arguments',
  'sections',
  'reason',
  'source_files',
  'file_names',
  'output_path',
  'pdf_path',
  'section_count',
]

const hasExecutionPayload = (event: AgentTraceEvent) => {
  const eventRecord = event as Record<string, unknown>
  return executionPayloadKeys.some((key) => {
    const value = eventRecord[key]
    if (value === undefined || value === null || value === '') return false
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
    return true
  })
}

const processEventHasExecutionContent = (event: AgentTraceEvent) => {
  if (markerOnlyEventTypes.has(event.type)) return false
  if (event.error) return true
  if (executionContentEventTypes.has(event.type) || event.type.includes('tool')) return true
  return hasExecutionPayload(event)
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

const processEventContextTitle = (event: AgentTraceEvent, group?: ChapterProcessGroup) => {
  return event.title
    || eventSectionTitle(event)
    || group?.title
    || phaseDisplayName(event.phase || 'run')
}

const withEventContext = (label: string, context?: string) => {
  return context ? `${label}：${context}` : label
}

const withEventDetail = (label: string, detail?: string, context?: string) => {
  const title = detail ? `${label}：${detail}` : label
  return context && context !== detail ? `${title}（${context}）` : title
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
  const phaseName = phaseDisplayName(event.phase || 'run')
  const contextTitle = processEventContextTitle(event, group)
  if (event.type === 'phase_started') return `${phaseName}开始`
  if (event.type === 'phase_completed') return `${phaseName}完成`
  if (event.type === 'llm_request') {
    return withEventContext('模型请求', contextTitle)
  }
  if (event.type === 'reasoning') {
    return withEventContext('模型思考', contextTitle)
  }
  if (event.type === 'assistant_message') {
    return withEventContext('模型输出', contextTitle)
  }
  if (event.type === 'section_started') {
    return withEventContext('章节开始', contextTitle)
  }
  if (event.type === 'section_completed') {
    return withEventContext('章节完成', contextTitle)
  }
  if (event.type === 'section_saved_in_memory') {
    return withEventContext('章节暂存', contextTitle)
  }
  if (event.type === 'tool_calls_planned') {
    const tools = Array.isArray(event.tools) ? event.tools.filter(Boolean).join('、') : ''
    return withEventDetail('计划工具', tools, contextTitle)
  }
  if (event.type === 'tool_call') {
    return withEventDetail('工具调用', event.name, contextTitle)
  }
  if (event.type === 'tool_result') {
    return withEventDetail('工具返回', event.name, contextTitle)
  }
  return processEventTitle(event, group)
}

const isToolProcessEvent = (event: AgentTraceEvent) => {
  return event.type === 'tool_calls_planned'
    || event.type === 'tool_call'
    || event.type === 'tool_result'
}

const eventToolCallId = (event: AgentTraceEvent) => {
  return typeof event.tool_call_id === 'string' ? event.tool_call_id : ''
}

const processToolBatchTitle = (event: AgentTraceEvent, batchNo: number) => {
  const turnSuffix = event.turn !== undefined ? ` · Turn ${event.turn}` : ''
  const tools = Array.isArray(event.tools) ? event.tools.filter(Boolean).join('、') : ''
  const detail = tools || event.name || ''
  return detail
    ? `工具调用批次 ${batchNo}${turnSuffix}：${detail}`
    : `工具调用批次 ${batchNo}${turnSuffix}`
}

const processEventPhaseKey = (event: AgentTraceEvent, group: ChapterProcessGroup) => {
  return normalizedPhase(event.phase || (group.index ? `generate_section:${group.title}` : 'run'))
}

const processEventGroupKey = (event: AgentTraceEvent, group: ChapterProcessGroup) => {
  const phase = processEventPhaseKey(event, group)
  const turn = event.turn !== undefined ? `:turn:${event.turn}` : ''
  return `phase:${phase}${turn}:kind:${processEventKind(event)}`
}

const processEventGroupTitle = (event: AgentTraceEvent, group: ChapterProcessGroup) => {
  const kind = processEventKind(event)
  const phaseName = phaseDisplayName(event.phase || (group.index ? `generate_section:${group.title}` : 'run'))
  const turnSuffix = event.turn !== undefined ? ` · Turn ${event.turn}` : ''
  if (kind === 'thought') return group.index ? `模型思考${turnSuffix}` : `模型思考：${phaseName}${turnSuffix}`
  if (kind === 'tool') return `${toolEventTitle(event)}${turnSuffix}`
  if (kind === 'error') return '异常信息'
  if (kind === 'result') {
    if (event.type === 'document_stitched') return '文档拼接结果'
    if (event.type === 'format_repaired' || event.type === 'table_repaired') return '格式修复记录'
    if (event.type === 'assistant_message') return group.index ? `模型输出${turnSuffix}` : `模型输出：${phaseName}${turnSuffix}`
    if (event.type.includes('section')) return group.index ? '章节生成结果' : '章节生成结果'
    return `${phaseName}结果${turnSuffix}`
  }
  if (event.type === 'phase_completed') return `${phaseName}完成`
  if (event.type === 'phase_started') return `${phaseName}开始`
  if (event.type === 'llm_request') return `模型请求${turnSuffix}`
  if (event.type === 'section_started') return '章节开始'
  return '执行进度'
}

const processEventBodySource = (event: AgentTraceEvent) => {
  if (event.type === 'section_completed') return undefined
  const eventRecord = event as Record<string, unknown>
  const statusSummary = processStatusEventBody(eventRecord)
  if (statusSummary) return statusSummary
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

const processStatusEventDetails = (eventRecord: Record<string, unknown>): ProcessEventDetailItem[] => {
  const items: ProcessEventDetailItem[] = []
  const phase = phaseDisplayName(formatEventValue(eventRecord.phase || 'run'))
  const pushDetail = (label: string, value: unknown, wide = false) => {
    const formatted = formatEventValue(value)
    if (formatted) items.push({ label, value: formatted, wide })
  }
  if (eventRecord.type === 'llm_request') {
    pushDetail('阶段', phase)
    if (eventRecord.turn !== undefined) pushDetail('轮次', `Turn ${eventRecord.turn}`)
    pushDetail('可调用工具', eventRecord.has_tools)
    pushDetail('动作', eventRecord.action, true)
  } else if (eventRecord.type === 'phase_started') {
    if (eventRecord.message) {
      pushDetail('阶段', phase)
      pushDetail('说明', eventRecord.message, true)
    }
  } else if (eventRecord.type === 'phase_completed') {
    const phaseCompletedItems: ProcessEventDetailItem[] = []
    const pushPhaseCompletedDetail = (label: string, value: unknown, wide = false) => {
      const formatted = formatEventValue(value)
      if (formatted) phaseCompletedItems.push({ label, value: formatted, wide })
    }
    const detailKeys = [
      ['message', '说明'],
      ['section_count', '章节数'],
      ['retry', '重试轮次'],
      ['issues_found', '发现问题'],
      ['markdown_path', 'Markdown'],
      ['pdf_path', 'PDF'],
    ] as const
    for (const [key, label] of detailKeys) {
      pushPhaseCompletedDetail(label, eventRecord[key], key === 'message' || key.endsWith('_path'))
    }
    if (phaseCompletedItems.length) {
      pushDetail('阶段', phase)
      items.push(...phaseCompletedItems)
    }
  }
  return items
}

const processStatusEventBody = (eventRecord: Record<string, unknown>) => {
  return processStatusEventDetails(eventRecord)
    .map((item) => `${item.label}：${item.value}`)
    .join('\n')
}

// ── Composable ────────────────────────────────────────────────────
export function useDocGen() {
  // ── Computed ──────────────────────────────────────────────────
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

  const selectedGenerationModeConfig = computed(() => {
    return generationModes.find((mode) => mode.value === selectedGenerationMode.value) || defaultGenerationModeConfig
  })

  const conversationRuns = computed(() => {
    return selectedRun.value ? [selectedRun.value] : []
  })

  const statusRun = computed(() => {
    const runs = conversationRuns.value
    return runs.length ? runs[runs.length - 1] : selectedRun.value
  })

  const previewFileTitle = computed(() => {
    if (previewFileKind.value === 'pdf') return basename(selectedRun.value?.pdf_path) || 'PDF 预览'
    if (previewFileKind.value === 'markdown') return basename(selectedRun.value?.output_path) || 'Markdown 预览'
    if (previewFileKind.value === 'image') return '图片预览'
    return '未选择文件'
  })

  const docImageUrl = (path: string) => {
    let decodedPath = path
    try {
      decodedPath = decodeURIComponent(path)
    } catch {
      decodedPath = path
    }
    return `/api/docgen_agent/documents/${encodeURIComponent(decodedPath)}/download`
  }

  const isLocalImagePath = (path: string) => {
    const value = path.trim().toLowerCase()
    return Boolean(value)
      && !value.startsWith('http://')
      && !value.startsWith('https://')
      && !value.startsWith('data:')
      && !value.startsWith('blob:')
      && !value.startsWith('/api/')
  }

  const previewMarkdownHtml = computed(() => {
    const html = marked.parse(previewFileText.value || '', { async: false }) as string
    return html.replace(/<img\b([^>]*?)\bsrc=(["'])(.*?)\2([^>]*)>/gi, (
      full: string,
      before: string,
      quote: string,
      src: string,
      after: string,
    ) => {
      if (!isLocalImagePath(src)) return full
      return `<img${before}src=${quote}${docImageUrl(src)}${quote}${after}>`
    })
  })

  const previewImagePaths = computed(() => {
    const text = previewFileText.value
    if (!text) return [] as { path: string; alt: string }[]
    const regex = /!\[([^\]]*)\]\(([^)]+)\)/g
    const results: { path: string; alt: string }[] = []
    let match: RegExpExecArray | null
    while ((match = regex.exec(text)) !== null) {
      const path = match[2]
      if (!path) continue
      if (!isLocalImagePath(path)) continue
      if (results.some((r) => r.path === path)) continue
      const alt = (match[1] || path.split('/').pop() || 'image') as string
      results.push({ path, alt })
    }
    return results
  })

  // ── Run progress helpers ──────────────────────────────────────
  const processEventTypes = new Set([
    'reasoning', 'phase_started', 'llm_request', 'tool_calls_planned',
    'tool_call', 'tool_result', 'assistant_message', 'section_started',
    'section_completed', 'section_saved_in_memory', 'document_stitched',
    'format_repaired', 'phase_completed', 'error',
  ])

  const processEventsForRun = (run?: RunTrace | null) => {
    if (!run) return []
    return run.events.filter((event) => {
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
        return event.type === 'section_completed' || event.type === 'section_saved_in_memory'
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

  const isHeaderProgressFlowing = computed(() => {
    return Boolean(statusRun.value && activeRunStatusSet.has(statusRun.value.status))
      && !isHeaderProgressCompleted.value
      && chapterProgressItems.value.some((item) => item.status === 'running')
  })

  // ── Chapter process groups ────────────────────────────────────
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

  // ── Chapter expansion ─────────────────────────────────────────
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
    if (userHasToggledChapters) return
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
    userHasToggledChapters = true
    const key = chapterGroupExpansionKey(runId, group)
    if (expandedChapterIds.value.includes(key)) {
      expandedChapterIds.value = expandedChapterIds.value.filter((item) => item !== key)
    } else {
      expandedChapterIds.value = [...expandedChapterIds.value, key]
    }
  }

  // ── Process event display groups ──────────────────────────────
  const processEventDisplayGroups = (group: ChapterProcessGroup): ProcessEventDisplayGroup[] => {
    const groups: ProcessEventDisplayGroup[] = []
    const indexByKey = new Map<string, ProcessEventDisplayGroup>()
    const latestChapterEvent = group.events[group.events.length - 1]
    const pendingDirectToolKeys = new Map<string, string>()
    let activeToolBatchKey = ''
    let activeToolBatchTitle = ''
    let toolBatchNo = 0
    for (const event of group.events) {
      let key = processEventGroupKey(event, group)
      let title = processEventGroupTitle(event, group)
      const isToolEvent = isToolProcessEvent(event)
      if (isToolEvent) {
        const phase = processEventPhaseKey(event, group)
        const toolCallId = eventToolCallId(event)
        const directKey = `${event.name || 'tool'}:${phase}`
        if (event.type === 'tool_calls_planned') {
          toolBatchNo += 1
          activeToolBatchKey = `phase:${phase}:tool-batch:turn:${event.turn ?? toolBatchNo}`
          activeToolBatchTitle = processToolBatchTitle(event, toolBatchNo)
          key = activeToolBatchKey
          title = activeToolBatchTitle
        } else if (activeToolBatchKey) {
          key = activeToolBatchKey
          title = activeToolBatchTitle
        } else if (toolCallId) {
          toolBatchNo += event.type === 'tool_call' ? 1 : 0
          key = `phase:${phase}:tool-call:${toolCallId}`
          title = processToolBatchTitle(event, Math.max(toolBatchNo, 1))
        } else if (event.type === 'tool_call') {
          toolBatchNo += 1
          key = `phase:${phase}:direct-tool:${toolBatchNo}`
          pendingDirectToolKeys.set(directKey, key)
          title = processToolBatchTitle(event, toolBatchNo)
        } else {
          key = pendingDirectToolKeys.get(directKey) || `phase:${phase}:direct-tool:${toolBatchNo + 1}`
          pendingDirectToolKeys.delete(directKey)
          title = processToolBatchTitle(event, Math.max(toolBatchNo, 1))
        }
      } else if (event.type === 'llm_request') {
        activeToolBatchKey = ''
        activeToolBatchTitle = ''
      }
      let item = indexByKey.get(key)
      if (!item) {
        item = {
          key,
          title,
          kind: processEventKind(event),
          state: processEventState(event),
          events: [],
        }
        indexByKey.set(key, item)
        groups.push(item)
      }
      item.events.push(event)
      if (!isToolEvent) item.title = title
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

  const isStreamingEventForRun = (run: RunTrace, event: AgentTraceEvent) => {
    if (!activeRunStatusSet.has(run.status)) return false
    const latest = run.events[run.events.length - 1]
    return Boolean(event.streaming && latest?.id === event.id)
  }

  const isStreamingEventGroup = (run: RunTrace, group: ProcessEventDisplayGroup) => {
    return group.events.some((event) => isStreamingEventForRun(run, event))
  }

  const processEventGroupVisualState = (
    run: RunTrace,
    group: ProcessEventDisplayGroup,
  ): ProcessExecutionState => {
    return isStreamingEventGroup(run, group) ? 'running' : group.state
  }

  // ── Process event visibility / pagination ─────────────────────
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

  // ── Process event expansion ──────────────────────────────────
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

  // ── Process entry helpers ─────────────────────────────────────
  const processEntryChapterKey = (event: AgentTraceEvent) => {
    return event.title || eventSectionTitle(event) || ''
  }

  const shouldShowProcessEventEntry = (_event: AgentTraceEvent) => {
    return true
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

  // ── Conversation task items ──────────────────────────────────
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

  const conversationTaskItems = computed<ConversationTaskItem[]>(() => {
    return conversationRuns.value.map((run) => ({
      run,
      messages: runConversationMessages(run),
      activeChapterTitle: activeChapterTitleForRun(run),
      groups: chapterProcessGroupsForRun(run),
    }))
  })

  // ── Run status display ───────────────────────────────────────
  const runStatusKind = (status: string): RunStatusKind => {
    if (status === 'completed') return 'completed'
    if (status === 'failed') return 'error'
    if (status === 'terminated' || status === 'terminate_requested') return 'stopped'
    return 'running'
  }

  const runStatusClass = (status: string) => {
    return `status-${runStatusKind(status)}`
  }

  const runStateClass = (status: string) => {
    return `run-state-${runStatusKind(status)}`
  }

  const runStatusIcon = (status: string) => {
    const kind = runStatusKind(status)
    if (kind === 'completed') return mdiCheckCircleOutline
    if (kind === 'error') return mdiAlertCircleOutline
    if (kind === 'stopped') return mdiStopCircleOutline
    return mdiProgressClock
  }

  const headerRunStatusIcon = computed(() => {
    return statusRun.value ? runStatusIcon(statusRun.value.status) : mdiProgressClock
  })

  const statusTextValue = (value: unknown) => {
    if (value === undefined || value === null || value === '') return ''
    if (typeof value === 'string') return value
    return JSON.stringify(value)
  }

  const latestRunEvent = (run: RunTrace) => {
    return [...run.events].reverse().find((event) => event.type !== 'tool_calls_planned')
  }

  const runErrorText = (run: RunTrace) => {
    const errorEvent = [...run.events].reverse().find((event) => {
      return event.type === 'error' || Boolean(event.error)
    })
    return statusTextValue(run.error)
      || statusTextValue(errorEvent?.error)
      || statusTextValue(errorEvent?.message)
      || '未返回具体错误'
  }

  const runProgressText = (run: RunTrace) => {
    const latest = latestRunEvent(run)
    const chapter = activeChapterTitleForRun(run)
    const phase = latest?.phase ? phaseDisplayName(latest.phase) : ''
    const eventTitle = latest ? processEventTitle(latest) : ''
    const parts = [
      chapter ? `章节：${chapter}` : '',
      phase ? `阶段：${phase}` : '',
      eventTitle ? `事件：${eventTitle}` : '',
    ].filter(Boolean)
    return parts.length ? parts.join(' · ') : '等待执行'
  }

  const runStatusTooltipText = (run?: RunTrace | null) => {
    if (!run) return ''
    const kind = runStatusKind(run.status)
    if (kind === 'completed') return '已完成'
    if (kind === 'error') return `错误：${runErrorText(run)}`
    if (kind === 'stopped') {
      const detail = runErrorText(run)
      return detail && detail !== '未返回具体错误' ? `中止：${detail}` : '中止'
    }
    if (activeRunStatusSet.has(run.status)) return `进行中：${runProgressText(run)}`
    return runStatusLabelMap[run.status] || '进行中'
  }

  // ── Process event entry helpers ──────────────────────────────
  const isRequestRecordEvent = (event: AgentTraceEvent) => {
    return event.type === 'llm_request'
  }

  const processRequestTurnLabel = (event: AgentTraceEvent) => {
    return `Turn ${event.turn ?? 0}`
  }

  const processRequestRecordContext = (event: AgentTraceEvent, group?: ChapterProcessGroup) => {
    const eventRecord = event as Record<string, unknown>
    const parts: string[] = []
    const phase = phaseDisplayName(formatEventValue(eventRecord.phase || 'run'))
    if (phase) parts.push(phase)
    const context = processEventContextTitle(event, group)
    if (context && context !== phase) parts.push(context)
    if (eventRecord.has_tools !== undefined) parts.push(`工具：${formatEventValue(eventRecord.has_tools)}`)
    if (eventRecord.action) parts.push(formatEventValue(eventRecord.action))
    return parts.filter(Boolean).join(' · ')
  }

  const processEventGroupStatusText = (group: ProcessEventDisplayGroup, run?: RunTrace) => {
    const state = run ? processEventGroupVisualState(run, group) : group.state
    if (group.kind === 'status' && state === 'completed') {
      if (group.title.includes('请求')) return '请求已返回'
      if (group.title.includes('完成')) return '阶段已完成'
      return '已记录'
    }
    return processExecutionStatusLabel(state)
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

  const processEventDetailItems = (event: AgentTraceEvent) => {
    return processStatusEventDetails(event as Record<string, unknown>)
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

  const shouldShowProcessEventGroupStatus = (group: ProcessEventDisplayGroup) => {
    return group.events.some(processEventHasExecutionContent)
  }

  const shouldShowProcessEventEntryStatus = (event: AgentTraceEvent) => {
    return processEventHasExecutionContent(event)
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

  // ── Core actions ──────────────────────────────────────────────
  const clearPreviewFile = () => {
    if (previewFileUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(previewFileUrl.value)
    }
    imageDownloadMenuOpen.value = false
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

  const handlePreviewFile = async (kind: 'markdown' | 'pdf') => {
    if (!selectedRunId.value || !canPreviewRunFile(kind)) return
    isPreviewLoading.value = true
    previewError.value = ''
    clearPreviewFile()
    previewFileKind.value = kind
    try {
      if (kind === 'pdf') {
        // Fetch backend-processed HTML for preview (PDF rendering done by browser print)
        const url = `/api/docgen_agent/task/${selectedRunId.value}/html`
        const token = localStorage.getItem('access_token')
        const resp = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const html = await resp.text()
        previewFileUrl.value = html
      } else {
        const blob = await fetchRunFile(selectedRunId.value, kind)
        previewFileText.value = await blob.text()
      }
    } catch (error) {
      previewError.value = `预览失败：${error}`
    } finally {
      isPreviewLoading.value = false
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

  const handleDownloadImage = async (imagePath: string) => {
    try {
      await downloadDocImage(imagePath)
    } catch (error) {
      previewError.value = `下载图片失败：${error}`
    } finally {
      imageDownloadMenuOpen.value = false
    }
  }

  const updateRunInHistory = (trace: RunTrace) => {
    const index = runHistory.value.findIndex((run) => run.run_id === trace.run_id)
    if (index >= 0) {
      runHistory.value[index] = trace
    } else {
      runHistory.value.unshift(trace)
    }
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
    userHasToggledChapters = false
    errorMessage.value = ''
    closePreviewDrawer()
    docTypeMenuOpen.value = false
    generationModeMenuOpen.value = false
    stopPolling()
  }

  const deleteRunById = async (runId: string) => {
    const run = runHistory.value.find((item) => item.run_id === runId)
      || (selectedRun.value?.run_id === runId ? selectedRun.value : null)
    if (!run) return

    if (!confirm(`确定要删除任务「${displayTaskTitle(run)}」吗？此操作不可撤销。`)) return

    errorMessage.value = ''
    try {
      const deleted = await deleteRun(runId)
      if (!deleted) {
        alert('任务仍在运行中，结束后才能删除。')
        return
      }

      if (selectedRunId.value === runId) {
        selectedRunId.value = null
        selectedRun.value = null
        expandedChapterIds.value = []
        userHasToggledChapters = false
        closePreviewDrawer()
        stopPolling()
      }

      runHistory.value = runHistory.value.filter((item) => item.run_id !== runId)
      removeMissingRunId(runId)
    } catch (error) {
      errorMessage.value = `删除任务失败：${error}`
    }
  }

  const clearSourceFiles = () => {
    sourceFiles.value = []
    if (sourceInputRef.value) sourceInputRef.value.value = ''
  }

  const onSourceFileChange = (event: Event) => {
    const input = event.target as HTMLInputElement
    sourceFiles.value = Array.from(input.files || [])
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
      generationModeMenuOpen.value = false
      const initialPrompt = promptInput.value.trim()
      const startedRuns: RunTrace[] = []
      for (const docType of selectedDocTypes.value) {
        const response = await startGeneration(initialPrompt, docType, sourceFiles.value, selectedGenerationMode.value)
        saveLocalRunId(response.task_id)
        saveRunPrompt(response.task_id, initialPrompt || docType)
        const stub: RunTrace = {
          run_id: response.task_id,
          status: 'running',
          doc_type: response.doc_type,
          task_title: response.task_title || response.doc_type,
          generation_mode: response.generation_mode || selectedGenerationMode.value,
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
    userHasToggledChapters = false
    errorMessage.value = ''
    previewFileKind.value = ''
    clearPreviewFile()
    docTypeMenuOpen.value = false
    generationModeMenuOpen.value = false
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
      // 兼容旧版本本地记录
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

  // ── Lifecycle ─────────────────────────────────────────────────
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

  // ── Return ────────────────────────────────────────────────────
  return {
    // State
    docTypes,
    selectedDocTypes,
    generationModes,
    selectedGenerationMode,
    promptInput,
    sourceFiles,
    isSubmitting,
    isTerminating,
    errorMessage,
    selectedRunId,
    selectedRun,
    runHistory,
    sourceInputRef,
    docSubmitButtonRef,
    previewDrawerOpen,
    docTypeMenuOpen,
    generationModeMenuOpen,
    previewFileKind,
    previewFileUrl,
    previewFileText,
    isPreviewLoading,
    previewError,
    imageDownloadMenuOpen,
    expandedChapterIds,
    expandedProcessEventIds,
    processEventVisibleCounts,
    processEventLoadingKeys,
    processEntryVisibleCounts,
    processEntryLoadingKeys,
    // Constants
    processEventKindLabelMap,
    chapterStatusLabelMap,
    // Computed
    isSelectedRunActive,
    canTerminateRun,
    selectedDocTypeLabel,
    selectedGenerationModeConfig,
    statusRun,
    previewFileTitle,
    previewMarkdownHtml,
    previewImagePaths,
    chapterProgressItems,
    activeChapterTitle,
    headerProgressStyle,
    isHeaderProgressCompleted,
    isHeaderProgressFlowing,
    conversationTaskItems,
    headerRunStatusIcon,
    // Functions
    displayTaskTitle,
    formatTime,
    truncateTitle,
    runStatusIcon,
    runStatusClass,
    runStateClass,
    runStatusTooltipText,
    chapterStatusLabel,
    chapterStatusIcon,
    chapterFinalEvents,
    chapterFinalBody,
    isChapterGroupExpanded,
    toggleChapterGroupExpansion,
    shouldShowGroupLoading,
    visibleProcessEventGroups,
    hasMoreProcessEvents,
    isProcessGroupLoading,
    processEventGroupTotalCount,
    visibleProcessCount,
    loadMoreProcessEvents,
    isProcessEventExpanded,
    toggleProcessEventExpansion,
    isStreamingEventGroup,
    isStreamingEventForRun,
    processEventGroupVisualState,
    visibleProcessEntries,
    hasMoreProcessEntries,
    isProcessEntryGroupLoading,
    visibleProcessEntryCount,
    loadMoreProcessEntries,
    isRequestRecordEvent,
    processRequestTurnLabel,
    processRequestRecordContext,
    processEventGroupStatusText,
    processEventEntryStatusText,
    processEventDetailItems,
    eventHasBody,
    processEventBody,
    shouldShowProcessEventGroupStatus,
    shouldShowProcessEventEntryStatus,
    processEventEntryState,
    processExecutionStatusIcon,
    processEventEntryTitle,
    processEventKind,
    lastProcessEvent,
    // Actions
    openNewDoc,
    submitGeneration,
    selectRun,
    deleteRunById,
    handleTerminate,
    handleDownload,
    handleDownloadImage,
    handlePreviewFile,
    handlePromptKeydown,
    onSourceFileChange,
    clearSourceFiles,
    closePreviewDrawer,
    backToPreviewList,
    canPreviewRunFile,
    basename,
  }
}
