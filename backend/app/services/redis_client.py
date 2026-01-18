"""
Redis 客户端服务
用于存储和检索事实数据
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "redis")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端（延迟连接）"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
        return self._client
    
    def is_connected(self) -> bool:
        """检查 Redis 是否连接"""
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 连接失败: {str(e)}")
            return False
    
    def save_facts(self, document_id: str, facts: List[Dict[str, Any]]) -> bool:
        """
        保存文档的事实列表
        
        Args:
            document_id: 文档ID
            facts: 事实列表
        
        Returns:
            是否保存成功
        """
        try:
            key = f"facts:{document_id}"
            value = json.dumps(facts, ensure_ascii=False)
            self.client.set(key, value)
            
            # 设置过期时间（24小时）
            self.client.expire(key, 86400)
            
            logger.info(f"保存事实成功: {document_id}, 共 {len(facts)} 条")
            return True
        except Exception as e:
            logger.error(f"保存事实失败: {str(e)}")
            return False
    
    def get_facts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取文档的事实列表
        
        Args:
            document_id: 文档ID
        
        Returns:
            事实列表，不存在返回 None
        """
        try:
            key = f"facts:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                return None
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取事实失败: {str(e)}")
            return None
    
    def delete_facts(self, document_id: str) -> bool:
        """删除文档的事实"""
        try:
            key = f"facts:{document_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除事实失败: {str(e)}")
            return False
    
    def save_document_metadata(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """保存文档元数据"""
        try:
            key = f"doc:{document_id}"
            value = json.dumps(metadata, ensure_ascii=False)
            self.client.set(key, value)
            self.client.expire(key, 86400)
            return True
        except Exception as e:
            logger.error(f"保存文档元数据失败: {str(e)}")
            return False
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档元数据"""
        try:
            key = f"doc:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                return None
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取文档元数据失败: {str(e)}")
            return None
    
    def list_documents(self) -> List[str]:
        """列出所有文档ID"""
        try:
            keys = self.client.keys("doc:*")
            return [key.replace("doc:", "") for key in keys]
        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return []
    
    def save_conflicts(self, document_id: str, conflicts: List[Dict[str, Any]]) -> bool:
        """
        保存文档的冲突列表
        
        Args:
            document_id: 文档ID
            conflicts: 冲突列表
        
        Returns:
            是否保存成功
        """
        try:
            key = f"conflicts:{document_id}"
            value = json.dumps(conflicts, ensure_ascii=False)
            self.client.set(key, value)
            
            # 设置过期时间（24小时）
            self.client.expire(key, 86400)
            
            logger.info(f"保存冲突成功: {document_id}, 共 {len(conflicts)} 条")
            return True
        except Exception as e:
            logger.error(f"保存冲突失败: {str(e)}")
            return False
    
    def get_conflicts(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取文档的冲突列表
        
        Args:
            document_id: 文档ID
        
        Returns:
            冲突列表，不存在返回 None
        """
        try:
            key = f"conflicts:{document_id}"
            value = self.client.get(key)
            
            if value is None:
                return None
            
            return json.loads(value)
        except Exception as e:
            logger.error(f"获取冲突失败: {str(e)}")
            return None
    
    def delete_conflicts(self, document_id: str) -> bool:
        """删除文档的冲突"""
        try:
            key = f"conflicts:{document_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"删除冲突失败: {str(e)}")
            return False


# 全局 Redis 客户端实例
redis_client = RedisClient()

