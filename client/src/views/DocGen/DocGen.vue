<template>
  <div class="docgen-layout">
    <RunSidebar />
    <main class="docgen-main">
      <DocComposer v-if="!selectedRunId" />
      <RunDetail v-else />
    </main>
    <PreviewDrawer />
  </div>
</template>

<script lang="ts" setup>
import RunSidebar from './RunSidebar.vue'
import DocComposer from './DocComposer.vue'
import RunDetail from './RunDetail.vue'
import PreviewDrawer from './PreviewDrawer.vue'
import { useDocGen } from './useDocGen'

const { selectedRunId } = useDocGen()
</script>

<style lang="scss" scoped>
@use "@/common/global.scss" as *;

.docgen-layout {
  height: calc(100vh - $control-bar-height);
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f8fafc;
  color: #1e293b;
  position: relative;
  overflow: hidden;
}

.docgen-main {
  height: 100%;
  min-height: 0;
  padding: 28px 32px;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 860px) {
  .docgen-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .docgen-main {
    padding: 22px 18px;
  }
}
</style>
