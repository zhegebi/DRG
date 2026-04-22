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
.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}
</style>
