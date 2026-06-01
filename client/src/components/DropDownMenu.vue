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
      <span class="trigger-actions">
        <AppTooltip v-if="statusIcon" :text="statusTitle">
          <SvgIcon
            type="mdi"
            :path="statusIcon"
            class="trigger-status-icon"
            :class="statusClass"
          />
        </AppTooltip>
        <span class="trigger-arrow" aria-hidden="true"></span>
      </span>
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import AppTooltip from '@/components/AppTooltip.vue'
import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiClockOutline,
  mdiProgressClock,
} from '@mdi/js'

export type DropDownStatus = 'pending' | 'running' | 'success' | 'failed'

interface Props {
  title?: string
  content?: string
  defaultOpen?: boolean
  panelType?: 'text' | 'menu'
  status?: DropDownStatus
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
const bottomStickThreshold = 25

const statusIconMap: Record<DropDownStatus, string> = {
  pending: mdiClockOutline,
  running: mdiProgressClock,
  success: mdiCheckCircleOutline,
  failed: mdiAlertCircleOutline,
}

const statusTitleMap: Record<DropDownStatus, string> = {
  pending: 'pending',
  running: 'running',
  success: 'success',
  failed: 'failed',
}

const statusIcon = computed(() => {
  return props.status ? statusIconMap[props.status] : ''
})

const statusTitle = computed(() => {
  return props.status ? statusTitleMap[props.status] : ''
})

const statusClass = computed(() => {
  return props.status ? `trigger-status-icon--${props.status}` : ''
})

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
@use "@/common/global.scss" as *;

.dropdown-menu {
  width: 100%;
  max-width: 960px;
  color: $text-body;
}

.dropdown-trigger {
  width: 100%;
  min-height: 44px;
  padding: 8px 16px;
  border: 1px solid rgba($primary, 0.16);
  border-radius: 8px;
  background: linear-gradient(180deg, $bg-white 0%, $bg-hover 100%);
  box-shadow: 0 1px 4px rgba($dark, 0.06);
  color: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
}

.dropdown-trigger:focus-visible {
  outline: 3px solid rgba($primary, 0.18);
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
  color: $text-title;
}

.trigger-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.trigger-status-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: currentColor;
}

.trigger-status-icon--pending {
  color: $text-muted;
}

.trigger-status-icon--running {
  color: $primary;
}

.trigger-status-icon--success {
  color: $success;
}

.trigger-status-icon--failed {
  color: $danger;
}

.trigger-arrow {
  width: 11px;
  height: 11px;
  flex: 0 0 auto;
  border-right: 2px solid $primary;
  border-bottom: 2px solid $primary;
  transform: rotate(45deg);
}

.dropdown-menu.is-open > .dropdown-trigger {
  border-color: rgba($primary, 0.45);
  box-shadow: 0 4px 14px rgba($dark, 0.08);
}

.dropdown-menu.is-open > .dropdown-trigger .trigger-arrow {
  transform: rotate(-135deg);
}

.dropdown-content {
  margin-top: 5px;
  height: 100px;
  padding: 5px 15px;
  border: 1px solid rgba($primary, 0.12);
  border-radius: 8px;
  background: $bg-white;
  box-shadow: 0 8px 24px rgba($dark, 0.08);
  font-size: 14px;
  line-height: 1.8;
  color: $text-content;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  scrollbar-width: thin;
  scrollbar-color: rgba($primary, 0.35) transparent;
}

.dropdown-content--menu {
  height: auto;
  padding: 10px;
  white-space: normal;
}

.dropdown-content--menu :deep(.dropdown-menu) {
  max-width: none;
  border: none;
}

.dropdown-content--menu :deep(.dropdown-menu + .dropdown-menu) {
  margin-top: 6px;
}

.dropdown-content--menu :deep(.dropdown-trigger) {
  border: none;
  border-radius: 6px;
  background: transparent;
  box-shadow: none;
  padding: 6px 12px;
}

.dropdown-content--menu :deep(.dropdown-trigger:hover) {
  background: rgba($primary, 0.05);
}

.dropdown-content--menu :deep(.dropdown-menu.is-open > .dropdown-trigger) {
  background: rgba($primary, 0.06);
  box-shadow: none;
}

.dropdown-content--menu :deep(.dropdown-content) {
  border: none;
  background: transparent;
  box-shadow: none;
  padding: 4px 0 4px 12px;
  border-radius: 0;
  margin-top: 2px;
}

.dropdown-content--menu :deep(.trigger-title) {
  font-size: 14px;
  font-weight: 600;
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
  background: rgba($primary, 0.35);
  border-radius: 999px;
}

.dropdown-content::-webkit-scrollbar-track {
  background: transparent;
}

</style>
