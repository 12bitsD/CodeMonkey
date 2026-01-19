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
  const baseStyle = "group relative inline-flex items-center justify-center font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-full focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-zinc-200";
  
  const sizes = {
    sm: "px-4 py-1.5 text-xs",
    md: "px-6 py-2.5 text-sm",
    lg: "px-8 py-3.5 text-base"
  };

  const variants = {
    primary: "bg-zinc-900 text-white hover:bg-zinc-800 shadow-[0_2px_10px_rgba(24,24,27,0.15)] hover:shadow-[0_4px_20px_rgba(24,24,27,0.2)] active:scale-[0.98]",
    secondary: "bg-white text-zinc-700 border border-zinc-200 hover:bg-zinc-50 hover:border-zinc-300 shadow-sm active:scale-[0.98]",
    ghost: "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100/50 active:scale-[0.98]",
    outline: "border border-zinc-200 text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 active:scale-[0.98]",
    danger: "text-red-600 bg-red-50 hover:bg-red-100 border border-red-100 active:scale-[0.98]",
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
