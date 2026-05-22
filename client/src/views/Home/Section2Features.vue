<template>
  <section class="full-section features-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="section-content">
      <div class="section-header">
        <span class="section-badge">核心能力</span>
        <h2 class="section-title">四大智能模块</h2>
        <p class="section-desc">覆盖 DRG 入组全流程，从病历解析到文档归档的自动化闭环</p>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="card-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          </div>
          <h3>DRG 入组智能体</h3>
          <p>基于《分组方案 2.0 版》规则，自动完成 MDC → ADRG → DRG 三层判定，支持 MCC/CC 排除表校验</p>
          <span class="card-tag">核心业务</span>
        </div>

        <div class="feature-card">
          <div class="card-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </div>
          <h3>文档自动生成</h3>
          <p>基于大模型自动生成需求规格说明书、架构设计文档、测试文档，支持 IEEE 830 标准模板</p>
          <span class="card-tag tag-blue">文档智能</span>
        </div>

        <div class="feature-card">
          <div class="card-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </div>
          <h3>测试用例生成</h3>
          <p>自动构建正常、边界、异常三类测试场景，覆盖 ICD 编码错误、排除表边界等全面验证</p>
          <span class="card-tag tag-green">质量保障</span>
        </div>

        <div class="feature-card">
          <div class="card-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
          </div>
          <h3>虚拟文档系统</h3>
          <p>统一的文档存储与提交中枢，支持文档持久化、检索浏览，串联各智能体的成果归档</p>
          <span class="card-tag tag-purple">基础架构</span>
        </div>
      </div>

      <!-- 流程指示 -->
      <div class="flow-row">
        <div class="flow-step">
          <span class="flow-dot"></span>
          <span>病历输入</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
          <span class="flow-dot"></span>
          <span>DRG 入组</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
          <span class="flow-dot"></span>
          <span>测试验证</span>
        </div>
        <span class="flow-arrow">→</span>
        <div class="flow-step">
          <span class="flow-dot"></span>
          <span>文档沉淀</span>
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
  background: $bg-page;
}

.section-content {
  max-width: 1100px;
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

/* 区块头部 */
.section-header {
  text-align: center;
  margin-bottom: 52px;
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
  max-width: 500px;
  margin: 0 auto;
}

/* 网格 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 48px;
}

.feature-card {
  background: $bg-white;
  padding: 32px 28px;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  text-align: left;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
    border-color: rgba($primary, 0.12);
  }
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba($primary, 0.08), rgba($primary, 0.04));
  color: $primary;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.feature-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: $text-title;
  margin-bottom: 10px;
}

.feature-card p {
  font-size: 14px;
  line-height: 1.7;
  color: $text-content;
  margin-bottom: 16px;
}

.card-tag {
  display: inline-block;
  padding: 3px 10px;
  background: rgba($primary, 0.06);
  color: $primary;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;

  &.tag-blue {
    background: rgba(#3b82f6, 0.06);
    color: #3b82f6;
  }
  &.tag-green {
    background: rgba(#16a34a, 0.06);
    color: #16a34a;
  }
  &.tag-purple {
    background: rgba(#8b5cf6, 0.06);
    color: #8b5cf6;
  }
}

/* 流程指示 */
.flow-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px 0;
  flex-wrap: wrap;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: $text-muted;
}

.flow-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: $primary;
  opacity: 0.5;
}

.flow-arrow {
  color: #d1d5db;
  font-size: 16px;
}
</style>
