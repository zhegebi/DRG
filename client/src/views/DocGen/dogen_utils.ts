import { listDocTypesApiDocgenAgentDocTypesGet } from '@/api'
import { useAuthStore } from '@/stores/auth'

export type DocType = '需求规格说明书' | '架构设计文档' | '测试文档'

export type RunStatus =
  | 'running'
  | 'completed'
  | 'failed'
  | 'terminate_requested'
  | 'terminated'

export interface AgentTraceEvent {
  id: number
  time: string
  type: string
  phase: string
  title?: string
  content?: string
  message?: string
  tools?: string[]
  name?: string
  arguments?: Record<string, unknown>
  result?: string
  section_count?: number
  sections?: string[]
  turn?: number
  output_path?: string
  pdf_path?: string
  error?: string
  streaming?: boolean
  [key: string]: unknown
}

export interface RunTrace {
  run_id: string
  status: RunStatus | string
  doc_type: string
  task_title: string
  created_at: string
  updated_at: string
  output_path: string | null
  pdf_path: string | null
  error: string | null
  terminated: boolean
  events: AgentTraceEvent[]
}

export interface StartGenerationResponse {
  status: string
  task_id: string
  doc_type: string
  task_title: string
}

interface DocgenTaskTraceResponse {
  task_id: string
  run_id?: string
  status: string
  doc_type?: string
  task_title?: string
  created_at?: string | null
  updated_at?: string | null
  output_path?: string | null
  pdf_path?: string | null
  error?: string | null
  terminated?: boolean
  events?: AgentTraceEvent[]
}

const DOCGEN_BASE = '/api/docgen_agent'
type SourceFileInput = File | File[] | null | undefined

const toError = (error: unknown) => {
  if (error instanceof Error) return error
  if (typeof error === 'string') return new Error(error)
  return new Error(JSON.stringify(error))
}

const normalizeTrace = (trace: DocgenTaskTraceResponse): RunTrace => ({
  run_id: trace.task_id || trace.run_id || '',
  status: trace.status,
  doc_type: trace.doc_type || '',
  task_title: trace.task_title || trace.doc_type || '',
  created_at: trace.created_at || '',
  updated_at: trace.updated_at || '',
  output_path: trace.output_path ?? null,
  pdf_path: trace.pdf_path ?? null,
  error: trace.error ?? null,
  terminated: trace.terminated ?? false,
  events: (trace.events || []) as AgentTraceEvent[],
})

