<script lang="ts" setup>
import { computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiHomeOutline,
  mdiHome,
  mdiGithub,
  mdiAccountCog,
  mdiMicroscope,
  mdiFileDocumentOutline,
  mdiLogin,
  mdiLogout,
  mdiAccountCircle,
} from "@mdi/js";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// 计算属性：是否已登录
const isLoggedIn = computed(() => authStore.isAuthenticated);
const currentUser = computed(() => authStore.user);

function jumpToGithub() {
  window.open('https://github.com/zhegebi/DRG', '_blank');
}

function jumpToAdmin() {
  alert('管理员功能待实现');
}

// 登录
function handleLogin() {
  router.push('/auth');
}

// 登出
async function handleLogout() {
  await authStore.logout();
  // 如果当前在需要登录的页面，跳转到首页
  if (route.meta.requiresAuth) {
    router.push('/');
  }
}

// 点击用户图标
function handleUserClick() {
  if (isLoggedIn.value) {
    handleLogout();
  } else {
    handleLogin();
  }
}

const showProjectName = computed(() => {
  return !!route.params.projectId;
});

const navItems = [
  { 
    name: "Home", 
    path: "/", 
    label: "首页", 
    routeName: "home",
    iconOutline: mdiHomeOutline,
    iconFilled: mdiHome
  },
  { 
    name: "DRG", 
    path: "/DRG", 
    label: "DRG入组智能体", 
    routeName: "drg",
    iconOutline: mdiMicroscope,
    iconFilled: mdiMicroscope
  },
  { 
    name: "DocGen", 
    path: "/DocGen", 
    label: "文档自动生成智能体", 
    routeName: "docgen",
    iconOutline: mdiFileDocumentOutline,
    iconFilled: mdiFileDocumentOutline
  },
];

const isActive = (item: typeof navItems[0]) => {
  if (item.routeName) return route.name === item.routeName;
  return route.path === item.path;
};
</script>

<template>
  <div class="control-bar">
    <div class="control-content">
      <div class="logo-area">
        <div class="logo-text">DRG</div>
      </div>

      <div class="middle-area">
        <nav class="nav-bar" v-if="!showProjectName">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-link"
            :class="{ active: isActive(item) }"
          >
            <span class="nav-inner">
              <SvgIcon
                v-if="item.iconOutline"
                type="mdi"
                :path="isActive(item) ? item.iconFilled : item.iconOutline"
                class="nav-icon"
              />
              <span class="nav-label">{{ item.label }}</span>
            </span>
          </RouterLink>
        </nav>
        <div v-else class="project-name">
          <h2>项目名称</h2>
        </div>
      </div>

      <div class="right-actions">
        <button class="action-btn github-btn" @click="jumpToGithub" title="GitHub">
          <SvgIcon type="mdi" :path="mdiGithub" class="action-icon" />
        </button>
        <button class="action-btn admin-btn" @click="jumpToAdmin" title="管理员">
          <SvgIcon type="mdi" :path="mdiAccountCog" class="action-icon" />
        </button>
        
        <!-- 用户图标：未登录显示登录图标，已登录显示登出图标 -->
        <div class="user-icon" @click="handleUserClick" :title="isLoggedIn ? '点击退出登录' : '点击登录'">
          <SvgIcon 
            type="mdi" 
            :path="isLoggedIn ? mdiLogout : mdiAccountCircle" 
            class="user-icon-svg"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/common/global.scss' as *;
/* ========== 可调节参数区域 ========== */
.control-bar {
  height: $control-bar-height;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
  position: relative;
  margin: 0;
}

.control-bar .control-content {
  padding: 0 28px;
}

.control-bar .logo-area .logo-text {
  font-size: 24px;
}

.control-bar .middle-area .nav-bar {
  gap: 12px;
}

.control-bar .middle-area .nav-bar .nav-link {
  font-size: 16px;
  padding: 8px 16px;
}

.control-bar .middle-area .nav-bar .nav-link .nav-icon {
  width: 20px;
  height: 20px;
}

.control-bar .middle-area .nav-bar .nav-link .nav-inner {
  gap: 8px;
}

.control-bar .right-actions {
  gap: 10px;
}

.control-bar .right-actions .action-btn {
  width: 34px;
  height: 34px;
}
/* ========== 可调节参数结束 ========== */

/* 基础样式 */
.control-bar {
  display: flex;
  flex-direction: row;
  width: 100%;
  color: black;
  background: #ffffff;
  z-index: 1100;
}

.control-bar .control-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  font-size: 14px;
}

.control-bar .logo-area {
  flex-shrink: 0;
  width: 100px;
}

.control-bar .logo-area .logo-text {
  font-weight: bold;
  color: #007fd4;
}

.control-bar .middle-area {
  flex: 1;
  display: flex;
  justify-content: center;
}

.control-bar .middle-area .nav-bar {
  display: flex;
  align-items: center;
}

.control-bar .middle-area .nav-bar .nav-link {
  color: #000000;
  text-decoration: none;
  font-weight: 500;
  margin: 0 2px;
  transition: all 0.2s ease;
  border-radius: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: rgba(40, 40, 40, 0.75);
}

.control-bar .middle-area .nav-bar .nav-link .nav-inner {
  display: inline-flex;
  align-items: center;
}

.control-bar .middle-area .nav-bar .nav-link .nav-icon {
  display: inline-block;
  fill: currentColor;
}

.control-bar .middle-area .nav-bar .nav-link:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.control-bar .middle-area .nav-bar .nav-link.active {
  color: #007fd4;
  background-color: white;
  box-shadow: 0px 2px 6px rgba(128, 128, 128, 0.15);
}

.control-bar .right-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  width: auto;
  justify-content: flex-end;
  gap: 10px;
}

.control-bar .right-actions .action-btn {
  background: transparent;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  color: #5b5b5b;
}

.control-bar .right-actions .action-btn:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.control-bar .right-actions .action-btn .action-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

/* 用户图标样式 */
.user-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 50%;
  transition: all 0.2s;
  color: #5b5b5b;
}

.user-icon:hover {
  background-color: rgba(0, 0, 0, 0.06);
}

.user-icon .user-icon-svg {
  width: 22px;
  height: 22px;
  fill: currentColor;
}
</style>