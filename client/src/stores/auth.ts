import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { 
  loginApiAuthLoginPost, 
  signupApiAuthSignupPost, 
  logoutApiAuthLogoutPost,
  refreshAccessTokenApiAuthRefreshPost 
} from '@/api';

interface User {
  id?: number;
  username?: string;
  email?: string;
  displayName?: string;
}

// 安全的 token 解码
const decodeToken = (token: string): { sub?: string } | null => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadPart = parts[1];
    if (!payloadPart) return null;
    const base64 = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const decoded = atob(base64);
    return JSON.parse(decoded);
  } catch (error) {
    console.error('解码 token 失败:', error);
    return null;
  }
};

const STORAGE_TOKEN_KEY = 'access_token';
const STORAGE_USER_KEY = 'user_info';

// 从 localStorage 恢复用户信息
function loadStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(STORAGE_USER_KEY);
    if (!raw) return decodeTokenUser();
    return JSON.parse(raw) as User;
  } catch {
    return decodeTokenUser();
  }
}

// 从 token 中解码用户 ID（备用，当 user_info 不存在时）
function decodeTokenUser(): User | null {
  const token = localStorage.getItem(STORAGE_TOKEN_KEY);
  if (!token) return null;
  const decoded = decodeToken(token);
  if (decoded?.sub) {
    return { id: parseInt(decoded.sub) };
  }
  return null;
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(STORAGE_TOKEN_KEY));
  const user = ref<User | null>(loadStoredUser());
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!accessToken.value);

  // 设置认证状态
  const setAuth = (token: string, userData?: User) => {
    accessToken.value = token;
    localStorage.setItem(STORAGE_TOKEN_KEY, token);

    if (userData) {
      user.value = userData;
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(userData));
    } else {
      const decoded = decodeToken(token);
      if (decoded?.sub) {
        user.value = { id: parseInt(decoded.sub) };
        localStorage.setItem(STORAGE_USER_KEY, JSON.stringify({ id: parseInt(decoded.sub) }));
      }
    }
  };

  // 清除认证状态
  const clearAuth = () => {
    accessToken.value = null;
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    user.value = null;
  };

  const login = async (identifier: string, password: string, type: 'email' | 'username' = 'email') => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const result = await loginApiAuthLoginPost({
        body: { type, identifier, password },
      });
      
      if (result.error) {
        const errorObj = result.error as any;
        const status = errorObj?.status;
        if (status === 401) {
          error.value = '用户名或密码错误';
        } else {
          error.value = errorObj?.detail || '登录失败';
        }
        return false;
      }
      
      const data = result.data as any;
      if (data && data.access_token) {
        console.log('【真实登录】登录成功');
        setAuth(data.access_token, { username: data.username, email: data.email });
        return true;
      }
      
      error.value = '登录失败：未收到令牌';
      return false;
    } catch (err: any) {
      console.error('登录错误:', err);
      error.value = err?.message || '网络错误，请稍后重试';
      return false;
    } finally {
      isLoading.value = false;
    }
  };

  const signup = async (username: string, email: string, password: string) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const result = await signupApiAuthSignupPost({
        body: { username, email, password },
      });
      
      if (result.error) {
        const errorObj = result.error as any;
        const status = errorObj?.status;
        const detail = errorObj?.detail;
        
        if (status === 400) {
          error.value = detail || '用户名或邮箱已被注册';
        } else if (status === 422) {
          error.value = detail || '用户名或密码格式无效（用户名至少3个字符，密码至少6个字符）';
        } else {
          error.value = detail || '注册失败';
        }
        return false;
      }
      
      const data = result.data as any;
      if (data && data.access_token) {
        console.log('【真实注册】注册成功', { username, email });
        setAuth(data.access_token, { username: data.username, email: data.email });
        return true;
      }
      
      error.value = '注册失败：未收到令牌';
      return false;
    } catch (err: any) {
      console.error('注册错误:', err);
      error.value = err?.message || '网络错误，请稍后重试';
      return false;
    } finally {
      isLoading.value = false;
    }
  };

  const logout = async () => {
    try {
      await logoutApiAuthLogoutPost();
    } catch (err) {
      console.error('登出请求失败:', err);
    } finally {
      clearAuth();
    }
  };

  const refreshToken = async () => {
    try {
      const result = await refreshAccessTokenApiAuthRefreshPost();
      const data = result.data as any;
      if (data && data.access_token) {
        accessToken.value = data.access_token;
        localStorage.setItem(STORAGE_TOKEN_KEY, data.access_token);
        return true;
      }
      return false;
    } catch {
      clearAuth();
      return false;
    }
  };

  return {
    user,
    accessToken,
    isLoading,
    error,
    isAuthenticated,
    login,
    signup,
    logout,
    refreshToken,
    clearAuth,
  };
});