<template>
  <section class="run-detail-view">
    <header class="run-detail-header">
      <div class="run-title-block">
        <div class="run-detail-label">当前任务</div>
        <div class="run-title-line">
          <h1 class="run-detail-title">{{ selectedRun ? displayTaskTitle(selectedRun) : '文档生成任务' }}</h1>
          <AppTooltip
            v-if="statusRun"
            :text="runStatusTooltipText(statusRun)"
            placement="bottom"
          >
            <span
              class="run-state-icon"
              :class="runStateClass(statusRun.status)"
              role="img"
              :aria-label="runStatusTooltipText(statusRun)"
            >
              <SvgIcon type="mdi" :path="headerRunStatusIcon" class="button-icon" />
            </span>
          </AppTooltip>
        </div>
        <div class="run-detail-meta">{{ selectedRunId }}</div>
      </div>
      <div class="run-title-side">
        <div class="header-progress-actions">
          <div
            v-if="chapterProgressItems.length"
            class="header-progress-rail"
            :class="{
              'progress-flowing': isHeaderProgressFlowing,
              'progress-completed': isHeaderProgressCompleted,
            }"
            :style="headerProgressStyle"
            aria-label="章节进度"
          >
            <AppTooltip
              v-for="item in chapterProgressItems"
              :key="item.title"
              :text="item.title"
              placement="bottom"
            >
              <span
                class="header-progress-step"
                :class="[`chapter-status-${item.status}`, { active: activeChapterTitle === item.title }]"
                :aria-label="`第 ${item.index} 章：${item.title}`"
              >
                <span class="header-progress-dot"></span>
                <span class="header-progress-label">{{ truncateTitle(item.title, 5) }}</span>
              </span>
            </AppTooltip>
          </div>
          <AppTooltip text="点击预览生成结果">
            <button
              class="action-btn action-preview header-preview-button"
              type="button"
              aria-label="预览生成结果"
              :disabled="!selectedRun"
              @click="previewDrawerOpen = true"
            >
              <SvgIcon type="mdi" :path="mdiFileEyeOutline" class="button-icon" />
              <span>预览结果</span>
            </button>
          </AppTooltip>
        </div>
      </div>
    </header>

    <div class="run-detail-scroll">
      <section v-if="selectedRun" class="run-insight-panel">
        <section class="chapter-menu-list">
          <template
            v-for="task in conversationTaskItems"
            :key="task.run.run_id"
          >
            <div class="chapter-process-list">
              <div v-if="task.messages.length" class="conversation-message-list">
                <article
                  v-for="message in task.messages"
                  :key="message.key"
                  class="conversation-message"
                >
                  <div class="conversation-message-meta">
                    <span>{{ message.label }}</span>
                    <time>{{ formatTime(message.time) }}</time>
                  </div>
                  <p>{{ message.content }}</p>
                </article>
              </div>

              <article
                v-for="group in task.groups"
                :key="`${task.run.run_id}-${group.key}`"
                class="chapter-process-card"
                :class="{
                  active: group.title === task.activeChapterTitle,
                  expanded: isChapterGroupExpanded(task.run.run_id, group),
                }"
              >
                <button
                  class="chapter-process-header"
                  type="button"
                  :aria-expanded="isChapterGroupExpanded(task.run.run_id, group)"
                  @click="toggleChapterGroupExpansion(task.run.run_id, group)"
                >
                  <div>
                    <span>第 {{ group.index }} 章</span>
                    <h2>{{ group.title }}</h2>
                  </div>
                  <span class="chapter-process-side">
                    <AppTooltip :text="chapterStatusLabel(group.status)" placement="left">
                      <strong
                        class="chapter-process-status"
                        :class="`chapter-process-status-${group.status}`"
                        :aria-label="chapterStatusLabel(group.status)"
                      >
                        <SvgIcon
                          type="mdi"
                          :path="chapterStatusIcon(group.status)"
                          class="chapter-process-status-icon"
                        />
                      </strong>
                    </AppTooltip>
                    <span class="chapter-event-count">{{ group.events.length }} 条</span>
                    <SvgIcon
                      type="mdi"
                      :path="isChapterGroupExpanded(task.run.run_id, group) ? mdiChevronUp : mdiChevronDown"
                      class="chapter-process-chevron"
                    />
                  </span>
                </button>
                <div v-if="isChapterGroupExpanded(task.run.run_id, group)" class="chapter-process-body">
                <article
                  v-for="finalEvt in chapterFinalEvents(group)"
                  :key="`${task.run.run_id}-${group.key}-final-${finalEvt.id}`"
                  class="chapter-final-result"
                >
                  <header>
                    <div>
                      <span>章节最终结果</span>
                      <h3>{{ group.title }}</h3>
                    </div>
                    <time>{{ formatTime(finalEvt.time) }}</time>
                  </header>
                  <pre>{{ chapterFinalBody(finalEvt) }}</pre>
                </article>
                <div
                  v-if="group.events.length"
                  class="process-event-list unified"
                >
                  <article
                    v-for="eventGroup in visibleProcessEventGroups(task.run.run_id, group)"
                    :key="`${task.run.run_id}-${group.key}-${eventGroup.key}`"
                    class="process-event-card"
                    :class="[
                      `process-event-${eventGroup.kind}`,
                      `process-event-state-${eventGroup.state}`,
                      {
                        'is-open': isProcessEventExpanded(task.run.run_id, group, eventGroup),
                        'stream-active': isStreamingEventGroup(task.run, eventGroup),
                        'process-event-error': eventGroup.kind === 'error',
                      },
                    ]"
                  >
                    <button
                      class="process-event-heading"
                      type="button"
                      :aria-expanded="isProcessEventExpanded(task.run.run_id, group, eventGroup)"
                      @click="toggleProcessEventExpansion(task.run.run_id, group, eventGroup)"
                    >
                      <div class="process-event-title-block">
                        <span
                          class="process-event-kind-label"
                          :class="`process-event-kind-${eventGroup.kind}`"
                        >
                          {{ processEventKindLabelMap[eventGroup.kind] }}
                        </span>
                        <h3>{{ eventGroup.title }}</h3>
                      </div>
                      <div class="process-event-meta">
                        <time>{{ formatTime(lastProcessEvent(eventGroup).time) }}</time>
                        <AppTooltip
                          v-if="shouldShowProcessEventGroupStatus(eventGroup)"
                          :text="processEventGroupStatusText(eventGroup, task.run)"
                          placement="left"
                        >
                        <span
                          class="process-event-current-status"
                          :class="`process-event-current-${processEventGroupVisualState(task.run, eventGroup)}`"
                          :aria-label="processEventGroupStatusText(eventGroup, task.run)"
                        >
                          <SvgIcon
                            type="mdi"
                            :path="processExecutionStatusIcon(processEventGroupVisualState(task.run, eventGroup))"
                            :class="[
                              'process-status-icon',
                              { 'loading-icon': processEventGroupVisualState(task.run, eventGroup) === 'running' },
                            ]"
                          />
                        </span>
                        </AppTooltip>
                        <SvgIcon
                          type="mdi"
                          :path="isProcessEventExpanded(task.run.run_id, group, eventGroup) ? mdiChevronUp : mdiChevronDown"
                          class="process-event-chevron"
                        />
                      </div>
                    </button>
                    <div
                      v-if="isProcessEventExpanded(task.run.run_id, group, eventGroup)
                        && visibleProcessEntries(task.run.run_id, group, eventGroup).length"
                      class="process-event-entry-list"
                    >
                      <div class="process-event-entry-panel">
                        <div
                          v-for="evt in visibleProcessEntries(task.run.run_id, group, eventGroup)"
                          :key="`${eventGroup.key}-${evt.id}`"
                          class="process-event-entry"
                          :class="[
                            `process-event-entry-${processEventKind(evt)}`,
                            { 'process-event-entry-request': evt.type === 'llm_request' },
                          ]"
                        >
                          <div v-if="isRequestRecordEvent(evt)" class="process-request-record">
                            <div class="process-request-main">
                              <span class="process-request-turn">{{ processRequestTurnLabel(evt) }}</span>
                              <span class="process-request-context">{{ processRequestRecordContext(evt, group) }}</span>
                            </div>
                            <time class="process-request-time">{{ formatTime(evt.time) }}</time>
                          </div>
                          <template v-else>
                            <div class="process-event-entry-head">
                              <span class="process-event-entry-title">
                                <strong>{{ processEventEntryTitle(evt, group) }}</strong>
                              </span>
                              <span class="process-event-entry-meta">
                                <time>{{ formatTime(evt.time) }}</time>
                                <AppTooltip
                                  v-if="shouldShowProcessEventEntryStatus(evt)"
                                  :text="processEventEntryStatusText(evt, eventGroup)"
                                  placement="left"
                                >
                                <span
                                  class="process-event-entry-status"
                                  :class="`process-event-current-${processEventEntryState(evt, eventGroup)}`"
                                  :aria-label="processEventEntryStatusText(evt, eventGroup)"
                                >
                                  <SvgIcon
                                    type="mdi"
                                    :path="processExecutionStatusIcon(processEventEntryState(evt, eventGroup))"
                                    :class="[
                                      'process-status-icon',
                                      { 'loading-icon': processEventEntryState(evt, eventGroup) === 'running' },
                                    ]"
                                  />
                                </span>
                                </AppTooltip>
                              </span>
                            </div>
                            <div
                              v-if="processEventDetailItems(evt).length"
                              class="process-event-detail-grid"
                            >
                              <div
                                v-for="detail in processEventDetailItems(evt)"
                                :key="detail.label"
                                class="process-event-detail-item"
                                :class="{ wide: detail.wide }"
                              >
                                <span class="process-event-detail-label">{{ detail.label }}</span>
                                <span class="process-event-detail-value">{{ detail.value }}</span>
                              </div>
                            </div>
                            <pre
                              v-else-if="eventHasBody(evt)"
                              class="process-event-body"
                              :class="{ streaming: isStreamingEventForRun(task.run, evt), prose: processEventKind(evt) !== 'tool' }"
                            >{{ processEventBody(evt) }}</pre>
                          </template>
                        </div>
                      </div>
                      <button
                        v-if="hasMoreProcessEntries(task.run.run_id, group, eventGroup)"
                        class="process-virtual-footer process-entry-footer"
                        type="button"
                        @click="loadMoreProcessEntries(task.run.run_id, group, eventGroup)"
                      >
                        <SvgIcon
                          v-if="isProcessEntryGroupLoading(task.run.run_id, group, eventGroup)"
                          type="mdi"
                          :path="mdiLoading"
                          class="button-icon loading-icon"
                        />
                        <span>
                          {{ isProcessEntryGroupLoading(task.run.run_id, group, eventGroup)
                            ? '正在加载更多细节'
                            : `继续加载 ${visibleProcessEntryCount(task.run.run_id, group, eventGroup)} / ${eventGroup.events.length}` }}
                        </span>
                      </button>
                    </div>
                  </article>
                  <button
                    v-if="hasMoreProcessEvents(task.run.run_id, group)"
                    class="process-virtual-footer"
                    type="button"
                    @click="loadMoreProcessEvents(task.run.run_id, group)"
                  >
                    <SvgIcon
                      v-if="isProcessGroupLoading(task.run.run_id, group)"
                      type="mdi"
                      :path="mdiLoading"
                      class="button-icon loading-icon"
                    />
                    <span>
                      {{ isProcessGroupLoading(task.run.run_id, group)
                        ? '正在加载更多过程'
                        : `继续加载 ${visibleProcessCount(task.run.run_id, group)} / ${processEventGroupTotalCount(group)}` }}
                    </span>
                  </button>
                </div>
                <div
                  v-else
                  class="result-empty"
                  :class="{ waiting: shouldShowGroupLoading(task.run, group) }"
                >
                  <SvgIcon
                    v-if="shouldShowGroupLoading(task.run, group)"
                    type="mdi"
                    :path="mdiLoading"
                    class="button-icon loading-icon"
                  />
                  <span>{{ group.emptyText }}</span>
                </div>
                </div>
              </article>
            </div>
          </template>
        </section>
      </section>
    </div>

    <div v-if="selectedRun && isSelectedRunActive" class="bottom-operation-bar">
      <div class="bottom-operation-card generation-control-card">
        <div class="generation-control-main">
          <div class="generation-control-text">
            <SvgIcon type="mdi" :path="mdiLoading" class="button-icon loading-icon" />
            <span>{{ isTerminating ? '正在终止当前任务' : '任务正在生成' }}</span>
          </div>
          <button
            class="action-btn action-terminate"
            type="button"
            :disabled="!canTerminateRun"
            @click="handleTerminate"
          >
            <SvgIcon
              type="mdi"
              :path="isTerminating ? mdiLoading : mdiStopCircleOutline"
              :class="['button-icon', { 'loading-icon': isTerminating }]"
            />
            {{ isTerminating ? '终止中' : '终止' }}
          </button>
        </div>
        <div v-if="errorMessage" class="composer-error-inline">{{ errorMessage }}</div>
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import SvgIcon from '@jamescoyle/vue-icon'
import AppTooltip from '@/components/AppTooltip.vue'
import {
  mdiChevronDown,
  mdiChevronUp,
  mdiFileEyeOutline,
  mdiLoading,
  mdiStopCircleOutline,
} from '@mdi/js'
import { useDocGen } from './useDocGen'

