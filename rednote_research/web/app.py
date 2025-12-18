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
            yield make_msg("log", level="info", message="📋 [Planner] 分析研究主题...")
            state = await orchestrator.planner.run(state)
            if state.plan:
                yield make_msg("log", level="success", message=f"📋 [Planner] 生成了 {len(state.plan.keywords)} 个搜索关键词")
                for kw in state.plan.keywords:
                    yield make_msg("log", level="info", message=f"  - {kw}")
            
            # 阶段2: 搜索
            yield make_msg("stage", stage="searching")
            yield make_msg("log", level="info", message="🔍 [Searcher] 开始搜索笔记...")
            state = await orchestrator.searcher.run(state)
            stats["notesFound"] = len(state.documents)
            yield make_msg("stats", stats=stats)
            yield make_msg("log", level="success", message=f"🔍 [Searcher] 收集了 {stats['notesFound']} 篇笔记")
            
            # 阶段3: 分析
            yield make_msg("stage", stage="analyzing")
            yield make_msg("log", level="info", message="🧠 [Analyzer] 分析数据中...")
            state = await orchestrator.analyzer.run(state)
            stats["contentsAnalyzed"] = len(state.documents)
            if state.insights:
                findings = state.insights.get("key_findings", [])
                stats["insightsExtracted"] = len(findings)
                yield make_msg("stats", stats=stats)
                yield make_msg("log", level="success", message=f"🧠 [Analyzer] 提取了 {stats['insightsExtracted']} 条核心发现")
            
            # 阶段4: 生成结构化大纲
            yield make_msg("stage", stage="generating")
            yield make_msg("log", level="info", message="📑 [OutlineGenerator] 生成结构化大纲...")
            
            from ..output.outline_generator import OutlineGenerator
            outline_generator = OutlineGenerator(_config.get_llm_client(), model=_config.llm.model)
            
            try:
                structured_outline = await outline_generator.generate(state)
                yield make_msg("log", level="success", message=f"📑 [OutlineGenerator] 生成了 {len(structured_outline)} 个章节")
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ 大纲生成失败: {str(e)[:100]}, 使用备用方案")
                structured_outline = outline_generator._generate_fallback_outline(state)
            
            yield make_msg("log", level="info", message="📝 [Writer] 生成图文交错报告...")
            html_generator = HTMLReportGenerator(_config.get_llm_client(), model=_config.llm.model)
            
            try:
                html_report = await html_generator.generate(state)
            except Exception as e:
                yield make_msg("log", level="warning", message=f"⚠ LLM生成失败: {str(e)[:100]}, 使用备用模板")
                html_report = html_generator.generate_fallback_html(state)
            
            yield make_msg("log", level="success", message="✅ 报告生成完成！")
            
            # 传递报告数据给前端（包含结构化大纲）
            report_data = {
                "topic": research_topic,
                "insights": state.insights,
                "outline": structured_outline,  # 新增：结构化大纲
                "notes": [
                    {
                        "id": note.preview.id,
                        "title": note.detail.title or note.preview.title,
                        "content": (note.detail.content or note.preview.content_preview)[:500],
                        "author": note.detail.author or note.preview.author,
                        "likes": note.detail.likes or note.preview.likes,
                        "images": note.detail.images[:3] if note.detail.images else [],
                        "url": note.detail.url or note.preview.url
                    }
                    for note in state.documents[:10]
                ]
            }
            yield make_msg("report", **report_data)
            
            final_status = "completed"
            history_service.update(record_id, {
                "status": "completed",
                "notes_count": stats["notesFound"],
                "sections_count": stats["insightsExtracted"]
            })
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


# ========== 历史记录 API ==========

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
    """获取单个历史记录"""
    service = get_history_service()
    record = service.get(record_id)
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
        "base_url": data.llm.get("baseUrl", "https://api.openai.com/v1"),
        "model": data.llm.get("model", "gpt-4o")
    }
    vlm_data = {
        "enabled": data.vlm.get("enabled", False),
        "api_key": data.vlm.get("apiKey", ""),
        "base_url": data.vlm.get("baseUrl", ""),
        "model": data.vlm.get("model", "")
    }
    image_gen_data = {
        "enabled": data.imageGen.get("enabled", False),
        "api_key": data.imageGen.get("apiKey", ""),
        "base_url": data.imageGen.get("baseUrl", ""),
        "model": data.imageGen.get("model", "")
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
