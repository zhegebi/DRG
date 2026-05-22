<template>
  <section class="full-section cta-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="cta-bg">
      <div class="cta-blob cta-blob-1"></div>
      <div class="cta-blob cta-blob-2"></div>
    </div>
    <div class="section-content">
      <h2 class="cta-title">开始使用 DRG 智能平台</h2>
      <p class="cta-desc">提升 DRG 编码效率与准确性，让 AI 为您分担繁琐的分组工作</p>
      <div class="cta-actions">
        <button class="btn-primary" @click="goToDRG">立即体验</button>
        <button class="btn-outline" @click="goToGithub">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
          查看源码
        </button>
      </div>

      <div class="footer-links">
        <a href="https://github.com/zhegebi/DRG" target="_blank">GitHub</a>
        <span class="footer-divider"></span>
        <a href="#">文档中心</a>
        <span class="footer-divider"></span>
        <a href="#">问题反馈</a>
      </div>

      <div class="footer-copy">
        <p>© 2026 DRG 智能辅助平台 · 软件工程课程大作业</p>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { useRouter } from 'vue-router'

defineProps<{ observer: (el: HTMLElement | null) => void }>()

const router = useRouter()
const goToDRG = () => router.push('/DRG')
const goToGithub = () => window.open('https://github.com/zhegebi/DRG', '_blank')
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
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  color: white;
  position: relative;
  overflow: hidden;
}

.cta-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.cta-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.1;

  &.cta-blob-1 {
    width: 600px;
    height: 600px;
    background: $primary;
    top: -200px;
    right: -150px;
    animation: ctaFloat 10s ease-in-out infinite;
  }
  &.cta-blob-2 {
    width: 400px;
    height: 400px;
    background: #667eea;
    bottom: -100px;
    left: -100px;
    animation: ctaFloat 12s ease-in-out infinite -5s;
  }
}

@keyframes ctaFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(20px, -30px) scale(1.1); }
}

.section-content {
  text-align: center;
  padding: 60px 40px;
  max-width: 700px;
  position: relative;
  z-index: 1;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1) 0.1s;
}

.visible .section-content {
  opacity: 1;
  transform: translateY(0);
}

.cta-title {
  font-size: 40px;
  font-weight: 800;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

.cta-desc {
  font-size: 17px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.7;
  margin-bottom: 36px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.cta-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 48px;
}

.btn-primary {
  padding: 14px 36px;
  background: linear-gradient(135deg, $primary, #0099ff);
  color: white;
  border: none;
  border-radius: 40px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba($primary, 0.35);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba($primary, 0.45);
  }
}

.btn-outline {
  padding: 14px 36px;
  background: transparent;
  color: white;
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 40px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  gap: 8px;

  &:hover {
    border-color: rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.05);
  }
}

.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 20px;

  a {
    color: rgba(255, 255, 255, 0.4);
    text-decoration: none;
    font-size: 13px;
    transition: color 0.2s;

    &:hover {
      color: rgba(255, 255, 255, 0.7);
    }
  }
}

.footer-divider {
  width: 1px;
  height: 12px;
  background: rgba(255, 255, 255, 0.15);
}

.footer-copy {
  p {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.25);
  }
}
</style>
