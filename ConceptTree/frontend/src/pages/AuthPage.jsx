import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BrainCircuit } from 'lucide-react';
import LanguageToggle from '../components/common/LanguageToggle';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import learningMapIllustration from '../assets/illustrations/learning-map.jpg';

export default function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirectTo = searchParams.get('redirect') || '/';
  const { t } = useLanguage();
  
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
      setError(t('auth.error.required'));
      return;
    }
    
    if (password.length < 6) {
      setError(t('auth.error.password'));
      return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError(t('auth.error.email'));
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
        setError(result.error || t('auth.error.generic'));
      }
    } catch (err) {
      setError(t('auth.error.network'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-canvas)] p-5 sm:p-8">
      <div className="grid w-full max-w-5xl items-center gap-12 lg:grid-cols-[minmax(0,1fr)_420px] lg:gap-20">
        <div className="hidden lg:block">
          <img src={learningMapIllustration} alt="" className="notion-illustration w-full" />
        </div>
      <div className="w-full max-w-md justify-self-center">
        <div className="mb-8 flex flex-col items-center text-center">
          <button type="button" onClick={() => navigate('/')} className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-black/[0.12] bg-white text-[#202020] shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-transform duration-150 active:scale-[0.98]" aria-label="PathFinder home">
            <BrainCircuit size={23} strokeWidth={1.8} />
          </button>
          <h1 className="mb-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--color-label)]">PathFinder</h1>
          <p className="text-[var(--color-label-secondary)]">{t('auth.subtitle')}</p>
          <LanguageToggle className="mt-5" />
        </div>

        <div className="rounded-xl border border-black/[0.12] bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:p-8">
        <div className="apple-segmented mb-8 flex p-1">
          <button
            className={`min-h-10 flex-1 rounded-[5px] py-2.5 text-sm font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] ${mode === 'login' ? 'bg-white text-zinc-900 shadow-[0_1px_3px_rgba(0,0,0,0.12)]' : 'text-zinc-500 hover:text-zinc-900'}`}
            onClick={() => {
              setMode('login');
              setError('');
            }}
          >
            {t('auth.login')}
          </button>
          <button
            className={`min-h-10 flex-1 rounded-[5px] py-2.5 text-sm font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] ${mode === 'register' ? 'bg-white text-zinc-900 shadow-[0_1px_3px_rgba(0,0,0,0.12)]' : 'text-zinc-500 hover:text-zinc-900'}`}
            onClick={() => {
              setMode('register');
              setError('');
            }}
          >
            {t('auth.register')}
          </button>
        </div>

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                {t('auth.email')}
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="apple-input w-full rounded-lg px-4 py-3 outline-none"
                placeholder="your@email.com"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                {t('auth.password')}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="apple-input w-full rounded-lg px-4 py-3 outline-none"
                placeholder={t('auth.passwordHint')}
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
              className="mt-2 min-h-11 w-full rounded-lg bg-[#202020] py-3 text-sm font-medium text-white shadow-[0_1px_2px_rgba(0,0,0,0.12)] transition-[background-color,transform] duration-150 hover:bg-black active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (mode === 'login' ? t('auth.loggingIn') : t('auth.registering')) : (mode === 'login' ? t('auth.login') : t('auth.register'))}
            </button>
          </form>

          {/* 提示 */}
          <div className="mt-6 text-center text-sm text-zinc-500">
            {mode === 'login' ? (
              <>
                {t('auth.noAccount')}
                <button
                  className="text-zinc-900 font-medium hover:underline ml-1"
                  onClick={() => {
                    setMode('register');
                    setError('');
                  }}
                >
                  {t('auth.register')}
                </button>
              </>
            ) : (
              <>
                {t('auth.haveAccount')}
                <button
                  className="text-zinc-900 font-medium hover:underline ml-1"
                  onClick={() => {
                    setMode('login');
                    setError('');
                  }}
                >
                  {t('auth.login')}
                </button>
              </>
            )}
          </div>
        </div>

        {/* 底部提示 */}
        <p className="text-center text-sm text-zinc-500 mt-6">
          {t('auth.agreement')}
        </p>
      </div>
      </div>
    </div>
  );
}
