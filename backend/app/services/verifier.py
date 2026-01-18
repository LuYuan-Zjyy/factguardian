"""
Fact Verification Service
Verifies extracted facts using external search and LLM assessment.
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.services.llm_client import LLMClient
from app.services.search_client import SearchClient
from app.services.redis_client import RedisClient

logger = logging.getLogger(__name__)

VERIFICATION_PROMPT_TEMPLATE = """
你需要验证以下事实的真实性。

文档中声称的事实：
"{claim}"

上下文背景：
"{context}"

搜索到的相关信息：
{search_results}

请评估该事实的真实性。

请严格按照以下 JSON 格式输出：
{{
  "is_supported": true/false,
  "confidence_level": "High/Medium/Low",
  "assessment": "简短的评估说明，解释为什么支持或不支持",
  "correction": "如果事实错误，请提供正确的建议值，否则留空"
}}
"""

QUERY_GENERATION_PROMPT = """
我需要通过搜索引擎验证以下事实。请为这个事实生成 1-2 个最有效的搜索关键词或查询语句。
只返回查询语句，每行一个，不要有其他废话。

事实：{fact_content}
上下文：{context}
"""

class FactVerifier:
    def __init__(self):
        self.llm_client = LLMClient()
        self.search_client = SearchClient()
        self.redis_client = RedisClient()

    async def verify_document_facts(self, document_id: str, fact_idxs: List[int] = None) -> List[Dict[str, Any]]:
        self.last_debug = {} # Store debug info
        
        # 1. Get facts from Redis
        facts_data = self.redis_client.get_facts(document_id)
        if not facts_data:
            logger.warning(f"No facts found for document {document_id}")
            self.last_debug["error"] = "No facts in redis (None)"
            return []

        if isinstance(facts_data, dict) and "facts" in facts_data:
            all_facts = facts_data["facts"]
        elif isinstance(facts_data, list):
            all_facts = facts_data
        else:
            self.last_debug["error"] = f"Invalid facts format: {type(facts_data)}"
            return []

        self.last_debug["total_facts"] = len(all_facts)
        self.last_debug["sample_type"] = all_facts[0].get("type") if all_facts else "None"
        
        # Determine which facts to verify
        facts_to_verify = []
        if fact_idxs:
            for idx in fact_idxs:
                if 0 <= idx < len(all_facts):
                    facts_to_verify.append((idx, all_facts[idx]))
        else:
            # Automatic mode: Only verify PUBLIC facts that can be externally verified
            # Skip internal data (company revenue, project dates, etc.)
            MAX_AUTO_VERIFY = 50
            
            for i, fact in enumerate(all_facts):
                if i >= MAX_AUTO_VERIFY: 
                    logger.warning(f"Reached verification limit {MAX_AUTO_VERIFY}, skipping rest")
                    break
                
                # Check if this is a verifiable public fact
                verifiable_type = fact.get('verifiable_type', 'public')
                if verifiable_type == 'internal':
                    logger.info(f"Skipping internal fact {i}: {fact.get('content', '')[:50]}")
                    continue
                    
                facts_to_verify.append((i, fact))
                        
        self.last_debug["selected_count"] = len(facts_to_verify)
        self.last_debug["selected_indices"] = [f[0] for f in facts_to_verify]
        
        results = []
        
        # 2. Process each fact
        # First, add skipped internal facts to results
        for i, fact in enumerate(all_facts):
            verifiable_type = fact.get('verifiable_type', 'public')
            if verifiable_type == 'internal' and not fact_idxs:
                # Mark as skipped
                results.append({
                    "fact_index": i,
                    "original_fact": fact,
                    "is_supported": None,
                    "confidence_level": "N/A",
                    "assessment": "内部数据，无法通过公开信息验证。建议使用'冲突检测'功能检查与其他事实的一致性。",
                    "correction": "",
                    "skipped": True,
                    "skip_reason": "internal_data"
                })
        
        # Then verify public facts
        for idx, fact in facts_to_verify:
            verification_result = await self._verify_single_fact(fact)
            verification_result["fact_index"] = idx
            verification_result["original_fact"] = fact
            verification_result["skipped"] = False
            results.append(verification_result)

        # 3. Store verification results in Redis (optional, but good for persistence)
        # We could append to a "verifications:{doc_id}" key
        try:
            if hasattr(self.redis_client, 'client'):
                self.redis_client.client.set(f"verifications:{document_id}", json.dumps(results, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"Failed to store verification results in Redis: {str(e)}, continuing anyway...")
        
        return results

    async def _verify_single_fact(self, fact: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a single fact"""
        content = fact.get("content", "")
        context = fact.get("context", "")
        
        # Check LLM availability
        if not self.llm_client.is_available():
            logger.warning("LLM not available, returning mock verification result")
            return {
                "is_supported": False,
                "confidence_level": "Low",
                "assessment": "LLM服务不可用（未配置 API Key），无法进行智能校验。仅作为占位返回。",
                "correction": "请配置 DEEPSEEK_API_KEY 以启用真实校验。",
                "search_query_used": "Mock Query",
                "search_snippets": ["Mock Search Result"]
            }

        # Step 1: Generate Search Query
        query_prompt = QUERY_GENERATION_PROMPT.format(fact_content=content, context=context)
        # Use a simple user message
        messages = [{"role": "user", "content": query_prompt}]
        query_response = await self.llm_client.chat(messages)
        
        # Parse query (take the first line)
        queries = [q.strip() for q in query_response.strip().split('\n') if q.strip()]
        search_query = queries[0] if queries else content
        
        logger.info(f"Generated search query: {search_query}")
        
        # Step 2: Perform Search
        search_results = await self.search_client.search(search_query, max_results=3)
        search_text = "\n\n".join(search_results)
        
        # Step 3: Verify with LLM
        verify_prompt = VERIFICATION_PROMPT_TEMPLATE.format(
            claim=content,
            context=context,
            search_results=search_text
        )
        
        messages = [{"role": "user", "content": verify_prompt}]
        raw_result = await self.llm_client.chat(messages)
        
        # Step 4: Parse JSON result
        try:
            # Clean up potential markdown code blocks
            clean_result = raw_result.strip()
            if clean_result.startswith("```json"):
                clean_result = clean_result[7:]
            if clean_result.endswith("```"):
                clean_result = clean_result[:-3]
            
            parsed_result = json.loads(clean_result)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse verification result: {raw_result}")
            parsed_result = {
                "is_supported": False,
                "confidence_level": "Low",
                "assessment": "无法解析模型输出",
                "correction": ""
            }
            
        parsed_result["search_query_used"] = search_query
        parsed_result["search_snippets"] = search_results
        
        return parsed_result
