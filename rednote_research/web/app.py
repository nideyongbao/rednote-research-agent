"""FastAPI Web应用 - 提供SSE实时研究界面"""

import os
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from ..config import Config
from ..state import ResearchState
from ..mcp.rednote import RedNoteMCPClient
from ..agents.orchestrator import ResearchOrchestrator
from ..output.html_generator import HTMLReportGenerator
from ..services.settings import get_settings_service, Settings


# 全局状态
_orchestrator: Optional[ResearchOrchestrator] = None
_mcp_client: Optional[RedNoteMCPClient] = None
_config: Optional[Config] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _orchestrator, _mcp_client, _config
    
    # 启动时初始化
    _config = Config.from_env()
    
    # MCP客户端路径（从环境变量获取）
    mcp_path = os.getenv("REDNOTE_MCP_PATH", "")
    if mcp_path:
        # 支持相对路径：自动转换为绝对路径
        if not os.path.isabs(mcp_path):
            # 获取项目根目录（rednote_research 的父目录）
            project_root = Path(__file__).parent.parent.parent
            mcp_path = str((project_root / mcp_path).resolve())
        _mcp_client = RedNoteMCPClient(mcp_path)
        _orchestrator = ResearchOrchestrator(_config, _mcp_client)
    
    yield
    
    # 关闭时清理
    if _mcp_client:
        await _mcp_client.disconnect()


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="RedNote Research Agent",
        description="基于MCP的小红书深度研究智能体",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # 挂载静态文件（生产环境：前端构建产物）
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # 注意：SPA catch-all 路由在文件末尾注册，确保 API 路由优先匹配
    return app


app = create_app()



