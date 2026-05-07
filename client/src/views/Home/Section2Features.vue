<template>
  <section class="full-section features-section">
    <div class="section-content">
      <h2 class="section-title">四大核心能力</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">🧠</div>
          <h3>DRG入组智能体</h3>
          <p>AI自动分组，准确率99.5%</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <h3>文档自动生成</h3>
          <p>一键生成标准医疗文书</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🧪</div>
          <h3>测试用例生成</h3>
          <p>自动化验证分组逻辑</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">☁️</div>
          <h3>虚拟文档系统</h3>
          <p>云端存储，团队协作</p>
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
  background: #f8fafc;
}

.section-content {
  max-width: 1000px;
  width: 100%;
  padding: 40px;
}

.section-title {
  font-size: 36px;
  text-align: center;
  margin-bottom: 48px;
  color: #1e293b;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.feature-card {
  background: white;
  padding: 24px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.feature-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.feature-card h3 {
  font-size: 18px;
  margin-bottom: 8px;
  color: #1e293b;
}

.feature-card p {
  font-size: 14px;
  color: #64748b;
}
</style>