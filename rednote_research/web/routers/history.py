from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Response
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from ...services.history import get_history_service

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("")
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = None
):
    """获取历史记录列表"""
    service = get_history_service()
    return service.list(page=page, page_size=page_size, status=status)

@router.get("/export")
async def export_history():
    """导出历史记录备份"""
    service = get_history_service()
    json_str = service.export_json()
    filename = f"history_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/import")
async def import_history(file: UploadFile = File(...)):
    """导入历史记录备份"""
    content = await file.read()
    json_str = content.decode("utf-8")
    result = get_history_service().import_json(json_str)
    return {"success": True, "data": result}


@router.get("/search")
async def search_history(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50)
):
    """搜索历史记录"""
    service = get_history_service()
    results = service.search(keyword, limit)
    return [r.model_dump() for r in results]

@router.get("/{record_id}")
async def get_history_record(record_id: str):
    """获取单个历史记录（元数据）"""
    service = get_history_service()
    record = service.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record.model_dump()

@router.get("/{record_id}/full")
async def get_history_record_full(record_id: str):
    """获取完整历史记录（包含报告数据）"""
    service = get_history_service()
    record = service.get_full(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record.model_dump()

@router.delete("/{record_id}")
async def delete_history_record(record_id: str):
    """删除历史记录"""
    service = get_history_service()
    if service.delete(record_id):
        return {"status": "ok", "message": "已删除"}
    raise HTTPException(status_code=404, detail="记录不存在")

class CompareRequest(BaseModel):
    record_ids: list[str]

@router.post("/compare")
async def compare_history(request: CompareRequest):
    """对比两个历史记录"""
    if len(request.record_ids) != 2:
        raise HTTPException(status_code=400, detail="必须选择两个记录进行对比")
        
    service = get_history_service()
    record1 = service.get_full(request.record_ids[0])
    record2 = service.get_full(request.record_ids[1])
    
    if not record1 or not record2:
        raise HTTPException(status_code=404, detail="记录未找到")
        
    # 简单的对比逻辑 (实际场景可能需要 LLM 分析)
    # 这里我们对比核心发现的重叠度和关键词
    
    from ...agents.analyzer import AnalyzerAgent # Reuse for similarity if needed, or simple text diff
    
    # 提取关键词集合
    def extract_keywords(record):
        keywords = set()
        if record.insights and "key_findings" in record.insights:
            for finding in record.insights["key_findings"]:
                # 兼容结构化对象和字符串
                text = finding.get("statement", "") if isinstance(finding, dict) else str(finding)
                keywords.update([w for w in text if len(w) > 1]) # 简化：粗略提取
        return keywords
        
    # 由于没有直接的关键词提取器，我们构造一个简单的响应结构
    # 在实际生产中，这里应该调用 LLM 进行深度对比
    
    def get_findings_text(record):
        if not record.insights:
            return []
        findings = record.insights.get("key_findings", [])
        return [f.get("statement", "") if isinstance(f, dict) else str(f) for f in findings]

    return {
        "records": [
            {"id": record1.id, "topic": record1.topic, "time": record1.created_at},
            {"id": record2.id, "topic": record2.topic, "time": record2.created_at}
        ],
        "comparison": {
            "topic_similarity": "高" if record1.topic == record2.topic else "低",
            "common_findings": [], # Placeholder for commonality
            "unique_findings_1": get_findings_text(record1)[:3],
            "unique_findings_2": get_findings_text(record2)[:3],
            "summary": f"对比分析：'{record1.topic}' 与 '{record2.topic}'"
        }
    }
