<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="auth-header">
        <h2>{{ isLoginMode ? '欢迎回来' : '创建账户' }}</h2>
        <p>{{ isLoginMode ? '使用邮箱或用户名登录' : '注册开始使用 DRG 智能分类系统' }}</p>
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
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <!-- 登录方式选择 -->
        <div v-if="isLoginMode" class="login-type">
          <button 
            type="button"
            :class="['type-btn', { active: loginType === 'email' }]"
            @click="loginType = 'email'"
          >
            📧 邮箱登录
          </button>
          <button 
            type="button"
            :class="['type-btn', { active: loginType === 'username' }]"
            @click="loginType = 'username'"
          >
            👤 用户名登录
          </button>
        </div>

        <!-- 登录：邮箱/用户名 -->
        <div v-if="isLoginMode" class="form-group">
          <label>{{ loginType === 'email' ? '邮箱地址' : '用户名' }}</label>
          <input
            v-model="loginIdentifier"
            :type="loginType === 'email' ? 'email' : 'text'"
            :placeholder="loginType === 'email' ? 'your@email.com' : '请输入用户名'"
            required
            :class="{ error: errors.loginIdentifier }"
            @input="clearError"
          />
          <span v-if="errors.loginIdentifier" class="error-text">{{ errors.loginIdentifier }}</span>
        </div>

        <!-- 注册：用户名 -->
        <div v-if="!isLoginMode" class="form-group">
          <label>用户名</label>
          <input
            v-model="signupData.username"
            type="text"
            placeholder="用户名（至少3个字符）"
            required
            :class="{ error: errors.username }"
            @input="clearError"
          />
          <span v-if="errors.username" class="error-text">{{ errors.username }}</span>
        </div>

        <!-- 注册：邮箱 -->
        <div v-if="!isLoginMode" class="form-group">
          <label>邮箱地址</label>
          <input
            v-model="signupData.email"
            type="email"
            placeholder="your@email.com"
            required
            :class="{ error: errors.email }"
            @input="clearError"
          />
          <span v-if="errors.email" class="error-text">{{ errors.email }}</span>
        </div>

        <!-- 密码 -->
        <div class="form-group">
          <label>密码</label>
          <div class="password-wrapper">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              :placeholder="isLoginMode ? '请输入密码' : '密码（至少6个字符）'"
              required
              :class="{ error: errors.password }"
              @input="clearError"
            />
            <button 
              type="button" 
              class="toggle-password"
              @click="showPassword = !showPassword"
            >
              {{ showPassword ? '🙈' : '👁️' }}
            </button>
          </div>
          <span v-if="errors.password" class="error-text">{{ errors.password }}</span>
          <span v-if="!isLoginMode && !errors.password" class="hint-text">
            密码长度至少6位
          </span>
        </div>

        <!-- 注册：确认密码 -->
        <div v-if="!isLoginMode" class="form-group">
          <label>确认密码</label>
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            required
            :class="{ error: errors.confirmPassword }"
            @input="clearError"
          />
          <span v-if="errors.confirmPassword" class="error-text">{{ errors.confirmPassword }}</span>
        </div>

        <!-- API 错误提示 -->
        <div v-if="authStore.error" class="api-error">
          ⚠️ {{ authStore.error }}
        </div>

        <!-- 提交按钮 -->
        <button type="submit" class="submit-btn" :disabled="authStore.isLoading">
          <span v-if="authStore.isLoading" class="spinner"></span>
          {{ authStore.isLoading ? '处理中...' : (isLoginMode ? '登录' : '注册') }}
        </button>
      </form>
    
      <div class="demo-hint" v-if="isLoginMode">
        <p>📋 演示账号：</p>
        <p>管理员：admin@example.com / admin123</p>
        <p>普通用户：user@example.com / user123</p>
        <p>（也支持用户名登录：admin / user）</p>
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
    // 登录成功后跳转到之前访问的页面或首页
    const redirect = (router.currentRoute.value.query.redirect as string) || '/';
    router.push(redirect);
  }
};
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.auth-card {
  background: white;
  border-radius: 20px;
  padding: 2.5rem;
  width: 100%;
  max-width: 450px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.auth-header {
  text-align: center;
  margin-bottom: 2rem;
}

.auth-header h2 {
  font-size: 1.8rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.auth-header p {
  color: #666;
  font-size: 0.9rem;
}

.auth-tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  background: #f5f5f5;
  padding: 0.25rem;
  border-radius: 12px;
}

.tab-btn {
  flex: 1;
  padding: 0.75rem;
  background: transparent;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s;
  color: #666;
}

.tab-btn.active {
  background: white;
  color: #667eea;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.login-type {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.type-btn {
  flex: 1;
  padding: 0.5rem;
  background: #f5f5f5;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.type-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #333;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 2px solid #e1e5e9;
  border-radius: 10px;
  font-size: 1rem;
  transition: all 0.3s;
  font-family: inherit;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input.error {
  border-color: #e74c3c;
}

.password-wrapper {
  position: relative;
  width: 100%;
}

.password-wrapper input {
  width: 100%;
  padding-right: 70px;
  box-sizing: border-box;
}

.toggle-password {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #667eea;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem 0.5rem;
}

.error-text {
  color: #e74c3c;
  font-size: 0.8rem;
}

.hint-text {
  color: #999;
  font-size: 0.8rem;
}

.api-error {
  background: #fee;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.85rem;
  text-align: center;
}

.submit-btn {
  padding: 0.875rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  background: #5a67d8;
  transform: translateY(-1px);
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid white;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.demo-hint {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #f0f7ff;
  border-radius: 8px;
  font-size: 0.75rem;
  color: #667eea;
  text-align: center;
}

.demo-hint p {
  margin: 0.25rem 0;
}

.demo-hint p:first-child {
  font-weight: bold;
}
.info-note {
  margin-top: 1.5rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 0.7rem;
  color: #888;
  text-align: center;
}

.info-note p {
  margin: 0.25rem 0;
}

@media (max-width: 480px) {
  .auth-card {
    padding: 1.5rem;
  }
  
  .auth-header h2 {
    font-size: 1.5rem;
  }
}
</style>