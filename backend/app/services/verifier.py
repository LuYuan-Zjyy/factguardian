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
from app.services.prompt_tuner import prompt_tuner

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

请采用思维链（Chain of Thought）的方式进行分析：
1. 分析事实的核心主张（主体、谓词、客体、时间等）。
2. 将核心主张与搜索到的信息进行比对。
3. 检查是否存在矛盾或确认的证据。
4. 综合判断置信度。

最后，请严格按照以下 JSON 格式输出结果（JSON需包含在 ```json 代码块中）：
```json
{{
  "is_supported": true或false,
  "confidence_level": "High"或"Medium"或"Low",
  "assessment": "根据上述分析的简短结论",
  "correction": "如果事实错误，请提供正确的建议值，否则留空"
}}
```
"""
QUERY_GENERATION_PROMPT = """
我需要通过搜索引擎验证以下事实。请为这个事实生成 1-2 个最有效的搜索关键词或查询语句。
只返回查询语句，每行一个，不要有其他废话。

事实：{fact_content}
上下文：{context}
结构化：主体={subject}，谓词={predicate}，客体={object}，时间={time}
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
            # Automatic mode: Verify more PUBLIC facts for better coverage
            # Increased limit from 50 to 200 to cover more facts
            MAX_AUTO_VERIFY = 200
            
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
        
        # Then verify public facts in parallel batches
        batch_size = 10  # 每批并行处理10个事实
        for i in range(0, len(facts_to_verify), batch_size):
            batch = facts_to_verify[i:i + batch_size]
            
            # Create verification tasks for this batch
            tasks = []
            for idx, fact in batch:
                task = self._verify_single_fact(fact)
                tasks.append((idx, fact, task))
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(
                *[task for _, _, task in tasks],
                return_exceptions=True
            )
            
            # Process results
            for (idx, fact, _), result in zip(tasks, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Verification failed for fact {idx}: {str(result)}")
                    # Add error result
                    results.append({
                        "fact_index": idx,
                        "original_fact": fact,
                        "is_supported": None,
                        "confidence_level": "Low",
                        "assessment": f"验证过程出错: {str(result)}",
                        "correction": "",
                        "skipped": False
                    })
                else:
                    result["fact_index"] = idx
                    result["original_fact"] = fact
                    result["skipped"] = False
                    results.append(result)

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

        # Step 1: Build Search Query using structured fields first
        structured_queries = prompt_tuner.build_verification_queries(fact)
        search_query = structured_queries[0] if structured_queries else None
        
        # If no good structured query, fall back to LLM query generation
        if not search_query:
            query_prompt = QUERY_GENERATION_PROMPT.format(
                fact_content=content,
                context=context,
                subject=(fact.get("subject") or ""),
                predicate=(fact.get("predicate") or ""),
                object=(fact.get("object") or ""),
                time=(fact.get("time") or "")
            )
            messages = [{"role": "user", "content": query_prompt}]
            query_response = await self.llm_client.chat(messages)
            queries = [q.strip() for q in query_response.strip().split('\n') if q.strip()]
            search_query = queries[0] if queries else content
        
        logger.info(f"Generated search query: {search_query}")
        
        # Step 2: Perform Search
        search_results = await self.search_client.search(search_query, max_results=3)
        search_text = "\n\n".join(search_results)
        
        # Step 3: Verify with LLM (simplified prompt)
        verify_prompt = VERIFICATION_PROMPT_TEMPLATE.format(
            claim=content,
            context=context,
            search_results=search_text
        )
        
        messages = [{"role": "user", "content": verify_prompt}]
        raw_result = await self.llm_client.chat(messages)
        logger.debug(f"Raw verification result: {raw_result[:300]}")
        
        # Step 4: Parse JSON result with robust error handling
        try:
            # 尝试提取 JSON 内容（兼容包含思维链的情况）
            content_to_parse = raw_result.strip()
            
            # 策略1: 寻找 markdown 代码块
            json_start = content_to_parse.find("```json")
            if json_start != -1:
                json_start += 7
                json_end = content_to_parse.find("```", json_start)
                if json_end != -1:
                    content_to_parse = content_to_parse[json_start:json_end]
                else:
                    content_to_parse = content_to_parse[json_start:]
            else:
                # 策略2: 寻找最外层的 {}
                start_idx = content_to_parse.find("{")
                end_idx = content_to_parse.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    content_to_parse = content_to_parse[start_idx:end_idx+1]

            content_to_parse = content_to_parse.strip()
            logger.debug(f"Parsed JSON content: {content_to_parse[:300]}")
            
            parsed_result = json.loads(content_to_parse)
            
            # Validate required fields
            if "is_supported" not in parsed_result:
                raise ValueError("Missing 'is_supported' field")
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse verification result: {e}. Raw: {raw_result[:500]}")
            # Return default result on parse error
            parsed_result = {
                "is_supported": None,
                "confidence_level": "Low",
                "assessment": "模型输出格式错误，无法解析。请检查LLM的返回格式。",
                "correction": ""
            }
            
        parsed_result["search_query_used"] = search_query
        parsed_result["search_snippets"] = search_results
        
        return parsed_result
