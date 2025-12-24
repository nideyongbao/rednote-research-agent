"""测试 xiaohongshu-mcp 连接"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入
from rednote_research.mcp.client import MCPClientBase
from rednote_research.state import NotePreview, NoteDetail, NoteData


class TestClient(MCPClientBase):
    """测试用客户端"""
    
    async def check_login_status(self) -> dict:
        result = await self._get("/api/v1/login/status")
        if result.get("success"):
            data = result.get("data", {})
            return {
                "is_logged_in": data.get("is_logged_in", False),
                "username": data.get("username", "")
            }
        return {"is_logged_in": False, "username": ""}
    
    async def search_notes(self, keyword: str, limit: int = 5) -> list:
        result = await self._post("/api/v1/feeds/search", {"keyword": keyword})
        if result.get("success"):
            data = result.get("data", {})
            return data.get("feeds", [])[:limit]
        return []


async def test_connection():
    """测试 MCP 连接和基本功能"""
    print("=" * 50)
    print("xiaohongshu-mcp Connection Test")
    print("=" * 50)
    
    client = TestClient(base_url="http://localhost:18060")
    
    try:
        # 1. 连接
        print("\n1. Connecting to MCP service...")
        await client.connect()
        print("   [OK] Connected!")
        
        # 2. 检查登录状态
        print("\n2. Checking login status...")
        status = await client.check_login_status()
        print(f"   Status: {status}")
        
        if status.get("is_logged_in"):
            username = status.get('username', 'unknown')
            print(f"   [OK] Logged in as: {username}")
            
            # 3. 测试搜索
            print("\n3. Testing search...")
            results = await client.search_notes("naicha", limit=3)
            print(f"   [OK] Found {len(results)} results")
            
            for i, feed in enumerate(results[:3], 1):
                title = feed.get("title", "No title")[:30]
                likes = feed.get("likedCount", 0)
                xsec = feed.get("xsecToken", "")[:20] if feed.get("xsecToken") else "None"
                print(f"   [{i}] {title}... (likes: {likes})")
                print(f"       xsec_token: {xsec}...")
        else:
            print("   [WARN] Not logged in, please run xiaohongshu-login first")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 4. 断开连接
        print("\n4. Disconnecting...")
        await client.disconnect()
        print("   [OK] Disconnected")
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    asyncio.run(test_connection())
