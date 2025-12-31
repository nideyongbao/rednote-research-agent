from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from datetime import datetime
from ...output.exporter import ReportExporter

router = APIRouter(prefix="/api", tags=["tools"])

class ImageValidateRequest(BaseModel):
    image_url: str
    context: str
    topic: str = ""

@router.post("/validate-image")
async def validate_image(request: ImageValidateRequest):
    from ...agents.image_validator import ImageValidator
    validator = ImageValidator()
    try:
        result = await validator.validate(request.image_url, request.context, request.topic)
        return result.model_dump()
    finally:
        await validator.close()

class BatchImageValidateRequest(BaseModel):
    images: list[dict]
    context: str
    topic: str = ""

@router.post("/validate-images")
async def validate_images_batch(request: BatchImageValidateRequest):
    from ...agents.image_validator import validate_images_batch
    return await validate_images_batch(request.images, request.context, request.topic)

class ExportRequest(BaseModel):
    format: str
    topic: str
    insights: dict = {}
    outline: list = []
    notes: list = []

@router.post("/export")
async def export_report(request: ExportRequest):
    if request.format == "markdown":
        content = ReportExporter.to_markdown(request.topic, request.insights, request.outline, request.notes)
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        return Response(content=content, media_type="text/markdown", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    elif request.format == "pdf":
        html = f"<html><body><h1>{request.topic}</h1></body></html>" # Simplified for brevity, logic mostly same as original
        # Re-implement full logic if needed, but for refactoring purpose, moving code is key.
        # Let's paste the full logic from app.py to be safe.
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{request.topic}</title>
<style>body{{font-family:sans-serif;max-width:800px;margin:0 auto;padding:20px;}}
h1{{color:#ff2442;}}h2{{border-bottom:2px solid #ff2442;padding-bottom:8px;}}</style>
</head><body>
<h1>{request.topic}</h1>
{"".join([f'<section><h2>{s.get("title","")}</h2><p>{s.get("content","")}</p></section>' for s in request.outline])}
</body></html>"""
        try:
            pdf_bytes = await ReportExporter.to_pdf(html)
            if pdf_bytes:
                filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=400, detail="Unsupported format")
