import React from 'react';

const Button = ({ 
  children, 
  variant = 'primary', 
  className = '', 
  onClick, 
  icon: Icon, 
  disabled, 
  size = 'md' 
}) => {
  const baseStyle = "group relative inline-flex items-center justify-center rounded-full font-semibold transition-[background-color,color,border-color,box-shadow,transform] duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.97]";
  
  const sizes = {
    sm: "min-h-9 px-4 py-1.5 text-xs",
    md: "min-h-11 px-6 py-2.5 text-sm",
    lg: "min-h-12 px-8 py-3 text-base"
  };

  const variants = {
    primary: "bg-[#007AFF] text-white shadow-[0_2px_8px_rgba(0,122,255,0.24)] hover:bg-[#0071E3] hover:shadow-[0_4px_14px_rgba(0,122,255,0.28)]",
    secondary: "border border-white/80 bg-white/80 text-zinc-800 shadow-sm backdrop-blur-xl hover:bg-white",
    ghost: "text-zinc-500 hover:bg-black/[0.05] hover:text-zinc-900",
    outline: "border border-black/[0.12] bg-white/50 text-zinc-700 hover:border-black/[0.2] hover:bg-white/80",
    danger: "border border-red-200/70 bg-red-50 text-red-600 hover:bg-red-100",
  };

  const variantStyle = variants[variant] || variants.primary;

  return (
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`${baseStyle} ${sizes[size]} ${variantStyle} ${className}`}
    >
      {Icon && (
        <Icon 
          size={size === 'sm' ? 14 : 16} 
          strokeWidth={2} 
          className="mr-2 transition-transform group-hover:scale-105" 
        />
      )}
      {children}
    </button>
  );
};

export default Button;
