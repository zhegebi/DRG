<template>
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
        <template v-else>
          <div v-if="previewFileKind === 'markdown' && previewImagePaths.length" class="drawer-preview-toolbar">
            <div class="drawer-image-menu">
              <AppTooltip text="下载文档图片" placement="left">
                <button
                  class="action-btn action-download drawer-image-menu-trigger"
                  type="button"
                  :aria-expanded="imageDownloadMenuOpen"
                  @click="imageDownloadMenuOpen = !imageDownloadMenuOpen"
                >
                  <SvgIcon type="mdi" :path="mdiImageMultipleOutline" class="button-icon" />
                  图片
                  <span class="drawer-image-count">{{ previewImagePaths.length }}</span>
                  <SvgIcon type="mdi" :path="mdiMenuDown" class="button-icon drawer-image-menu-caret" />
                </button>
              </AppTooltip>
              <div v-if="imageDownloadMenuOpen" class="drawer-image-menu-panel">
                <AppTooltip
                  v-for="img in previewImagePaths"
                  :key="img.path"
                  :text="`下载 ${img.alt}`"
                  placement="left"
                >
                  <button
                    class="drawer-image-menu-item"
                    type="button"
                    @click="handleDownloadImage(img.path)"
                  >
                    <SvgIcon type="mdi" :path="mdiFileImageOutline" class="button-icon" />
                    <span class="drawer-image-name">{{ img.alt }}</span>
                    <SvgIcon type="mdi" :path="mdiDownload" class="button-icon" />
                  </button>
                </AppTooltip>
              </div>
            </div>
          </div>
          <iframe
            v-if="previewFileKind === 'pdf' && previewFileUrl"
            class="drawer-pdf-preview"
            :srcdoc="previewFileUrl"
            title="文档预览"
          ></iframe>
          <img
            v-else-if="previewFileKind === 'image' && previewFileUrl"
            class="drawer-image-preview"
            :src="previewFileUrl"
            :alt="previewFileTitle"
          />
          <div
            v-else-if="previewFileKind === 'markdown'"
            class="drawer-markdown-preview"
            v-html="previewMarkdownHtml"
          ></div>
        </template>
      </section>

      <div v-else class="final-output-card">
        <div class="preview-output-header">
          <strong>生成文件</strong>
          <AppTooltip :text="runStatusTooltipText(selectedRun)" placement="left">
            <SvgIcon
              type="mdi"
              :path="runStatusIcon(selectedRun.status)"
              :class="[
                'preview-status-icon',
                runStatusClass(selectedRun.status),
              ]"
              :aria-label="runStatusTooltipText(selectedRun)"
            />
          </AppTooltip>
        </div>

        <!-- Markdown Row -->
        <div class="preview-file-row">
          <div class="preview-file-info">
            <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="preview-file-icon" />
            <div>
              <span>Markdown</span>
              <strong>{{ basename(selectedRun.output_path) || '待生成' }}</strong>
            </div>
          </div>
          <div class="preview-file-actions">
            <button
              class="file-icon-btn"
              type="button"
              :disabled="!canPreviewRunFile('markdown') || isPreviewLoading"
              aria-label="预览 Markdown"
              @click="handlePreviewFile('markdown')"
            >
              <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
            </button>
            <button
              class="file-icon-btn"
              type="button"
              :disabled="selectedRun.status !== 'completed'"
              aria-label="下载 Markdown"
              @click="handleDownload('markdown')"
            >
              <SvgIcon type="mdi" :path="mdiDownload" class="button-icon" />
            </button>
          </div>
        </div>

        <!-- PDF Row -->
        <div class="preview-file-row">
          <div class="preview-file-info">
            <SvgIcon type="mdi" :path="mdiFilePdfBox" class="preview-file-icon" />
            <div>
              <span>PDF</span>
              <strong>{{ basename(selectedRun.pdf_path) || '待生成' }}</strong>
            </div>
          </div>
          <div class="preview-file-actions">
            <button
              class="file-icon-btn"
              type="button"
              :disabled="!canPreviewRunFile('pdf') || isPreviewLoading"
              aria-label="预览 PDF"
              @click="handlePreviewFile('pdf')"
            >
              <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
            </button>
            <button
              class="file-icon-btn"
              type="button"
              :disabled="selectedRun.status !== 'completed' || isPreviewLoading"
              aria-label="打印 PDF"
              @click="handlePrintPdf"
            >
              <SvgIcon type="mdi" :path="mdiPrinter" class="button-icon" />
            </button>
          </div>
        </div>

        <!-- Image Row -->
        <div class="preview-file-row image-file-row" :class="{ expanded: imageMenuExpanded }">
          <div class="preview-file-info" @click="toggleImageMenu">
              <SvgIcon type="mdi" :path="mdiImageMultipleOutline" class="preview-file-icon" />
            <div>
              <span>图片</span>
              <strong>{{ imageSummaryText }}</strong>
            </div>
          </div>
          <div class="preview-file-actions">
            <button
              class="file-icon-btn image-expand-arrow"
              type="button"
              :disabled="!canOpenImageMenu"
              :aria-expanded="imageMenuExpanded"
              aria-label="展开图片列表"
              @click="toggleImageMenu"
            >
              <SvgIcon
                type="mdi"
                :path="isLoadingImages ? mdiLoading : mdiChevronDown"
                :class="['button-icon', { 'loading-icon': isLoadingImages, 'rotate-up': imageMenuExpanded }]"
              />
            </button>
          </div>
        </div>

        <!-- Image Sub-menu -->
        <div v-if="imageMenuExpanded && imageItems.length" class="image-submenu">
          <div
            v-for="img in imageItems"
            :key="img.path"
            class="image-submenu-item"
          >
            <div class="image-submenu-info">
              <SvgIcon type="mdi" :path="mdiFileImageOutline" class="button-icon" />
              <span class="image-submenu-name">{{ img.alt }}</span>
            </div>
            <div class="image-submenu-actions">
              <button
                class="file-icon-btn"
                type="button"
                aria-label="预览图片"
                @click="handlePreviewImage(img.path)"
              >
                <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
              </button>
              <button
                class="file-icon-btn"
                type="button"
                aria-label="下载图片"
                @click="handleDownloadImage(img.path)"
              >
                <SvgIcon type="mdi" :path="mdiDownload" class="button-icon" />
              </button>
            </div>
          </div>
        </div>
        <div v-else-if="imageMenuExpanded && isLoadingImages" class="image-submenu-loading">
          <SvgIcon type="mdi" :path="mdiLoading" class="button-icon loading-icon" />
          <span>正在加载图片列表</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import AppTooltip from '@/components/AppTooltip.vue'
