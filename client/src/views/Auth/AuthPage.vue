<template>
  <div class="auth-page">
    <div class="auth-bg">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
    </div>

    <div class="auth-container">
      <div class="auth-card">
        <div class="auth-header">
          <div class="auth-logo">DRG</div>
          <h2>{{ isLoginMode ? '欢迎回来' : '创建账户' }}</h2>
          <p>{{ isLoginMode ? '使用邮箱或用户名登录系统' : '注册后即可使用 DRG 智能分类系统' }}</p>
        </div>

        <!-- Tab 切换 -->
        <div class="auth-tabs">
          <button
            :class="['tab-btn', { active: isLoginMode }]"
            @click="switchMode(true)"
          >
            登录
          </button>
          <button
            :class="['tab-btn', { active: !isLoginMode }]"
            @click="switchMode(false)"
          >
            注册
          </button>
          <div class="tab-slider" :class="{ right: !isLoginMode }"></div>
        </div>

        <form @submit.prevent="handleSubmit" class="auth-form">
          <!-- 登录方式切换 -->
          <div v-if="isLoginMode" class="login-type-row">
            <button
              type="button"
              :class="['type-chip', { active: loginType === 'email' }]"
              @click="loginType = 'email'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              邮箱登录
            </button>
            <button
              type="button"
              :class="['type-chip', { active: loginType === 'username' }]"
              @click="loginType = 'username'"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              用户名登录
            </button>
          </div>

          <!-- 登录：邮箱/用户名 -->
          <div v-if="isLoginMode" class="form-group">
            <label>{{ loginType === 'email' ? '邮箱地址' : '用户名' }}</label>
            <div class="input-wrapper" :class="{ 'has-error': errors.loginIdentifier }">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-if="loginType === 'email'"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-else><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <input
                v-model="loginIdentifier"
                :type="loginType === 'email' ? 'email' : 'text'"
                :placeholder="loginType === 'email' ? 'your@email.com' : '请输入用户名'"
                required
                @input="clearError"
              />
            </div>
            <span v-if="errors.loginIdentifier" class="error-text">{{ errors.loginIdentifier }}</span>
          </div>

          <!-- 注册：用户名 -->
          <div v-if="!isLoginMode" class="form-group">
            <label>用户名</label>
            <div class="input-wrapper" :class="{ 'has-error': errors.username }">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              <input
                v-model="signupData.username"
                type="text"
                placeholder="用户名（至少3个字符）"
                required
                @input="clearError"
              />
            </div>
            <span v-if="errors.username" class="error-text">{{ errors.username }}</span>
          </div>

          <!-- 注册：邮箱 -->
          <div v-if="!isLoginMode" class="form-group">
            <label>邮箱地址</label>
            <div class="input-wrapper" :class="{ 'has-error': errors.email }">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <input
                v-model="signupData.email"
                type="email"
                placeholder="your@email.com"
                required
                @input="clearError"
              />
            </div>
            <span v-if="errors.email" class="error-text">{{ errors.email }}</span>
          </div>

          <!-- 密码 -->
          <div class="form-group">
            <label>密码</label>
            <div class="input-wrapper" :class="{ 'has-error': errors.password }">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="isLoginMode ? '请输入密码' : '至少6位密码'"
                required
                @input="clearError"
              />
              <button type="button" class="toggle-password" @click="showPassword = !showPassword">
                <svg v-if="!showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
            <span v-if="errors.password" class="error-text">{{ errors.password }}</span>
            <span v-if="!isLoginMode && !errors.password" class="hint-text">密码长度至少6位</span>
          </div>

          <!-- 注册：确认密码 -->
          <div v-if="!isLoginMode" class="form-group">
            <label>确认密码</label>
            <div class="input-wrapper" :class="{ 'has-error': errors.confirmPassword }">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <input
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                placeholder="请再次输入密码"
                required
                @input="clearError"
              />
              <button type="button" class="toggle-password" @click="showConfirmPassword = !showConfirmPassword">
                <svg v-if="!showConfirmPassword" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
            <span v-if="errors.confirmPassword" class="error-text">{{ errors.confirmPassword }}</span>
          </div>

          <!-- API 错误提示 -->
          <div v-if="authStore.error" class="api-error">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {{ authStore.error }}
          </div>

          <!-- 提交按钮 -->
          <button type="submit" class="submit-btn" :disabled="authStore.isLoading">
            <div v-if="authStore.isLoading" class="spinner"></div>
            <span v-else>{{ isLoginMode ? '登录' : '注册' }}</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

// UI 状态
const isLoginMode = ref(true);
const loginType = ref<'email' | 'username'>('email');
const showPassword = ref(false);
const showConfirmPassword = ref(false);

// 表单数据
const loginIdentifier = ref('');
const password = ref('');
const signupData = reactive({
  username: '',
  email: '',
});
const confirmPassword = ref('');

// 前端验证错误
const errors = reactive({
  loginIdentifier: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
});

// 清空错误
const clearError = () => {
  if (authStore.error) authStore.error = null;
};

// 切换模式时清空表单
const switchMode = (isLogin: boolean) => {
  isLoginMode.value = isLogin;
  loginIdentifier.value = '';
  password.value = '';
  signupData.username = '';
  signupData.email = '';
  confirmPassword.value = '';
  loginType.value = 'email';
  authStore.error = null;
  showPassword.value = false;
  showConfirmPassword.value = false;

  // 清空错误
  Object.keys(errors).forEach(key => {
    errors[key as keyof typeof errors] = '';
  });
};

