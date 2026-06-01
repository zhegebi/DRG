<template>
  <section class="new-doc-view">
    <div class="agent-title-area">
      <h1 class="agent-title">文档生成智能体</h1>
    </div>

    <div class="doc-composer">
      <textarea
        v-model="promptInput"
        class="prompt-input"
        rows="5"
        placeholder="补充生成重点，例如：突出接口定义、模块职责、测试边界和部署视图"
        @keydown="handlePromptKeydown"
      ></textarea>

      <div class="composer-actions">
        <input
          ref="sourceInputRef"
          class="file-input"
          type="file"
          multiple
          accept=".md,.txt,text/markdown,text/plain"
          @change="onSourceFileChange"
        />
        <AppTooltip :text="sourceFiles.length ? sourceFiles.map((file) => file.name).join('、') : '添加文件'">
          <button
            class="composer-tool-button"
            type="button"
            @click="sourceInputRef?.click()"
          >
            <SvgIcon type="mdi" :path="mdiFilePlusOutline" class="button-icon" />
          </button>
        </AppTooltip>
        <button
          v-if="sourceFiles.length"
          class="icon-button"
          type="button"
          aria-label="移除文件"
          @click="clearSourceFiles"
        >
          <SvgIcon type="mdi" :path="mdiClose" class="button-icon" />
        </button>

        <div class="doc-type-dropdown">
          <AppTooltip :text="selectedDocTypeLabel">
            <button
              class="doc-type-control doc-type-trigger"
              type="button"
              :aria-expanded="docTypeMenuOpen"
              aria-label="文档类型"
              @click="docTypeMenuOpen = !docTypeMenuOpen"
            >
              <SvgIcon type="mdi" :path="mdiFormatListBulletedType" class="button-icon" />
            </button>
          </AppTooltip>
          <div v-if="docTypeMenuOpen" class="doc-type-menu">
            <label
              v-for="dt in docTypes"
              :key="dt"
              class="doc-type-option"
              :class="{ checked: selectedDocTypes.includes(dt) }"
            >
              <input v-model="selectedDocTypes" type="checkbox" :value="dt" />
              <span>{{ dt }}</span>
            </label>
          </div>
        </div>

        <div class="generation-mode-dropdown">
          <AppTooltip :text="selectedGenerationModeConfig.label">
            <button
              class="doc-type-control generation-mode-trigger"
              type="button"
              :aria-expanded="generationModeMenuOpen"
              aria-label="生成模式"
              @click="generationModeMenuOpen = !generationModeMenuOpen"
            >
              <SvgIcon type="mdi" :path="mdiFileDocumentOutline" class="button-icon" />
            </button>
          </AppTooltip>
          <div v-if="generationModeMenuOpen" class="generation-mode-menu">
            <button
              v-for="mode in generationModes"
              :key="mode.value"
              class="generation-mode-option"
              :class="{ checked: selectedGenerationMode === mode.value }"
              type="button"
              @click="selectedGenerationMode = mode.value; generationModeMenuOpen = false"
            >
              <span class="generation-mode-label">{{ mode.label }}</span>
              <span class="generation-mode-description">{{ mode.description }}</span>
            </button>
          </div>
        </div>

        <button
          ref="docSubmitButtonRef"
          class="submit-button"
          type="button"
          :disabled="isSubmitting || selectedDocTypes.length === 0"
          @click="submitGeneration"
        >
          <SvgIcon
            type="mdi"
            :path="isSubmitting ? mdiLoading : mdiSend"
            :class="['button-icon', { 'loading-icon': isSubmitting }]"
          />
        </button>
      </div>

      <div v-if="sourceFiles.length" class="composer-file-hint">
        已添加：{{ sourceFiles.map((file) => file.name).join('、') }}
      </div>

      <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import SvgIcon from '@jamescoyle/vue-icon'
import AppTooltip from '@/components/AppTooltip.vue'
import {
  mdiClose,
  mdiFileDocumentOutline,
  mdiFilePlusOutline,
  mdiFormatListBulletedType,
  mdiLoading,
  mdiSend,
} from '@mdi/js'
import { useDocGen } from './useDocGen'

