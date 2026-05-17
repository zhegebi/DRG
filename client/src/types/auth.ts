// 登录请求参数
export interface LoginRequest {
  type: 'email' | 'username';
  identifier: string;
  password: string;
}

// 注册请求参数
export interface SignupRequest {
  username: string;
  email: string;
  password: string;
}

// Token 响应
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// 用户信息（从 token 解码或在需要时获取）
export interface User {
  id: string;
  username: string;
  email: string;
}

// API 错误响应
export interface ApiError {
  detail?: string;
  message?: string;
}