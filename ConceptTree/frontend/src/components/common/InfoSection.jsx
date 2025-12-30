import React from 'react';

const InfoSection = ({ icon: Icon, title, children }) => (
  <section className="bg-zinc-50/50 p-6 rounded-2xl border border-zinc-100/50">
    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-3 flex items-center gap-2">
      <Icon size={14} /> {title}
    </h4>
    <div className="text-sm text-zinc-700 leading-relaxed font-light">
      {children}
    </div>
  </section>
);

export default InfoSection;
