"""
LLM 客户端服务
封装 DeepSeek API 调用
"""
import os
import json
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """DeepSeek LLM 客户端"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY 未设置，LLM 功能将不可用")
    
    def is_available(self) -> bool:
        """检查 LLM 是否可用"""
        return bool(self.api_key)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Optional[str]:
        """
        调用 DeepSeek Chat API
        
        Args:
            messages: 对话消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
        
        Returns:
            生成的文本内容，失败返回 None
        """
        if not self.is_available():
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API 请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"LLM 调用异常: {str(e)}")
            raise
    
    async def extract_facts(
        self,
        text: str,
        section_title: str = "",
        section_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取事实信息
        
        Args:
            text: 待提取的文本
            section_title: 章节标题（用于位置信息）
            section_index: 章节索引
        
        Returns:
            提取的事实列表，每个事实包含：
            - type: 事实类型（数据/日期/人名/结论/事件）
            - content: 事实内容
            - original_text: 原文引用
            - location: 位置信息
            - confidence: 置信度
        """
        prompt = self._build_extraction_prompt(text, section_title)
        
        messages = [
            {
                "role": "system",
                     "content": """你是一个专业的事实提取助手。你的任务是从给定文本中准确提取关键事实信息。

提取规则：
1. **提取完整事实，避免碎片化**：将相关信息合并成一条完整独立的事实
    ❌ 错误示例：单独提取 "SpaceX" + "比尔·盖茨" + "SpaceX是由比尔·盖茨创立的"
    ✅ 正确示例：只提取 "SpaceX是由比尔·盖茨创立的航天公司"（已包含公司名和创始人）

2. **去除重复**：如果一个完整事实已包含某个元素（人名、公司名），不要将该元素单独提取
3. **识别可验证性**：
    - verifiable_type: "public" → 可通过公开信息验证（历史事件、名人、公司创始人、科学事实）
    - verifiable_type: "internal" → 内部数据/上下文相关（没有具体公司名的营收、内部项目日期、团队信息）

输出要求：
- 必须返回有效的 JSON 数组格式
- 每个事实必须包含原文引用
- 评估每个事实的置信度（0-1）
- verifiable_type 字段必须填写
- 不要编造不存在的信息"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.chat(messages, temperature=0.1)
            facts = self._parse_facts_response(response, section_title, section_index)
            return facts
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            return []
    
    def _build_extraction_prompt(self, text: str, section_title: str) -> str:
        """构建事实提取提示词"""
        return f"""请从以下文本中提取关键事实信息。

章节：{section_title if section_title else "未知"}

文本内容：
---
{text}
---

提取规则（重要）：
1. **避免重复**：如果一个完整事实已经包含了某个元素（如人名、机构名），不要将该元素单独提取
   例如："SpaceX是由埃隆·马斯克创立的" → 只提取这一条，不要再单独提取"SpaceX"和"埃隆·马斯克"
   
2. **合并相关事实**：将紧密相关的信息合并成一条完整事实
   例如："Python由吉多·范罗苏姆于1991年发布" → 合并为一条，不要拆分成两条
   
3. **识别数据类型**：
   - verifiable_type: "public" - 可公开验证的事实（历史事件、名人、公司创始人、语言发布时间等）
   - verifiable_type: "internal" - 内部数据，无法联网验证（公司营收、项目启动时间、内部结论等）

输出格式（JSON 数组）：
[
  {{
    "type": "事件",
    "content": "SpaceX是由埃隆·马斯克于2002年创立的航天公司",
    "original_text": "SpaceX是由埃隆·马斯克创立的航天公司",
    "verifiable_type": "public",
    "confidence": 0.95
  }},
  {{
    "type": "数据",
    "content": "第一季度公司总营收为1000万美元",
    "original_text": "根据第一季度财报显示，公司总营收为 1000 万美元",
    "verifiable_type": "internal",
    "confidence": 0.90
  }}
]

字段说明：
- type: ["数据", "日期", "人名", "机构", "结论", "事件"] 之一
- content: 完整、独立的事实描述（避免碎片化）
- original_text: 原文引用
- verifiable_type: "public" 或 "internal"
- confidence: 0-1 之间的置信度

请只返回 JSON 数组："""
    
    def _parse_facts_response(
        self,
        response: str,
        section_title: str,
        section_index: int
    ) -> List[Dict[str, Any]]:
        """解析 LLM 返回的事实数据"""
        try:
            # 尝试提取 JSON 内容
            response = response.strip()
            
            # 移除可能的 markdown 代码块
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            facts = json.loads(response)
            
            if not isinstance(facts, list):
                facts = [facts]
            
            # 添加位置信息
            for i, fact in enumerate(facts):
                fact["location"] = {
                    "section_title": section_title,
                    "section_index": section_index
                }
                fact["fact_id"] = f"fact_{section_index}_{i}"
            
            return facts
            
        except json.JSONDecodeError as e:
            logger.error(f"解析事实 JSON 失败: {e}, 原始响应: {response[:200]}")
            return []


# 全局 LLM 客户端实例
llm_client = LLMClient()

