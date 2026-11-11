# -*- coding: utf-8 -*-
"""
Prompt Tuner
材料驱动提示优化器：根据输入材料（文本/事实）提炼领域提示、单位、时间短语等，
用于增强提取、验证、冲突检测的提示效果。
"""
import re
from typing import Dict, Any, List, Tuple

UNITS_PATTERNS = [
    r"\%", r"万元|人民币|元|美元|万元人民币|亿|万", r"人|户|家|台|件|公里|米|平方米|亩",
]
TIME_PATTERNS = [
    r"\d{4}年\d{1,2}月\d{1,2}日", r"\d{4}年\d{1,2}月", r"\d{4}年", r"\d{1,2}月\d{1,2}日",
    r"\d{4}-\d{1,2}-\d{1,2}", r"\d{4}-\d{1,2}", r"\d{4}/\d{1,2}/\d{1,2}",
    r"月底|年初|年末|上半年|下半年|季度|Q\d",
]

_CJK_RE = re.compile(r"[\u4e00-\u9fa5]")
_LATIN_RE = re.compile(r"[A-Za-z]")

# CJK characters as a share of all (CJK + Latin) letters at or above this
# ratio count as a Chinese document.
_ZH_RATIO_THRESHOLD = 0.2


def detect_language(text: str) -> str:
    """Detect the document language with a simple character heuristic.

    Returns "zh" when CJK characters make up at least
    ``_ZH_RATIO_THRESHOLD`` of the letters in ``text``, "en" when Latin
    letters dominate, and "zh" (the historical default) when the text has
    no letters at all.
    """
    text = text or ""
    cjk = len(_CJK_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    if cjk + latin == 0:
        return "zh"
    return "zh" if cjk / (cjk + latin) >= _ZH_RATIO_THRESHOLD else "en"


# English prompt templates, keyed by the names used in get_template().
# These mirror the Chinese templates used by llm_client (fact extraction),
# conflict_detector (conflict judgment) and verifier (verification) call
# sites: same placeholders and the same output schema. Enum values inside
# the output schema (fact "type", "conflict_type", "severity") deliberately
# keep the canonical values of the Chinese templates so parsed results and
# statistics stay comparable across languages.
PROMPT_TEMPLATES_EN: Dict[str, str] = {
    "extraction_system": """You are a professional fact-extraction assistant. Your task is to accurately extract key facts from the given text and output them in structured fields, for later consistency/conflict checking.

Extraction principles:
1. Extract complete facts, avoid fragmentation: merge closely related information into one complete fact.
2. Remove duplication: if a complete fact already contains an element (a person, organization, or place name), do not extract that element again on its own.
3. Judge verifiability:
   - verifiable_type: "public" -> verifiable through public information (historical events, organizations, people, published policies/guidelines)
   - verifiable_type: "internal" -> internal data / context-dependent (unpublished revenue, internal project dates, process states)
4. Structured fields: fill in the following fields where possible to support later checking:
   - subject (who / which project / which organization)
   - predicate (the relation, e.g. "founded", "complies with", "scheduled", "invested")
   - object (the target, e.g. "resident coordination", "the new guideline", "the booking system")
   - value (a numeric or text value; if it involves a ratio/amount/quantity, keep the original unit in modifiers.units)
   - modifiers (a dict, may contain units, scope, condition, etc.)
   - time (a normalized date or time range, e.g. 2026-03-20, end of March 2026)
   - polarity ("affirmative"/"negative")

Output requirements:
- Must return a valid JSON array
- Every fact must include original_text (a quote from the source) and confidence (0-1)
- Fill fields as completely as possible, but do not invent information that is not there""",
    "extraction_user": """Extract the key facts from the following text and output them in structured fields.

Section: {section_title}

Text:
---
{text}
---

Material-driven hints (from this section):
- Domain keywords (reference): {keywords}
- Common units (reference): {units}
- Time phrases (reference): {times}

Output format (a JSON array, one element per fact):
[
  {{
    "type": "事件",
    "subject": "SpaceX",
    "predicate": "founded",
    "object": "aerospace company",
    "value": "",
    "modifiers": {{"by": "Elon Musk"}},
    "time": "2002-01-01",
    "polarity": "affirmative",
    "content": "SpaceX is an aerospace company founded by Elon Musk in 2002",
    "original_text": "SpaceX was founded by Elon Musk",
    "verifiable_type": "public",
    "confidence": 0.95
  }},
  {{
    "type": "数据",
    "subject": "The company",
    "predicate": "total revenue",
    "object": "first quarter",
    "value": 1000,
    "modifiers": {{"units": "万美元"}},
    "time": "2024-Q1",
    "polarity": "affirmative",
    "content": "The company's total revenue in the first quarter was 10 million US dollars",
    "original_text": "According to the first-quarter report, the company's total revenue was 10 million US dollars",
    "verifiable_type": "public",
    "confidence": 0.90
  }}
]

Field notes:
- type: one of ["数据", "日期", "人名", "机构", "结论", "事件"] (canonical labels, kept identical to the Chinese template so stored facts stay comparable)
- subject/predicate/object: fill in where possible, to support later conflict detection
- value: a numeric or text value; for ratios/amounts give the raw number and put the unit in modifiers.units
- modifiers: extra notes (e.g. units, scope, condition)
- time: a normalized date or time range (e.g. 2026-03-20, end of March 2026, 2024-Q1)
- polarity: affirmative/negative
- content: a complete, standalone description of the fact (avoid fragmentation)
- original_text: a quote from the source text

verifiable_type rules (universal, apply to all kinds of text):

Mark as "public" (verifiable from external public sources) only when all of these hold:
1. **Tense**: describes an event that has already happened or a state that already exists (not a future plan)
2. **Verifiability**: information that can be checked from external sources, such as:
   - times, places, and people of historical events
   - published data, statistics, and reports
   - names or contents of published policies, regulations, and standards
   - observable objective facts (weather, accidents, public events)
3. **Non-subjectivity**: an objective statement, not a subjective evaluation or opinion

Mark as "internal" (the document's own position; do not verify online) when it is:
1. **A future commitment**: describes what will be done, a plan, or a goal (tense: will, plan to, intend to)
2. **The document's own view**: the author/organization's subjective evaluation, conclusion, or recommendation (e.g. "we believe", "it can be concluded", "we recommend")
3. **Internal data**: specific numbers provided by the author that cannot be checked externally (e.g. "we completed 65%", "this project invested 18 million")
4. **Planned measures**: descriptions of follow-up corrective measures, implementation plans, or management mechanisms

Examples (cross-domain):
- "Einstein was born in Germany in 1879" -> public (historical fact, checkable)
- "The company plans to launch a new product in 2026" -> internal (future plan)
- "According to the annual report, 2023 revenue was 5 billion dollars" -> public (published data, checkable)
- "Our revenue grew 15% year over year" -> internal (internal data provided by this document)
- "The Paris Agreement was signed in 2015" -> public (historical event)
- "The project will set up a daily reporting mechanism" -> internal (future measure)
- "Research shows a 2°C temperature rise leads to ..." -> public (published research conclusion)
- "We believe this technology is promising" -> internal (subjective evaluation)

- confidence: a confidence score between 0 and 1

Return only the JSON array:""",
    "conflict_system": "You are a professional document review assistant, skilled at spotting factual conflicts and logical contradictions in documents. Judge accurately whether two facts conflict, and avoid false positives.",
    "conflict": """Below are two facts extracted from different places in the same document. Judge whether they conflict or contradict each other.

Fact A: {fact_a_content}
(type: {fact_a_type} | location: {fact_a_location})

Fact B: {fact_b_content}
(type: {fact_b_type} | location: {fact_b_location})

Analyze the two facts carefully and judge whether a conflict exists (data inconsistency, logical contradiction, time conflict, etc.).

Return a single-line JSON only (no line breaks, no indentation, no extra whitespace):
{{"has_conflict": true or false, "conflict_type": "无冲突/数据不一致/逻辑矛盾/时间冲突", "severity": "无/低/中/高", "explanation": "brief explanation", "confidence": 0.5}}""",
    "verification": """
You are a rigorous fact-checking expert. Based on the search results, verify the truth of the following factual claim.

[Fact to verify]
"{claim}"

[Context]
"{context}"

[Relevant information found]
{search_results}

[Verification requirements]
1. Analyze with chain of thought:
   - Extract the core elements of the fact (subject, predicate, object, values, time, etc.)
   - Compare the core elements against the search results one by one
   - Identify direct evidence, indirect evidence, or contradicting evidence
   - Assess the reliability and timeliness of the sources

2. Key principles to prevent hallucination:
   - If the search results are completely unrelated to the fact, mark it as "cannot verify" rather than "supported"
   - If the search results are insufficient to judge, lower the confidence to "Low"
   - If an obvious contradiction is found, provide the correct information in correction
   - Do not reason from common sense; judge only from the search results

3. Output format (strict JSON, inside a ```json code block):
```json
{{
  "is_supported": true or false or null,
  "confidence_level": "High" or "Medium" or "Low",
  "assessment": "brief conclusion (under 50 words)",
  "correction": "if the fact is wrong, suggest a correction; if it is correct or cannot be judged, leave empty"
}}
```

[Special notes]
- is_supported=true: the search results clearly support the fact
- is_supported=false: the search results clearly refute the fact
- is_supported=null: the search results are insufficient to judge (unrelated or not enough information)
- confidence_level should be based on evidence strength: High (multiple authoritative sources), Medium (a single source or indirect evidence), Low (insufficient evidence or contradictions)
""",
    "query_generation": """
I need to verify the following fact with a search engine. Generate the 1-2 most effective search keywords or query strings for this fact.
Return only the query strings, one per line, nothing else.

Fact: {fact_content}
Context: {context}
Structured: subject={subject}, predicate={predicate}, object={object}, time={time}
""",
}


class PromptTuner:
    def detect_language(self, text: str) -> str:
        """Detect the document language; see the module-level function."""
        return detect_language(text)

    def get_template(self, name: str, zh_template: str, text: str = "", language: str = None) -> str:
        """Pick the prompt template matching the document language.

        ``language`` ("zh"/"en") wins when given; otherwise the language is
        detected from ``text``. Chinese (and any unknown language) returns
        ``zh_template`` unchanged, so existing Chinese behavior is
        preserved; English returns the template registered under ``name``
        in PROMPT_TEMPLATES_EN, falling back to ``zh_template`` when no
        English version exists.
        """
        lang = language or detect_language(text)
        if lang == "en":
            return PROMPT_TEMPLATES_EN.get(name, zh_template)
        return zh_template

    def derive_hints_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键词、单位、时间短语等提示信息。"""
        text = text or ""
        # 简单关键词（中文/英文词，长度>=2）
        tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{2,}", text)
        keywords = list({t for t in tokens if len(t) >= 2})[:20]
        # 单位
        units: List[str] = []
        for pat in UNITS_PATTERNS:
            units += re.findall(pat, text)
        units = list({u for u in units})
        # 时间短语
        times: List[str] = []
        for pat in TIME_PATTERNS:
            times += re.findall(pat, text)
        times = list({t for t in times})
        return {
            "keywords": keywords,
            "units": units,
            "time_phrases": times,
        }

    def build_verification_queries(self, fact: Dict[str, Any]) -> List[str]:
        """用结构字段组合1-2个查询语句，避免过度依赖LLM生成。"""
        subject = (fact.get("subject") or "").strip()
        predicate = (fact.get("predicate") or "").strip()
        obj = (fact.get("object") or "").strip()
        time = (fact.get("time") or "").strip()
        content = (fact.get("content") or "").strip()
        queries: List[str] = []
        base = " ".join([p for p in [subject, predicate, obj, time] if p])
        if base:
            queries.append(base)
        # 次选用原始内容（截断至较短）
        if content:
            queries.append(content[:200])
        return queries[:2]

# 全局实例
prompt_tuner = PromptTuner()
