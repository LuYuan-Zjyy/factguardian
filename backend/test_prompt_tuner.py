"""Tests for prompt_tuner language detection and template selection.

Run from the repo root:  python -m pytest backend/test_prompt_tuner.py
"""
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).parent / "app" / "services" / "prompt_tuner.py"
_spec = importlib.util.spec_from_file_location("prompt_tuner", _MODULE_PATH)
prompt_tuner_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prompt_tuner_mod)

detect_language = prompt_tuner_mod.detect_language
PROMPT_TEMPLATES_EN = prompt_tuner_mod.PROMPT_TEMPLATES_EN
tuner = prompt_tuner_mod.PromptTuner()

ZH_TEXT = "公司第一季度总营收为一千万美元，同比增长百分之十五，这是一个重要的财务数据。"
EN_TEXT = (
    "The company reported first-quarter revenue of ten million dollars, "
    "up fifteen percent year over year, according to the filing."
)


def test_detect_language_chinese():
    assert detect_language(ZH_TEXT) == "zh"


def test_detect_language_english():
    assert detect_language(EN_TEXT) == "en"


def test_detect_language_defaults_to_chinese_without_letters():
    assert detect_language("") == "zh"
    assert detect_language("12345 !!!") == "zh"


def test_detect_language_english_with_chinese_names():
    text = "The guideline was issued by the committee in Beijing last March and takes effect in June."
    assert detect_language(text) == "en"


def test_get_template_chinese_text_returns_zh_template_unchanged():
    zh = "中文模板 {x}"
    assert tuner.get_template("conflict", zh, text=ZH_TEXT) is zh


def test_get_template_english_text_returns_english_template():
    zh = "中文模板"
    result = tuner.get_template("conflict", zh, text=EN_TEXT)
    assert result is PROMPT_TEMPLATES_EN["conflict"]


def test_get_template_explicit_language_wins():
    zh = "中文模板"
    assert tuner.get_template("conflict", zh, text=ZH_TEXT, language="en") is PROMPT_TEMPLATES_EN["conflict"]
    assert tuner.get_template("conflict", zh, text=EN_TEXT, language="zh") is zh


def test_get_template_unknown_name_falls_back_to_zh():
    zh = "中文模板"
    assert tuner.get_template("no_such_template", zh, text=EN_TEXT) is zh


def test_english_conflict_template_formats_with_callsite_kwargs():
    out = PROMPT_TEMPLATES_EN["conflict"].format(
        fact_a_content="Revenue was 10 million dollars",
        fact_a_type="数据",
        fact_a_location="Section 1",
        fact_b_content="Revenue was 12 million dollars",
        fact_b_type="数据",
        fact_b_location="Section 3",
        fact_a_subject="extra kwargs are ignored",
    )
    assert "Revenue was 10 million dollars" in out
    assert '"has_conflict"' in out


def test_english_verification_template_formats():
    out = PROMPT_TEMPLATES_EN["verification"].format(
        claim="Revenue grew 15%", context="Q1 report", search_results="snippet"
    )
    assert "Revenue grew 15%" in out
    assert '"is_supported"' in out


def test_english_query_generation_template_formats():
    out = PROMPT_TEMPLATES_EN["query_generation"].format(
        fact_content="Revenue grew 15%", context="Q1",
        subject="company", predicate="grew", object="revenue", time="2024-Q1",
    )
    assert "Revenue grew 15%" in out


def test_english_extraction_user_template_formats():
    out = PROMPT_TEMPLATES_EN["extraction_user"].format(
        section_title="Overview", text=EN_TEXT,
        keywords="revenue", units="dollars", times="first quarter",
    )
    assert EN_TEXT in out
    assert '"verifiable_type"' in out


def test_all_expected_english_templates_present():
    for name in (
        "extraction_system",
        "extraction_user",
        "conflict_system",
        "conflict",
        "verification",
        "query_generation",
    ):
        assert name in PROMPT_TEMPLATES_EN and PROMPT_TEMPLATES_EN[name].strip()
