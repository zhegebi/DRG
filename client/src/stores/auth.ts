import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { 
  loginApiAuthLoginPost, 
  signupApiAuthSignupPost, 
  logoutApiAuthLogoutPost,
  refreshAccessTokenApiAuthRefreshPost 
} from '@/api';

// 测试模式开关 - 设为 true 时优先使用测试用户
const TEST_MODE = true

// 预设的测试用户（用户名/邮箱 + 密码）
const TEST_USERS = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    password: 'admin123',
    displayName: '管理员'
  },
  {
    id: 2,
    username: 'user',
    email: 'user@example.com',
    password: 'user123',
    displayName: '普通用户'
  }
]

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

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'));
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!accessToken.value);

  // 设置认证状态
  const setAuth = (token: string, userData?: User) => {
    accessToken.value = token;
    localStorage.setItem('access_token', token);
    
    if (userData) {
      user.value = userData;
    } else {
      const decoded = decodeToken(token);
      if (decoded?.sub) {
        user.value = { id: parseInt(decoded.sub) };
      }
    }
  };

  // 清除认证状态
  const clearAuth = () => {
    accessToken.value = null;
    localStorage.removeItem('access_token');
    user.value = null;
  };

  // 验证预设测试用户
  const verifyTestUser = (identifier: string, password: string, type: 'email' | 'username'): User | null => {
    const foundUser = TEST_USERS.find(u => {
      if (type === 'email') {
        return u.email.toLowerCase() === identifier.toLowerCase() && u.password === password;
      } else {
        return u.username.toLowerCase() === identifier.toLowerCase() && u.password === password;
      }
    });
    
    if (foundUser) {
      return {
        id: foundUser.id,
        username: foundUser.username,
        email: foundUser.email,
        displayName: foundUser.displayName
      };
    }
    return null;
  };

  // 登录：优先测试用户，其次真实后端
  const login = async (identifier: string, password: string, type: 'email' | 'username' = 'email') => {
    isLoading.value = true;
    error.value = null;
    
    // 1. 先检查是否是测试用户
    if (TEST_MODE) {
      const testUser = verifyTestUser(identifier, password, type);
      if (testUser) {
        console.log('【测试模式】使用测试用户登录', testUser);
        await new Promise(resolve => setTimeout(resolve, 500));
        setAuth(`test-token-${testUser.id}`, testUser);
        isLoading.value = false;
        return true;
      }
      // 不是测试用户，继续尝试真实登录
      console.log('【测试模式】不是测试用户，尝试真实登录');
    }
    
    // 2. 尝试真实后端登录
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
        setAuth(data.access_token);
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

  // 注册：真实后端
  const signup = async (username: string, email: string, password: string) => {
    isLoading.value = true;
    error.value = null;
    
    // 检查用户名是否与测试用户冲突
    if (TEST_MODE) {
      const conflict = TEST_USERS.some(u => 
        u.username === username || u.email === email
      );
      if (conflict) {
        error.value = '用户名或邮箱与演示账号冲突，请换一个';
        isLoading.value = false;
        return false;
      }
    }
    
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
        setAuth(data.access_token);
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

  // 登出
  const logout = async () => {
    // 测试模式的 token 不需要调用后端
    if (TEST_MODE && accessToken.value?.startsWith('test-token')) {
      console.log('【测试模式】测试用户登出');
      clearAuth();
      return;
    }
    
    try {
      await logoutApiAuthLogoutPost();
    } catch (err) {
      console.error('登出请求失败:', err);
    } finally {
      clearAuth();
    }
  };

  // 刷新 token
  const refreshToken = async () => {
    if (TEST_MODE && accessToken.value?.startsWith('test-token')) {
      return true;
    }
    
    try {
      const result = await refreshAccessTokenApiAuthRefreshPost();
      const data = result.data as any;
      if (data && data.access_token) {
        accessToken.value = data.access_token;
        localStorage.setItem('access_token', data.access_token);
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