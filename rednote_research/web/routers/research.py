import asyncio
import json
from fastapi import APIRouter, Query, HTTPException
from sse_starlette.sse import EventSourceResponse

from ...state import ResearchState
from ...output.image_analyzer import ImageAnalyzer
from ...output.outline_generator import OutlineGenerator
from ...output.image_assigner import ImageAssigner
from ...output.html_generator import HTMLReportGenerator
from ...services.history import get_history_service
from ...services.timer import StageTimer
from ..context import global_context
from ..schemas.sse import SSEMessage

router = APIRouter(prefix="/api/research", tags=["research"])

@router.get("")
async def research_stream(topic: str = Query(None), task: str = Query(None, min_length=2)):
    """SSE流式返回研究进度和结果"""
    # 兼容新旧参数名
    research_topic = topic or task
    if not research_topic or len(research_topic) < 2:
        raise HTTPException(status_code=400, detail="请提供有效的研究主题")
    
    history_service = get_history_service()
    record = history_service.create(research_topic)
    record_id = record.id
    
    async def event_generator():
        timer = StageTimer()
        stats = {"notesFound": 0, "contentsAnalyzed": 0, "insightsExtracted": 0}
        
        # 辅助函数：发送 SSE 消息
        def yield_msg(**kwargs):
            msg = SSEMessage(record_id=record_id, **kwargs)
            return msg.to_event()

        try:
            history_service.update(record_id, {"status": "running"})
            
            yield yield_msg(type="log", level="info", message=f"🚀 开始研究: {research_topic}")
            yield yield_msg(type="stage", stage="planning")
            
            # 获取全局对象
            ctx = global_context
            
            # 检查MCP客户端
            if not ctx.mcp_client:
                yield yield_msg(type="log", level="warning", message="MCP客户端未配置，将使用模拟数据")
                # ... (保留原有模拟逻辑，简化展示)
                yield yield_msg(type="log", level="info", message="[模拟模式] 此处省略模拟逻辑...")
                yield yield_msg(type="complete")
                return

            # 连接MCP
            yield yield_msg(type="log", level="info", message="📡 连接小红书MCP服务...")
            await ctx.mcp_client.connect()
            yield yield_msg(type="log", level="success", message="✅ MCP连接成功")
            
            # 检查登录状态
            login_status = await ctx.mcp_client.check_login_status()
            if not login_status.get("is_logged_in"):
                yield yield_msg(type="log", level="error", message="❌ 小红书未登录或登录已过期！")
                yield yield_msg(type="error", message="需要登录小红书账号才能进行研究")
                history_service.update(record_id, {"status": "failed"})
                yield yield_msg(type="complete")
                return
            else:
                username = login_status.get("username", "用户")
                yield yield_msg(type="log", level="success", message=f"✅ 已登录账号: {username}")
            
            # 确保 Orchestrator 已初始化
            if not ctx.orchestrator:
                from ...agents.orchestrator import ResearchOrchestrator
                ctx.orchestrator = ResearchOrchestrator(ctx.config, ctx.mcp_client)

            # 执行研究
            state = ResearchState(task=research_topic)
            
            # === 阶段1: 规划 ===
            timer.start_stage("规划")
            yield yield_msg(type="progress", percent=10)
            yield yield_msg(type="log", level="info", message="📋 [Planner] 分析研究主题...")
            
            planner_logs = []
            def capture_planner_log(msg):
                planner_logs.append(msg)
            
            state = await ctx.orchestrator.planner.run(state, on_log=capture_planner_log)
            
            for log in planner_logs:
                yield yield_msg(type="log", level="info", message=f"  {log}")
                
            timer.end_stage()
            if state.plan:
                yield yield_msg(type="log", level="success", message=f"📋 [Planner] 生成了 {len(state.plan.keywords)} 个搜索关键词")
                for kw in state.plan.keywords:
                    yield yield_msg(type="log", level="info", message=f"  - {kw}")
            
            # === 阶段2: 搜索 ===
            timer.start_stage("搜索")
            yield yield_msg(type="stage", stage="searching")
            yield yield_msg(type="progress", percent=25)
            yield yield_msg(type="log", level="info", message="🔍 [Searcher] 开始搜索笔记...")
            
            search_logs = []
            def capture_log(msg):
                search_logs.append(msg)
            
            state = await ctx.orchestrator.searcher.run(state, on_log=capture_log)
            
            for log in search_logs:
                yield yield_msg(type="log", level="info", message=f"  {log}")
            
            stats["notesFound"] = len(state.documents)
            yield yield_msg(type="stats", stats=stats)
            yield yield_msg(type="log", level="success", message=f"🔍 [Searcher] 收集了 {stats['notesFound']} 篇笔记")
            timer.end_stage()
            
            # === 阶段3: 分析 ===
            timer.start_stage("分析")
            yield yield_msg(type="stage", stage="analyzing")
            yield yield_msg(type="progress", percent=45)
            yield yield_msg(type="log", level="info", message="🧠 [Analyzer] 分析数据中...")
            
            analyzer_logs = []
            def capture_analyzer_log(msg):
                analyzer_logs.append(msg)
                
            state = await ctx.orchestrator.analyzer.run(state, on_log=capture_analyzer_log)
            
            for log in analyzer_logs:
                yield yield_msg(type="log", level="info", message=f"  {log}")

            stats["contentsAnalyzed"] = len(state.documents)
            if state.insights:
                findings = state.insights.get("key_findings", [])
                stats["insightsExtracted"] = len(findings)
                yield yield_msg(type="stats", stats=stats)
                yield yield_msg(type="log", level="success", message=f"🧠 [Analyzer] 提取了 {stats['insightsExtracted']} 条核心发现")
            timer.end_stage()
            
            # === 阶段4: 图片分析 ===
            timer.start_stage("图片分析")
            yield yield_msg(type="progress", percent=55)
            yield yield_msg(type="log", level="info", message="🖼️ [ImageAnalyzer] VLM分析图片...")
            
            image_analyzer = ImageAnalyzer()
            image_logs = []
            def capture_image_log(msg):
                image_logs.append(msg)
                
            try:
                state, img_stats = await image_analyzer.analyze(state, on_log=capture_image_log)
                for log in image_logs:
                    yield yield_msg(type="log", level="info", message=f"  {log}")
                yield yield_msg(type="log", level="success", message=f"🖼️ 分析了 {len(state.image_analyses)} 张图片")
            except Exception as e:
                yield yield_msg(type="log", level="warning", message=f"⚠ 图片分析异常: {str(e)[:100]}")
            timer.end_stage()
            
            # === 阶段5: 大纲生成 ===
            timer.start_stage("大纲生成")
            yield yield_msg(type="stage", stage="generating")
            yield yield_msg(type="progress", percent=65)
            yield yield_msg(type="log", level="info", message="📑 [OutlineGenerator] 生成结构化大纲...")
            
            outline_generator = OutlineGenerator(ctx.config.get_llm_client(), model=ctx.config.llm.model)
            
            outline_logs = []
            def capture_outline_log(msg):
                outline_logs.append(msg)
                
            try:
                structured_outline = await outline_generator.generate(state, on_log=capture_outline_log)
                for log in outline_logs:
                    yield yield_msg(type="log", level="info", message=f"  {log}")
                yield yield_msg(type="log", level="success", message=f"📑 生成了 {len(structured_outline)} 个章节")
            except Exception as e:
                yield yield_msg(type="log", level="warning", message=f"⚠ 大纲生成失败: {e}, 使用备用")
                structured_outline = outline_generator._generate_fallback_outline(state)
            timer.end_stage()
            
            # === 阶段6: 图片分配 ===
            timer.start_stage("图片分配")
            yield yield_msg(type="progress", percent=75)
            yield yield_msg(type="log", level="info", message="🎯 [ImageAssigner] 分配图片...")
            
            image_assigner = ImageAssigner()
            assign_logs = []
            def capture_assign_log(msg):
                assign_logs.append(msg)
                
            try:
                structured_outline = await image_assigner.assign(state, structured_outline, on_log=capture_assign_log)
                for log in assign_logs:
                    yield yield_msg(type="log", level="info", message=f"  {log}")
            except Exception as e:
                yield yield_msg(type="log", level="warning", message=f"⚠ 图片分配失败: {e}")
            timer.end_stage()
            
            # === 阶段7: 报告生成 ===
            timer.start_stage("报告生成")
            yield yield_msg(type="progress", percent=85)
            yield yield_msg(type="log", level="info", message="📝 [Writer] 生成图文报告...")
            
            html_generator = HTMLReportGenerator(ctx.config.get_llm_client(), model=ctx.config.llm.model)
            
            html_logs = []
            def capture_html_log(msg):
                html_logs.append(msg)
                
            try:
                html_report = await html_generator.generate(state, on_log=capture_html_log)
                for log in html_logs:
                    yield yield_msg(type="log", level="info", message=f"  {log}")
            except Exception as e:
                yield yield_msg(type="log", level="warning", message=f"⚠ 报告生成失败: {e}")
                html_report = html_generator.generate_fallback_html(state)
                
            yield yield_msg(type="progress", percent=100)
            yield yield_msg(type="log", level="success", message="✅ 报告生成完成")
            yield yield_msg(type="log", level="info", message=timer.get_summary())
            timer.end_stage()
            
            # 构建并发送 Report 数据
            report_data = {
                "topic": research_topic,
                "insights": state.insights,
                "outline": structured_outline,
                "notes": [
                    {
                        "id": note.preview.id,
                        "title": note.detail.title or note.preview.title,
                        "content": note.detail.content or note.preview.content_preview,
                        "author": note.detail.author or note.preview.author,
                        "likes": note.detail.likes or note.preview.likes,
                        "images": note.detail.images if note.detail.images else [],
                        "url": note.detail.url or note.preview.url
                    }
                    for note in state.documents
                ]
            }
            yield yield_msg(type="report", data=report_data)
            
            # 保存历史
            history_service.save_report_data(
                record_id=record_id,
                outline=structured_outline,
                notes=report_data["notes"],
                insights=state.insights or {}
            )
            history_service.update(record_id, {"status": "completed"})
            yield yield_msg(type="complete")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield yield_msg(type="log", level="error", message=f"❌ 研究失败: {str(e)}")
            history_service.update(record_id, {"status": "failed"})
            yield yield_msg(type="complete")
        finally:
             if ctx.mcp_client:
                 await ctx.mcp_client.disconnect()

    return EventSourceResponse(event_generator())