@app.get("/api/research")
async def research_stream(topic: str = Query(None), task: str = Query(None, min_length=2)):
    """
    SSE流式返回研究进度和结果
    
    事件类型:
    - message: JSON格式的消息，包含 type, level, message, stage, stats 等字段
    
    消息类型(type):
    - log: 进度日志
    - stage: 阶段切换
    - stats: 统计更新
    - complete: 完成信号
    - error: 错误信息
    """
    import json
    global _orchestrator, _mcp_client, _config
    
    # 兼容新旧参数名
    research_topic = topic or task
    if not research_topic or len(research_topic) < 2:
        raise HTTPException(status_code=400, detail="请提供有效的研究主题")
    
    # 创建历史记录
    from ..services.history import get_history_service
    history_service = get_history_service()
    record = history_service.create(research_topic)
    record_id = record.id
    
    async def event_generator():
        stats = {"notesFound": 0, "contentsAnalyzed": 0, "insightsExtracted": 0}
        final_status = "failed"  # 默认失败，成功时更新
        
        def make_msg(msg_type: str, **kwargs) -> dict:
            """生成标准消息格式"""
            return {"data": json.dumps({"type": msg_type, "recordId": record_id, **kwargs}, ensure_ascii=False)}
        
        try:
            # 更新状态为运行中
            history_service.update(record_id, {"status": "running"})
            
            yield make_msg("log", level="info", message=f"🚀 开始研究: {research_topic}")
            yield make_msg("stage", stage="planning")
            
            # 检查MCP客户端
            if not _mcp_client:
                yield make_msg("log", level="warning", message="MCP客户端未配置，将使用模拟数据")
                # 模拟研究流程
                yield make_msg("log", level="info", message="📋 [Planner] 分析研究主题...")
                await asyncio.sleep(1)
                yield make_msg("log", level="success", message="📋 [Planner] 生成了 3 个搜索关键词")
                
                yield make_msg("stage", stage="searching")
                yield make_msg("log", level="info", message="🔍 [Searcher] 开始搜索笔记...")
                await asyncio.sleep(1)
                stats["notesFound"] = 15
                yield make_msg("stats", stats=stats)
                yield make_msg("log", level="success", message=f"🔍 [Searcher] 收集了 {stats['notesFound']} 篇笔记")
                
                yield make_msg("stage", stage="analyzing")
                yield make_msg("log", level="info", message="🧠 [Analyzer] 分析数据中...")
                await asyncio.sleep(1)
                stats["contentsAnalyzed"] = 15
                stats["insightsExtracted"] = 8
                yield make_msg("stats", stats=stats)
                yield make_msg("log", level="success", message=f"🧠 [Analyzer] 提取了 {stats['insightsExtracted']} 条核心发现")
                
                yield make_msg("stage", stage="generating")
                yield make_msg("log", level="info", message="📝 [Writer] 生成研究报告...")
                await asyncio.sleep(1)
                yield make_msg("log", level="success", message="✅ 报告生成完成！")
                yield make_msg("complete")
                return
            
            # 连接MCP
            yield make_msg("log", level="info", message="📡 连接小红书MCP服务...")
            await _mcp_client.connect()
            yield make_msg("log", level="success", message="✅ MCP连接成功")
            
            # 创建编排器
            orchestrator = ResearchOrchestrator(_config, _mcp_client)
            
            # 执行研究
            state = ResearchState(task=research_topic)
            
            # 阶段1: 规划
            yield make_msg("progress", percent=10)
            yield make_msg("log", level="info", message="📋 [Planner] 分析研究主题...")
            state = await orchestrator.planner.run(state)
            if state.plan:
                yield make_msg("log", level="success", message=f"📋 [Planner] 生成了 {len(state.plan.keywords)} 个搜索关键词")
                yield make_msg("log", level="info", message=f"💡 理解: {state.plan.understanding}")
                yield make_msg("log", level="info", message=f"📊 维度: {', '.join(state.plan.dimensions)}")
                for kw in state.plan.keywords:
                    yield make_msg("log", level="info", message=f"  - {kw}")
                yield make_msg("log", level="info", message=f"📐 [阶段1统计] 关键词: {len(state.plan.keywords)}个 | 维度: {len(state.plan.dimensions)}个 | LLM调用: 1次")
            
            # 阶段2: 搜索
            yield make_msg("stage", stage="searching")
            yield make_msg("progress", percent=25)
            yield make_msg("log", level="info", message="🔍 [Searcher] 开始搜索笔记...")
            
            # 收集搜索日志用于前端显示
            search_logs = []
            def capture_log(msg):
                search_logs.append(msg)
            
            state = await orchestrator.searcher.run(state, on_log=capture_log)
            
            # 输出每个关键词的搜索结果到前端
            for log in search_logs:
                yield make_msg("log", level="info", message=f"  {log}")
            
            stats["notesFound"] = len(state.documents)
            yield make_msg("stats", stats=stats)
            yield make_msg("log", level="success", message=f"🔍 [Searcher] 收集了 {stats['notesFound']} 篇笔记")
            
            # 计算并输出详细统计
            total_images = sum(len(note.detail.images) for note in state.documents if note.detail.images)
            total_text_length = sum(len(note.detail.content or "") for note in state.documents)
            avg_text_length = total_text_length // len(state.documents) if state.documents else 0
            yield make_msg("log", level="info", message=f"📊 [统计] 共 {total_images} 张图片，总文本 {total_text_length} 字，平均每篇 {avg_text_length} 字")
            
            # 阶段3: 分析
            yield make_msg("stage", stage="analyzing")
            yield make_msg("progress", percent=45)
            yield make_msg("log", level="info", message="🧠 [Analyzer] 分析数据中...")
            state = await orchestrator.analyzer.run(state)
            stats["contentsAnalyzed"] = len(state.documents)
            if state.insights:
                findings = state.insights.get("key_findings", [])
                stats["insightsExtracted"] = len(findings)
                yield make_msg("stats", stats=stats)
                yield make_msg("log", level="success", message=f"🧠 [Analyzer] 提取了 {stats['insightsExtracted']} 条核心发现")
                yield make_msg("log", level="info", message=f"📐 [阶段3统计] 分析笔记: {len(state.documents)}篇 | 提取发现: {stats['insightsExtracted']}条 | LLM调用: 1次")
            
            # 阶段4: 图片VLM分析（提前到大纲之前）
            yield make_msg("progress", percent=55)
            yield make_msg("log", level="info", message="🖼️ [ImageAnalyzer] VLM分析图片...")
            
            from ..output.image_analyzer import ImageAnalyzer
            image_analyzer = ImageAnalyzer()
            
            image_logs = []
            def capture_image_log(msg):
                image_logs.append(msg)
            
            try:
                state, img_stats = await image_analyzer.analyze(state, on_log=capture_image_log)
                
                # 输出详细日志
                for log in image_logs:
                    yield make_msg("log", level="info", message=f"  {log}")
                
                analyzed_count = len(state.image_analyses)
                usable_count = sum(1 for r in state.image_analyses.values() if r.should_use)
                vlm_calls = img_stats.get("vlm_calls", 0)
                yield make_msg("log", level="success", message=f"🖼️ [ImageAnalyzer] 分析了 {analyzed_count} 张图片，{usable_count} 张可用")
                
                # 统计分类
                categories = {}
                for r in state.image_analyses.values():
                    cat = r.category or "未分类"
                    categories[cat] = categories.get(cat, 0) + 1
                cat_str = ", ".join(f"{k}:{v}" for k, v in categories.items())
                yield make_msg("log", level="info", message=f"📐 [阶段4统计] 分类: {cat_str} | VLM调用: {vlm_calls}次")
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ 图片分析失败: {str(e)[:100]}")
            
            # 阶段5: 生成结构化大纲（含图片上下文）
            yield make_msg("stage", stage="generating")
            yield make_msg("progress", percent=65)
            yield make_msg("log", level="info", message="📑 [OutlineGenerator] 生成结构化大纲（含图片上下文）...")
            
            from ..output.outline_generator import OutlineGenerator
            outline_generator = OutlineGenerator(_config.get_llm_client(), model=_config.llm.model)
            
            try:
                structured_outline = await outline_generator.generate(state)
                yield make_msg("log", level="success", message=f"📑 [OutlineGenerator] 生成了 {len(structured_outline)} 个章节")
                yield make_msg("log", level="info", message=f"📐 [阶段5统计] 章节数: {len(structured_outline)} | LLM调用: 1次")
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ 大纲生成失败: {str(e)[:100]}, 使用备用方案")
                structured_outline = outline_generator._generate_fallback_outline(state)
            
            # 阶段6: 图片分配（基于VLM分析结果）
            yield make_msg("progress", percent=75)
            yield make_msg("log", level="info", message="🎯 [ImageAssigner] 分配图片到章节...")
            
            from ..output.image_assigner import ImageAssigner
            image_assigner = ImageAssigner()
            
            assign_logs = []
            def capture_assign_log(msg):
                assign_logs.append(msg)
            
            try:
                structured_outline = await image_assigner.assign(state, structured_outline, on_log=capture_assign_log)
                
                # 输出分配与生成日志
                for log in assign_logs:
                    yield make_msg("log", level="info", message=f"  {log}")
                
                assigned_count = sum(len(section.get('images', [])) for section in structured_outline)
                yield make_msg("log", level="success", message=f"🎯 [ImageAssigner] 分配了 {assigned_count} 张图片")
                yield make_msg("log", level="info", message=f"📐 [阶段6统计] 分配图片: {assigned_count}张")
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ 图片分配失败: {str(e)[:100]}")
            
            # 阶段7: 生成HTML报告
            yield make_msg("progress", percent=85)
            yield make_msg("log", level="info", message="📝 [Writer] 生成图文交错报告...")
            html_generator = HTMLReportGenerator(_config.get_llm_client(), model=_config.llm.model)
            
            try:
                html_report = await html_generator.generate(state)
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ LLM生成失败: {str(e)[:100]}, 使用备用模板")
                html_report = html_generator.generate_fallback_html(state)
            
            yield make_msg("progress", percent=100)
            yield make_msg("log", level="success", message="✅ 报告生成完成！")
            yield make_msg("log", level="info", message=f"📐 [阶段7统计] 报告HTML长度: {len(html_report)}字符 | 章节数: {len(structured_outline)} | LLM调用: {len(structured_outline)+1}次")
            
            # 传递报告数据给前端（包含结构化大纲）
            report_data = {
                "topic": research_topic,
                "insights": state.insights,
                "outline": structured_outline,  # 新增：结构化大纲
                "notes": [
                    {
                        "id": note.preview.id,
                        "title": note.detail.title or note.preview.title,
                        "content": note.detail.content or note.preview.content_preview,  # 全量内容
                        "author": note.detail.author or note.preview.author,
                        "likes": note.detail.likes or note.preview.likes,
                        "images": note.detail.images if note.detail.images else [],  # 全量图片
                        "url": note.detail.url or note.preview.url
                    }
                    for note in state.documents  # 全量笔记
                ]
            }
            yield make_msg("report", **report_data)
            
            final_status = "completed"
            
            # 保存完整报告数据到历史记录（用于历史恢复编辑）
            history_service.save_report_data(
                record_id=record_id,
                outline=structured_outline,
                notes=report_data["notes"],
                insights=state.insights or {}
            )
            history_service.update(record_id, {"status": "completed"})
            
            yield make_msg("complete")
            
        except Exception as e:
            yield make_msg("log", level="error", message=f"❌ 研究失败: {str(e)}")
            history_service.update(record_id, {"status": "failed"})
            yield make_msg("complete")
        
        finally:
            # 断开MCP连接
            if _mcp_client:
                try:
                    await _mcp_client.disconnect()
                except:
                    pass
    
    return EventSourceResponse(event_generator())


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "mcp_configured": _mcp_client is not None,
        "timestamp": datetime.now().isoformat()
    }


