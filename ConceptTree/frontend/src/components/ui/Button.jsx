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
  const baseStyle = "group relative inline-flex items-center justify-center rounded-[7px] font-medium transition-[background-color,color,border-color,box-shadow,transform] duration-150 ease-out disabled:cursor-not-allowed disabled:opacity-45 active:scale-[0.98]";
  
  const sizes = {
    sm: "min-h-8 px-3 py-1.5 text-xs",
    md: "min-h-10 px-4 py-2 text-sm",
    lg: "min-h-11 px-5 py-2.5 text-sm"
  };

  const variants = {
    primary: "bg-[#202020] text-white shadow-[0_1px_2px_rgba(0,0,0,0.12)] hover:bg-black",
    secondary: "border border-black/[0.12] bg-white text-[#37352f] shadow-[0_1px_1px_rgba(0,0,0,0.04)] hover:bg-[#f7f6f3]",
    ghost: "text-zinc-500 hover:bg-black/[0.05] hover:text-zinc-900",
    outline: "border border-black/[0.12] bg-white text-zinc-700 hover:border-black/[0.2] hover:bg-[#f7f6f3]",
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