// 前端验证
const validateForm = (): boolean => {
  let isValid = true;

  // 清空调错误
  errors.loginIdentifier = '';
  errors.username = '';
  errors.email = '';
  errors.password = '';
  errors.confirmPassword = '';

  if (isLoginMode.value) {
    // 登录验证
    if (!loginIdentifier.value.trim()) {
      errors.loginIdentifier = loginType.value === 'email' ? '请输入邮箱' : '请输入用户名';
      isValid = false;
    }
    if (loginType.value === 'email' && loginIdentifier.value.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(loginIdentifier.value)) {
        errors.loginIdentifier = '请输入有效的邮箱地址';
        isValid = false;
      }
    }
    if (!password.value) {
      errors.password = '请输入密码';
      isValid = false;
    }
  } else {
    // 注册验证
    if (!signupData.username.trim()) {
      errors.username = '请输入用户名';
      isValid = false;
    } else if (signupData.username.length < 3) {
      errors.username = '用户名至少3个字符';
      isValid = false;
    }

    if (!signupData.email.trim()) {
      errors.email = '请输入邮箱';
      isValid = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(signupData.email)) {
      errors.email = '请输入有效的邮箱地址';
      isValid = false;
    }

    if (!password.value) {
      errors.password = '请输入密码';
      isValid = false;
    } else if (password.value.length < 6) {
      errors.password = '密码长度至少6位';
      isValid = false;
    }

    if (!confirmPassword.value) {
      errors.confirmPassword = '请确认密码';
      isValid = false;
    } else if (password.value !== confirmPassword.value) {
      errors.confirmPassword = '两次输入的密码不一致';
      isValid = false;
    }
  }

  return isValid;
};

// 提交表单
const handleSubmit = async () => {
  if (!validateForm()) return;

  let success = false;

  if (isLoginMode.value) {
    success = await authStore.login(
      loginIdentifier.value.trim(),
      password.value,
      loginType.value
    );
  } else {
    success = await authStore.signup(
      signupData.username.trim(),
      signupData.email.trim(),
      password.value
    );
  }

  if (success) {
    const redirect = (router.currentRoute.value.query.redirect as string) || '/';
    router.push(redirect);
  }
};
</script>

<style scoped>
/* ===== 页面背景 ===== */
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  position: relative;
  overflow: hidden;
}

.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.12;
  animation: blobFloat 8s ease-in-out infinite;
}

.blob-1 {
  width: 600px;
  height: 600px;
  background: #007fd4;
  top: -200px;
  left: -100px;
  animation-delay: 0s;
}

.blob-2 {
  width: 500px;
  height: 500px;
  background: #667eea;
  bottom: -200px;
  right: -100px;
  animation-delay: -3s;
}

.blob-3 {
  width: 300px;
  height: 300px;
  background: #764ba2;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -6s;
}

@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ===== 卡片容器 ===== */
.auth-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 1rem;
  animation: cardEnter 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes cardEnter {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.auth-card {
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 2.5rem 2rem;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.4);
}

/* ===== 头部 ===== */
.auth-header {
  text-align: center;
  margin-bottom: 1.75rem;
}

.auth-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #007fd4, #0099ff);
  color: white;
  font-size: 18px;
  font-weight: 800;
  border-radius: 14px;
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

.auth-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.auth-header p {
  font-size: 0.85rem;
  color: #64748b;
}

/* ===== Tab 切换 ===== */
.auth-tabs {
  position: relative;
  display: flex;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  margin-bottom: 1.75rem;
}

.tab-btn {
  flex: 1;
  padding: 0.6rem;
  background: transparent;
  border: none;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  transition: color 0.3s;
  color: #94a3b8;
  position: relative;
  z-index: 1;
  font-family: inherit;
}

.tab-btn.active {
  color: #0f172a;
}

.tab-slider {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-slider.right {
  transform: translateX(100%);
}

/* ===== 表单 ===== */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper .input-icon {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  pointer-events: none;
  flex-shrink: 0;
}

.input-wrapper input {
  width: 100%;
  padding: 0.7rem 0.75rem 0.7rem 38px;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9rem;
  font-family: inherit;
  transition: all 0.2s;
  background: #f8fafc;
  color: #0f172a;
  box-sizing: border-box;
}

.input-wrapper input::placeholder {
  color: #94a3b8;
}

.input-wrapper input:focus {
  outline: none;
  border-color: #007fd4;
  background: white;
  box-shadow: 0 0 0 3px rgba(0, 127, 212, 0.1);
}

.input-wrapper.has-error input {
  border-color: #ef4444;
  background: #fef2f2;
}

.input-wrapper.has-error input:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.toggle-password {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.toggle-password:hover {
  color: #475569;
}

/* ===== 登录方式切换 ===== */
.login-type-row {
  display: flex;
  gap: 8px;
}

.type-chip {
  flex: 1;
  padding: 0.5rem;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.2s;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-family: inherit;
}

.type-chip.active {
  background: rgba(0, 127, 212, 0.06);
  border-color: #007fd4;
  color: #007fd4;
}

.type-chip:hover:not(.active) {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

/* ===== 错误提示 ===== */
.error-text {
  color: #ef4444;
  font-size: 0.75rem;
  font-weight: 500;
}

.hint-text {
  color: #94a3b8;
  font-size: 0.75rem;
}

.api-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0.65rem 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 500;
}

/* ===== 提交按钮 ===== */
.submit-btn {
  padding: 0.8rem;
  background: linear-gradient(135deg, #007fd4, #0099ff);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  font-family: inherit;
  box-shadow: 0 4px 14px rgba(0, 127, 212, 0.3);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 127, 212, 0.4);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  background: #94a3b8;
  box-shadow: none;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}



.demo-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.demo-accounts {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.demo-accounts span {
  font-size: 0.75rem;
  color: #64748b;
  font-family: "SFMono-Regular", Consolas, monospace;
  background: #f8fafc;
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-block;
  width: fit-content;
  margin: 0 auto;
}
</style>
