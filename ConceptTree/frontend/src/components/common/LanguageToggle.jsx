import React from "react";
import { Languages } from "lucide-react";
import { useLanguage } from "../../contexts/LanguageContext";

const LanguageToggle = ({ className = "" }) => {
  const { language, setLanguage, t } = useLanguage();

  return (
    <div
      className={`apple-segmented inline-flex items-center gap-1 ${className}`}
      role="group"
      aria-label={t("language.switch")}
    >
      <Languages size={14} aria-hidden="true" className="ml-1.5 text-[var(--color-label-tertiary)]" />
      {[
        ["en", "EN"],
        ["zh-CN", "中文"],
      ].map(([value, label]) => (
        <button
          key={value}
          type="button"
          onClick={() => setLanguage(value)}
          className={`min-h-8 rounded-[9px] px-2.5 text-xs font-semibold transition-[background-color,color,box-shadow,transform] duration-150 active:scale-[0.97] ${
            language === value
              ? "bg-white text-[var(--color-label)] shadow-[0_1px_3px_rgba(0,0,0,0.12)]"
              : "text-[var(--color-label-secondary)] hover:text-[var(--color-label)]"
          }`}
          aria-pressed={language === value}
        >
          {label}
        </button>
      ))}
    </div>
  );
};

export default LanguageToggle;
