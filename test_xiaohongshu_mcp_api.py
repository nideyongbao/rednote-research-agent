"""
xiaohongshu-mcp REST API 测试脚本

测试 xiaohongshu-mcp Docker 服务的所有 REST API 接口
"""
import asyncio
import httpx
import json
from typing import Optional


class XiaohongshuMCPClient:
    """xiaohongshu-mcp REST API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:18060"):
        self.base_url = base_url.rstrip("/")
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def check_login_status(self) -> dict:
        """检查登录状态"""
        response = await self.client.get("/api/v1/login/status")
        return response.json()
    
    async def get_login_qrcode(self) -> dict:
        """获取登录二维码"""
        response = await self.client.get("/api/v1/login/qrcode")
        return response.json()
    
    async def search_feeds(self, keyword: str, filters: dict = None) -> dict:
        """搜索笔记"""
        data = {"keyword": keyword}
        if filters:
            data["filters"] = filters
        response = await self.client.post("/api/v1/feeds/search", json=data)
        return response.json()
    
    async def get_feed_detail(self, feed_id: str, xsec_token: str) -> dict:
        """获取笔记详情"""
        response = await self.client.post("/api/v1/feeds/detail", json={
            "feed_id": feed_id,
            "xsec_token": xsec_token
        })
        return response.json()
    
    async def publish_content(self, title: str, content: str, images: list, tags: list = None) -> dict:
        """发布图文内容"""
        data = {
            "title": title,
            "content": content,
            "images": images
        }
        if tags:
            data["tags"] = tags
        response = await self.client.post("/api/v1/publish", json=data)
        return response.json()


async def test_all_apis():
    """测试所有 API 接口"""
    print("=" * 60)
    print("xiaohongshu-mcp REST API 测试")
    print("=" * 60)
    
    async with XiaohongshuMCPClient() as client:
        
        # 1. 测试登录状态
        print("\n[1/4] 测试登录状态...")
        try:
            status = await client.check_login_status()
            print(f"  响应: {json.dumps(status, ensure_ascii=False, indent=2)}")
            
            if status.get("data", {}).get("is_logged_in"):
                print("  ✅ 已登录")
            else:
                print("  ⚠️ 未登录")
                return
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            return
        
        # 2. 测试搜索功能
        print("\n[2/4] 测试搜索功能...")
        search_keyword = "奶茶推荐"
        try:
            result = await client.search_feeds(search_keyword)
            feeds = result.get("data", {}).get("feeds", [])
            print(f"  关键词: {search_keyword}")
            print(f"  结果数量: {len(feeds)}")
            
            if feeds:
                # 保存第一条结果用于后续测试
                first_feed = feeds[0]
                print(f"  第一条笔记:")
                print(f"    ID: {first_feed.get('id', 'N/A')}")
                print(f"    标题: {first_feed.get('noteCard', {}).get('displayTitle', 'N/A')[:30]}")
                xsec_token = first_feed.get("xsecToken", "")
                print(f"    xsecToken: {xsec_token[:30]}..." if xsec_token else "    xsecToken: N/A")
                print("  ✅ 搜索成功")
            else:
                print("  ⚠️ 未找到结果")
                first_feed = None
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            first_feed = None
        
        # 3. 测试获取详情 (如果搜索成功)
        print("\n[3/4] 测试获取笔记详情...")
        if first_feed and first_feed.get("id") and first_feed.get("xsecToken"):
            try:
                detail = await client.get_feed_detail(
                    first_feed["id"],
                    first_feed["xsecToken"]
                )
                if detail.get("success"):
                    data = detail.get("data", {})
                    print(f"  标题: {data.get('title', 'N/A')[:30]}")
                    print(f"  内容: {data.get('desc', 'N/A')[:50]}...")
                    print(f"  图片数: {len(data.get('imageList', []))}")
                    print("  ✅ 获取详情成功")
                else:
                    print(f"  ⚠️ 获取失败: {detail.get('message', '未知错误')}")
            except Exception as e:
                print(f"  ❌ 失败: {e}")
        else:
            print("  ⏭️ 跳过 (无搜索结果)")
        
        # 4. 发布测试 (默认跳过，避免误发)
        print("\n[4/4] 发布功能测试...")
        print("  ⏭️ 跳过 (需手动开启，避免误发)")
        print("  如需测试发布，请取消下方代码注释")
        
        #取消注释以测试发布功能
        try:
            result = await client.publish_content(
                title="MCP测试发布",
                content="这是一条测试内容",
                images=["https://picsum.photos/800/600"],
                tags=["测试"]
            )
            print(f"  响应: {result}")
            if result.get("success"):
                print("  ✅ 发布成功")
            else:
                print(f"  ⚠️ 发布失败: {result.get('message')}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_apis())
