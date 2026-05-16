<template>
  <div class="dropdown-menu" :class="{ 'is-open': isOpen }">
    <button
      class="dropdown-trigger"
      type="button"
      :aria-expanded="isOpen"
      :aria-controls="panelId"
      @click="toggleMenu"
    >
      <span class="trigger-copy">
        <span class="trigger-title">{{ title }}</span>
      </span>
      <span class="trigger-arrow" aria-hidden="true"></span>
    </button>

    <div
      v-if="isOpen"
      :id="panelId"
      ref="contentRef"
      class="dropdown-content"
      :class="{ 'dropdown-content--menu': panelType === 'menu' }"
    >
      <slot>
        <p>{{ content }}</p>
      </slot>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { nextTick, onMounted, ref, watch } from 'vue'

interface Props {
  title?: string
  content?: string
  defaultOpen?: boolean
  panelType?: 'text' | 'menu'
}

const props = withDefaults(defineProps<Props>(), {
  title: '下拉菜单标题',
  content: '这里可以显示下拉菜单中的详细文字内容。',
  defaultOpen: false,
  panelType: 'text',
})

const isOpen = ref(props.defaultOpen)
const contentRef = ref<HTMLElement | null>(null)
const panelId = `dropdown-panel-${Math.random().toString(36).slice(2, 10)}`
const bottomStickThreshold = 15

const scrollToBottom = () => {
  const content = contentRef.value
  if (!content) return
  content.scrollTop = content.scrollHeight
}

const isContentNearBottom = () => {
  const content = contentRef.value
  if (!content) return false

  return content.scrollHeight - content.scrollTop - content.clientHeight <= bottomStickThreshold
}

const shouldAutoScroll = () => props.panelType === 'text'

const scrollToBottomAfterRender = async () => {
  await nextTick()
  requestAnimationFrame(scrollToBottom)
}

const toggleMenu = async () => {
  isOpen.value = !isOpen.value
  if (!isOpen.value || !shouldAutoScroll()) return

  await scrollToBottomAfterRender()
}

onMounted(() => {
  if (isOpen.value && shouldAutoScroll()) {
    void scrollToBottomAfterRender()
  }
})

watch(
  () => props.content,
  () => {
    if (!isOpen.value) return
    if (!shouldAutoScroll()) return
    if (!isContentNearBottom()) return

    void scrollToBottomAfterRender()
  },
  { flush: 'pre' },
)
</script>

<style lang="scss" scoped>
.dropdown-menu {
  width: 100%;
  max-width: 960px;
  color: #1e293b;
}

.dropdown-trigger {
  width: 100%;
  min-height: 44px;
  padding: 8px 16px;
  border: 1px solid rgba(0, 127, 212, 0.16);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  color: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
}

.dropdown-trigger:focus-visible {
  outline: 3px solid rgba(0, 127, 212, 0.18);
  outline-offset: 3px;
}

.trigger-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trigger-title {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.35;
  color: #0f172a;
}

.trigger-arrow {
  width: 11px;
  height: 11px;
  flex: 0 0 auto;
  border-right: 2px solid #007fd4;
  border-bottom: 2px solid #007fd4;
  transform: rotate(45deg);
}

.dropdown-menu.is-open > .dropdown-trigger {
  border-color: rgba(0, 127, 212, 0.45);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}

.dropdown-menu.is-open > .dropdown-trigger .trigger-arrow {
  transform: rotate(-135deg);
}

.dropdown-content {
  margin-top: 5px;
  height: 60px;
  padding: 5px 15px;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  font-size: 14px;
  line-height: 1.8;
  color: #475569;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 127, 212, 0.35) transparent;
}

.dropdown-content--menu {
  height: auto;
  padding: 10px;
  white-space: normal;
}

.dropdown-content--menu :deep(.dropdown-menu) {
  max-width: none;
}

.dropdown-content--menu :deep(.dropdown-menu + .dropdown-menu) {
  margin-top: 8px;
}

.dropdown-content :deep(p) {
  margin: 0;
  white-space: inherit;
  overflow-wrap: inherit;
  word-break: inherit;
}

.dropdown-content::-webkit-scrollbar {
  width: 6px;
}

.dropdown-content::-webkit-scrollbar-thumb {
  background: rgba(0, 127, 212, 0.35);
  border-radius: 999px;
}

.dropdown-content::-webkit-scrollbar-track {
  background: transparent;
}

</style>
