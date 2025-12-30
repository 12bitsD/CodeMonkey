import React from 'react';

const StatCard = ({ label, value }) => (
  <div className="bg-zinc-50 border border-zinc-100 p-6 rounded-2xl text-center hover:bg-white hover:shadow-md transition-all">
    <div className="text-3xl font-light text-zinc-900 mb-2">{value}</div>
    <div className="text-xs font-bold text-zinc-400 uppercase tracking-wider">{label}</div>
  </div>
);

export default StatCard;
