import asyncio
import os
import sys

# 添加当前目录到 path 以便导入模块
sys.path.append(os.getcwd())

from rednote_research.mcp.http_client import XiaohongshuHTTPClient, NotePreview

async def main():
    print("开始验证修复...")
    client = XiaohongshuHTTPClient()
    
    try:
        await client.connect()
        print("Connected to MCP")
        
        # 1. 搜索
        keyword = "美食"
        print(f"搜索关键词: {keyword}")
        notes, _ = await client.search_feeds(keyword)
        print(f"搜索到 {len(notes)} 篇笔记")
        
        if not notes:
            print("❌ 没有搜索到笔记，无法继续验证")
            return

        # 检查 token缓存
        print(f"Token缓存大小: {len(client._last_search_tokens)}")
        
        # 2. 获取详情
        target_note = notes[0]
        print(f"尝试获取笔记详情: {target_note.title} (ID: {target_note.id})")
        
        token = client._last_search_tokens.get(target_note.id)
        if not token:
            print(f"❌ 警告: 没有在缓存中找到 ID {target_note.id} 的 token")
        else:
            print(f"✅ 找到 token: {token[:10]}...")
            
        note_data = await client.get_note_with_detail(target_note)
        
        # 调试：再次调用 get_feed_detail 并打印原始数据
        print("\n--- DEBUG: 原始响应分析 ---")
        try:
            response = await client._client.post("/api/v1/feeds/detail", json={
                "feed_id": target_note.id,
                "xsec_token": token
            })
            raw_data = response.json()
            print(f"原始响应 Keys: {list(raw_data.keys())}")
            if "data" in raw_data:
                data_obj = raw_data["data"]
                print(f"Data Keys: {list(data_obj.keys())}")
                if "note" in data_obj:
                    print(f"Note Keys: {list(data_obj['note'].keys())}")
                    if "imageList" in data_obj['note']:
                        print(f"ImageList Count: {len(data_obj['note']['imageList'])}")
                    else:
                        print("Note Missing imageList")
                else:
                    print(f"Data Missing note object. Content: {data_obj}")
            else:
                print("Response Missing data object")
        except Exception as e:
            print(f"DEBUG Error: {e}")
        print("--- DEBUG END ---\n")

        # 3. 验证结果
        detail = note_data.detail
        print(f"详情标题: {detail.title}")
        print(f"详情内容长度: {len(detail.content)}")
        print(f"图片数量: {len(detail.images)}")
        
        if len(detail.images) > 0 or len(detail.content) > 0:
            print("✅ 验证成功！能够正确获取到内容或图片。")
        else:
            print("❌ 验证失败！内容和图片都为空。")

    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
