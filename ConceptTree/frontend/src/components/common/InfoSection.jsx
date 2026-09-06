import React from 'react';

const InfoSection = ({ icon: Icon, title, children }) => (
  <section className="rounded-xl border border-black/[0.07] bg-[#fbfbfa] p-5">
    <h4 className="mb-3 flex items-center gap-2 text-[0.65625rem] font-semibold uppercase leading-4 tracking-[0.075em] text-[#8f8e8b]">
      <Icon size={13} strokeWidth={1.8} /> {title}
    </h4>
    <div className="text-[0.8125rem] font-normal leading-[1.65] text-[#5f5e5b]">
      {children}
    </div>
  </section>
);

export default InfoSection;
