"""测试增加延迟后详情获取是否正常"""
import asyncio
import httpx
import time

async def test_with_delay():
    """测试带延迟的详情获取"""
    print("=" * 50)
    print("Testing feed detail with delays")
    print("=" * 50)
    
    async with httpx.AsyncClient(base_url="http://localhost:18060", timeout=120) as client:
        # 1. 先搜索获取最新的 feed 和 token
        print("\n1. Searching for fresh feeds...")
        r = await client.post("/api/v1/feeds/search", json={"keyword": "meishi"})
        data = r.json()
        
        if not data.get("success"):
            print(f"   [ERROR] Search failed: {data}")
            return
        
        feeds = data.get("data", {}).get("feeds", [])
        print(f"   [OK] Found {len(feeds)} feeds")
        
        if not feeds:
            print("   [ERROR] No feeds found")
            return
        
        # 2. 测试多个 feed 的详情获取
        success_count = 0
        fail_count = 0
        
        for i, feed in enumerate(feeds[:5], 1):
            feed_id = feed.get("id")
            xsec_token = feed.get("xsecToken")
            note_card = feed.get("noteCard", {})
            title = note_card.get("displayTitle", "No title")[:30]
            
            print(f"\n2.{i} Testing feed: {title}...")
            print(f"     ID: {feed_id}")
            print(f"     Token: {xsec_token[:30]}..." if xsec_token else "     Token: None")
            
            # 添加延迟
            delay = 3.0  # 3秒延迟
            print(f"     Waiting {delay}s...")
            await asyncio.sleep(delay)
            
            # 请求详情
            start = time.time()
            try:
                r = await client.post("/api/v1/feeds/detail", json={
                    "feed_id": feed_id,
                    "xsec_token": xsec_token
                })
                elapsed = time.time() - start
                
                detail = r.json()
                if detail.get("success"):
                    d = detail.get("data", {})
                    content_len = len(d.get("content", ""))
                    images = d.get("images", [])
                    print(f"     [OK] Got detail in {elapsed:.1f}s")
                    print(f"         Content: {content_len} chars")
                    print(f"         Images: {len(images)}")
                    success_count += 1
                else:
                    error = detail.get("error", "Unknown error")
                    print(f"     [FAIL] {error}")
                    fail_count += 1
            except Exception as e:
                print(f"     [ERROR] {e}")
                fail_count += 1
        
        print("\n" + "=" * 50)
        print(f"Results: {success_count} success, {fail_count} failed")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_with_delay())
