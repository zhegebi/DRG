<template>
  <section class="full-section cta-section">
    <div class="section-content">
      <h2 class="cta-title">开始使用</h2>
      <p class="cta-sub">提升DRG编码效率，从今天开始</p>
      <div class="cta-buttons">
        <button class="btn-primary" @click="goToDRG">立即体验</button>
        <button class="btn-outline" @click="goToGithub">查看源码</button>
      </div>
      <footer class="footer">
        <p>© 2026 DRG 智能辅助平台</p>
      </footer>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const goToDRG = () => router.push('/DRG')
const goToGithub = () => window.open('https://github.com/zhegebi/DRG', '_blank')
</script>

<style scoped>
.full-section {
  min-height: 100vh;
  width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  color: white;
}

.section-content {
  text-align: center;
  padding: 40px;
}

.cta-title {
  font-size: 42px;
  margin-bottom: 16px;
}

.cta-sub {
  font-size: 18px;
  margin-bottom: 32px;
  opacity: 0.9;
}

.cta-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 60px;
}

.btn-primary, .btn-outline {
  padding: 12px 32px;
  font-size: 16px;
  border-radius: 40px;
  cursor: pointer;
}

.btn-primary {
  background: #667eea;
  color: white;
  border: none;
}

.btn-outline {
  background: transparent;
  color: white;
  border: 2px solid white;
}

.footer {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 30px;
  font-size: 12px;
  opacity: 0.6;
}
</style>