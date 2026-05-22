<template>
  <section class="full-section tutorial-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="section-content">
      <div class="section-header">
        <span class="section-badge">快速上手</span>
        <h2 class="section-title">三步完成 DRG 入组</h2>
        <p class="section-desc">简洁的工作流程，让智能体为您分担复杂的分组工作</p>
      </div>

      <div class="steps-row">
        <div class="step-card">
          <div class="step-num">01</div>
          <div class="step-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
          </div>
          <h3>导入病历</h3>
          <p>上传或输入电子病历文本，系统自动结构化提取诊断与手术编码</p>
        </div>

        <div class="step-connector">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
        </div>

        <div class="step-card">
          <div class="step-num">02</div>
          <div class="step-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </div>
          <h3>智能分析</h3>
          <p>AI 自动执行 MDC → ADRG → DRG 三层分组，含 MCC/CC 排除表校验</p>
        </div>

        <div class="step-connector">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
        </div>

        <div class="step-card">
          <div class="step-num">03</div>
          <div class="step-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </div>
          <h3>获取结果</h3>
          <p>查看 DRG 组号、组名、入组原因说明，支持结果追溯与审核</p>
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
  max-width: 1000px;
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
  margin-bottom: 56px;
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
  max-width: 450px;
  margin: 0 auto;
}

/* 步骤 */
.steps-row {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
}

.step-card {
  flex: 1;
  max-width: 260px;
  text-align: center;
  padding: 36px 24px;
  border-radius: 16px;
  transition: all 0.3s;

  &:hover {
    background: rgba($primary, 0.03);
  }
}

.step-num {
  font-size: 13px;
  font-weight: 700;
  color: $primary;
  letter-spacing: 2px;
  margin-bottom: 16px;
}

.step-icon-box {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba($primary, 0.08), rgba($primary, 0.03));
  color: $primary;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.step-card h3 {
  font-size: 18px;
  font-weight: 700;
  color: $text-title;
  margin-bottom: 10px;
}

.step-card p {
  font-size: 14px;
  line-height: 1.7;
  color: $text-content;
}

.step-connector {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-top: 72px;
}
</style>
