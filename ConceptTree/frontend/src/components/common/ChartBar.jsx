import React from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

const ChartBar = ({ label, value, color, count }) => {
  const { t } = useLanguage();
  return <div className="space-y-2">
    <div className="flex justify-between text-xs font-medium text-zinc-500">
      <span>{label}</span>
      <span>{t('chart.concepts', { count })}</span>
    </div>
    <div className="h-3 bg-zinc-200/50 rounded-full overflow-hidden">
      <div 
        className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`} 
        style={{ width: `${value}%` }}
      />
    </div>
  </div>;
};

export default ChartBar;
