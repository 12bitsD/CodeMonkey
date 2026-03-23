import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  User, 
  Archive, 
  BookOpen, 
  BarChart3,
  Search,
  Plus,
  RotateCcw,
  CornerDownLeft,
  X,
} from 'lucide-react';
import { Button, Badge } from '../components/ui';
import { StatCard, ChartBar } from '../components/common';
import { useAppContext } from '../contexts/AppContext';
import { statsApi } from '../services/api';

const MyLearningPage = () => {
  const navigate = useNavigate();
  const { userProfile, plans, allNotes, actions } = useAppContext();
  
  const [activeTab, setActiveTab] = useState('profile');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlanFilter, setSelectedPlanFilter] = useState('all');
  const [isComposing, setIsComposing] = useState(false);
  const [localOccupation, setLocalOccupation] = useState(userProfile?.occupation || '');
  const [localEducation, setLocalEducation] = useState(userProfile?.education || '');

  // 同步异步加载的 profile 数据到本地状态
  useEffect(() => {
    setLocalOccupation(userProfile?.occupation || '');
    setLocalEducation(userProfile?.education || '');
  }, [userProfile?.occupation, userProfile?.education]);

  const [statsData, setStatsData] = useState(null);
  const [distributionData, setDistributionData] = useState([]);

  useEffect(() => {
    if (activeTab === 'stats') {
      Promise.all([
        statsApi.getOverview().catch(() => null),
        statsApi.getDistribution().catch(() => []),
      ]).then(([overview, distribution]) => {
        if (overview) setStatsData(overview);
        // getDistribution returns { distribution: [...], total: N } — extract array
        if (distribution) setDistributionData(Array.isArray(distribution) ? distribution : (distribution.distribution || []));
      });
    }
  }, [activeTab]);

  const tabs = [
    { id: 'profile', label: '我的画像', icon: User },
    { id: 'archived', label: '归档计划', icon: Archive },
    { id: 'notes', label: '全部笔记', icon: BookOpen },
    { id: 'stats', label: '学习统计', icon: BarChart3 },
  ];

  const handleRestore = async (id) => {
    await actions.restorePlan(id);
  };

  const handleAddAbility = () => {
    const newAbility = prompt('添加新的能力标签:');
    if (newAbility?.trim()) {
      actions.setUserProfile({
        ...userProfile,
        abilities: [...(userProfile.abilities || []), newAbility.trim()]
      });
    }
  };

  const handleRemoveAbility = (index) => {
    const newAbilities = [...userProfile.abilities];
    newAbilities.splice(index, 1);
    actions.setUserProfile({ ...userProfile, abilities: newAbilities });
  };

  const handleOccupationChange = (e) => {
    setLocalOccupation(e.target.value);
    if (!isComposing) {
      actions.setUserProfile({ ...userProfile, occupation: e.target.value });
    }
  };

  const handleOccupationBlur = () => {
    actions.setUserProfile({ ...userProfile, occupation: localOccupation });
  };

  const handleEducationChange = (e) => {
    setLocalEducation(e.target.value);
    if (!isComposing) {
      actions.setUserProfile({ ...userProfile, education: e.target.value });
    }
  };

  const handleEducationBlur = () => {
    actions.setUserProfile({ ...userProfile, education: localEducation });
  };

  const archivedPlans = plans.filter(p => p.status === 'archived');
  const activePlans = plans.filter(p => p.status === 'active');
  
  const filteredNotes = useMemo(() => {
    return allNotes.filter(n => {
      const matchesPlan = selectedPlanFilter === 'all' || n.planId === selectedPlanFilter;
      const matchesSearch = !searchQuery || n.content.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesPlan && matchesSearch;
    });
  }, [allNotes, selectedPlanFilter, searchQuery]);

  const notesByPlan = useMemo(() => {
    return filteredNotes.reduce((acc, note) => {
      const key = note.planId;
      if (!acc[key]) acc[key] = { title: note.planTitle || note.planId, notes: [] };
      acc[key].notes.push(note);
      return acc;
    }, {});
  }, [filteredNotes]);

  const completedPlansCount = archivedPlans.filter(p => p.progress === p.total && p.total > 0).length;
  const masteredKnowledgeCount = userProfile?.masteredKnowledge?.length || 0;

  return (
    <div className="max-w-screen-xl mx-auto px-6 md:px-12 py-10 min-h-screen flex flex-col">
      <div className="flex items-center gap-4 mb-12">
        <button onClick={() => navigate('/')} className="p-2 hover:bg-zinc-100 rounded-full text-zinc-400 hover:text-zinc-900 transition-colors">
          <ArrowLeft size={24} strokeWidth={1.5}/>
        </button>
        <h1 className="text-2xl font-light text-zinc-900">我的学习</h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-12">
        {/* Sidebar Navigation */}
        <div className="w-full lg:w-64 flex-shrink-0 space-y-1">
          {tabs.map(tab => (
            <button 
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-4 px-6 py-4 rounded-xl transition-all duration-300 text-sm font-medium
                ${activeTab === tab.id 
                  ? 'bg-zinc-900 text-white shadow-lg shadow-zinc-200' 
                  : 'text-zinc-500 hover:bg-white hover:text-zinc-900 hover:shadow-sm'}
              `}
            >
              <tab.icon size={18} strokeWidth={1.5} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="flex-1 bg-white rounded-[2rem] shadow-[0_4px_20px_rgba(0,0,0,0.02)] border border-zinc-100 p-10 min-h-[600px]">
          
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="max-w-2xl space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">基础信息</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">职业/身份</label>
                    <input 
                      type="text" 
                      value={localOccupation}
                      onChange={handleOccupationChange}
                      onBlur={handleOccupationBlur}
                      onCompositionStart={() => setIsComposing(true)}
                      onCompositionEnd={() => setIsComposing(false)}
                      placeholder="例如：大三计算机学生"
                      className="w-full p-3 bg-zinc-50 border border-zinc-100 rounded-lg text-sm focus:bg-white focus:border-zinc-300 outline-none transition-colors" 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">教育背景</label>
                    <input 
                      type="text" 
                      value={localEducation}
                      onChange={handleEducationChange}
                      onBlur={handleEducationBlur}
                      onCompositionStart={() => setIsComposing(true)}
                      onCompositionEnd={() => setIsComposing(false)}
                      placeholder="例如：香港理工大学 计算机"
                      className="w-full p-3 bg-zinc-50 border border-zinc-100 rounded-lg text-sm focus:bg-white focus:border-zinc-300 outline-none transition-colors" 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">编程基础</label>
                    <select
                      value={userProfile?.programmingLevel || '入门'}
                      onChange={e => actions.setUserProfile({ ...userProfile, programmingLevel: e.target.value })}
                      className="w-full p-3 bg-zinc-50 border border-zinc-100 rounded-lg text-sm focus:bg-white focus:border-zinc-300 outline-none transition-colors"
                    >
                      {['无基础', '入门', '熟练'].map(level => (
                        <option key={level} value={level}>{level}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-zinc-500">数学基础</label>
                    <select
                      value={userProfile?.mathLevel || '入门'}
                      onChange={e => actions.setUserProfile({ ...userProfile, mathLevel: e.target.value })}
                      className="w-full p-3 bg-zinc-50 border border-zinc-100 rounded-lg text-sm focus:bg-white focus:border-zinc-300 outline-none transition-colors"
                    >
                      {['无基础', '入门', '熟练'].map(level => (
                        <option key={level} value={level}>{level}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </section>

              <section>
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">能力标签</h2>
                <div className="flex flex-wrap gap-2">
                  {(userProfile?.abilities || []).map((tag, i) => (
                    <Badge key={i} onDelete={() => handleRemoveAbility(i)}>
                      {tag}
                    </Badge>
                  ))}
                  <button 
                    onClick={handleAddAbility}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-white border border-dashed border-zinc-300 text-zinc-400 hover:text-zinc-900 hover:border-zinc-400 transition-colors flex items-center gap-1"
                  >
                    <Plus size={12}/> 添加
                  </button>
                </div>
              </section>

              {(userProfile?.masteredKnowledge?.length > 0) && (
                <section>
                  <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">已掌握知识</h2>
                  <div className="flex flex-wrap gap-2">
                    {userProfile.masteredKnowledge.map((knowledge, i) => (
                      <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-teal-50 text-teal-700 border border-teal-100">
                        {knowledge}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}

          {/* Archived Tab */}
          {activeTab === 'archived' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">归档计划</h2>
              {archivedPlans.length > 0 ? (
                archivedPlans.map(plan => (
                  <div key={plan.id} className="flex items-center justify-between p-6 border border-zinc-100 rounded-2xl hover:bg-zinc-50 transition-colors group">
                    <div>
                      <h3 className="font-medium text-zinc-900">{plan.title}</h3>
                      <p className="text-xs text-zinc-400 mt-1">最后访问: {plan.lastAccess}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      {plan.progress === plan.total && plan.total > 0 && (
                        <span className="text-xs font-medium bg-zinc-100 text-zinc-600 px-2 py-1 rounded">已完成</span>
                      )}
                      <Button variant="outline" size="sm" onClick={() => handleRestore(plan.id)} icon={RotateCcw}>
                        恢复
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-20 text-zinc-400">
                  <Archive size={48} className="mx-auto mb-4 opacity-20" strokeWidth={1}/>
                  暂无归档计划
                </div>
              )}
            </div>
          )}

          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-6 border-b border-zinc-50">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest">全部笔记</h2>
                  <select
                    value={selectedPlanFilter}
                    onChange={e => setSelectedPlanFilter(e.target.value)}
                    className="text-xs text-zinc-500 bg-zinc-50 border border-zinc-100 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-zinc-200"
                  >
                    <option value="all">全部计划</option>
                    {plans.map(p => (
                      <option key={p.id} value={p.id}>{p.title}</option>
                    ))}
                  </select>
                </div>
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"/>
                  <input 
                    type="text" 
                    placeholder="搜索笔记..." 
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 bg-zinc-50 rounded-full text-sm border-none focus:ring-1 focus:ring-zinc-200 w-56 transition-all" 
                  />
                </div>
              </div>

              {filteredNotes.length > 0 ? (
                <div className="space-y-8">
                  {Object.entries(notesByPlan).map(([planId, group]) => (
                    <div key={planId}>
                      <h3 className="text-xs font-semibold text-zinc-400 mb-4 uppercase tracking-widest">
                        {group.title}
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {group.notes.map(note => (
                          <div
                            key={note.id}
                            className="group relative p-6 bg-zinc-50 rounded-2xl border border-zinc-100/50 hover:bg-white hover:shadow-md transition-all"
                          >
                            <button
                              onClick={() => actions.deleteNote(note.id)}
                              className="absolute top-3 right-3 p-1 text-zinc-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded-full hover:bg-red-50"
                              title="删除笔记"
                            >
                              <X size={13} />
                            </button>
                            <div
                              className="cursor-pointer"
                              onClick={() => navigate(`/graph/${note.planId}${note.nodeId ? `?node=${note.nodeId}` : ''}`)}
                            >
                              <div className="flex justify-between mb-3 pr-4">
                                <div className="flex flex-col gap-0.5">
                                  {note.nodeName && (
                                    <span className="text-[10px] font-medium text-teal-500">{note.nodeName}</span>
                                  )}
                                  <span className="text-[10px] text-zinc-400">{note.date}</span>
                                </div>
                                <CornerDownLeft size={13} className="text-zinc-300 group-hover:text-teal-500 transition-colors flex-shrink-0 mt-1" />
                              </div>
                              <p className="text-sm text-zinc-600 leading-relaxed line-clamp-3">{note.content}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-20 text-zinc-400">
                  <BookOpen size={48} className="mx-auto mb-4 opacity-20" strokeWidth={1}/>
                  {searchQuery || selectedPlanFilter !== 'all' ? '没有找到匹配的笔记' : '暂无笔记'}
                </div>
              )}
            </div>
          )}

          {/* Stats Tab */}
          {activeTab === 'stats' && (
            <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <section>
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">总览</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="已完成计划" value={statsData?.summary?.completedPlans ?? completedPlansCount} />
                  <StatCard label="进行中" value={statsData?.summary?.activePlans ?? activePlans.length} />
                  <StatCard label="掌握知识点" value={statsData?.summary?.masteredKnowledge ?? masteredKnowledgeCount} />
                  <StatCard label="学习笔记" value={statsData?.summary?.totalNotes ?? allNotes.length} />
                </div>
              </section>

              <section>
                <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest mb-6">知识领域分布</h2>
                <div className="bg-zinc-50 p-8 rounded-2xl border border-zinc-100 space-y-6">
                   {distributionData.length > 0 ? (
                     distributionData.map((item, i) => (
                       <ChartBar
                         key={item.domain || i}
                         label={item.domain || '未知'}
                         value={item.percentage || 0}
                         color={
                           item.domain?.includes('数学')
                             ? 'bg-blue-500'
                             : item.domain?.includes('编程')
                               ? 'bg-amber-500'
                               : 'bg-teal-500'
                         }
                         count={item.count || 0}
                       />
                     ))
                   ) : masteredKnowledgeCount > 0 ? (
                     <>
                       <ChartBar label="深度学习" value={0} color="bg-teal-500" count={0} />
                       <ChartBar label="数学基础" value={0} color="bg-blue-500" count={0} />
                       <ChartBar label="编程" value={0} color="bg-amber-500" count={0} />
                     </>
                   ) : (
                    <div className="text-center py-8 text-zinc-400 text-sm">
                      开始学习后，这里将显示你的知识领域分布
                    </div>
                  )}
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyLearningPage;
