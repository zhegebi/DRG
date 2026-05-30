<template>
  <section class="full-section templates-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="section-content">
      <div class="section-header">
        <span class="section-badge">疾病覆盖</span>
        <h2 class="section-title">常见疾病分类模板</h2>
        <p class="section-desc">基于 CHS-DRG 2.0 版分组方案，覆盖主要诊断大类</p>
      </div>

      <div class="templates-grid">
        <div class="template-card">
          <div class="template-icon">❤️</div>
          <div class="template-info">
            <h3>循环系统疾病</h3>
            <p>MDCF · 高血压、冠心病等</p>
          </div>
          <span class="template-arrow">→</span>
        </div>
        <div class="template-card">
          <div class="template-icon">🫁</div>
          <div class="template-info">
            <h3>呼吸系统疾病</h3>
            <p>MDCD · COPD、肺炎等</p>
          </div>
          <span class="template-arrow">→</span>
        </div>
        <div class="template-card">
          <div class="template-icon">🦴</div>
          <div class="template-info">
            <h3>骨骼肌肉系统</h3>
            <p>MDCI · 骨折、关节置换等</p>
          </div>
          <span class="template-arrow">→</span>
        </div>
        <div class="template-card">
          <div class="template-icon">🔬</div>
          <div class="template-info">
            <h3>消化系统疾病</h3>
            <p>MDCG · 阑尾炎、消化道出血等</p>
          </div>
          <span class="template-arrow">→</span>
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
  max-width: 800px;
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

.templates-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 560px;
  margin: 0 auto;
}

.template-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: $bg-white;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: all 0.25s;

  &:hover {
    transform: translateX(4px);
    border-color: rgba($primary, 0.15);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);

    .template-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }
}

.template-icon {
  font-size: 24px;
  flex-shrink: 0;
  width: 40px;
  text-align: center;
}

.template-info {
  flex: 1;
  min-width: 0;

  h3 {
    font-size: 15px;
    font-weight: 600;
    color: $text-title;
    margin-bottom: 2px;
  }
  p {
    font-size: 13px;
    color: $text-muted;
  }
}

.template-arrow {
  color: $primary;
  font-size: 16px;
  opacity: 0;
  transform: translateX(-8px);
  transition: all 0.25s;
  flex-shrink: 0;
}
</style>
