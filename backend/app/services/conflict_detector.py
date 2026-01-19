"""
冲突检测服务
检测文档内部事实之间的矛盾和冲突
使用 LSH (局部敏感哈希) 快速过滤不相似的事实对，提高效率
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from itertools import combinations

from .llm_client import llm_client
from .redis_client import redis_client
from .lsh_filter import lsh_filter

logger = logging.getLogger(__name__)

# 冲突检测 Prompt 模板
CONFLICT_DETECTION_PROMPT = """以下是从同一文档不同位置提取的两个事实，请判断它们是否存在冲突或矛盾。

事实A：{fact_a_content}
类型：{fact_a_type}
原文：{fact_a_original}
位置：{fact_a_location}

事实B：{fact_b_content}
类型：{fact_b_type}
原文：{fact_b_original}
位置：{fact_b_location}

请仔细分析这两个事实，判断是否存在以下类型的冲突：
1. 数据不一致：同一指标出现不同数值
2. 逻辑矛盾：两个陈述在逻辑上互相排斥
3. 时间冲突：时间线或日期描述不一致
4. 定义冲突：对同一概念的定义不一致

注意：
- 如果两个事实描述的是不同的对象/指标，则不算冲突
- 如果数值差异在合理范围内（如四舍五入），则不算冲突
- 只有明确的矛盾才判定为冲突

请以 JSON 格式返回判断结果：
```json
{{
  "has_conflict": true或false,
  "conflict_type": "数据不一致/逻辑矛盾/时间冲突/定义冲突/无冲突",
  "severity": "高/中/低/无",
  "explanation": "详细说明冲突原因，如果无冲突则说明原因",
  "confidence": 0.0到1.0之间的置信度
}}
```

