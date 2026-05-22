<template>
  <section class="full-section hero-section" :ref="(el) => observer(el as HTMLElement | null)">
    <div class="hero-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>
    <div class="section-content">
      <div class="hero-badge">🚀 AI 智能医疗平台</div>
      <h1 class="hero-title">
        <span class="title-line">DRG 智能</span>
        <span class="title-line accent">辅助平台</span>
      </h1>
      <p class="hero-subtitle">
        基于大模型与智能体框架，实现疾病诊断相关分组（DRG）的自动化入组、
        文档自动生成与智能测试验证
      </p>
      <div class="hero-actions">
        <button class="btn-primary" @click="goToDRG">立即体验</button>
        <button class="btn-outline" @click="goToGithub">查看源码</button>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <span class="stat-num">26</span>
          <span class="stat-label">MDC 大类</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-num">4</span>
          <span class="stat-label">核心模块</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-num">AI</span>
          <span class="stat-label">智能驱动</span>
        </div>
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
  position: relative;
  overflow: hidden;
}

.hero-section {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  color: white;
}

/* 背景装饰 */
.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
  animation: blobFloat 8s ease-in-out infinite;

  &.blob-1 {
    width: 500px;
    height: 500px;
    background: $primary;
    top: -100px;
    right: -100px;
    animation-delay: 0s;
  }
  &.blob-2 {
    width: 400px;
    height: 400px;
    background: #667eea;
    bottom: -80px;
    left: -80px;
    animation-delay: -3s;
  }
  &.blob-3 {
    width: 300px;
    height: 300px;
    background: #764ba2;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    animation-delay: -6s;
  }
}

@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.section-content {
  text-align: center;
  padding: 40px 20px;
  max-width: 800px;
  position: relative;
  z-index: 1;
  opacity: 0;
  transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.visible .section-content {
  opacity: 1;
  transform: translateY(0);
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  background: rgba($primary, 0.15);
  border: 1px solid rgba($primary, 0.3);
  border-radius: 20px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 28px;
  letter-spacing: 0.5px;
}

.hero-title {
  margin-bottom: 20px;

  .title-line {
    display: block;
    font-size: 52px;
    font-weight: 800;
    letter-spacing: -1px;
    line-height: 1.15;

    &.accent {
      background: linear-gradient(135deg, #60a5fa, $primary);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
  }
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.65);
  max-width: 600px;
  margin: 0 auto 36px;
}

.hero-actions {
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

  &:hover {
    border-color: rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.05);
  }
}

.hero-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-num {
  font-size: 28px;
  font-weight: 800;
  color: white;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.12);
}
</style>