const {
  docTypes,
  selectedDocTypes,
  generationModes,
  selectedGenerationMode,
  promptInput,
  sourceFiles,
  isSubmitting,
  errorMessage,
  sourceInputRef,
  docSubmitButtonRef,
  docTypeMenuOpen,
  generationModeMenuOpen,
  selectedDocTypeLabel,
  selectedGenerationModeConfig,
  submitGeneration,
  handlePromptKeydown,
  onSourceFileChange,
  clearSourceFiles,
} = useDocGen()
</script>

<style lang="scss" scoped>
.new-doc-view {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.agent-title-area {
  width: min(920px, 100%);
  margin: 0 auto 24px;
}

.agent-title {
  margin: 0;
  color: #007fd4;
  font-size: 48px;
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: 0;
  text-align: center;
}

.doc-composer {
  width: min(920px, 100%);
  margin: 0 auto;
  padding: 12px;
  border: 1px solid rgba(0, 127, 212, 0.14);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.composer-file-hint {
  max-width: 100%;
  align-self: flex-end;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-input {
  resize: vertical;
  min-height: 116px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 12px;
  background: #ffffff;
  color: #1e293b;
  font-family: inherit;
  font-size: 14px;
  line-height: 20px;
  outline: none;
}

.doc-type-dropdown,
.generation-mode-dropdown {
  position: relative;
  width: 38px;
  min-width: 38px;
}

.doc-type-trigger,
.generation-mode-trigger {
  width: 38px;
  min-width: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
}

.doc-type-menu,
.generation-mode-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 6px);
  z-index: 20;
  min-width: 220px;
  padding: 6px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
  display: grid;
  gap: 4px;
}

.generation-mode-menu {
  min-width: 260px;
}

.doc-type-option {
  min-height: 32px;
  padding: 0 10px;
  border-radius: 6px;
  color: #475569;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  user-select: none;
}

.doc-type-option input {
  width: 14px;
  height: 14px;
  margin: 0;
  accent-color: #007fd4;
}

.doc-type-option.checked {
  background: #e8f5ff;
  color: #005f9e;
}

.generation-mode-option {
  width: 100%;
  min-height: 44px;
  padding: 8px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  text-align: left;
  display: grid;
  gap: 2px;
}

.generation-mode-option.checked {
  background: #e8f5ff;
  color: #005f9e;
}

.generation-mode-label {
  font-size: 13px;
  font-weight: 800;
}

.generation-mode-description {
  color: #64748b;
  font-size: 12px;
  line-height: 1.35;
}

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

.file-input {
  display: none;
}

.submit-button {
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

.submit-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.submit-button,
.composer-tool-button,
.doc-type-control {
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

.composer-tool-button,
.doc-type-control {
  height: 38px;
  background: #f8fafc;
}

.doc-composer .composer-tool-button,
.doc-composer .submit-button,
.doc-composer .doc-type-trigger,
.doc-composer .generation-mode-trigger,
.icon-button {
  width: 38px;
  min-width: 38px;
  height: 38px;
  min-height: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
  box-shadow: none;
}

.doc-composer .composer-tool-button:hover,
.doc-composer .submit-button:hover,
.doc-composer .doc-type-trigger:hover,
.doc-composer .generation-mode-trigger:hover,
.icon-button:hover {
  background: #eef6ff;
}

.doc-type-control {
  padding-right: 4px;
  cursor: pointer;
}

.doc-type-control.doc-type-trigger,
.doc-type-control.generation-mode-trigger {
  padding: 0;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.icon-button {
  width: 38px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  color: #007fd4;
}

.error-message {
  width: min(920px, 100%);
  margin: 10px auto 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 860px) {
  .agent-title {
    font-size: 36px;
  }

  .composer-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .doc-type-dropdown {
    width: 38px;
    min-width: 38px;
    align-self: flex-end;
  }

  .doc-type-menu {
    left: auto;
    right: 0;
    width: auto;
    min-width: 220px;
    box-sizing: border-box;
  }

  .doc-composer .submit-button,
  .doc-composer .composer-tool-button,
  .doc-composer .doc-type-trigger {
    width: 38px;
    align-self: flex-end;
  }

  .composer-file-hint {
    align-self: stretch;
  }
}
</style>
