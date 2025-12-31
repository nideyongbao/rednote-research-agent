from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import FileResponse
import os

from ...services.publisher import get_publish_service

router = APIRouter(prefix="/api/publish", tags=["publish"])

class CreatePublishRequest(BaseModel):
    topic: str
    summary: str = ""
    key_findings: List[str] = []
    sections: List[dict] = []
    notes: List[dict] = []
    source_id: Optional[str] = None

class UpdatePublishRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None
    section_images: Optional[List[str]] = None

@router.post("/create")
async def create_publish_draft(request: CreatePublishRequest):
    service = get_publish_service()
    draft = service.create_draft(
        topic=request.topic,
        summary=request.summary,
        key_findings=request.key_findings,
        sections=request.sections,
        notes=request.notes
    )
    if request.source_id:
        try:
            from ...services.history import get_history_service
            # Save link logic...
            pass
        except:
            pass
    return {"success": True, "data": draft.model_dump()}

@router.get("")
async def list_publish_drafts(limit: int = Query(20, ge=1, le=50)):
    service = get_publish_service()
    drafts = service.list_drafts(limit=limit)
    return {"success": True, "data": [d.model_dump() for d in drafts]}

@router.get("/{draft_id}")
async def get_publish_draft(draft_id: str):
    service = get_publish_service()
    draft = service.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "data": draft.model_dump()}

@router.put("/{draft_id}")
async def update_publish_draft(draft_id: str, request: UpdatePublishRequest):
    service = get_publish_service()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    draft = service.update_draft(draft_id, updates)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "data": draft.model_dump()}

@router.delete("/{draft_id}")
async def delete_publish_draft(draft_id: str):
    service = get_publish_service()
    if service.delete_draft(draft_id):
        return {"success": True, "message": "Deleted"}
    raise HTTPException(status_code=404, detail="Draft not found")

@router.get("/{draft_id}/generate-images")
async def generate_publish_images(draft_id: str, type: str = Query("all")):
    service = get_publish_service()
    async def event_generator():
        logs = []
        def on_log(msg): logs.append(msg)
        
        yield {"data": json.dumps({"type": "start", "message": "Starting image generation..."})}
        
        task = asyncio.create_task(service.generate_images(draft_id, generation_type=type, on_log=on_log))
        
        last_log_count = 0
        while not task.done():
            await asyncio.sleep(0.5)
            if len(logs) > last_log_count:
                for log in logs[last_log_count:]:
                    yield {"data": json.dumps({"type": "log", "message": log})}
                last_log_count = len(logs)
                
        yield {"data": json.dumps({"type": "complete"})}
        
    return EventSourceResponse(event_generator())

@router.get("/{draft_id}/images/{image_name}")
async def serve_publish_image(draft_id: str, image_name: str):
    service = get_publish_service()
    draft_dir = service._get_draft_dir(draft_id)
    image_path = os.path.join(draft_dir, "images", image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)
