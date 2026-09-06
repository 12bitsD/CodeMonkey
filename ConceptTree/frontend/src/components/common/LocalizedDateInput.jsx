import React from "react";

import { useLanguage } from "../../contexts/LanguageContext";

export const formatLocalizedDate = (value, language) => {
  if (!value) return language === "zh-CN" ? "年 / 月 / 日" : "MM / DD / YYYY";

  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;

  return language === "zh-CN"
    ? `${year} / ${month} / ${day}`
    : `${month} / ${day} / ${year}`;
};

const LocalizedDateInput = ({
  language: languageOverride,
  value = "",
  wrapperClassName = "",
  className = "",
  ...inputProps
}) => {
  const { language: contextLanguage } = useLanguage();
  const language = languageOverride || contextLanguage;

  return (
    <div className={`relative ${wrapperClassName}`}>
      <input
        {...inputProps}
        type="date"
        lang={language === "zh-CN" ? "zh-CN" : "en-US"}
        value={value}
        className={`localized-date-input relative z-10 w-full text-transparent caret-transparent ${className}`}
      />
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute inset-y-0 left-4 right-10 z-20 flex items-center text-sm ${
          value ? "text-zinc-700" : "text-zinc-500"
        }`}
      >
        {formatLocalizedDate(value, language)}
      </span>
    </div>
  );
};

export default LocalizedDateInput;
