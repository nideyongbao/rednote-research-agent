"""历史记录相关 API 路由"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Response

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


@router.get("/search")
async def search_history(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50)
):
    """搜索历史记录"""
    service = get_history_service()
    results = service.search(keyword, limit)
    return [r.model_dump() for r in results]


@router.get("/export")
async def export_history():
    """导出历史记录备份"""
    json_str = get_history_service().export_json()
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
    """获取完整历史记录（包含报告数据，用于历史恢复编辑）"""
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
