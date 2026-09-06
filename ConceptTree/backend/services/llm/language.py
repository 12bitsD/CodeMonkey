from __future__ import annotations

from typing import Literal


LanguageCode = Literal["en-US", "zh-CN"]
DEFAULT_LANGUAGE: LanguageCode = "en-US"


def normalize_language(language: str | None) -> LanguageCode:
    return "zh-CN" if language == "zh-CN" else DEFAULT_LANGUAGE


def response_language_instruction(
    language: str | None,
    *,
    json_mode: bool = False,
) -> str:
    normalized = normalize_language(language)
    format_note = (
        " Keep JSON keys and enum values exactly as specified; translate only "
        "user-visible natural-language values."
        if json_mode
        else ""
    )
    if normalized == "zh-CN":
        return (
            "[最高优先级语言要求] 用户界面语言为简体中文。所有面向用户的标题、"
            "解释、问题、反馈、原因、学习内容和建议都必须只使用自然、清晰的简体中文。"
            "不要夹杂英文句子；代码、公式、专有名词和无法自然翻译的术语除外。"
            + (
                " JSON 的键名和枚举值必须保持 schema 原样，只翻译面向用户的自然语言值。"
                if json_mode
                else ""
            )
        )
    return (
        "[HIGHEST-PRIORITY LANGUAGE REQUIREMENT] The interface language is English. "
        "Write every user-visible title, explanation, question, feedback message, reason, "
        "lesson, and recommendation in natural, clear English only. Do not include Chinese "
        "sentences, even when the user's input or existing learning context is Chinese; "
        "translate that context into English. Code, formulas, and proper nouns may remain unchanged."
        + format_note
    )


def apply_response_language(
    system_prompt: str,
    language: str | None,
    *,
    json_mode: bool = False,
) -> str:
    return f"{system_prompt.rstrip()}\n\n{response_language_instruction(language, json_mode=json_mode)}"
