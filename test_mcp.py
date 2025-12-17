"""测试 MCP 客户端连接"""
import asyncio
from rednote_research.mcp.rednote import RedNoteMCPClient

async def test():
    print("Creating MCP client...")
    client = RedNoteMCPClient(r'E:\code\workspace\1216_2\rednote-research-agent\rednote-mcp\dist\index.js')
    
    print("Connecting...")
    try:
        await client.connect()
        print("SUCCESS! Connected to MCP server.")
        
        # 测试搜索
        print("Testing search...")
        notes = await client.search_notes("咖啡店", limit=3)
        print(f"Found {len(notes)} notes")
        
        await client.disconnect()
        print("Disconnected.")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
