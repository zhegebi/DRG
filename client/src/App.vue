<script setup lang="ts">
import ControlBar from './ControlBar.vue';

</script>
<template>
    <div class="app-container">
        <ControlBar></ControlBar>
        <RouterView></RouterView>
    </div>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
    margin: 0;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
}

.app-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}
</style>