import {
  mdiChevronDown,
  mdiChevronRight,
  mdiClose,
  mdiDownload,
  mdiFileDocumentOutline,
  mdiFileEyeOutline,
  mdiFileImageOutline,
  mdiFilePdfBox,
  mdiImageMultipleOutline,
  mdiLoading,
  mdiMenuDown,
  mdiPrinter,
} from '@mdi/js'
import { useDocGen } from './useDocGen'
import { fetchDocImage, fetchImageList } from './dogen_utils'

const {
  selectedRun,
  selectedRunId,
  previewDrawerOpen,
  previewFileKind,
  previewFileUrl,
  isPreviewLoading,
  previewError,
  imageDownloadMenuOpen,
  previewFileTitle,
  previewMarkdownHtml,
  previewImagePaths,
  displayTaskTitle,
  runStatusIcon,
  runStatusClass,
  runStatusTooltipText,
  closePreviewDrawer,
  backToPreviewList,
  canPreviewRunFile,
  handlePreviewFile,
  handleDownload,
  handleDownloadImage,
  basename,
} = useDocGen()

// ── Image sub-menu state ─────────────────────────────────────────
interface ImageItem {
  path: string
  alt: string
}

const imageMenuExpanded = ref(false)
const isLoadingImages = ref(false)
const hasLoadedImageItems = ref(false)
const loadedImageItems = ref<ImageItem[]>([])

const imageItems = computed(() => {
  return loadedImageItems.value
})

