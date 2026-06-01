<template>
  <aside class="run-sidebar">
    <div class="sidebar-actions">
      <button class="new-doc-button" type="button" @click="openNewDoc">
        <SvgIcon type="mdi" :path="mdiPlus" class="button-icon" />
        <span>新建任务</span>
      </button>
      <button
        class="edit-toggle-btn"
        type="button"
        title="管理任务"
        :class="{ active: isEditing }"
        @click="isEditing = !isEditing"
      >
        <SvgIcon type="mdi" :path="mdiPencil" class="button-icon" />
      </button>
    </div>

    <div class="run-list">
      <div
        v-for="run in runHistory"
        :key="run.run_id"
        class="run-card-row"
      >
        <button
          class="run-card"
          :class="{ active: selectedRunId === run.run_id }"
          type="button"
          @click="selectRun(run.run_id)"
        >
          <span class="run-card-main">
            <AppTooltip :text="run.task_title || run.doc_type" placement="top">
              <span class="run-name">{{ displayTaskTitle(run) }}</span>
            </AppTooltip>
            <span class="run-time">{{ formatTime(run.created_at || run.updated_at) }}</span>
          </span>
          <AppTooltip :text="runStatusTooltipText(run)" placement="left">
            <SvgIcon
              type="mdi"
              :path="runStatusIcon(run.status)"
              class="run-status-icon"
              :class="runStatusClass(run.status)"
            />
          </AppTooltip>
        </button>
        <button
          v-if="isEditing"
          class="run-delete-btn"
          type="button"
          title="删除任务"
          @click.stop="deleteRunById(run.run_id)"
        >
          <SvgIcon
            type="mdi"
            :path="mdiDelete"
            class="run-delete-icon"
          />
        </button>
      </div>
      <div v-if="runHistory.length === 0" class="run-empty">暂无任务</div>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import SvgIcon from '@jamescoyle/vue-icon'
import AppTooltip from '@/components/AppTooltip.vue'
import { mdiDelete, mdiPencil, mdiPlus } from '@mdi/js'
import { useDocGen } from './useDocGen'

const {
  runHistory,
  selectedRunId,
  displayTaskTitle,
  formatTime,
  runStatusIcon,
  runStatusClass,
  runStatusTooltipText,
  openNewDoc,
  selectRun,
  deleteRunById,
} = useDocGen()

const isEditing = ref(false)
</script>

<style lang="scss" scoped>
.run-sidebar {
  padding: 16px;
  box-sizing: border-box;
  border-right: 1px solid rgba(0, 127, 212, 0.12);
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.sidebar-actions {
  display: flex;
  gap: 8px;
}

.new-doc-button {
  flex: 1;
  min-height: 44px;
  border: none;
  border-radius: 8px;
  background: #007fd4;
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.button-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.edit-toggle-btn {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.edit-toggle-btn:hover,
.edit-toggle-btn.active {
  border-color: rgba(0, 127, 212, 0.32);
  background: #eef8ff;
  color: #007fd4;
}

.run-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.run-card-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.run-card {
  flex: 1;
  min-width: 0;
  min-height: 58px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}

.run-card:hover,
.run-card-row:hover .run-card {
  border-color: rgba(0, 127, 212, 0.28);
  background: #f8fbff;
}

.run-card.active {
  border-color: rgba(0, 127, 212, 0.56);
  background: #eef8ff;
}

.run-card-row:hover .run-card.active {
  border-color: rgba(0, 127, 212, 0.62);
  background: #e6f4ff;
}

.run-card-row:hover .run-delete-btn {
  color: #64748b;
}

.run-card-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.run-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 700;
}

.run-time,
.run-empty {
  color: #64748b;
  font-size: 12px;
}

.run-empty {
  padding: 8px 4px;
}

.run-status-icon {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  fill: currentColor;
}

.run-delete-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.run-delete-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.run-delete-icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.status-running {
  color: #007fd4;
}

.status-completed {
  color: #16a34a;
}

.status-stopped {
  color: #f59e0b;
}

.status-error {
  color: #dc2626;
}
</style>
