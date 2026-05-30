<template>
  <div class="virtual-doc-layout">
    <!-- 左侧分类侧边栏 -->
    <aside class="category-sidebar">
      <div class="sidebar-header">
        <h3 class="sidebar-title">文档分类</h3>
      </div>

      <div class="category-list">
        <button
          class="category-item"
          :class="{ active: selectedCategory === null }"
          @click="selectCategory(null)"
        >
          <SvgIcon type="mdi" :path="mdiFolderMultipleOutline" class="category-icon" />
          <span class="category-name">全部文档</span>
          <span class="category-count">{{ totalCount }}</span>
        </button>

        <button
          v-for="cat in categories"
          :key="cat"
          class="category-item"
          :class="{ active: selectedCategory === cat }"
          @click="selectCategory(cat)"
        >
          <SvgIcon type="mdi" :path="mdiFolderOutline" class="category-icon" />
          <span class="category-name">{{ catLabel(cat) }}</span>
          <span class="category-count">{{ countByCategory[cat] ?? 0 }}</span>
        </button>

        <div v-if="loadingCategories" class="category-loading">
          <div class="spinner"></div>
        </div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="doc-main">
      <!-- 头部 -->
      <header class="doc-header">
        <div class="doc-header-left">
          <h1 class="doc-title">{{ selectedCategory ? catLabel(selectedCategory) : '全部文档' }}</h1>
          <span class="doc-count">{{ filteredDocs.length }} 条记录</span>
        </div>
        <div class="doc-header-right">
          <div class="search-wrapper">
            <SvgIcon type="mdi" :path="mdiMagnify" class="search-icon" />
            <input
              v-model="searchQuery"
              class="search-input"
              type="text"
              placeholder="搜索文档标题..."
            />
          </div>
          <button class="refresh-btn" type="button" @click="loadAll" title="刷新">
            <SvgIcon type="mdi" :path="mdiRefresh" class="button-icon" />
          </button>
        </div>
      </header>

      <!-- 数据表格 -->
      <div class="table-container">
        <table class="doc-table">
          <thead>
            <tr>
              <th class="col-id">ID</th>
              <th class="col-title">标题</th>
              <th class="col-category">分类</th>
              <th class="col-time">创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loadingDocs" class="table-row-empty">
              <td colspan="4">
                <div class="table-empty">
                  <div class="spinner"></div>
                  <span>加载中...</span>
                </div>
              </td>
            </tr>
            <tr v-else-if="filteredDocs.length === 0" class="table-row-empty">
              <td colspan="4">
                <div class="table-empty">
                  <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="empty-icon" />
                  <span>{{ searchQuery ? '未找到匹配的文档' : '暂无文档' }}</span>
                </div>
              </td>
            </tr>
            <tr
              v-for="(doc, index) in filteredDocs"
              :key="doc.id ?? index"
              class="table-row"
              :class="{ 'row-active': detailDoc?.id === doc.id }"
              @click="openDetail(doc)"
            >
              <td class="col-id">{{ doc.id }}</td>
              <td class="col-title">
                <span class="doc-title-text">{{ doc.title }}</span>
              </td>
              <td class="col-category">
                <span class="category-badge">{{ catLabel(doc.category) }}</span>
              </td>
              <td class="col-time">{{ formatTime(doc.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>

    <!-- 文档详情抽屉 -->
    <Teleport to="body">
      <Transition name="drawer-fade">
        <div v-if="detailDoc" class="drawer-backdrop" @click="closeDetail"></div>
      </Transition>
      <Transition name="drawer-slide">
        <aside v-if="detailDoc" class="detail-drawer">
          <header class="drawer-header">
            <div class="drawer-title-block">
              <span class="drawer-label">文档详情</span>
              <h2 class="drawer-title">{{ detailDoc.title }}</h2>
              <div class="drawer-meta">
                <span class="drawer-meta-item">
                  <SvgIcon type="mdi" :path="mdiIdentifier" class="drawer-meta-icon" />
                  ID: {{ detailDoc.id }}
                </span>
                <span class="drawer-meta-item">
                  <SvgIcon type="mdi" :path="mdiFolderOutline" class="drawer-meta-icon" />
                  {{ catLabel(detailDoc.category) }}
                </span>
                <span class="drawer-meta-item">
                  <SvgIcon type="mdi" :path="mdiCalendarOutline" class="drawer-meta-icon" />
                  {{ formatTime(detailDoc.created_at) }}
                </span>
              </div>
            </div>
            <button class="drawer-close" @click="closeDetail">
              <SvgIcon type="mdi" :path="mdiClose" class="drawer-close-icon" />
            </button>
          </header>
          <div class="drawer-body">
            <div class="drawer-content markdown-body" v-html="renderedContent"></div>
          </div>
        </aside>
      </Transition>
    </Teleport>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import {
  mdiRefresh,
  mdiCalendarOutline,
  mdiIdentifier,
  mdiFolderOutline,
  mdiFolderMultipleOutline,
  mdiMagnify,
  mdiFileDocumentOutline,
  mdiClose,
} from '@mdi/js'
import { listDocsApiDocListPost, getDocApiDocIdGet, listCategoriesApiDocCategoriesGet } from '@/api/sdk.gen'
import type { Document } from '@/api/types.gen'
import { marked } from 'marked'

// 分类标签汉化映射
const categoryLabels: Record<string, string> = {
  tech: '技术文档',
  medical: '医学知识',
  test: '测试文档',
  operation: '运营文档',
  report: '报告文档',
  regulation: '法规文档',
  education: '培训文档',
}

function catLabel(cat: string | null | undefined): string {
  if (!cat) return '未分类'
  return categoryLabels[cat] || cat
}

// 状态
const docs = ref<Document[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref<string | null>(null)
const detailDoc = ref<Document | null>(null)
const searchQuery = ref('')
const loadingDocs = ref(false)
const loadingCategories = ref(false)

// 总数
const totalCount = computed(() => docs.value.length)

// 按分类统计
const countByCategory = computed(() => {
  const counts: Record<string, number> = {}
  for (const doc of docs.value) {
    const cat = doc.category || '未分类'
    counts[cat] = (counts[cat] || 0) + 1
  }
  return counts
})

// 过滤后的文档
const filteredDocs = computed(() => {
  let list = docs.value
  if (selectedCategory.value) {
    list = list.filter(d => (d.category || '未分类') === selectedCategory.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(d => d.title.toLowerCase().includes(q))
  }
  return list
})

// 渲染 markdown 内容
const renderedContent = computed(() => {
  if (!detailDoc.value?.content) return ''
  return marked(detailDoc.value.content)
})

function formatTime(dateStr?: string | null): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${day} ${h}:${min}`
  } catch {
    return dateStr
  }
}

async function loadCategories() {
  loadingCategories.value = true
  try {
    const { data } = await listCategoriesApiDocCategoriesGet()
    if (data) {
      categories.value = Array.isArray(data) ? data : []
    }
  } catch (err) {
    console.error('获取分类列表失败:', err)
    categories.value = []
  } finally {
    loadingCategories.value = false
  }
}

async function loadDocs() {
  loadingDocs.value = true
  try {
    const { data } = await listDocsApiDocListPost()
    if (data) {
      docs.value = Array.isArray(data) ? data : []
    }
  } catch (err) {
    console.error('获取文档列表失败:', err)
    docs.value = []
  } finally {
    loadingDocs.value = false
  }
}

async function loadAll() {
  await Promise.all([loadDocs(), loadCategories()])
}

function selectCategory(cat: string | null) {
  selectedCategory.value = cat
  searchQuery.value = ''
}

async function openDetail(doc: Document) {
  if (doc.content) {
    detailDoc.value = doc
    return
  }
  try {
    const { data } = await getDocApiDocIdGet({ path: { id: String(doc.id) } })
    detailDoc.value = data ?? doc
  } catch (err) {
    console.error('获取文档详情失败:', err)
    detailDoc.value = doc
  }
}

function closeDetail() {
  detailDoc.value = null
}

onMounted(() => {
  loadAll()
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.virtual-doc-layout {
  height: calc(100vh - $control-bar-height);
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  background: $bg-page;
  color: $text-body;
  overflow: hidden;
}

/* ===== 分类侧边栏 ===== */
.category-sidebar {
  padding: 16px 12px;
  box-sizing: border-box;
  border-right: 1px solid rgba($dark, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  min-height: 0;
  background: $bg-white;
}

.sidebar-header {
  padding: 0 8px;
}

.sidebar-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.category-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-item {
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-family: inherit;
  color: $text-body;
  transition: all 0.15s;
  text-align: left;

  &:hover {
    background: $bg-hover;
  }

  &.active {
    background: $bg-active;
    color: $primary;
    font-weight: 600;
  }
}

.category-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
  flex-shrink: 0;
}

.category-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-count {
  font-size: 12px;
  color: $text-muted;
  background: rgba($dark, 0.06);
  padding: 1px 7px;
  border-radius: 10px;
  flex-shrink: 0;
}

.category-loading {
  display: flex;
  justify-content: center;
  padding: 16px;
}

/* ===== 主区域 ===== */
.doc-main {
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.doc-header {
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba($dark, 0.06);
  flex-shrink: 0;
}

.doc-header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.doc-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: $text-title;
}

.doc-count {
  font-size: 13px;
  color: $text-muted;
}

.doc-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  width: 16px;
  height: 16px;
  fill: $text-muted;
  pointer-events: none;
}

.search-input {
  width: 220px;
  padding: 7px 10px 7px 32px;
  border: 1.5px solid rgba($dark, 0.12);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  background: $bg-white;
  color: $text-body;
  outline: none;
  transition: all 0.2s;
  box-sizing: border-box;

  &::placeholder {
    color: $text-muted;
  }

  &:focus {
    border-color: $primary;
    box-shadow: 0 0 0 3px rgba($primary, 0.1);
  }
}

.refresh-btn {
  width: 34px;
  height: 34px;
  border: 1.5px solid rgba($dark, 0.12);
  border-radius: 8px;
  background: $bg-white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  color: $text-muted;

  &:hover {
    border-color: $primary;
    color: $primary;
    background: $bg-hover;
  }
}

.button-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

/* ===== 表格 ===== */
.table-container {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 24px 24px;
}

.doc-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 14px;
}

.doc-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.doc-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: $bg-page;
  border-bottom: 2px solid rgba($dark, 0.08);
  white-space: nowrap;
}

.col-id { width: 70px; }
.col-title { min-width: 200px; }
.col-category { width: 120px; }
.col-time { width: 160px; }

.table-row {
  cursor: pointer;
  transition: background 0.12s;

  &:hover {
    background: $bg-hover;
  }

  &.row-active {
    background: $bg-active;
  }

  td {
    padding: 12px;
    border-bottom: 1px solid rgba($dark, 0.05);
    vertical-align: middle;
  }
}

.table-row-empty td {
  padding: 0;
}

.doc-title-text {
  font-weight: 500;
  color: $text-title;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 100%;
}

.category-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: rgba($primary, 0.08);
  color: $primary;
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 16px;
  color: $text-muted;
  font-size: 14px;
}

.empty-icon {
  width: 40px;
  height: 40px;
  fill: rgba($dark, 0.1);
}

.spinner {
  width: 22px;
  height: 22px;
  border: 2.5px solid rgba($primary, 0.2);
  border-top-color: $primary;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 详情抽屉 ===== */
.drawer-backdrop {
  position: fixed;
  inset: $control-bar-height 0 0 0;
  z-index: 35;
  background: rgba($dark, 0.18);
}

.detail-drawer {
  position: fixed;
  top: $control-bar-height;
  right: 0;
  bottom: 0;
  width: 560px;
  max-width: 90vw;
  z-index: 40;
  background: $bg-white;
  box-shadow: -8px 0 30px rgba($dark, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drawer-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba($dark, 0.08);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}

.drawer-title-block {
  flex: 1;
  min-width: 0;
}

.drawer-label {
  font-size: 11px;
  font-weight: 700;
  color: $text-muted;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.drawer-title {
  margin: 4px 0 0;
  font-size: 20px;
  font-weight: 700;
  color: $text-title;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 8px;
}

.drawer-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: $text-muted;
}

.drawer-meta-icon {
  width: 14px;
  height: 14px;
  fill: currentColor;
}

.drawer-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $text-muted;
  flex-shrink: 0;
  transition: all 0.15s;

  &:hover {
    background: rgba($dark, 0.06);
    color: $text-body;
  }
}

.drawer-close-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 24px;
}

.drawer-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: $text-content;
  word-wrap: break-word;
}

/* ===== Markdown 渲染样式 ===== */
.markdown-body {
  :deep(h1) {
    margin: 20px 0 10px;
    font-size: 22px;
    font-weight: 700;
    color: $text-title;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba($dark, 0.08);
  }

  :deep(h2) {
    margin: 18px 0 8px;
    font-size: 18px;
    font-weight: 700;
    color: $text-title;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba($dark, 0.06);
  }

  :deep(h3) {
    margin: 16px 0 6px;
    font-size: 16px;
    font-weight: 600;
    color: $text-title;
  }

  :deep(h4),
  :deep(h5),
  :deep(h6) {
    margin: 14px 0 6px;
    font-size: 15px;
    font-weight: 600;
    color: $text-title;
  }

  :deep(p) {
    margin: 8px 0;
    line-height: 1.8;
  }

  :deep(ul),
  :deep(ol) {
    margin: 6px 0;
    padding-left: 24px;
    line-height: 1.8;
  }

  :deep(li) {
    margin: 2px 0;
  }

  :deep(blockquote) {
    margin: 10px 0;
    padding: 8px 16px;
    border-left: 4px solid $primary;
    background: rgba($primary, 0.04);
    color: $text-muted;
  }

  :deep(code) {
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba($dark, 0.06);
    color: #e11d48;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 0.9em;
  }

  :deep(pre) {
    margin: 12px 0;
    padding: 14px 16px;
    border-radius: 8px;
    background: rgba($dark, 0.04);
    overflow-x: auto;
  }

  :deep(pre code) {
    padding: 0;
    background: none;
    color: inherit;
    font-size: 13px;
    line-height: 1.6;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 14px;
  }

  :deep(th) {
    padding: 8px 12px;
    border: 1px solid rgba($dark, 0.1);
    background: rgba($dark, 0.04);
    font-weight: 600;
    text-align: left;
  }

  :deep(td) {
    padding: 6px 12px;
    border: 1px solid rgba($dark, 0.1);
  }

  :deep(hr) {
    margin: 20px 0;
    border: none;
    border-top: 1px solid rgba($dark, 0.08);
  }

  :deep(img) {
    max-width: 100%;
    border-radius: 6px;
  }

  :deep(a) {
    color: $primary;
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }

  :deep(strong) {
    font-weight: 600;
  }
}

/* ===== 抽屉动画 ===== */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.2s;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-slide-leave-active {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(100%);
}
</style>
