<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ControlBar from './ControlBar.vue';
import { client } from '@/api/client.gen';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const showControlBar = computed(() => route.name !== 'auth');

onMounted(() => {
  // 全局拦截 401：access_token 过期时自动登出
  client.instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error?.response?.status === 401) {
        const auth = useAuthStore();
        const wasLoggedIn = auth.isAuthenticated;
        auth.clearAuth();
        if (wasLoggedIn && route.name !== 'auth') {
          router.push('/auth');
        }
      }
      return Promise.reject(error);
    }
  );
});
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
