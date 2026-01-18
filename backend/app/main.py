"""
FactGuardian Backend - FastAPI Application
"""
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.services.parser import DocumentParser
from app.services.fact_extractor import fact_extractor
from app.services.conflict_detector import conflict_detector
from app.services.verifier import FactVerifier
from app.services.redis_client import redis_client
from app.services.llm_client import llm_client

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FactGuardian API",
    description="A cloud-native intelligent agent for long-text fact consistency verification",
    version="1.0.0"
)

# 初始化文档解析器
parser = DocumentParser()
verifier = FactVerifier()


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "message": "FactGuardian API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    redis_status = "connected" if redis_client.is_connected() else "disconnected"
    llm_status = "configured" if llm_client.is_available() else "not_configured"
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "FactGuardian Backend",
            "redis": redis_status,
            "llm": llm_status
        }
    )


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档并解析
    
    支持的文件类型：
    - Word 文档 (.docx)
    - PDF 文档 (.pdf)
    - 文本文件 (.txt)
    - Markdown 文件 (.md, .markdown)
    
    返回解析后的结构化文本，包含章节信息
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        logger.info(f"开始解析文件: {file.filename}, 类型: {file_ext}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 解析文档
        try:
            result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        # 验证解析结果
        if result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空，无法解析")
        
        logger.info(f"解析成功: {file.filename}, 字数: {result['word_count']}, 章节数: {len(result['sections'])}")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]

        # 保存解析结果到 Redis，以便后续步骤复用
        document_data = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": result['file_type'],
            "word_count": result['word_count'],
            "section_count": len(result['sections']),
            "metadata": result['metadata'],
            "sections": result['sections'],
            "text": result['text']
        }
        redis_client.save_document_metadata(document_id, document_data)
        
        # 返回结构化结果
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "file_type": result['file_type'],
            "word_count": result['word_count'],
            "section_count": len(result['sections']),
            "metadata": result['metadata'],
            "sections": result['sections'],
            "full_text": result['text']  # 完整文本（可选，如果文本很大可以只返回摘要）
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/extract-facts")
async def extract_facts(file: UploadFile = File(...)):
    """
    上传文档并提取事实
    
    流程：
    1. 解析文档
    2. 使用 LLM 提取事实（数据、日期、人名、结论等）
    3. 保存到 Redis
    
    返回提取的事实列表，包含位置信息和置信度
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        logger.info(f"开始处理文件: {file.filename}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 解析文档
        try:
            parse_result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        if parse_result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]
        
        # 保存解析结果到 Redis
        document_data = {
            "document_id": document_id,
            "filename": file.filename,
            "file_type": parse_result['file_type'],
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "metadata": parse_result['metadata'],
            "sections": parse_result['sections'],
            "text": parse_result['text']
        }
        redis_client.save_document_metadata(document_id, document_data)
        
        logger.info(f"开始提取事实: {file.filename}, 文档ID: {document_id}")
        
        # 提取事实
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=parse_result['sections'],
                filename=file.filename,
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
        
        logger.info(f"事实提取完成: {file.filename}, 共 {extraction_result['total_facts']} 条事实")
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "total_facts": extraction_result['total_facts'],
            "facts": extraction_result['facts'],
            "statistics": extraction_result['statistics'],
            "section_stats": extraction_result['section_stats'],
            "saved_to_redis": extraction_result.get('saved_to_redis', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/documents/{document_id}/extract-facts")
async def extract_facts_by_id(document_id: str):
    """
    根据文档ID提取事实（复用已上传的文档）
    
    前提：必须先调用 /api/upload 上传并解析文档，获取 document_id
    """
    try:
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
            
        # 从 Redis 获取文档元数据（包含内容）
        doc_data = redis_client.get_document_metadata(document_id)
        if not doc_data:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期，请先调用 /api/upload 上传文档"
            )
            
        sections = doc_data.get('sections', [])
        filename = doc_data.get('filename', 'unknown')
        
        if not sections:
            raise HTTPException(
                status_code=400,
                detail="文档内容为空或格式错误"
            )
            
        logger.info(f"开始基于ID提取事实: {filename}, 文档ID: {document_id}")
        
        # 提取事实
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=sections,
                filename=filename,
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
            
        logger.info(f"事实提取完成: {filename}, 共 {extraction_result['total_facts']} 条事实")
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": filename,
            "word_count": doc_data.get('word_count', 0),
            "section_count": len(sections),
            "total_facts": extraction_result['total_facts'],
            "facts": extraction_result['facts'],
            "statistics": extraction_result['statistics'],
            "section_stats": extraction_result['section_stats'],
            "saved_to_redis": extraction_result.get('saved_to_redis', False)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取事实时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )



@app.get("/api/facts/{document_id}")
async def get_document_facts(document_id: str):
    """
    获取已保存的文档事实
    
    Args:
        document_id: 文档ID（从 extract-facts 返回）
    
    Returns:
        该文档的所有事实
    """
    try:
        facts = fact_extractor.get_facts(document_id)
        metadata = fact_extractor.get_document_info(document_id)
        
        if facts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期"
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "metadata": metadata,
            "total_facts": len(facts),
            "facts": facts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取事实失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/detect-conflicts/{document_id}")
async def detect_conflicts(document_id: str):
    """
    检测文档中事实之间的冲突
    
    流程：
    1. 从 Redis 获取已提取的事实
    2. 使用 LLM 成对比对事实
    3. 识别数据不一致、逻辑矛盾、时间冲突等
    4. 保存冲突结果到 Redis
    
    Args:
        document_id: 文档ID（从 extract-facts 返回）
    
    Returns:
        冲突检测结果，包含冲突列表和统计信息
    """
    try:
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        # 检查文档是否存在
        facts = fact_extractor.get_facts(document_id)
        if facts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 不存在或已过期，请先使用 /api/extract-facts 提取事实"
            )
        
        logger.info(f"开始冲突检测: 文档 {document_id}, 共 {len(facts)} 条事实")
        
        # 执行冲突检测
        try:
            result = await conflict_detector.detect_conflicts(
                document_id=document_id,
                facts=facts,
                save_to_redis=True,
                use_lsh=False,
                max_pairs=200
            )
        except Exception as e:
            logger.error(f"冲突检测失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"冲突检测失败: {str(e)}"
            )
        
        logger.info(f"冲突检测完成: 文档 {document_id}, 发现 {result['conflicts_found']} 个冲突")
        
        return {
            "success": True,
            "document_id": document_id,
            "total_facts": result["total_facts"],
            "total_comparisons": result["total_comparisons"],
            "conflicts_found": result["conflicts_found"],
            "conflicts": result["conflicts"],
            "statistics": result["statistics"],
            "saved_to_redis": result.get("saved_to_redis", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"冲突检测时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.get("/api/conflicts/{document_id}")
async def get_document_conflicts(document_id: str):
    """
    获取已保存的文档冲突
    
    Args:
        document_id: 文档ID
    
    Returns:
        该文档的所有冲突
    """
    try:
        conflicts = conflict_detector.get_conflicts(document_id)
        
        if conflicts is None:
            raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 的冲突数据不存在，请先使用 /api/detect-conflicts 检测冲突"
            )
        
        return {
            "success": True,
            "document_id": document_id,
            "total_conflicts": len(conflicts),
            "conflicts": conflicts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取冲突失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/documents/{document_id}/verify-facts")
async def verify_facts(document_id: str):
    """
    溯源校验：对文档提取的事实进行联网验证
    
    Args:
        document_id: 文档ID (必须先调用 /extract-facts)
        
    Returns:
        验证结果列表，包含每个事实的支持情况、置信度和搜索依据
    """
    try:
        # 检查是否已提取事实
        facts_data = redis_client.get_facts(document_id)
        if not facts_data:
             raise HTTPException(
                status_code=404,
                detail=f"文档 {document_id} 的事实数据不存在，请先使用 /api/documents/{document_id}/extract-facts 提取事实"
            )
            
        logger.info(f"开始溯源校验: {document_id}")
        
        # 执行校验
        results = await verifier.verify_document_facts(document_id)
        
        return {
            "success": True,
            "document_id": document_id,
            "verified_count": len(results),
            "verifications": results,
            "debug": getattr(verifier, "last_debug", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"溯源校验失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )


@app.post("/api/analyze")
async def analyze_document(file: UploadFile = File(...)):
    """
    一站式文档分析（上传 -> 提取事实 -> 检测冲突）
    
    流程：
    1. 解析文档
    2. 提取事实
    3. 检测冲突
    4. 返回完整分析结果
    
    支持的文件类型：docx, pdf, txt, md
    """
    try:
        # 验证文件类型
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        if file_ext not in ['docx', 'pdf', 'txt', 'md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}。支持的类型: docx, pdf, txt, md"
            )
        
        # 检查 LLM 是否可用
        if not llm_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM 服务不可用，请检查 DEEPSEEK_API_KEY 是否已配置"
            )
        
        logger.info(f"开始完整分析: {file.filename}")
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        # 1. 解析文档
        try:
            parse_result = parser.parse(file_content, file.filename)
        except Exception as e:
            logger.error(f"解析文件失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"文档解析失败: {str(e)}"
            )
        
        if parse_result['word_count'] == 0:
            raise HTTPException(status_code=400, detail="文档内容为空")
        
        # 生成文档ID
        document_id = str(uuid.uuid4())[:8]
        
        # 2. 提取事实
        logger.info(f"提取事实中: {file.filename}")
        try:
            extraction_result = await fact_extractor.extract_from_document(
                document_id=document_id,
                sections=parse_result['sections'],
                filename=file.filename,
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"事实提取失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"事实提取失败: {str(e)}"
            )
        
        # 3. 检测冲突
        logger.info(f"检测冲突中: {file.filename}")
        try:
            conflict_result = await conflict_detector.detect_conflicts(
                document_id=document_id,
                facts=extraction_result['facts'],
                save_to_redis=True
            )
        except Exception as e:
            logger.error(f"冲突检测失败: {str(e)}")
            # 冲突检测失败不影响整体结果
            conflict_result = {
                "conflicts_found": 0,
                "conflicts": [],
                "statistics": {},
                "error": str(e)
            }
        
        logger.info(f"分析完成: {file.filename}, 事实: {extraction_result['total_facts']}, 冲突: {conflict_result['conflicts_found']}")
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": file.filename,
            "word_count": parse_result['word_count'],
            "section_count": len(parse_result['sections']),
            "analysis": {
                "facts": {
                    "total": extraction_result['total_facts'],
                    "items": extraction_result['facts'],
                    "statistics": extraction_result['statistics']
                },
                "conflicts": {
                    "total": conflict_result['conflicts_found'],
                    "items": conflict_result['conflicts'],
                    "statistics": conflict_result.get('statistics', {})
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析文件时发生错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"服务器错误: {str(e)}"
        )