const canLoadImages = computed(() => {
  return Boolean(selectedRunId.value && selectedRun.value?.status === 'completed')
})

const canOpenImageMenu = computed(() => {
  return imageItems.value.length > 0
    || isLoadingImages.value
    || (!hasLoadedImageItems.value && canLoadImages.value)
})

const imageSummaryText = computed(() => {
  if (isLoadingImages.value || (!hasLoadedImageItems.value && canLoadImages.value)) return '正在检查图片'
  if (imageItems.value.length) return `${imageItems.value.length} 张图片`
  return '暂无图片'
})

const toggleImageMenu = async () => {
  if (!canOpenImageMenu.value) return
  imageMenuExpanded.value = !imageMenuExpanded.value
  if (imageMenuExpanded.value && !hasLoadedImageItems.value) {
    await loadImageItems()
  }
}

const loadImageItems = async () => {
  const runId = selectedRunId.value
  if (!runId || isLoadingImages.value) return
  isLoadingImages.value = true
  hasLoadedImageItems.value = true
  try {
    const items = await fetchImageList(runId)
    if (selectedRunId.value !== runId) return
    loadedImageItems.value = items
  } catch {
    if (selectedRunId.value === runId) loadedImageItems.value = []
  } finally {
    if (selectedRunId.value === runId) isLoadingImages.value = false
  }
}

const resetImageItems = () => {
  imageMenuExpanded.value = false
  isLoadingImages.value = false
  hasLoadedImageItems.value = false
  loadedImageItems.value = []
}

watch(
  () => ({
    runId: selectedRunId.value,
    status: selectedRun.value?.status,
    isOpen: previewDrawerOpen.value,
  }),
  (current, previous) => {
    if (current.runId !== previous?.runId) resetImageItems()
    if (current.isOpen && current.runId && current.status === 'completed' && !hasLoadedImageItems.value) {
      void loadImageItems()
    }
  },
  { immediate: true },
)

// PDF download via browser print (fetches backend-processed HTML)
const handlePrintPdf = async () => {
  if (!selectedRunId.value || isPreviewLoading.value) return
  isPreviewLoading.value = true
  try {
    const baseUrl = '/api/docgen_agent'
    const url = `${baseUrl}/task/${selectedRunId.value}/html`
    const token = localStorage.getItem('access_token')
    const resp = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const html = await resp.text()
    const w = window.open('', '_blank')
    if (w) {
      w.document.write(html)
      w.document.close()
      w.addEventListener('load', () => {
        w.print()
      }, { once: true })
    }
  } catch (err) {
    previewError.value = `打印 PDF 失败：${err}`
  } finally {
    isPreviewLoading.value = false
  }
}

const handlePreviewImage = async (imagePath: string) => {
  if (!selectedRunId.value || isPreviewLoading.value) return
  previewFileKind.value = 'image'
  isPreviewLoading.value = true
  previewError.value = ''
  try {
    const blob = await fetchDocImage(imagePath)
    const objectUrl = URL.createObjectURL(blob)
    if (previewFileUrl.value && previewFileUrl.value.startsWith('blob:')) {
      URL.revokeObjectURL(previewFileUrl.value)
    }
    previewFileUrl.value = objectUrl
  } catch (error) {
    previewError.value = `预览图片失败：${error}`
  } finally {
    isPreviewLoading.value = false
  }
}
</script>

<style lang="scss" scoped>
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

.action-btn {
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

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-download {
  color: #007fd4;
  border-color: rgba(0, 127, 212, 0.32);
}

.icon-button {
  width: 38px;
  min-height: 38px;
  padding: 0;
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
  border-color: transparent;
  background: transparent;
  color: #007fd4;
}

.icon-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.icon-button:hover {
  background: #eef6ff;
}

/* Pure icon file action buttons */
.file-icon-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, background 0.15s;
}

.file-icon-btn:hover:not(:disabled) {
  color: #007fd4;
  background: rgba(0, 127, 212, 0.08);
}

.file-icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.file-icon-btn .button-icon {
  width: 20px;
  height: 20px;
}

.preview-backdrop {
  position: fixed;
  inset: 64px 0 0 0;
  z-index: 35;
  background: rgba(15, 23, 42, 0.18);
}

