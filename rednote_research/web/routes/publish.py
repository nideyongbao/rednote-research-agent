"""发布相关 API 路由"""

import os
import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/publish", tags=["publish"])


class CreatePublishRequest(BaseModel):
    """创建发布草稿请求"""
    topic: str
    summary: str = ""
    key_findings: list[str] = []
    sections: list[dict] = []
    notes: list[dict] = []
    source_id: Optional[str] = None


class UpdatePublishRequest(BaseModel):
    """更新发布草稿请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    cover_image: Optional[str] = None
    section_images: Optional[list[str]] = None


@router.post("/create")
async def create_publish_draft(request: CreatePublishRequest):
    """创建发布草稿"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    draft = service.create_draft(
        topic=request.topic,
        summary=request.summary,
        key_findings=request.key_findings,
        sections=request.sections,
        notes=request.notes
    )
    
    # 如果有 source_id，关联到历史记录
    if request.source_id:
        try:
            from ...services.history import get_history_service
            history_service = get_history_service()
            history_service.save_report_data(
                record_id=request.source_id,
                outline=request.sections,
                notes=request.notes,
                insights={
                    "key_findings": request.key_findings,
                    "summary": request.summary
                },
                draft_id=draft.id
            )
        except Exception as e:
            print(f"Failed to link draft to history: {e}")
    
    return {
        "success": True,
        "data": draft.model_dump()
    }


@router.get("")
async def list_publish_drafts(limit: int = Query(20, ge=1, le=50)):
    """列出所有发布草稿"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    drafts = service.list_drafts(limit=limit)
    
    return {
        "success": True,
        "data": [d.model_dump() for d in drafts]
    }


@router.get("/{draft_id}")
async def get_publish_draft(draft_id: str):
    """获取发布草稿"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    draft = service.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    return {
        "success": True,
        "data": draft.model_dump()
    }


@router.put("/{draft_id}")
async def update_publish_draft(draft_id: str, request: UpdatePublishRequest):
    """更新发布草稿"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    
    updates = {}
    if request.title is not None:
        updates["title"] = request.title[:20]
    if request.content is not None:
        updates["content"] = request.content[:200]
    if request.tags is not None:
        updates["tags"] = request.tags[:8]
    if request.cover_image is not None:
        updates["cover_image"] = request.cover_image
    if request.section_images is not None:
        updates["section_images"] = request.section_images
    
    draft = service.update_draft(draft_id, updates)
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    return {
        "success": True,
        "data": draft.model_dump()
    }


@router.delete("/{draft_id}")
async def delete_publish_draft(draft_id: str):
    """删除发布草稿"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    
    if service.delete_draft(draft_id):
        return {"success": True, "message": "已删除"}
    
    raise HTTPException(status_code=404, detail="草稿不存在")


@router.get("/{draft_id}/generate-images")
async def generate_publish_images(draft_id: str, type: str = Query("all")):
    """SSE: 生成发布图片（封面+章节图）"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    draft = service.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    async def event_generator():
        logs = []
        
        def on_log(msg: str):
            logs.append(msg)
        
        try:
            yield {"data": json.dumps({
                "type": "start",
                "message": "开始生成图片..."
            }, ensure_ascii=False)}
            
            async def generate_with_logs():
                nonlocal logs
                await service.generate_images(draft_id, generation_type=type, on_log=on_log)
            
            task = asyncio.create_task(generate_with_logs())
            
            last_log_count = 0
            while not task.done():
                await asyncio.sleep(0.5)
                
                if len(logs) > last_log_count:
                    for log in logs[last_log_count:]:
                        yield {"data": json.dumps({
                            "type": "log",
                            "message": log
                        }, ensure_ascii=False)}
                    last_log_count = len(logs)
            
            yield {"data": json.dumps({
                "type": "log",
                "message": "正在生成并保存..."
            }, ensure_ascii=False)}
            
            for log in logs[last_log_count:]:
                yield {"data": json.dumps({
                    "type": "log",
                    "message": log
                }, ensure_ascii=False)}
            
            updated_draft = service.get_draft(draft_id)
            
            yield {"data": json.dumps({
                "type": "complete",
                "data": updated_draft.model_dump() if updated_draft else {}
            }, ensure_ascii=False)}
            
        except Exception as e:
            yield {"data": json.dumps({
                "type": "error",
                "message": str(e)
            }, ensure_ascii=False)}
    
    return EventSourceResponse(event_generator())


@router.get("/{draft_id}/execute")
async def execute_publish(draft_id: str):
    """SSE: 执行发布到小红书"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    draft = service.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    async def event_generator():
        logs = []
        
        def on_log(msg: str):
            logs.append(msg)
        
        try:
            yield {"data": json.dumps({
                "type": "start",
                "message": "开始发布..."
            }, ensure_ascii=False)}
            
            updated_draft = await service.publish(draft_id, on_log=on_log)
            
            for log in logs:
                yield {"data": json.dumps({
                    "type": "log",
                    "message": log
                }, ensure_ascii=False)}
            
            yield {"data": json.dumps({
                "type": "complete",
                "success": updated_draft.status == "published",
                "data": updated_draft.model_dump()
            }, ensure_ascii=False)}
            
        except Exception as e:
            yield {"data": json.dumps({
                "type": "error",
                "message": str(e)
            }, ensure_ascii=False)}
    
    return EventSourceResponse(event_generator())


@router.get("/{draft_id}/images/{image_name}")
async def serve_publish_image(draft_id: str, image_name: str):
    """提供发布图片访问"""
    from ...services.publisher import get_publish_service
    
    service = get_publish_service()
    draft_dir = service._get_draft_dir(draft_id)
    image_path = os.path.join(draft_dir, "images", image_name)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return FileResponse(image_path)
