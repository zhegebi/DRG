<template>
  <section class="full-section deploy-section">
    <div class="section-content">
      <h2 class="section-title">灵活部署</h2>
      <div class="deploy-options">
        <div class="option">☁️ 云服务版</div>
        <div class="option">🏢 私有化部署</div>
        <div class="option">💻 开源社区版</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.full-section {
  min-height: calc(100vh - 64px);
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

.deploy-options {
  display: flex;
  justify-content: center;
  gap: 30px;
  flex-wrap: wrap;
}

.option {
  background: white;
  padding: 20px 30px;
  border-radius: 12px;
  font-size: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
</style>