请只返回 JSON，不要包含其他内容："""


class ConflictDetector:
    """冲突检测器"""
    
    def __init__(self):
        self.llm = llm_client
        self.redis = redis_client
        self.lsh = lsh_filter
    
    async def detect_conflicts(
        self,
        document_id: str,
        facts: List[Dict[str, Any]] = None,
        save_to_redis: bool = True,
        use_lsh: bool = False,
        max_pairs: int = 200
    ) -> Dict[str, Any]:
        """
        检测文档中事实之间的冲突
        
        Args:
            document_id: 文档ID
            facts: 事实列表（如果为空，从 Redis 获取）
            save_to_redis: 是否保存结果到 Redis
            use_lsh: 是否使用 LSH 预过滤（提高效率）
            max_pairs: 最大比对对数
        
        Returns:
            冲突检测结果
        """
        # 如果没有提供事实列表，从 Redis 获取
        if facts is None:
            facts = self.redis.get_facts(document_id)
            if facts is None:
                raise ValueError(f"文档 {document_id} 的事实数据不存在")
        
        if len(facts) < 2:
            return {
                "document_id": document_id,
                "total_facts": len(facts),
                "total_comparisons": 0,
                "conflicts_found": 0,
                "conflicts": [],
                "message": "事实数量不足，无法进行冲突检测"
            }
        
        logger.info(f"开始冲突检测: 文档 {document_id}, 共 {len(facts)} 条事实")
        
        # 使用 LSH 预过滤或传统方法生成事实对
        if use_lsh:
            # 使用 LSH 预过滤；若结果过少，则回退到全量生成
            fact_pairs = self.lsh.filter_similar_pairs(facts, max_pairs=max_pairs)
            logger.info(f"LSH 过滤后: {len(fact_pairs)} 对事实进行比对 (原始可能 {len(facts) * (len(facts) - 1) // 2} 对)")
            if not fact_pairs:
                fact_pairs = self._generate_comparison_pairs(facts, max_pairs=max_pairs)
                logger.info(f"LSH 未命中，回退生成 {len(fact_pairs)} 对事实进行比对")
        else:
            # 直接全量/按类型生成，确保覆盖潜在矛盾
            fact_pairs = self._generate_comparison_pairs(facts, max_pairs=max_pairs)
            logger.info(f"生成 {len(fact_pairs)} 对事实进行比对")
        
        # 检测冲突
        conflicts = []
        comparison_count = 0
        
        for fact_a, fact_b in fact_pairs:
            comparison_count += 1
            
            try:
                result = await self._compare_facts(fact_a, fact_b)
                
                if result and result.get("has_conflict"):
                    conflict = {
                        "conflict_id": f"conflict_{document_id}_{len(conflicts)}",
                        "fact_a": {
                            "fact_id": fact_a.get("fact_id"),
                            "type": fact_a.get("type"),
                            "content": fact_a.get("content"),
                            "original_text": fact_a.get("original_text"),
                            "location": fact_a.get("location")
                        },
                        "fact_b": {
                            "fact_id": fact_b.get("fact_id"),
                            "type": fact_b.get("type"),
                            "content": fact_b.get("content"),
                            "original_text": fact_b.get("original_text"),
                            "location": fact_b.get("location")
                        },
                        "conflict_type": result.get("conflict_type", "未知"),
                        "severity": result.get("severity", "中"),
                        "explanation": result.get("explanation", ""),
                        "confidence": result.get("confidence", 0.5)
                    }
                    conflicts.append(conflict)
                    logger.info(f"发现冲突: {conflict['conflict_type']} - {conflict['explanation'][:50]}")
                    
            except Exception as e:
                logger.error(f"比对事实时出错: {str(e)}")
                continue
        
        # 按严重程度排序
        severity_order = {"高": 0, "中": 1, "低": 2, "无": 3}
        conflicts.sort(key=lambda x: severity_order.get(x.get("severity", "中"), 1))
        
        # 统计信息
        severity_stats = {}
        type_stats = {}
        for conflict in conflicts:
            severity = conflict.get("severity", "中")
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
            
            conflict_type = conflict.get("conflict_type", "未知")
            type_stats[conflict_type] = type_stats.get(conflict_type, 0) + 1
        
        result = {
            "document_id": document_id,
            "total_facts": len(facts),
            "total_comparisons": comparison_count,
            "conflicts_found": len(conflicts),
            "conflicts": conflicts,
            "statistics": {
                "by_severity": severity_stats,
                "by_type": type_stats
            }
        }
        
        # 保存到 Redis
        if save_to_redis and conflicts:
            try:
                self.redis.save_conflicts(document_id, conflicts)
                result["saved_to_redis"] = True
            except Exception as e:
                logger.error(f"保存冲突到 Redis 失败: {str(e)}")
                result["saved_to_redis"] = False
        
        logger.info(f"冲突检测完成: 文档 {document_id}, 发现 {len(conflicts)} 个冲突")
        
        return result
    
    def _generate_comparison_pairs(
        self,
        facts: List[Dict[str, Any]],
        max_pairs: int = 30
    ) -> List[Tuple[Dict, Dict]]:
        """
        生成需要比对的事实对
        
        优先比对同类型的事实（更可能存在冲突）
        """
        pairs = []
        
        # 按类型分组
        facts_by_type = {}
        for fact in facts:
            fact_type = fact.get("type", "未知")
            if fact_type not in facts_by_type:
                facts_by_type[fact_type] = []
            facts_by_type[fact_type].append(fact)
        
        # 优先添加同类型事实对
        for fact_type, type_facts in facts_by_type.items():
            if len(type_facts) >= 2:
                for pair in combinations(type_facts, 2):
                    pairs.append(pair)
                    if len(pairs) >= max_pairs:
                        return pairs
        
        # 如果同类型比对不够，添加跨类型比对（数据类型优先）
        data_types = ["数据", "日期", "结论"]
        for type_a in data_types:
            for type_b in data_types:
                if type_a != type_b:
                    facts_a = facts_by_type.get(type_a, [])
                    facts_b = facts_by_type.get(type_b, [])
                    for fa in facts_a:
                        for fb in facts_b:
                            pairs.append((fa, fb))
                            if len(pairs) >= max_pairs:
                                return pairs
        
        return pairs
    
    async def _compare_facts(
        self,
        fact_a: Dict[str, Any],
        fact_b: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 比对两个事实是否冲突
        """
        if not self.llm.is_available():
            raise ValueError("LLM 服务不可用")
        
        # 构建提示词
        prompt = CONFLICT_DETECTION_PROMPT.format(
            fact_a_content=fact_a.get("content", ""),
            fact_a_type=fact_a.get("type", "未知"),
            fact_a_original=fact_a.get("original_text", ""),
            fact_a_location=self._format_location(fact_a.get("location")),
            fact_b_content=fact_b.get("content", ""),
            fact_b_type=fact_b.get("type", "未知"),
            fact_b_original=fact_b.get("original_text", ""),
            fact_b_location=self._format_location(fact_b.get("location"))
        )
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的文档审核助手，擅长发现文档中的事实冲突和逻辑矛盾。请准确判断两个事实是否存在冲突，避免误报。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = await self.llm.chat(messages, temperature=0.1)
            return self._parse_conflict_response(response)
        except Exception as e:
            logger.error(f"LLM 比对失败: {str(e)}")
            return None
    
    def _format_location(self, location: Optional[Dict]) -> str:
        """格式化位置信息"""
        if not location:
            return "未知位置"
        
        section_title = location.get("section_title", "")
        section_index = location.get("section_index", 0)
        
        if section_title:
            return f"章节 {section_index + 1}: {section_title}"
        return f"章节 {section_index + 1}"
    
    def _parse_conflict_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 返回的冲突检测结果"""
        try:
            response = response.strip()
            
            # 移除可能的 markdown 代码块
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            result = json.loads(response)
            
            # 验证必需字段
            if "has_conflict" not in result:
                result["has_conflict"] = False
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析冲突检测 JSON 失败: {e}, 原始响应: {response[:200]}")
            return None
    
    def get_conflicts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """从 Redis 获取已保存的冲突"""
        return self.redis.get_conflicts(document_id)


# 全局冲突检测器实例
conflict_detector = ConflictDetector()