# ========== 设置 API ==========

class LLMTestRequest(BaseModel):
    """LLM 测试请求"""
    apiKey: str
    baseUrl: str
    model: str


@app.get("/api/settings")
async def get_settings():
    """获取设置（脱敏）"""
    service = get_settings_service()
    return service.get_masked()


@app.post("/api/settings")
async def save_settings(settings: Settings):
    """保存设置"""
    service = get_settings_service()
    service.save(settings)
    return {"status": "ok", "message": "设置已保存"}


@app.post("/api/settings/test")
async def test_llm_connection(request: LLMTestRequest):
    """测试 LLM 连接"""
    from openai import AsyncOpenAI
    
    try:
        client = AsyncOpenAI(
            api_key=request.apiKey,
            base_url=request.baseUrl
        )
        
        # 发送简单测试请求
        response = await client.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        
        return {"status": "ok", "message": "连接成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")


class VLMTestRequest(BaseModel):
    """VLM 测试请求"""
    apiKey: str
    baseUrl: str
    model: str


@app.post("/api/settings/test-vlm")
async def test_vlm_connection(request: VLMTestRequest):
    """测试 VLM 连接（发送图片验证请求）"""
    from openai import AsyncOpenAI
    
    try:
        client = AsyncOpenAI(
            api_key=request.apiKey,
            base_url=request.baseUrl,
            timeout=30.0  # 添加超时设置
        )
        
        # 使用一个简单的 base64 编码的测试图片（100x100 红色方块）
        # 满足模型对图片尺寸的最低要求(宽高>10)
        test_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAaklEQVR42u3QMQEAAAwCIPuX1hjL8AETDlNVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXVH2YBy8IABVQAAABJRU5ErkJggg=="
        
        response = await client.chat.completions.create(
            model=request.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What color is this image? Answer in one word."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": test_image_base64
                        }
                    }
                ]
            }],
            max_tokens=10
        )
        
        return {"status": "ok", "message": f"VLM 连接成功！模型: {request.model}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"VLM 连接失败: {str(e)}")


class ImageGenTestRequest(BaseModel):
    """图片生成模型测试请求"""
    apiKey: str
    baseUrl: str
    model: str


@app.post("/api/settings/test-imagegen")
async def test_imagegen_connection(request: ImageGenTestRequest):
    """测试图片生成模型连接"""
    import httpx
    
    try:
        # 根据模型类型选择不同的测试方式
        if "wanx" in request.model.lower():
            # 通义万相使用阿里云 DashScope API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{request.baseUrl}/services/aigc/text2image/image-synthesis",
                    headers={
                        "Authorization": f"Bearer {request.apiKey}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": request.model,
                        "input": {"prompt": "test"},
                        "parameters": {"n": 1, "size": "256*256"}
                    }
                )
                if response.status_code in [200, 202]:  # 202 表示异步任务已接受
                    return {"status": "ok", "message": f"图片生成模型连接成功！模型: {request.model}"}
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
        else:
            # 其他模型使用 OpenAI 兼容接口
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=request.apiKey,
                base_url=request.baseUrl
            )
            # 只测试连接，不实际生成图片（避免消耗配额）
            # 通过 models.list 来验证 API 是否可用
            await client.models.list()
            return {"status": "ok", "message": f"图片生成模型 API 连接成功！模型: {request.model}"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"图片生成模型连接失败: {str(e)}")