const {
  selectedRun,
  selectedRunId,
  statusRun,
  isSelectedRunActive,
  isTerminating,
  canTerminateRun,
  errorMessage,
  chapterProgressItems,
  activeChapterTitle,
  headerProgressStyle,
  isHeaderProgressCompleted,
  isHeaderProgressFlowing,
  headerRunStatusIcon,
  conversationTaskItems,
  previewDrawerOpen,
  displayTaskTitle,
  formatTime,
  truncateTitle,
  runStateClass,
  runStatusTooltipText,
  chapterStatusLabel,
  chapterStatusIcon,
  chapterFinalEvents,
  chapterFinalBody,
  isChapterGroupExpanded,
  toggleChapterGroupExpansion,
  shouldShowGroupLoading,
  visibleProcessEventGroups,
  hasMoreProcessEvents,
  isProcessGroupLoading,
  processEventGroupTotalCount,
  visibleProcessCount,
  loadMoreProcessEvents,
  isProcessEventExpanded,
  toggleProcessEventExpansion,
  isStreamingEventGroup,
  isStreamingEventForRun,
  processEventGroupVisualState,
  visibleProcessEntries,
  hasMoreProcessEntries,
  isProcessEntryGroupLoading,
  visibleProcessEntryCount,
  loadMoreProcessEntries,
  isRequestRecordEvent,
  processRequestTurnLabel,
  processRequestRecordContext,
  processEventGroupStatusText,
  processEventEntryStatusText,
  processEventDetailItems,
  eventHasBody,
  processEventBody,
  shouldShowProcessEventGroupStatus,
  shouldShowProcessEventEntryStatus,
  processEventEntryState,
  processExecutionStatusIcon,
  processEventEntryTitle,
  processEventKindLabelMap,
  processEventKind,
  lastProcessEvent,
  handleTerminate,
} = useDocGen()
</script>

