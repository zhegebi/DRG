<template>
  <section class="full-section templates-section">
    <div class="section-content">
      <h2 class="section-title">精选模板</h2>
      <div class="templates-grid">
        <div class="template">❤️ 心血管疾病</div>
        <div class="template">🫁 呼吸系统疾病</div>
        <div class="template">🧬 肿瘤疾病</div>
        <div class="template">🔪 外科手术</div>
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
  text-align: center;
  padding: 40px;
}

.section-title {
  font-size: 36px;
  margin-bottom: 48px;
  color: #1e293b;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  max-width: 500px;
  margin: 0 auto;
}

.template {
  background: white;
  padding: 20px;
  border-radius: 12px;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  cursor: pointer;
}
</style>