import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BrainCircuit } from 'lucide-react';
import LanguageToggle from '../components/common/LanguageToggle';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4 sm:p-6">
      <div className="pointer-events-none absolute left-1/2 top-[-18rem] h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-blue-300/25 blur-3xl" />
      <div className="relative w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <button type="button" onClick={() => navigate('/')} className="mb-4 flex h-14 w-14 items-center justify-center rounded-[17px] bg-gradient-to-b from-[#1687ff] to-[#006ee6] text-white shadow-[0_8px_24px_rgba(0,122,255,0.28)] transition-transform duration-150 active:scale-[0.96]" aria-label="PathFinder home">
            <BrainCircuit size={27} strokeWidth={1.8} />
          </button>
          <h1 className="mb-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--color-label)]">PathFinder</h1>
          <p className="text-[var(--color-label-secondary)]">{t('auth.subtitle')}</p>
          <LanguageToggle className="mt-5" />
        </div>

        <div className="apple-card rounded-[28px] p-6 sm:p-8">
        <div className="apple-segmented mb-8 flex rounded-[13px] p-1">
          <button
            className={`min-h-10 flex-1 rounded-[10px] py-2.5 text-sm font-semibold transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] ${mode === 'login' ? 'bg-white text-zinc-900 shadow-[0_1px_4px_rgba(0,0,0,0.13)]' : 'text-zinc-500 hover:text-zinc-900'}`}
            onClick={() => {
              setMode('login');
              setError('');
            }}
          >
            {t('auth.login')}
          </button>
          <button
            className={`min-h-10 flex-1 rounded-[10px] py-2.5 text-sm font-semibold transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.98] ${mode === 'register' ? 'bg-white text-zinc-900 shadow-[0_1px_4px_rgba(0,0,0,0.13)]' : 'text-zinc-500 hover:text-zinc-900'}`}
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
                className="apple-input w-full rounded-xl px-4 py-3 outline-none"
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
                className="apple-input w-full rounded-xl px-4 py-3 outline-none"
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
              className="mt-2 min-h-12 w-full rounded-xl bg-[#007AFF] py-3.5 text-sm font-semibold text-white shadow-[0_4px_14px_rgba(0,122,255,0.25)] transition-[background-color,box-shadow,transform] duration-150 hover:bg-[#0071E3] hover:shadow-[0_6px_20px_rgba(0,122,255,0.3)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
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
  );
}
