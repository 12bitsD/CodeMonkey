import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get('redirect') || '/';
  
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // 验证
    if (!email || !password) {
      setError('请填写邮箱和密码');
      return;
    }
    
    if (password.length < 6) {
      setError('密码长度至少6位');
      return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('邮箱格式不正确');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const result = mode === 'login' 
        ? await login(email, password)
        : await register(email, password);
      
      if (result.success) {
        navigate(redirectTo);
      } else {
        setError(result.error || '操作失败，请重试');
      }
    } catch (err) {
      setError('网络错误，请检查后端服务是否启动');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 to-zinc-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo 区域 */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-zinc-900 mb-2">ConceptTree</h1>
          <p className="text-zinc-600">你的学习路径规划器</p>
        </div>

        {/* 登录/注册表单 */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* 切换标签 */}
        <div className="flex mb-8 bg-zinc-100/80 p-1.5 rounded-xl">
          <button
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${mode === 'login' ? 'bg-white text-zinc-900 shadow-[0_2px_10px_rgba(0,0,0,0.05)]' : 'text-zinc-500 hover:text-zinc-900'}`}
            onClick={() => {
              setMode('login');
              setError('');
            }}
          >
            登录
          </button>
          <button
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${mode === 'register' ? 'bg-white text-zinc-900 shadow-[0_2px_10px_rgba(0,0,0,0.05)]' : 'text-zinc-500 hover:text-zinc-900'}`}
            onClick={() => {
              setMode('register');
              setError('');
            }}
          >
            注册
          </button>
        </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-zinc-200 focus:border-zinc-400 focus:outline-none transition-colors"
                placeholder="your@email.com"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-zinc-200 focus:border-zinc-400 focus:outline-none transition-colors"
                placeholder="至少6位"
                disabled={isLoading}
              />
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 bg-zinc-900 text-white font-medium rounded-xl shadow-[0_4px_14px_rgba(0,0,0,0.1)] hover:shadow-[0_6px_20px_rgba(0,0,0,0.15)] hover:bg-zinc-800 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 text-sm mt-2"
            >
              {isLoading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登录' : '注册')}
            </button>
          </form>

          {/* 提示 */}
          <div className="mt-6 text-center text-sm text-zinc-500">
            {mode === 'login' ? (
              <>
                还没有账号？
                <button
                  className="text-zinc-900 font-medium hover:underline ml-1"
                  onClick={() => {
                    setMode('register');
                    setError('');
                  }}
                >
                  立即注册
                </button>
              </>
            ) : (
              <>
                已有账号？
                <button
                  className="text-zinc-900 font-medium hover:underline ml-1"
                  onClick={() => {
                    setMode('login');
                    setError('');
                  }}
                >
                  立即登录
                </button>
              </>
            )}
          </div>
        </div>

        {/* 底部提示 */}
        <p className="text-center text-sm text-zinc-500 mt-6">
          登录即表示同意我们的服务条款和隐私政策
        </p>
      </div>
    </div>
  );
}
