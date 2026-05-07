<template>
  <section class="full-section hero-section">
    <div class="section-content">
      <h1 class="hero-title">DRG 智能辅助平台</h1>
      <p class="hero-subtitle">基于AI的疾病诊断相关分组智能辅助系统</p>
      <button class="hero-btn" @click="scrollToNext">探索功能 →</button>
    </div>
  </section>
</template>

<script lang="ts" setup>
const emit = defineEmits(['scrollNext'])
const scrollToNext = () => {
  emit('scrollNext')
}
</script>

<style scoped>
.full-section {
  min-height: 100vh;
  width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.section-content {
  text-align: center;
  padding: 20px;
  max-width: 800px;
}

.hero-title {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 16px;
}

.hero-subtitle {
  font-size: 20px;
  margin-bottom: 32px;
  opacity: 0.95;
}

.hero-btn {
  padding: 12px 32px;
  background: white;
  color: #667eea;
  border: none;
  border-radius: 40px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
}
</style>