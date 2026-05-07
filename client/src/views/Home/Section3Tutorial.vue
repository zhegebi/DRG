<template>
  <section class="full-section tutorial-section">
    <div class="section-content">
      <h2 class="section-title">三步上手</h2>
      <div class="steps">
        <div class="step">
          <div class="step-num">1</div>
          <div class="step-text">导入病历数据</div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-num">2</div>
          <div class="step-text">AI智能分析</div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-num">3</div>
          <div class="step-text">生成医疗文书</div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.full-section {
  min-height: 100vh;
  width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
}

.section-content {
  text-align: center;
  padding: 40px;
}

.section-title {
  font-size: 36px;
  margin-bottom: 48px;
  color: #1e293b;
}

.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
}

.step {
  text-align: center;
}

.step-num {
  width: 60px;
  height: 60px;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 12px;
}

.step-text {
  font-size: 16px;
  color: #4a5568;
}

.step-arrow {
  font-size: 24px;
  color: #cbd5e0;
}
</style>