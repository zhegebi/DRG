<script lang="ts" setup>
import { ref, computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiHomeOutline,
  mdiHome,
  mdiGithub,
  mdiMicroscope,
  mdiFileDocumentOutline,
  mdiLogout,
  mdiAccountCircle,
  mdiEmailOutline,
  mdiAccountOutline,
  mdiIdentifier,
} from "@mdi/js";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// 计算属性：是否已登录
const isLoggedIn = computed(() => authStore.isAuthenticated);
const currentUser = computed(() => authStore.user);

// 悬浮卡片控制
const showUserCard = ref(false);
let hoverTimer: ReturnType<typeof setTimeout> | null = null;

function onUserMouseEnter() {
  if (hoverTimer) clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => {
    showUserCard.value = true;
  }, 200);
}

function onUserMouseLeave() {
  if (hoverTimer) clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => {
    showUserCard.value = false;
  }, 300);
}

function onCardMouseEnter() {
  if (hoverTimer) clearTimeout(hoverTimer);
  showUserCard.value = true;
}

function onCardMouseLeave() {
  showUserCard.value = false;
}

// 显示名称
const displayName = computed(() => {
  const u = currentUser.value;
  if (u?.displayName) return u.displayName;
  if (u?.username) return u.username;
  if (u?.id) return `用户 #${u.id}`;
  return '未知用户';
});

// 头像首字母
const avatarLetter = computed(() => {
  return displayName.value.charAt(0).toUpperCase();
});

function jumpToGithub() {
  window.open('https://github.com/zhegebi/DRG', '_blank');
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
  if (!isLoggedIn.value) {
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
        
        <!-- 用户图标：未登录显示登录图标，已登录显示登出图标 -->
        <div
          class="user-icon-wrapper"
          @mouseenter="onUserMouseEnter"
          @mouseleave="onUserMouseLeave"
        >
          <div class="user-icon" @click="handleUserClick" :title="isLoggedIn ? '用户信息' : '点击登录'">
            <template v-if="isLoggedIn">
              <span class="user-avatar">{{ avatarLetter }}</span>
            </template>
            <SvgIcon v-else type="mdi" :path="mdiAccountCircle" class="user-icon-svg" />
          </div>

          <!-- 悬浮用户信息卡片 -->
          <Transition name="card-fade">
            <div v-if="showUserCard" class="user-card" @mouseenter="onCardMouseEnter" @mouseleave="onCardMouseLeave">
              <!-- 已登录 -->
              <template v-if="isLoggedIn">
                <div class="card-header">
                  <span class="card-avatar">{{ avatarLetter }}</span>
                  <div class="card-user-info">
                    <span class="card-display-name">{{ displayName }}</span>
                    <span class="card-status">已登录</span>
                  </div>
                </div>
                <div class="card-body">
                  <div class="card-row" v-if="currentUser?.username">
                    <SvgIcon type="mdi" :path="mdiAccountOutline" class="row-icon" />
                    <span>{{ currentUser.username }}</span>
                  </div>
                  <div class="card-row" v-if="currentUser?.email">
                    <SvgIcon type="mdi" :path="mdiEmailOutline" class="row-icon" />
                    <span>{{ currentUser.email }}</span>
                  </div>
                  <div class="card-row" v-if="currentUser?.id">
                    <SvgIcon type="mdi" :path="mdiIdentifier" class="row-icon" />
                    <span>ID: {{ currentUser.id }}</span>
                  </div>
                </div>
                <div class="card-footer">
                  <button class="logout-btn" @click="handleLogout">
                    <SvgIcon type="mdi" :path="mdiLogout" class="logout-icon" />
                    退出登录
                  </button>
                </div>
              </template>
              <!-- 未登录 -->
              <template v-else>
                <div class="card-header">
                  <div class="card-avatar guest-avatar">
                    <SvgIcon type="mdi" :path="mdiAccountCircle" class="guest-avatar-icon" />
                  </div>
                  <div class="card-user-info">
                    <span class="card-display-name">未登录</span>
                    <span class="card-status status-guest">请登录后使用</span>
                  </div>
                </div>
                <div class="card-body">
                  <p class="guest-tip">登录后可体验 DRG 入组、文档生成等完整功能</p>
                </div>
                <div class="card-footer">
                  <button class="login-btn" @click="handleLogin">
                    <SvgIcon type="mdi" :path="mdiAccountCircle" class="login-icon" />
                    立即登录
                  </button>
                </div>
              </template>
            </div>
          </Transition>
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
.user-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

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

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #007fd4, #00a8ff);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  user-select: none;
}

/* ===== 悬浮用户信息卡片 ===== */
.user-card {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 260px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 1200;
  overflow: hidden;
}

.user-card::before {
  content: '';
  position: absolute;
  top: -6px;
  right: 12px;
  width: 12px;
  height: 12px;
  background: #ffffff;
  transform: rotate(45deg);
  box-shadow: -2px -2px 4px rgba(0, 0, 0, 0.04);
  border-radius: 2px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.card-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #007fd4, #00a8ff);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  user-select: none;
}

.card-user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.card-display-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-status {
  font-size: 12px;
  color: #52c41a;
  margin-top: 2px;
}

.card-body {
  padding: 12px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #555;
}

.row-icon {
  width: 16px;
  height: 16px;
  fill: #999;
  flex-shrink: 0;
}

.card-footer {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
}

.logout-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  background: #fff;
  color: #ff4d4f;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #fff2f0;
}

.logout-icon {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

/* 未登录状态 */
.guest-avatar {
  background: linear-gradient(135deg, #94a3b8, #cbd5e1) !important;
}

.guest-avatar-icon {
  width: 22px;
  height: 22px;
  fill: white;
}

.status-guest {
  color: #94a3b8 !important;
}

.guest-tip {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin: 4px 0;
  text-align: center;
}

.login-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #007fd4, #0099ff);
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 127, 212, 0.25);
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 127, 212, 0.35);
}

.login-icon {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

/* 卡片动画 */
.card-fade-enter-active {
  transition: all 0.2s ease-out;
}

.card-fade-leave-active {
  transition: all 0.15s ease-in;
}

.card-fade-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}

.card-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>