@app.post("/api/settings/test-mcp")
async def test_mcp_connection():
    """测试 MCP 连接（检查小红书登录状态）"""
    global _mcp_client
    
    if not _mcp_client:
        raise HTTPException(
            status_code=400, 
            detail="MCP 客户端未配置。请确保 REDNOTE_MCP_PATH 环境变量已设置。"
        )
    
    try:
        # 连接 MCP
        await _mcp_client.connect()
        
        # 尝试搜索一个测试关键词
        results = await _mcp_client.search_notes("测试", limit=1)
        
        # 断开连接
        await _mcp_client.disconnect()
        
        if results:
            return {
                "status": "ok", 
                "message": f"MCP 连接成功！小红书登录状态正常，找到 {len(results)} 条测试结果。"
            }
        else:
            return {
                "status": "ok", 
                "message": "MCP 连接成功！但未找到测试结果，可能需要重新登录小红书。"
            }
            
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "登录" in error_msg:
            raise HTTPException(
                status_code=400, 
                detail=f"MCP 连接失败：需要重新登录小红书。错误: {error_msg[:100]}"
            )
        raise HTTPException(status_code=400, detail=f"MCP 连接失败: {error_msg[:200]}")




from ..services.history import get_history_service, ResearchRecord


@app.get("/api/history")
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    status: Optional[str] = None
):
    """获取历史记录列表"""
    service = get_history_service()
    return service.list(page=page, page_size=page_size, status=status)


