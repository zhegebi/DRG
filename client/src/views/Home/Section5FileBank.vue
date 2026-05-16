<template>
  <section class="full-section filebank-section">
    <div class="section-content">
      <h2 class="section-title">文件库</h2>
      <p class="subtitle">随时随地管理您的病例文档</p>
      <div class="file-demo">
        <div class="file">📄 心梗病例.pdf</div>
        <div class="file">📄 肺炎诊疗记录.docx</div>
        <div class="file">📊 分组统计报告.xlsx</div>
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
  background: white;
}

.section-content {
  text-align: center;
  padding: 40px;
}

.section-title {
  font-size: 36px;
  margin-bottom: 16px;
  color: #1e293b;
}

.subtitle {
  color: #64748b;
  margin-bottom: 40px;
}

.file-demo {
  max-width: 400px;
  margin: 0 auto;
  text-align: left;
}

.file {
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  color: #4a5568;
}
</style>
