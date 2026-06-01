<template>
  <span
    ref="rootRef"
    class="app-tooltip"
    :class="[
      `app-tooltip-${effectivePlacement}`,
      { 'app-tooltip-block': block, 'app-tooltip-clickable': usesClick },
    ]"
    :aria-describedby="isVisible && !disabled ? tooltipId : undefined"
    @mouseenter="showHover"
    @mouseleave="hideHover"
    @focusin="showHover"
    @focusout="hideHover"
    @click="toggleClick"
    @keydown.esc="close"
  >
    <slot></slot>
  </span>

  <Teleport to="body">
    <Transition name="app-tooltip-fade">
      <span
        v-if="isVisible && !disabled"
        ref="panelRef"
        :id="tooltipId"
        class="app-tooltip-panel"
        :class="`app-tooltip-panel-${effectivePlacement}`"
        :style="panelStyle"
        role="tooltip"
      >
        <slot name="content">{{ text }}</slot>
      </span>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right'
type TooltipTrigger = 'hover' | 'click' | 'both'

interface Props {
  text?: string
  placement?: TooltipPlacement
  trigger?: TooltipTrigger
  disabled?: boolean
  block?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  placement: 'top',
  trigger: 'hover',
  disabled: false,
  block: false,
})

const rootRef = ref<HTMLElement | null>(null)
const panelRef = ref<HTMLElement | null>(null)
const hoverOpen = ref(false)
const clickOpen = ref(false)
const effectivePlacement = ref<TooltipPlacement>(props.placement)
const panelStyle = ref<Record<string, string>>({})
const tooltipId = `tooltip-${Math.random().toString(36).slice(2, 10)}`

const usesHover = computed(() => props.trigger === 'hover' || props.trigger === 'both')
const usesClick = computed(() => props.trigger === 'click' || props.trigger === 'both')
const isVisible = computed(() => {
  return Boolean((usesHover.value && hoverOpen.value) || (usesClick.value && clickOpen.value))
})

const OPPOSITES: Record<TooltipPlacement, TooltipPlacement> = {
  top: 'bottom',
  bottom: 'top',
  left: 'right',
  right: 'left',
}
const GAP = 8
const VIEWPORT_PADDING = 12

const clamp = (value: number, min: number, max: number) => {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

const choosePlacement = (
  rootRect: DOMRect,
  panelWidth: number,
  panelHeight: number,
  viewportWidth: number,
  viewportHeight: number,
) => {
  const space = {
    top: rootRect.top - VIEWPORT_PADDING,
    bottom: viewportHeight - rootRect.bottom - VIEWPORT_PADDING,
    left: rootRect.left - VIEWPORT_PADDING,
    right: viewportWidth - rootRect.right - VIEWPORT_PADDING,
  }
  const fits = {
    top: space.top >= panelHeight + GAP,
    bottom: space.bottom >= panelHeight + GAP,
    left: space.left >= panelWidth + GAP,
    right: space.right >= panelWidth + GAP,
  }
  const preferred = props.placement
  if (fits[preferred]) return preferred
  const opposite = OPPOSITES[preferred]
  if (fits[opposite]) return opposite
  if (preferred === 'top' || preferred === 'bottom') {
    return space.bottom >= space.top ? 'bottom' : 'top'
  }
  return space.right >= space.left ? 'right' : 'left'
}

const updatePanelPosition = () => {
  const root = rootRef.value
  const panel = panelRef.value
  if (!root || !panel || !isVisible.value || props.disabled) return

  const rootRect = root.getBoundingClientRect()
  const viewportWidth = document.documentElement.clientWidth || window.innerWidth
  const viewportHeight = document.documentElement.clientHeight || window.innerHeight
  const panelRect = panel.getBoundingClientRect()
  const panelWidth = panelRect.width || panel.offsetWidth
  const panelHeight = panelRect.height || panel.offsetHeight
  const placement = choosePlacement(rootRect, panelWidth, panelHeight, viewportWidth, viewportHeight)

  let top = rootRect.bottom + GAP
  let left = rootRect.left + (rootRect.width - panelWidth) / 2
  if (placement === 'top') {
    top = rootRect.top - panelHeight - GAP
  } else if (placement === 'left') {
    top = rootRect.top + (rootRect.height - panelHeight) / 2
    left = rootRect.left - panelWidth - GAP
  } else if (placement === 'right') {
    top = rootRect.top + (rootRect.height - panelHeight) / 2
    left = rootRect.right + GAP
  }

  effectivePlacement.value = placement
  panelStyle.value = {
    left: `${Math.round(clamp(left, VIEWPORT_PADDING, viewportWidth - panelWidth - VIEWPORT_PADDING))}px`,
    top: `${Math.round(clamp(top, VIEWPORT_PADDING, viewportHeight - panelHeight - VIEWPORT_PADDING))}px`,
  }
}

const schedulePanelPosition = async () => {
  await nextTick()
  updatePanelPosition()
  requestAnimationFrame(updatePanelPosition)
}

const repositionIfOpen = () => {
  if (isVisible.value) updatePanelPosition()
}

const showHover = () => {
  if (!usesHover.value || props.disabled) return
  hoverOpen.value = true
  void schedulePanelPosition()
}

const hideHover = () => {
  if (!usesHover.value) return
  hoverOpen.value = false
}

const toggleClick = () => {
  if (!usesClick.value || props.disabled) return
  clickOpen.value = !clickOpen.value
  if (clickOpen.value) void schedulePanelPosition()
}

const close = () => {
  hoverOpen.value = false
  clickOpen.value = false
}

const closeFromOutside = (event: PointerEvent) => {
  const root = rootRef.value
  const panel = panelRef.value
  const target = event.target as Node
  if (!root || root.contains(target) || panel?.contains(target)) return
  clickOpen.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', closeFromOutside, true)
  window.addEventListener('resize', repositionIfOpen)
  window.addEventListener('scroll', repositionIfOpen, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', closeFromOutside, true)
  window.removeEventListener('resize', repositionIfOpen)
  window.removeEventListener('scroll', repositionIfOpen, true)
})
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.app-tooltip {
  position: relative;
  display: inline-flex;
  min-width: 0;
}

.app-tooltip-block {
  display: flex;
  width: 100%;
}

.app-tooltip-clickable {
  cursor: help;
}

.app-tooltip-panel {
  position: fixed;
  z-index: 10000;
  width: max-content;
  max-width: min(320px, calc(100vw - 24px));
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 36px rgba($dark, 0.16);
  color: $text-title;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
  pointer-events: none;
  white-space: normal;
}

.app-tooltip-fade-enter-active,
.app-tooltip-fade-leave-active {
  transition: opacity 0.14s ease;
}

.app-tooltip-fade-enter-from,
.app-tooltip-fade-leave-to {
  opacity: 0;
}
</style>
