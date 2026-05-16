<template>
  <div class="home">
    <div class="sections-container" ref="containerRef" @wheel="handleWheel">
      <Section1Hero />
      <Section2Features />
      <Section3Tutorial />
      <Section4Templates />
      <Section5FileBank />
      <Section6Deploy />
      <Section7CTA />
    </div>

    <div class="scroll-progress">
      <div 
        v-for="(_, index) in 7" 
        :key="index"
        class="progress-dot"
        :class="{ active: currentSection === index }"
        @click="scrollToSection(index)"
      ></div>
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
let isScrolling = false

const scrollToSection = (index: number) => {
  if (index < 0 || index >= totalSections || isScrolling) return
  isScrolling = true
  currentSection.value = index
  const sections = containerRef.value?.children
  if (sections && sections[index]) {
    (sections[index] as HTMLElement).scrollIntoView({ behavior: 'smooth' })
  }
  setTimeout(() => {
    isScrolling = false
  }, 500)
}

const handleWheel = (e: WheelEvent) => {
  if (isScrolling) return
  if (e.deltaY > 0 && currentSection.value < totalSections - 1) {
    scrollToSection(currentSection.value + 1)
  } else if (e.deltaY < 0 && currentSection.value > 0) {
    scrollToSection(currentSection.value - 1)
  }
}

const handleScroll = () => {
  if (isScrolling) return
  const container = containerRef.value
  if (!container) return
  const sections = Array.from(container.children)
  const scrollTop = container.scrollTop
  const viewportHeight = window.innerHeight
  
  for (let i = 0; i < sections.length; i++) {
    const section = sections[i] as HTMLElement
    const sectionTop = section.offsetTop
    if (scrollTop >= sectionTop - viewportHeight / 3) {
      currentSection.value = i
    }
  }
}

onMounted(() => {
  const container = containerRef.value
  if (container) {
    container.addEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  const container = containerRef.value
  if (container) {
    container.removeEventListener('scroll', handleScroll)
  }
})
</script>

<style scoped>
.home {
  width: 100%;
  min-height: calc(100vh - 64px);
  background: #f8fafc;
}

.sections-container {
  height: calc(100vh - 64px);
  overflow-y: scroll;
  overflow-x: hidden;
  scroll-behavior: smooth;
  scroll-snap-type: y mandatory;
}

.sections-container::-webkit-scrollbar {
  width: 6px;
}

.scroll-progress {
  position: fixed;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 1000;
}

.progress-dot {
  width: 8px;
  height: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s;
}

.progress-dot.active {
  width: 20px;
  border-radius: 4px;
  background: #007fd4;
}
</style>