.result-drawer {
  position: fixed;
  top: 64px;
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
  display: grid;
  gap: 0;
}

.preview-output-header {
  min-height: 34px;
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  color: #0f172a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-output-header strong {
  font-size: 15px;
  font-weight: 800;
}

.preview-status-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: currentColor;
}

.status-running {
  color: #007fd4;
}

.status-completed {
  color: #16a34a;
}

.status-stopped {
  color: #f59e0b;
}

.status-error {
  color: #dc2626;
}

.preview-file-row {
  padding: 14px 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.preview-file-row:last-of-type {
  border-bottom: 0;
}

.image-file-row {
  cursor: pointer;
}

.image-file-row:hover {
  background: rgba(0, 127, 212, 0.03);
}

.preview-file-info {
  min-width: 0;
  flex: 1 1 0;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.preview-file-info > div {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.preview-file-icon {
  width: 24px;
  height: 24px;
  color: #007fd4;
  fill: currentColor;
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
  width: 80px;
  flex: 0 0 80px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.image-expand-arrow .button-icon {
  transition: transform 0.2s ease;
}

.image-expand-arrow .button-icon.rotate-up {
  transform: rotate(180deg);
}

/* Image sub-menu */
.image-submenu {
  padding: 0 0 8px 44px;
  display: grid;
  gap: 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.image-submenu-item {
  padding: 8px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
}

.image-submenu-item:last-child {
  border-bottom: 0;
}

.image-submenu-info {
  min-width: 0;
  flex: 1 1 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
}

.image-submenu-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #334155;
}

.image-submenu-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.image-submenu-loading {
  padding: 16px 0 16px 44px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
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
  padding: 0;
  border: none;
  border-radius: 0;
  background: #ffffff;
  gap: 0;
}

.drawer-preview-empty,
.drawer-preview-error {
  flex: 1;
  min-height: 0;
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
  color: #dc2626;
}

.drawer-preview-toolbar {
  flex: 0 0 auto;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.drawer-image-menu {
  position: relative;
  flex: 0 0 auto;
}

.drawer-image-menu-trigger {
  min-height: 34px;
  padding: 0 10px;
}

.drawer-image-count {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
}

.drawer-image-menu-caret {
  width: 16px;
  height: 16px;
}

.drawer-image-menu-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  width: min(340px, calc(100vw - 40px));
  max-height: 260px;
  padding: 6px;
  overflow-y: auto;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
  display: grid;
  gap: 4px;
}

.drawer-image-menu-item {
  width: 100%;
  min-height: 34px;
  padding: 0 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 8px;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}

.drawer-image-menu-item:hover {
  background: #eef6ff;
  color: #007fd4;
}

.drawer-image-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-pdf-preview,
.drawer-markdown-preview,
.drawer-image-preview {
  flex: 1;
  min-height: 0;
  border: 0;
  border-radius: 0;
  background: #ffffff;
}

.drawer-pdf-preview {
  width: 100%;
}

.drawer-image-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 16px;
  box-sizing: border-box;
}

.drawer-markdown-preview {
  margin: 0;
  padding: 18px 20px;
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

.drawer-markdown-preview :deep(h4),
.drawer-markdown-preview :deep(h5),
.drawer-markdown-preview :deep(h6) {
  margin: 14px 0 8px;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.45;
}

.drawer-markdown-preview :deep(h1:first-child),
.drawer-markdown-preview :deep(h2:first-child),
.drawer-markdown-preview :deep(h3:first-child),
.drawer-markdown-preview :deep(h4:first-child),
.drawer-markdown-preview :deep(h5:first-child),
.drawer-markdown-preview :deep(h6:first-child) {
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

@media (max-width: 860px) {
  .result-drawer {
    width: 100vw;
  }

  .preview-file-row,
  .preview-file-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-file-info,
  .preview-file-actions {
    width: 100%;
    flex: 0 1 auto;
  }

  .preview-file-actions {
    flex-direction: row;
    justify-content: flex-end;
  }

  .image-submenu {
    padding-left: 20px;
  }
}
</style>