@app.get("/api/history/{record_id}")
async def get_history_record(record_id: str):
    """获取单个历史记录（元数据）"""
    service = get_history_service()
    record = service.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record.model_dump()


@app.get("/api/history/{record_id}/full")
async def get_history_record_full(record_id: str):
    """获取完整历史记录（包含报告数据，用于历史恢复编辑）"""
    service = get_history_service()
    record = service.get_full(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record.model_dump()


@app.delete("/api/history/{record_id}")
async def delete_history_record(record_id: str):
    """删除历史记录"""
    service = get_history_service()
    if service.delete(record_id):
        return {"status": "ok", "message": "已删除"}
    raise HTTPException(status_code=404, detail="记录不存在")


@app.get("/api/history/search")
async def search_history(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50)
):
    """搜索历史记录"""
    service = get_history_service()
    results = service.search(keyword, limit)
    return [r.model_dump() for r in results]


# ========== 图片验证 API ==========

class ImageValidateRequest(BaseModel):
    """图片验证请求"""
    image_url: str
    context: str
    topic: str = ""


@app.post("/api/validate-image")
async def validate_image(request: ImageValidateRequest):
    """验证图片与内容的相关性"""
    from ..agents.image_validator import ImageValidator
    
    validator = ImageValidator()
    try:
        result = await validator.validate(
            image_source=request.image_url,
            context=request.context,
            topic=request.topic
        )
        return result.model_dump()
    finally:
        await validator.close()


class BatchImageValidateRequest(BaseModel):
    """批量图片验证请求"""
    images: list[dict]  # [{url: str, caption?: str}, ...]
    context: str
    topic: str = ""


@app.post("/api/validate-images")
async def validate_images_batch(request: BatchImageValidateRequest):
    """批量验证图片"""
    from ..agents.image_validator import validate_images_batch
    
    results = await validate_images_batch(
        images=request.images,
        context=request.context,
        topic=request.topic
    )
    return results


# ========== 报告导出 API ==========

class ExportRequest(BaseModel):
    """导出请求"""
    format: str  # 'markdown' | 'pdf'
    topic: str
    insights: dict = {}
    outline: list = []
    notes: list = []


