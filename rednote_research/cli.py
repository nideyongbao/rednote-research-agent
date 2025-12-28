"""命令行入口"""

import asyncio
import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .config import Config
from .state import ResearchState
from .mcp.xiaohongshu import XiaohongshuMCPClient
from .agents.orchestrator import ResearchOrchestrator
from .output.html_generator import HTMLReportGenerator


console = Console()


async def run_research(task: str, container_name: str = "xiaohongshu-mcp", output_dir: str = "./reports"):
    """执行研究任务"""
    
    console.print(Panel(f"🔍 研究主题: {task}", style="bold red"))
    
    # 初始化配置
    config = Config.from_env()
    
    # 创建MCP客户端（使用 Docker 容器）
    mcp_client = XiaohongshuMCPClient(container_name=container_name)
    
    # 创建编排器
    orchestrator = ResearchOrchestrator(config, mcp_client)
    
    # 日志回调
    def on_log(message: str):
        console.print(f"  {message}")
    
    try:
        # 连接MCP
        console.print("[cyan]📡 连接小红书MCP服务...[/cyan]")
        await mcp_client.connect()
        console.print("[green]✅ MCP连接成功[/green]")
        
        # 执行研究
        state = await orchestrator.run(task, on_log)
        
        # 生成HTML报告
        console.print("[cyan]📝 生成HTML报告...[/cyan]")
        html_generator = HTMLReportGenerator(config.get_llm_client())
        
        try:
            html_report = await html_generator.generate(state)
        except Exception as e:
            console.print(f"[yellow]⚠ LLM生成失败: {e}，使用备用模板[/yellow]")
            html_report = html_generator.generate_fallback_html(state)
        
        # 保存报告
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_file = output_path / filename
        report_file.write_text(html_report, encoding="utf-8")
        
        console.print(Panel(
            f"[green]✅ 研究完成！[/green]\n\n"
            f"📊 收集了 {len(state.documents)} 篇笔记\n"
            f"📄 报告已保存: {report_file}",
            title="完成",
            style="green"
        ))
        
        return str(report_file)
        
    finally:
        await mcp_client.disconnect()


def main():
    """CLI主入口"""
    parser = argparse.ArgumentParser(
        description="RedNote Research Agent - 小红书深度研究智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # research 命令
    research_parser = subparsers.add_parser("research", help="执行研究任务")
    research_parser.add_argument("task", help="研究主题")
    research_parser.add_argument(
        "--container", "-c",
        default=os.getenv("XIAOHONGSHU_MCP_CONTAINER", "xiaohongshu-mcp"),
        help="xiaohongshu-mcp 容器名称"
    )
    research_parser.add_argument(
        "--output", "-o",
        default="./reports",
        help="报告输出目录"
    )
    
    # server 命令
    server_parser = subparsers.add_parser("server", help="启动Web服务")
    server_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    server_parser.add_argument("--port", "-p", type=int, default=8000, help="监听端口")
    
    args = parser.parse_args()
    
    if args.command == "research":
        asyncio.run(run_research(args.task, args.container, args.output))
        
    elif args.command == "server":
        import uvicorn
        from .web.app import app
        
        console.print(Panel(
            f"🚀 启动Web服务\n"
            f"地址: http://{args.host}:{args.port}",
            style="bold blue"
        ))
        uvicorn.run(app, host=args.host, port=args.port)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
