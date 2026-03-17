import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BrainCircuit, 
  User, 
  Sparkles, 
  Check, 
  CheckCircle2,
  Circle,
  Edit3, 
  Archive, 
  MoreVertical,
  LogOut
} from 'lucide-react';
import { Button, Modal } from '../components/ui';
import { LOADING_TEXTS } from '../constants';
import { useAppContext } from '../contexts/AppContext';
import { useAuth } from '../contexts/AuthContext';
import { graphApi, aiApi } from '../services/api';

const HomePage = () => {
  const navigate = useNavigate();
  const { userProfile, plans, actions } = useAppContext();
  const { isAuthenticated, login, register, logout } = useAuth();
  
  const [inputText, setInputText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [parsedGoal, setParsedGoal] = useState(null);
  
  const [activeMenuPlanId, setActiveMenuPlanId] = useState(null);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [planToRename, setPlanToRename] = useState(null);
  const [newName, setNewName] = useState('');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [authMode, setAuthMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleStartAnalysis = async () => {
    if (!inputText.trim()) return;
    setIsAnalyzing(true);
    
    try {
      // 调用 AI 解析 API
      const result = await aiApi.parseGoal(inputText, userProfile);
      setParsedGoal(result);
      setShowConfirmModal(true);
    } catch (error) {
      console.error("Analysis failed", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleConfirmGeneration = async () => {
    setShowConfirmModal(false);
    setIsGenerating(true);
    
    // 启动加载动画计时器
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setLoadingStep(step);
      if (step >= LOADING_TEXTS.length) {
        clearInterval(interval);
      }
    }, 800);

    try {
      // 1. 生成图谱数据
      const graphResult = await graphApi.generate(inputText, userProfile);
      
      // 2. 创建计划
      const newPlan = await actions.createPlan(inputText, graphResult);
      
      // 3. 跳转 (确保动画至少播放一会)
      clearInterval(interval);
      setTimeout(() => {
        setIsGenerating(false);
        navigate(`/graph/${newPlan.id}`);
        setInputText('');
      }, 500);
      
    } catch (error) {
      console.error("Generation failed", error);
      clearInterval(interval);
      setIsGenerating(false);
    }
  };

  const handleArchive = async (id) => {
    await actions.archivePlan(id);
    setActiveMenuPlanId(null);
  };

  const openRenameModal = (plan) => {
    setPlanToRename(plan);
    setNewName(plan.title);
    setShowRenameModal(true);
    setActiveMenuPlanId(null);
  };

  const saveNewName = async () => {
    if (planToRename && newName.trim()) {
      await actions.updatePlan(planToRename.id, { title: newName });
      setShowRenameModal(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const handleLogin = async () => {
    try {
      if (authMode === 'login') {
        const result = await login(email, password);
        if (result.success) {
          setShowLoginModal(false);
          setEmail('');
          setPassword('');
        } else {
          alert(result.error || '登录失败');
        }
      } else {
        const result = await register(email, password);
        if (result.success) {
          setShowLoginModal(false);
          setEmail('');
          setPassword('');
        } else {
          alert(result.error || '注册失败');
        }
      }
    } catch (error) {
      alert('操作失败，请重试');
    }
  };

  const activePlans = plans.filter(p => p.status === 'active');

  return (
    <div 
      className="max-w-screen-xl mx-auto px-6 md:px-12 py-10 min-h-screen flex flex-col relative" 
      onClick={() => setActiveMenuPlanId(null)}
    >
      {/* Header */}
      <header className="flex justify-between items-center mb-24">
        <div className="flex items-center gap-3 group cursor-pointer" onClick={() => navigate('/')}>
          <div className="w-10 h-10 bg-zinc-900 rounded-xl flex items-center justify-center text-white shadow-lg shadow-zinc-200 transition-transform group-hover:rotate-3 group-hover:scale-105">
            <BrainCircuit size={20} strokeWidth={1.5} />
          </div>
          <span className="font-semibold text-lg tracking-tight text-zinc-900">PathFinder</span>
        </div>
        <div className="flex items-center gap-4">
          {!isAuthenticated ? (
            <button 
              onClick={() => navigate('/auth')}
              className="px-6 py-2.5 rounded-full bg-zinc-900 text-white text-sm font-medium hover:bg-zinc-800 transition-all duration-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
            >
              登录 / 注册
            </button>
          ) : (
            <div className="flex items-center gap-2 bg-white p-1.5 rounded-full border border-zinc-100 shadow-sm">
              <button 
                onClick={() => navigate('/my-learning')} 
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-zinc-600 hover:text-zinc-900 hover:bg-zinc-50 rounded-full transition-all duration-200"
              >
                <User size={16} strokeWidth={2} className="text-zinc-400 group-hover:text-zinc-900" />
                我的学习
              </button>
              <div className="w-px h-4 bg-zinc-200" />
              <button 
                onClick={handleLogout} 
                className="p-2 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-all duration-200"
                title="登出"
              >
                <LogOut size={16} strokeWidth={2} />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Hero Input */}
      <section className="flex-1 flex flex-col justify-center max-w-3xl mx-auto w-full mb-24">
        <div className="text-center mb-12 space-y-4">
          <h1 className="text-4xl md:text-5xl font-light tracking-tight text-zinc-900 leading-tight">
            今天想 <span className="font-medium">掌握</span> 什么？
          </h1>
          <p className="text-lg text-zinc-400 font-light">
            AI 驱动的课程设计，根据你的背景量身定制。
          </p>
        </div>

        <div className="bg-white rounded-3xl shadow-[0_8px_40px_rgba(0,0,0,0.04)] border border-zinc-100 p-2 transition-all duration-300 focus-within:shadow-[0_12px_50px_rgba(0,0,0,0.06)] focus-within:border-zinc-200 relative overflow-hidden group">
          <textarea
            className="w-full h-40 p-6 text-xl font-light leading-relaxed resize-none outline-none text-zinc-700 placeholder:text-zinc-300 bg-transparent"
            placeholder="例如：我想理解深度学习中的反向传播，我有Python基础但数学不好..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          
          <div className="px-6 pb-6 flex justify-between items-end">
            <div className="flex items-center gap-3 max-w-[60%] overflow-hidden">
              {userProfile?.abilities?.slice(0, 2).map((tag, i) => (
                <span 
                  key={i} 
                  className="text-xs font-medium text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-100/50 whitespace-nowrap"
                >
                  {tag}
                </span>
              ))}
            </div>
            <Button 
              onClick={handleStartAnalysis} 
              disabled={!inputText.trim() || isAnalyzing} 
              size="md" 
              icon={Sparkles}
            >
              {isAnalyzing ? "解析中..." : "生成图谱"}
            </Button>
          </div>

          {isGenerating && (
            <div className="absolute inset-0 bg-white/98 z-10 flex flex-col items-center justify-center text-zinc-800 transition-opacity duration-500">
              <div className="w-12 h-12 border-[3px] border-zinc-100 border-t-zinc-900 rounded-full animate-spin mb-6" />
              <p className="text-sm font-medium uppercase tracking-widest animate-pulse text-zinc-400">
                {LOADING_TEXTS[loadingStep]}
              </p>
            </div>
          )}
        </div>

        {!inputText && (
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {["理解反向传播算法", "Python 数据分析入门", "Transformer 架构详解"].map((text) => (
              <button 
                key={text} 
                onClick={() => setInputText(text)} 
                className="text-sm text-zinc-500 bg-white border border-zinc-200 px-5 py-2.5 rounded-full hover:border-zinc-400 hover:text-zinc-900 hover:shadow-sm transition-all duration-200"
              >
                {text}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Active Plans */}
      {activePlans.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">继续学习</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {activePlans.map(plan => (
              <div 
                key={plan.id}
                onClick={() => navigate(`/graph/${plan.id}`)}
                className="bg-white p-8 rounded-3xl border border-zinc-100 shadow-[0_2px_10px_rgba(0,0,0,0.02)] hover:shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:border-zinc-200 transition-all cursor-pointer group relative overflow-visible"
              >
                <div className="flex justify-between items-start mb-6 relative z-10">
                  <div>
                    <h3 className="text-lg font-medium text-zinc-900 mb-1 group-hover:text-teal-700 transition-colors">
                      {plan.title}
                    </h3>
                    <p className="text-xs text-zinc-400 font-medium tracking-wide">
                      上次学习: {plan.lastAccess}
                    </p>
                  </div>
                  <div className="relative" onClick={(e) => e.stopPropagation()}>
                    <button 
                      onClick={() => setActiveMenuPlanId(activeMenuPlanId === plan.id ? null : plan.id)}
                      className="w-8 h-8 rounded-full bg-zinc-50 flex items-center justify-center text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
                    >
                      <MoreVertical size={16} />
                    </button>
                    {activeMenuPlanId === plan.id && (
                      <div className="absolute right-0 top-10 w-32 bg-white border border-zinc-100 shadow-xl rounded-xl z-20 py-1 animate-in fade-in zoom-in-95 duration-100">
                        <button 
                          onClick={() => openRenameModal(plan)} 
                          className="w-full text-left px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 flex items-center gap-2"
                        >
                          <Edit3 size={14} /> 重命名
                        </button>
                        <button 
                          onClick={() => handleArchive(plan.id)} 
                          className="w-full text-left px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 flex items-center gap-2"
                        >
                          <Archive size={14} /> 归档
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="relative z-0">
                  <div className="flex justify-between text-xs font-medium text-zinc-400 mb-2">
                    <span>进度</span>
                    <span className="text-zinc-900">
                      {plan.total > 0 ? Math.round((plan.progress / plan.total) * 100) : 0}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-zinc-900 rounded-full transition-all duration-500 ease-out" 
                      style={{ width: `${plan.total > 0 ? (plan.progress / plan.total) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Confirmation Modal */}
      <Modal 
        isOpen={showConfirmModal} 
        onClose={() => setShowConfirmModal(false)}
        title="确认学习目标"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowConfirmModal(false)}>修改输入</Button>
            <Button onClick={handleConfirmGeneration} icon={Check}>确认生成</Button>
          </>
        }
      >
        <div className="space-y-6">
          <div className="p-6 bg-zinc-50 rounded-2xl border border-zinc-100">
            <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-3 flex items-center gap-2">
              识别目标
            </h4>
            <p className="text-xl font-light text-zinc-900">{parsedGoal?.interpretation}</p>
          </div>
          
           {parsedGoal?.backgroundSummary?.length > 0 && (
            <div className="space-y-4">
              <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">基于你的背景</h4>
              <div className="flex flex-col gap-3">
                {parsedGoal.backgroundSummary.map((item, i) => (
                  <div key={i} className={`flex items-start gap-3 p-4 bg-white border rounded-xl shadow-sm ${item.isStrength ? 'border-zinc-100' : 'border-amber-100'}`}>
                    {item.isStrength ? (
                      <CheckCircle2 size={18} className="text-teal-600 mt-0.5 shrink-0" strokeWidth={2}/>
                    ) : (
                      <Circle size={18} className="text-amber-500 mt-0.5 shrink-0" strokeWidth={2}/>
                    )}
                    <span className="text-sm font-medium text-zinc-900">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsedGoal?.shouldSplit && parsedGoal?.splitSuggestions?.length > 0 && (
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <p className="text-sm text-amber-800 font-medium">
                  🎯 目标较大，建议拆分为以下子目标分步学习：
                </p>
              </div>
              <div className="flex flex-col gap-3">
                {parsedGoal.splitSuggestions.map((suggestion, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInputText(suggestion.title);
                      setShowConfirmModal(false);
                      setParsedGoal(null);
                    }}
                    className="text-left p-4 bg-white border border-zinc-200 rounded-xl hover:border-teal-300 hover:shadow-sm transition-all group"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h5 className="text-sm font-semibold text-zinc-900 group-hover:text-teal-700 transition-colors">
                          {suggestion.title}
                        </h5>
                        <p className="text-xs text-zinc-500 mt-1">{suggestion.description}</p>
                      </div>
                      <span className="text-xs text-zinc-400 bg-zinc-100 px-2 py-1 rounded-full shrink-0 ml-3">
                        ~{suggestion.estimatedNodes} 节点
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Rename Modal */}
      <Modal
        isOpen={showRenameModal}
        onClose={() => setShowRenameModal(false)}
        title="重命名计划"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowRenameModal(false)}>取消</Button>
            <Button onClick={saveNewName}>保存</Button>
          </>
        }
      >
        <input 
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="w-full p-4 bg-zinc-50 border border-zinc-100 rounded-xl outline-none focus:bg-white focus:border-zinc-300 transition-colors text-sm"
          autoFocus
        />
      </Modal>

      {/* Login / Register Modal */}
      <Modal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        title={authMode === 'login' ? '欢迎回来' : '创建账号'}
        footer={
          <button 
            onClick={handleLogin}
            className="w-full py-3.5 px-6 bg-green-500 text-white font-medium rounded-2xl shadow-md hover:shadow-lg hover:bg-green-600 active:bg-green-700 transition-all duration-200 text-sm"
          >
            {authMode === 'login' ? '登录' : '注册'}
          </button>
        }
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-500">邮箱</label>
            <input 
              type="email" 
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3.5 bg-zinc-50 border border-zinc-200 rounded-xl text-sm focus:bg-white focus:border-zinc-400 focus:ring-2 focus:ring-zinc-100 outline-none transition-all duration-200" 
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold text-zinc-500">密码</label>
            <input 
              type="password" 
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3.5 bg-zinc-50 border border-zinc-200 rounded-xl text-sm focus:bg-white focus:border-zinc-400 focus:ring-2 focus:ring-zinc-100 outline-none transition-all duration-200" 
            />
          </div>
          
          <div className="pt-2 text-center">
            <button 
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              className="text-xs text-zinc-400 hover:text-zinc-900 transition-colors"
            >
              {authMode === 'login' ? '还没有账号？去注册' : '已有账号？去登录'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default HomePage;