@app.post("/api/export")
async def export_report(request: ExportRequest):
    """导出报告为不同格式"""
    from fastapi.responses import Response
    from ..output.exporter import ReportExporter
    
    if request.format == "markdown":
        content = ReportExporter.to_markdown(
            topic=request.topic,
            insights=request.insights,
            outline=request.outline,
            notes=request.notes
        )
        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md"'
            }
        )
    
    elif request.format == "pdf":
        # PDF需要先生成HTML再转换
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
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
                    }
                )
            else:
                raise HTTPException(status_code=500, detail="PDF转换返回空结果")
        except ImportError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF导出失败: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {request.format}")


# ============ 设置相关 API ============

def get_effective_config() -> Config:
    """
    获取有效配置（UI 设置优先，然后 ENV）
    
    优先级：
    1. UI 设置（如果配置了 API Key）
    2. 环境变量配置
    """
    config = Config.from_env()
    ui_settings = get_settings_service().load()
    
    # UI 设置覆盖 ENV（如果 UI 设置了 API Key）
    if ui_settings.llm.api_key:
        config.llm.api_key = ui_settings.llm.api_key
        config.llm.base_url = ui_settings.llm.base_url
        config.llm.model = ui_settings.llm.model
    
    return config


@app.get("/api/settings")
async def get_settings():
    """获取脱敏后的设置"""
    return get_settings_service().get_masked()


class SettingsUpdateRequest(BaseModel):
    """设置更新请求"""
    llm: dict = {}
    vlm: dict = {}
    imageGen: dict = {}


@app.post("/api/settings")
async def save_settings(data: SettingsUpdateRequest):
    """保存设置"""
    from ..services.settings import LLMSettings, VLMSettings, ImageGenSettings
    
    # 转换字段名（前端使用 camelCase，后端使用 snake_case）
    llm_data = {
        "api_key": data.llm.get("apiKey", ""),
        "base_url": data.llm.get("baseUrl", "https://api-inference.modelscope.cn/v1"),
        "model": data.llm.get("model", "")
    }
    vlm_data = {
        "enabled": data.vlm.get("enabled", False),
        "api_key": data.vlm.get("apiKey", ""),
        "base_url": data.vlm.get("baseUrl", ""),
        "model": data.vlm.get("model", ""),
        "rate_limit_mode": data.vlm.get("rateLimitMode", True)
    }
    image_gen_data = {
        "enabled": data.imageGen.get("enabled", False),
        "api_key": data.imageGen.get("apiKey", ""),
        "base_url": data.imageGen.get("baseUrl", ""),
        "model": data.imageGen.get("model", ""),
        "rate_limit_mode": data.imageGen.get("rateLimitMode", True)
    }
    
    settings = Settings(
        llm=LLMSettings(**llm_data),
        vlm=VLMSettings(**vlm_data),
        imageGen=ImageGenSettings(**image_gen_data)
    )
    get_settings_service().save(settings)
    return {"success": True, "message": "设置已保存"}


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求"""
    apiKey: str
    baseUrl: str
    model: str


@app.post("/api/settings/test")
async def test_llm_connection(data: LLMTestRequest):
    """测试 LLM 连接"""
    from openai import AsyncOpenAI
    
    try:
        client = AsyncOpenAI(
            api_key=data.apiKey,
            base_url=data.baseUrl
        )
        response = await client.chat.completions.create(
            model=data.model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return {
            "success": True, 
            "message": f"连接成功！模型: {response.model}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== SPA 路由（必须在所有 API 路由之后注册）==========

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists() and (_static_dir / "index.html").exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """SPA 兜底路由：返回 index.html 或静态文件"""
        # API 路由不处理（正常情况下不会到这里，因为 API 路由已先注册）
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API not found")
        
        # 检查是否请求静态文件
        requested_file = _static_dir / full_path
        if requested_file.exists() and requested_file.is_file():
            return FileResponse(str(requested_file))
        
        # 其他所有请求返回 index.html（SPA 路由）
        return FileResponse(str(_static_dir / "index.html"))


# 直接运行入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
