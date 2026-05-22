<template>
  <section class="full-section filebank-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="section-content">
      <div class="section-header">
        <span class="section-badge">文件管理</span>
        <h2 class="section-title">虚拟文档系统</h2>
        <p class="section-desc">智能体生成的文档统一归档，随时随地检索浏览</p>
      </div>

      <div class="filebank-card">
        <div class="filebank-header">
          <div class="filebank-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            文档库
          </div>
          <span class="filebank-count">共 12 份</span>
        </div>

        <div class="file-list">
          <div class="file-item" v-for="i in 4" :key="i">
            <div class="file-icon-box" :class="`file-type-${i}`">
              <svg v-if="i === 1" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <svg v-else-if="i === 2" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/></svg>
              <svg v-else-if="i === 3" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
              <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            </div>
            <div class="file-info">
              <span class="file-name">{{ ['需求规格说明书_v2.md', '架构设计文档.md', 'DRG入组测试用例集.md', '入组结果报告_20260520.md'][i-1] }}</span>
              <span class="file-meta">{{ ['DRG入组智能体', '文档生成智能体', '测试用例生成智能体', 'DRG入组智能体'][i-1] }} · {{ ['2026-05-20', '2026-05-19', '2026-05-18', '2026-05-17'][i-1] }}</span>
            </div>
            <svg class="file-more" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
defineProps<{ observer: (el: HTMLElement | null) => void }>()
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.full-section {
  min-height: calc(100vh - $control-bar-height);
  width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $bg-white;
}

.section-content {
  max-width: 600px;
  width: 100%;
  padding: 60px 40px;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.1s;
}

.visible .section-content {
  opacity: 1;
  transform: translateY(0);
}

.section-header {
  text-align: center;
  margin-bottom: 40px;
}

.section-badge {
  display: inline-block;
  padding: 4px 14px;
  background: rgba($primary, 0.08);
  color: $primary;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 36px;
  font-weight: 800;
  color: $text-title;
  margin-bottom: 12px;
}

.section-desc {
  font-size: 15px;
  color: $text-muted;
}

/* 文档卡片 */
.filebank-card {
  background: $bg-page;
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.filebank-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.filebank-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: $text-title;
}

.filebank-count {
  font-size: 12px;
  color: $text-muted;
}

/* 文件列表 */
.file-list {
  padding: 4px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: rgba($primary, 0.03);
  }
}

.file-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.file-type-1 { background: rgba($primary, 0.08); color: $primary; }
  &.file-type-2 { background: rgba(#8b5cf6, 0.08); color: #8b5cf6; }
  &.file-type-3 { background: rgba(#16a34a, 0.08); color: #16a34a; }
  &.file-type-4 { background: rgba(#f59e0b, 0.08); color: #f59e0b; }
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: $text-title;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: $text-muted;
}

.file-more {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
}

.file-item:hover .file-more {
  opacity: 1;
}
</style>