const authHeaders = (): Record<string, string> => {
  const token = useAuthStore().accessToken
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const normalizeFiles = (sourceFiles?: SourceFileInput): File[] => {
  if (!sourceFiles) return []
  return Array.isArray(sourceFiles) ? sourceFiles : [sourceFiles]
}

const appendSourceFiles = (form: FormData, sourceFiles?: SourceFileInput) => {
  for (const file of normalizeFiles(sourceFiles)) {
    form.append('source_files', file)
  }
}

const multipartPost = async <T>(url: string, form: FormData): Promise<T> => {
  const resp = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (!resp.ok) {
    let message = `HTTP ${resp.status}`
    try {
      const payload = await resp.json()
      message = payload?.detail || payload?.message || message
    } catch {
      message = await resp.text() || message
    }
    throw new Error(message)
  }
  return await resp.json() as T
}

export const terminalRunStatusSet = new Set<string>([
  'completed',
  'failed',
  'terminated',
])

export const activeRunStatusSet = new Set<string>([
  'running',
  'terminate_requested',
])

export const getDocTypes = async (): Promise<DocType[]> => {
  const { data, error } = await listDocTypesApiDocgenAgentDocTypesGet()
  if (error) throw toError(error)
  return (data || []) as DocType[]
}

export const startGeneration = async (
  prompt: string,
  docType: DocType,
  sourceFiles?: SourceFileInput,
): Promise<StartGenerationResponse> => {
  const form = new FormData()
  form.append('prompt', prompt)
  form.append('doc_type', docType)
  appendSourceFiles(form, sourceFiles)
  return await multipartPost<StartGenerationResponse>(`${DOCGEN_BASE}/task/create`, form)
}

export const getRunTrace = async (runId: string): Promise<RunTrace> => {
  const resp = await fetch(`${DOCGEN_BASE}/task/${runId}/trace`, {
    headers: authHeaders(),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
  return normalizeTrace(await resp.json() as DocgenTaskTraceResponse)
}

export const listRunHistory = async (): Promise<RunTrace[]> => {
  const resp = await fetch(`${DOCGEN_BASE}/task/list`, {
    headers: authHeaders(),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
  const payload = await resp.json() as DocgenTaskTraceResponse[]
  return payload.map(normalizeTrace)
}

export const streamRunTrace = async (
  runId: string,
  onTrace: (trace: RunTrace) => void,
  signal?: AbortSignal,
) => {
  const resp = await fetch(`${DOCGEN_BASE}/task/${runId}/trace/stream`, {
    headers: authHeaders(),
    signal,
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
  const reader = resp.body?.getReader()
  if (!reader) throw new Error('运行轨迹流不可读取')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    for (const frame of frames) {
      const line = frame.split('\n').find((item) => item.startsWith('data: '))
      if (!line) continue
      const payload = line.slice(6)
      if (payload === '[END]') return
      const parsed = JSON.parse(payload) as DocgenTaskTraceResponse
      onTrace(normalizeTrace(parsed))
    }
  }
}

export const terminateRun = async (runId: string) => {
  const resp = await fetch(`${DOCGEN_BASE}/task/${runId}/terminate`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`)
}

const filenameFromDisposition = (disposition: string | null, fallback: string) => {
  if (!disposition) return fallback
  const encoded = disposition.match(/filename\*=utf-8''([^;]+)/i)?.[1]
  if (encoded) return decodeURIComponent(encoded)
  const plain = disposition.match(/filename="?([^"]+)"?/i)?.[1]
  return plain || fallback
}

const downloadRunFile = async (runId: string, kind: 'markdown' | 'pdf', fallbackName: string) => {
  const url = kind === 'pdf'
    ? `${DOCGEN_BASE}/task/${runId}/download/pdf`
    : `${DOCGEN_BASE}/task/${runId}/download`
  const resp = await fetch(url, { headers: authHeaders() })
  if (!resp.ok) throw new Error(`下载失败：HTTP ${resp.status}`)

  const blob = await resp.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filenameFromDisposition(resp.headers.get('Content-Disposition'), fallbackName)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export const fetchRunFile = async (runId: string, kind: 'markdown' | 'pdf') => {
  const url = kind === 'pdf'
    ? `${DOCGEN_BASE}/task/${runId}/download/pdf`
    : `${DOCGEN_BASE}/task/${runId}/download`
  const resp = await fetch(url, { headers: authHeaders() })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return await resp.blob()
}

export const downloadMarkdown = async (runId: string, fileName: string) => {
  await downloadRunFile(runId, 'markdown', fileName)
}

export const downloadPdf = async (runId: string, fileName: string) => {
  await downloadRunFile(runId, 'pdf', fileName)
}

export const phaseLabelMap: Record<string, string> = {
  run: '总控',
  read_files: '读取文件',
  split_sections: '拆解章节',
  generate_sections: '逐节生成',
  validate: 'Schema 合规校验',
  stitch: '拼接校验',
  save: '保存文档',
  convert_pdf: '转为 PDF',
}

export const eventTypeLabelMap: Record<string, string> = {
  run_started: '开始',
  phase_started: '阶段开始',
  phase_completed: '阶段完成',
  llm_request: 'LLM 调用',
  reasoning: '思考',
  assistant_message: '模型输出',
  tool_calls_planned: '计划工具',
  tool_call: '执行工具',
  tool_result: '工具返回',
  section_started: '章节开始',
  section_completed: '章节完成',
  section_saved_in_memory: '暂存章节',
  section_retry: '重试章节',
  section_missing: '缺失章节',
  document_stitched: '拼接完成',
  table_repaired: '表格修复',
  format_repaired: '格式修复',
  terminate_requested: '请求终止',
  error: '错误',
}

export const runStatusLabelMap: Record<string, string> = {
  running: '生成中',
  completed: '已完成',
  failed: '失败',
  terminate_requested: '终止中',
  terminated: '已终止',
}
