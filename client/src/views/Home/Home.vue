<template>
  <div class="home">
    <div class="sections-container" ref="containerRef">
      <Section1Hero :observer="observeSection" />
      <Section2Features :observer="observeSection" />
      <Section3Tutorial :observer="observeSection" />
      <Section4Templates :observer="observeSection" />
      <Section5FileBank :observer="observeSection" />
      <Section6Deploy :observer="observeSection" />
      <Section7CTA :observer="observeSection" />
    </div>

    <div class="scroll-progress">
      <div
        v-for="(_, index) in 7"
        :key="index"
        class="progress-dot"
        :class="{ active: currentSection === index }"
        @click="scrollToSection(index)"
      >
        <div class="dot-inner"></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Section1Hero from './Section1Hero.vue'
import Section2Features from './Section2Features.vue'
import Section3Tutorial from './Section3Tutorial.vue'
import Section4Templates from './Section4Templates.vue'
import Section5FileBank from './Section5FileBank.vue'
import Section6Deploy from './Section6Deploy.vue'
import Section7CTA from './Section7CTA.vue'

const containerRef = ref<HTMLElement>()
const currentSection = ref(0)
const totalSections = 7

// 滚动到指定区块
const scrollToSection = (index: number) => {
  if (index < 0 || index >= totalSections) return
  const sections = containerRef.value?.children
  if (sections && sections[index]) {
    (sections[index] as HTMLElement).scrollIntoView({ behavior: 'smooth' })
  }
}

// 监听滚动更新进度点
const handleScroll = () => {
  const container = containerRef.value
  if (!container) return
  const sections = Array.from(container.children)
  const scrollTop = container.scrollTop
  const viewportHeight = window.innerHeight

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i] as HTMLElement
    const sectionTop = section.offsetTop
    const threshold = i === 0 ? 0 : viewportHeight * 0.4
    if (scrollTop >= sectionTop - threshold) {
      currentSection.value = i
    }
  }
}

// IntersectionObserver：给可见区块添加 .visible 类
const observeSection = (el: HTMLElement | null) => {
  if (!el) return
  observerRef.value?.observe(el)
}

const observerRef = ref<IntersectionObserver | null>(null)

onMounted(() => {
  const container = containerRef.value
  if (container) {
    container.addEventListener('scroll', handleScroll)
  }

  observerRef.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
        }
      })
    },
    { threshold: 0.15 }
  )
})

onUnmounted(() => {
  const container = containerRef.value
  if (container) {
    container.removeEventListener('scroll', handleScroll)
  }
  observerRef.value?.disconnect()
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.home {
  width: 100%;
  min-height: calc(100vh - $control-bar-height);
  background: $bg-page;
  position: relative;
}

.sections-container {
  height: calc(100vh - $control-bar-height);
  overflow-y: scroll;
  overflow-x: hidden;
  scroll-snap-type: y mandatory;
  scroll-behavior: smooth;

  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.12);
    border-radius: 2px;
  }
}

/* 滚动进度点 */
.scroll-progress {
  position: fixed;
  right: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 100;
}

.progress-dot {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;

  .dot-inner {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.18);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  }

  &:hover .dot-inner {
    background: rgba(0, 0, 0, 0.35);
    transform: scale(1.3);
  }

  &.active .dot-inner {
    width: 10px;
    height: 10px;
    background: $primary;
    box-shadow: 0 0 8px rgba($primary, 0.4);
  }
}
</style>
