<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import ControlBar from './ControlBar.vue';

const route = useRoute();
const showControlBar = computed(() => route.name !== 'auth');
</script>
<template>
    <div class="app-container">
        <ControlBar v-if="showControlBar"></ControlBar>
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
