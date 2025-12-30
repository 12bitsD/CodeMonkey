import React from 'react';

const ChartBar = ({ label, value, color, count }) => (
  <div className="space-y-2">
    <div className="flex justify-between text-xs font-medium text-zinc-500">
      <span>{label}</span>
      <span>{count} 知识点</span>
    </div>
    <div className="h-3 bg-zinc-200/50 rounded-full overflow-hidden">
      <div 
        className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`} 
        style={{ width: `${value}%` }}
      />
    </div>
  </div>
);

export default ChartBar;