<style lang="scss" scoped>
.button-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.loading-icon {
  animation: icon-spin 0.95s linear infinite;
}

@keyframes icon-spin {
  to {
    transform: rotate(360deg);
  }
}

.action-btn {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.action-preview {
  color: #007fd4;
  border-color: rgba(0, 127, 212, 0.32);
}

.action-terminate {
  color: #dc2626;
  border-color: rgba(220, 38, 38, 0.32);
}

.run-detail-view {
  width: min(1080px, 100%);
  height: 100%;
  min-height: 0;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.run-detail-header {
  flex: 0 0 auto;
  position: relative;
  z-index: 4;
  padding-bottom: 2px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.run-title-block {
  min-width: 0;
  flex: 1 1 auto;
}

.run-detail-label {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 13px;
}

.run-detail-title {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
  line-height: 1.25;
}

.run-title-line {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.run-title-line .run-detail-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-detail-meta {
  margin-top: 5px;
  color: #94a3b8;
  font-family: Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

.run-title-side {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0;
}

.header-progress-actions {
  width: auto;
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.header-progress-rail {
  position: relative;
  min-width: 0;
  max-width: min(560px, 48vw);
  padding: 5px 4px 2px;
  overflow-x: auto;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 0;
  scrollbar-width: none;
}

.header-progress-rail::before,
.header-progress-rail::after {
  content: "";
  position: absolute;
  top: 12px;
  left: 33px;
  height: 2px;
  border-radius: 999px;
}

.header-progress-rail::before {
  right: 33px;
  background: #cbd5e1;
}

.header-progress-rail::after {
  z-index: 0;
  right: 33px;
  background:
    linear-gradient(
      90deg,
      #16a34a 0%,
      #16a34a calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--progress-ratio, 0) * 100%),
      transparent calc(var(--progress-ratio, 0) * 100%),
      transparent 100%
    );
}

.header-progress-rail.progress-completed::after {
  background: #16a34a;
}

.header-progress-rail.progress-flowing:not(.progress-completed)::after {
  background:
    linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.72) 48%, transparent 74%),
    linear-gradient(
      90deg,
      #16a34a 0%,
      #16a34a calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--completed-ratio, 0) * 100%),
      #007fd4 calc(var(--progress-ratio, 0) * 100%),
      transparent calc(var(--progress-ratio, 0) * 100%),
      transparent 100%
    );
  background-position: -48px 0, 0 0;
  background-size: 54px 100%, 100% 100%;
  -webkit-mask-image: linear-gradient(
    90deg,
    #000 0%,
    #000 calc(var(--progress-ratio, 0) * 100%),
    transparent calc(var(--progress-ratio, 0) * 100%),
    transparent 100%
  );
  mask-image: linear-gradient(
    90deg,
    #000 0%,
    #000 calc(var(--progress-ratio, 0) * 100%),
    transparent calc(var(--progress-ratio, 0) * 100%),
    transparent 100%
  );
  animation: header-progress-flow 1.05s linear infinite;
}

.header-progress-rail::-webkit-scrollbar {
  display: none;
}

.header-progress-step {
  position: relative;
  z-index: 1;
  width: 58px;
  min-width: 58px;
  color: #64748b;
  display: grid;
  justify-items: center;
  gap: 4px;
}

.header-progress-dot {
  position: relative;
  z-index: 1;
  width: 13px;
  height: 13px;
  padding: 0;
  border: 2px solid #cbd5e1;
  border-radius: 50%;
  background: #ffffff;
}

.header-progress-label {
  max-width: 48px;
  overflow: hidden;
  color: #64748b;
  font-size: 10px;
  line-height: 1.1;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-progress-step.chapter-status-completed .header-progress-dot {
  border-color: #16a34a;
  background: #16a34a;
}

.header-progress-step.chapter-status-running .header-progress-dot {
  border-color: #007fd4;
  background: #007fd4;
}

.header-progress-step.active .header-progress-dot {
  box-shadow: 0 0 0 5px rgba(0, 127, 212, 0.14);
}

.header-progress-step.chapter-status-running .header-progress-dot::after {
  content: "";
  position: absolute;
  inset: -7px;
  border: 2px solid rgba(0, 127, 212, 0.32);
  border-radius: 50%;
  animation: header-progress-dot-pulse 1.25s ease-out infinite;
}

@keyframes header-progress-flow {
  to {
    background-position: 54px 0, 0 0;
  }
}

@keyframes header-progress-dot-pulse {
  0% {
    opacity: 0.75;
    transform: scale(0.72);
  }
  100% {
    opacity: 0;
    transform: scale(1.45);
  }
}

.run-state-icon {
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  border-radius: 6px;
  background: transparent;
  cursor: default;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.run-state-icon .button-icon {
  width: 26px;
  height: 26px;
}

.run-state-running {
  color: #007fd4;
}

.run-state-completed {
  color: #16a34a;
}

.run-state-stopped {
  color: #f59e0b;
}

.run-state-error {
  color: #dc2626;
}

.header-preview-button {
  min-width: 92px;
  min-height: 34px;
  padding: 0 10px;
  flex: 0 0 auto;
  background: transparent;
  white-space: nowrap;
}

.error-message {
  padding: 8px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

.run-insight-panel {
  width: 100%;
  margin: 0 auto;
  display: grid;
  gap: 12px;
}

.run-detail-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 4px 4px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 127, 212, 0.35) transparent;
}

.run-detail-scroll::-webkit-scrollbar {
  width: 6px;
}

.run-detail-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 127, 212, 0.35);
  border-radius: 999px;
}

.run-detail-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.composer-error-inline {
  padding: 8px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

/* Chapter menu */
.chapter-menu-list {
  display: grid;
  gap: 12px;
}

.chapter-process-list {
  display: grid;
  gap: 8px;
  margin-top: 0;
  padding: 10px;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.chapter-process-card {
  min-width: 0;
  border: 1px solid rgba(0, 127, 212, 0.12);
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.chapter-process-card.active {
  border-color: rgba(0, 127, 212, 0.35);
  box-shadow: 0 0 0 3px rgba(0, 127, 212, 0.06);
}

.chapter-process-card.expanded {
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
}

.chapter-process-header {
  width: 100%;
  min-height: 42px;
  padding: 8px 12px;
  border: none;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: inherit;
  cursor: pointer;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chapter-process-card.expanded > .chapter-process-header {
  border-bottom: 1px solid rgba(0, 127, 212, 0.1);
}

.chapter-process-header:focus-visible {
  outline: 3px solid rgba(0, 127, 212, 0.18);
  outline-offset: 3px;
}

.chapter-process-header > div {
  min-width: 0;
}

.chapter-process-header span {
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
}

.chapter-process-header h2 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 17px;
  line-height: 1.35;
  font-weight: 900;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chapter-process-side {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.chapter-process-status,
.chapter-event-count {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.chapter-process-status {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.chapter-process-status-icon {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

.chapter-process-status-running .chapter-process-status-icon {
  animation: icon-spin 0.95s linear infinite;
}

.chapter-process-status-running {
  color: #007fd4;
}

.chapter-process-status-completed {
  color: #16a34a;
}

.chapter-process-status-pending {
  color: #64748b;
}

.chapter-process-chevron {
  width: 17px;
  height: 17px;
  color: #64748b;
}

.chapter-process-body {
  min-width: 0;
}

.chapter-final-result {
  margin: 10px 12px 12px;
  padding: 12px;
  border: 1px solid rgba(14, 116, 144, 0.2);
  border-radius: 8px;
  background: #ecfeff;
}

.chapter-final-result header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.chapter-final-result span {
  color: #0e7490;
  font-size: 12px;
  font-weight: 800;
}

.chapter-final-result h3 {
  margin: 3px 0 0;
  color: #164e63;
  font-size: 14px;
  line-height: 1.35;
}

.chapter-final-result time {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.chapter-final-result pre {
  margin: 10px 0 0;
  padding: 10px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #1e293b;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

/* Conversation messages */
.conversation-message-list {
  display: grid;
  gap: 8px;
}

.conversation-message {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.conversation-message-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.conversation-message p {
  margin: 6px 0 0;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}

/* Process events */
.process-event-heading:focus-visible {
  outline: 3px solid rgba(0, 127, 212, 0.18);
  outline-offset: 3px;
}

.process-event-list {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.process-event-list.unified {
  overflow: visible;
  padding: 10px 12px 12px;
  gap: 6px;
}

.process-event-card {
  border: none;
  border-radius: 8px;
  background: transparent;
  overflow: visible;
}

.process-event-list.unified .process-event-card {
  padding: 0;
  border: none;
  border-radius: 8px;
  background: transparent;
}

.process-event-list.unified .process-event-card.process-event-thought,
.process-event-list.unified .process-event-card.process-event-tool,
.process-event-list.unified .process-event-card.process-event-result,
.process-event-list.unified .process-event-card.process-event-status,
.process-event-list.unified .process-event-card.process-event-error,
.process-event-card.stream-active {
  box-shadow: none;
}

.process-event-heading {
  width: 100%;
  min-height: 40px;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.process-event-heading:hover {
  background: rgba(0, 127, 212, 0.05);
}

.process-event-card.is-open > .process-event-heading {
  background: rgba(0, 127, 212, 0.06);
}

.process-event-card.process-event-thought > .process-event-heading {
  background: #f0f9ff;
}

.process-event-card.process-event-tool > .process-event-heading {
  background: #f5f3ff;
}

.process-event-card.process-event-result > .process-event-heading {
  background: #f0fdf4;
}

.process-event-card.process-event-status > .process-event-heading {
  background: #f8fafc;
}

.process-event-card.process-event-error > .process-event-heading {
  background: #fef2f2;
}

.process-event-card.process-event-thought > .process-event-heading:hover,
.process-event-card.process-event-thought.is-open > .process-event-heading {
  background: #e0f2fe;
}

.process-event-card.process-event-tool > .process-event-heading:hover,
.process-event-card.process-event-tool.is-open > .process-event-heading {
  background: #ede9fe;
}

.process-event-card.process-event-result > .process-event-heading:hover,
.process-event-card.process-event-result.is-open > .process-event-heading {
  background: #dcfce7;
}

.process-event-card.process-event-status > .process-event-heading:hover,
.process-event-card.process-event-status.is-open > .process-event-heading {
  background: #f1f5f9;
}

.process-event-card.process-event-error > .process-event-heading:hover,
.process-event-card.process-event-error.is-open > .process-event-heading {
  background: #fee2e2;
}

.process-event-title-block {
  min-width: 0;
  flex: 1 1 auto;
  display: grid;
  gap: 3px;
}

.process-event-kind-label {
  margin-bottom: 2px;
  color: #007fd4;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  display: inline-flex;
}

.process-event-kind-tool {
  color: #7c3aed;
}

.process-event-kind-result {
  color: #15803d;
}

.process-event-kind-status {
  color: #64748b;
}

.process-event-kind-error {
  color: #dc2626;
}

.process-event-chevron {
  width: 17px;
  height: 17px;
  color: #64748b;
}

.process-event-card h3 {
  min-width: 0;
  margin: 0;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.38;
  font-weight: 900;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-meta {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.process-event-meta time {
  font-size: 13px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.process-event-current-status,
.process-event-entry-status {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.process-status-icon {
  width: 15px;
  height: 15px;
  fill: currentColor;
}

.process-event-current-started { color: #64748b; }
.process-event-current-running { color: #007fd4; }
.process-event-current-completed { color: #16a34a; }
.process-event-current-failed { color: #dc2626; }

/* Process event entries */
.process-event-entry-list {
  width: 100%;
  margin: 4px 0 8px;
  padding: 8px 8px 8px 12px;
  box-sizing: border-box;
  overflow: visible;
  display: grid;
  gap: 8px;
}

.process-event-entry-panel {
  min-width: 0;
  border-radius: 8px;
  background: #f8fafc;
  overflow: hidden;
}

.process-event-entry {
  min-width: 0;
  padding: 8px 10px;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.process-event-entry + .process-event-entry {
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.process-event-entry-thought {
  border-color: rgba(0, 127, 212, 0.18);
  background: rgba(240, 249, 255, 0.72);
}

.process-event-entry-tool {
  border-color: rgba(124, 58, 237, 0.2);
  background: rgba(245, 243, 255, 0.72);
}

.process-event-entry-result {
  border-color: rgba(22, 163, 74, 0.18);
  background: rgba(240, 253, 244, 0.72);
}

.process-event-entry-error {
  border-color: rgba(220, 38, 38, 0.22);
  background: rgba(254, 242, 242, 0.72);
}

.process-event-entry-head {
  min-height: 20px;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.process-event-entry-title {
  flex: 1 1 auto;
  min-width: 0;
  display: inline-flex;
  align-items: center;
}

.process-event-entry-title strong {
  color: #0f172a;
  font-size: 13px;
  line-height: 1.35;
  font-weight: 800;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-entry-meta {
  flex: 0 0 auto;
  margin-left: auto;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  white-space: nowrap;
}

.process-event-entry-meta time {
  font-size: 12px;
  font-weight: 700;
}

.process-event-entry-request {
  padding: 0;
}

.process-request-record {
  width: 100%;
  min-width: 0;
  min-height: 46px;
  padding: 8px 10px;
  box-sizing: border-box;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.35;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 4px;
  align-items: start;
}

.process-request-main {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 5px 10px;
}

.process-request-turn {
  color: #334155;
  font-weight: 800;
  white-space: nowrap;
}

.process-request-context {
  color: #64748b;
  flex: 1 1 180px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-request-time {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  white-space: nowrap;
}

.process-event-entry .process-event-body {
  margin-top: 8px;
}

.process-event-detail-grid {
  margin-top: 7px;
  padding: 7px 9px;
  box-sizing: border-box;
  border-radius: 6px;
  background: #ffffff;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 14px;
}

.process-event-detail-item {
  min-width: 0;
  max-width: 100%;
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
}

.process-event-detail-item.wide {
  flex-basis: 100%;
}

.process-event-detail-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  white-space: nowrap;
}

.process-event-detail-value {
  min-width: 0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-entry-request .process-event-detail-grid {
  gap: 5px 12px;
}

.process-event-body {
  margin: 8px 0 0;
  padding: 10px;
  overflow: visible;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-family: Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.process-event-body.prose {
  color: #1e293b;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
}

.process-event-body.streaming::after {
  content: "";
  display: inline-block;
  width: 7px;
  height: 1em;
  margin-left: 3px;
  vertical-align: -2px;
  background: #007fd4;
  animation: stream-caret 0.9s steps(2, start) infinite;
}

@keyframes stream-caret {
  50% { opacity: 0; }
}

.result-empty {
  min-height: 78px;
  margin: 10px 12px 12px;
  padding: 14px;
  box-sizing: border-box;
  border: 1px dashed rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.result-empty.waiting {
  border-color: rgba(0, 127, 212, 0.22);
  background: #f0f9ff;
  color: #007fd4;
}

.process-event-error {
  background: #fef2f2;
}

.process-virtual-footer {
  width: 100%;
  min-height: 42px;
  border: none;
  border-top: 1px dashed rgba(0, 127, 212, 0.18);
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.process-virtual-footer:hover {
  color: #007fd4;
  background: #f0f9ff;
}

/* Bottom operation bar */
.bottom-operation-bar {
  position: relative;
  flex: 0 0 auto;
  z-index: 8;
  width: 100%;
  margin: 0;
  padding: 14px 0 0;
  box-sizing: border-box;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
  display: flex;
  justify-content: center;
}

.bottom-operation-card {
  width: 100%;
  margin: 0 auto;
  padding: 12px;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  box-sizing: border-box;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.generation-control-card {
  padding: 10px 12px;
}

.generation-control-main {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.generation-control-text {
  min-width: 0;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.generation-control-text .button-icon {
  color: #007fd4;
}

/* Media queries */
@media (max-width: 860px) {
  .run-detail-header,
  .generation-control-main {
    align-items: stretch;
    flex-direction: column;
  }

  .run-title-side {
    width: 100%;
    justify-content: flex-end;
  }

  .header-progress-actions {
    width: 100%;
  }

  .header-progress-rail {
    flex: 1 1 auto;
    max-width: calc(100% - 112px);
    justify-content: flex-start;
  }

  .header-preview-button {
    width: auto;
    min-width: 96px;
    align-self: center;
  }
}
</style>
