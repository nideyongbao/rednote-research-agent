"""发布服务 - 管理小红书发布流程

功能：
1. 内容转换：报告 → 小红书格式（标题≤20字，正文≤200字）
2. 草稿管理：创建、更新、获取、删除
3. 图片生成协调：封面图 + 章节图
4. 发布执行：调用 xiaohongshu-mcp
"""

import os
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from pydantic import BaseModel


class PublishDraft(BaseModel):
    """发布草稿"""
    id: str
    topic: str
    title: str  # ≤20字
    content: str  # ≤200字（图文笔记）
    cover_image: Optional[str] = None
    section_images: list[str] = []
    tags: list[str] = []
    status: str = "draft"  # draft | generating | ready | publishing | published | failed
    created_at: str = ""
    updated_at: str = ""
    published_url: Optional[str] = None
    error: Optional[str] = None
    
    # 原始数据（用于重新生成）
    key_findings: list[str] = []
    sections: list[dict] = []


class PublishService:
    """发布服务"""
    
    # 表情符号映射
    EMOJI_MAP = {
        "推荐": "💡", "必打卡": "📍", "避雷": "⚠️",
        "美食": "🍜", "旅游": "✈️", "价格": "💰",
        "分享": "💬", "收藏": "⭐", "攻略": "📋",
        "好物": "✨", "探店": "🏠", "穿搭": "👗"
    }
    
    def __init__(self, output_base_dir: str = None):
        """
        初始化发布服务
        
        Args:
            output_base_dir: 输出基础目录，默认为项目下的 output/publish
        """
        if output_base_dir:
            self.output_base_dir = output_base_dir
        else:
            # 默认使用项目目录下的 output/publish
            project_dir = Path(__file__).parent.parent
            self.output_base_dir = str(project_dir / "output" / "publish")
        
        # 草稿存储目录
        self.drafts_dir = os.path.join(self.output_base_dir, "drafts")
        Path(self.drafts_dir).mkdir(parents=True, exist_ok=True)
    
    # ===== 内容转换 =====
    
    def convert_to_xiaohongshu(
        self,
        topic: str,
        summary: str,
        key_findings: list[str],
        sections: list[dict],
        notes: list[dict] = None
    ) -> dict:
        """
        将研究报告转换为小红书格式
        
        Args:
            topic: 研究主题
            summary: 摘要
            key_findings: 关键发现
            sections: 章节列表
            notes: 原始笔记（可选）
            
        Returns:
            {title, content, tags, key_findings, sections}
        """
        # 1. 生成标题（≤20字）
        title = self._generate_title(topic, key_findings)
        
        # 2. 生成正文（≤200字）
        content = self._generate_content(topic, summary, key_findings, sections)
        
        # 3. 生成标签
        tags = self._generate_tags(topic, key_findings)
        
        return {
            "title": title,
            "content": content,
            "tags": tags,
            "key_findings": key_findings,
            "sections": sections
        }
    
    def _generate_title(self, topic: str, key_findings: list[str]) -> str:
        """
        生成标题（≤20字）
        
        格式：{emoji} {主题}｜{亮点}
        示例：✨ 穿搭分享｜显瘦又时髦
        """
        # 主题相关emoji映射
        topic_emojis = {
            "穿搭": "👗", "美食": "🍜", "旅游": "✈️", "护肤": "💆",
            "美妆": "💄", "健身": "💪", "家居": "🏠", "数码": "📱",
            "育儿": "👶", "宠物": "🐱", "摄影": "📸", "职场": "💼"
        }
        
        # 选择emoji
        emoji = "✨"
        for keyword, e in topic_emojis.items():
            if keyword in topic:
                emoji = e
                break
        
        # 提取主题核心（去掉过长的描述）
        core_topic = topic[:8] if len(topic) > 8 else topic
        
        # 提取亮点（从关键发现中提取精华）
        highlight = ""
        if key_findings:
            # 清理并提取关键词
            first_finding = key_findings[0]
            # 去除"笔记"等字眼，提取核心内容
            cleaned = first_finding.replace("笔记", "").replace("分析", "").replace("发现", "").strip()
            max_len = 20 - len(emoji) - len(core_topic) - 2  # emoji + 空格 + 分隔符
            if max_len > 3 and cleaned:
                highlight = cleaned[:max_len]
        
        if highlight:
            title = f"{emoji}{core_topic}｜{highlight}"
        else:
            title = f"{emoji}{core_topic}"
        
        return title[:20]
    
    def _generate_content(
        self, 
        topic: str, 
        summary: str, 
        key_findings: list[str],
        sections: list[dict]
    ) -> str:
        """
        生成正文（≤200字）
        
        结构：
        【开头吸引】- 25字
        【核心亮点】- 130字
        【互动引导】- 25字
        """
        lines = []
        
        # 开头吸引语（自然流畅）
        openers = [
            f"✨ 整理了一份超实用的{topic[:6]}，码住不亏！",
            f"🔥 {topic[:8]}来啦，亲测有效！",
            f"💡 关于{topic[:6]}，这些干货分享给你~",
            f"📋 {topic[:8]}全攻略，建议收藏！"
        ]
        import random
        intro = random.choice(openers)[:30]
        lines.append(intro)
        lines.append("")
        
        # 核心亮点（清理和重组关键发现）
        if key_findings:
            lines.append("📌 划重点：")
            for i, finding in enumerate(key_findings[:3]):
                # 清理"笔记"等字眼，提取核心内容
                cleaned = self._clean_finding(finding)
                if cleaned:
                    emoji = self._get_emoji_for_content(cleaned)
                    # 确保语句完整流畅
                    line = f"{emoji} {cleaned[:40]}"
                    lines.append(line)
        
        lines.append("")
        
        # 互动引导（多样化）
        outros = [
            "💬 觉得有用就点个赞吧~",
            "❤️ 收藏起来慢慢看！",
            "💭 你们还想了解什么？评论区告诉我~",
            "🙋 有问题评论区交流哦！"
        ]
        lines.append(random.choice(outros))
        
        content = "\n".join(lines)
        return content[:200]
    
    def _clean_finding(self, finding: str) -> str:
        """清理关键发现，去除不自然的字眼"""
        # 需要去除的词汇
        remove_words = [
            "笔记", "笔记1", "笔记2", "笔记3", "笔记4", "笔记5",
            "分析显示", "数据表明", "研究发现", "统计显示",
            "根据", "通过", "总结", "归纳"
        ]
        
        result = finding
        for word in remove_words:
            result = result.replace(word, "")
        
        # 清理多余的标点和空格
        result = result.strip()
        result = result.lstrip("，,、：:；;")
        result = result.strip()
        
        return result
    
    def _generate_tags(self, topic: str, key_findings: list[str]) -> list[str]:
        """生成标签（3-5个）"""
        tags = []
        
        # 从主题提取
        topic_words = topic.replace("｜", " ").replace("，", " ").replace(",", " ").split()
        for word in topic_words[:2]:
            if len(word) >= 2:
                tags.append(word)
        
        # 从关键发现提取
        for finding in key_findings[:3]:
            words = finding.split()
            for word in words:
                if 2 <= len(word) <= 6 and word not in tags:
                    tags.append(word)
                    break
        
        # 添加通用标签
        common_tags = ["分享", "攻略", "推荐"]
        for tag in common_tags:
            if len(tags) < 5 and tag not in tags:
                tags.append(tag)
        
        return tags[:8]
    
    def _get_emoji_for_content(self, text: str) -> str:
        """根据内容获取合适的表情符号"""
        for keyword, emoji in self.EMOJI_MAP.items():
            if keyword in text:
                return emoji
        return "💡"
    
    # ===== 草稿管理 =====
    
    def create_draft(
        self,
        topic: str,
        summary: str,
        key_findings: list[str],
        sections: list[dict],
        notes: list[dict] = None
    ) -> PublishDraft:
        """创建发布草稿"""
        # 转换内容
        converted = self.convert_to_xiaohongshu(
            topic, summary, key_findings, sections, notes
        )
        
        # 创建草稿
        draft_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        draft = PublishDraft(
            id=draft_id,
            topic=topic,
            title=converted["title"],
            content=converted["content"],
            tags=converted["tags"],
            key_findings=key_findings,
            sections=sections,
            status="draft",
            created_at=now,
            updated_at=now
        )
        
        # 创建草稿目录
        draft_dir = self._get_draft_dir(draft_id)
        Path(draft_dir).mkdir(parents=True, exist_ok=True)
        
        # 保存草稿
        self._save_draft(draft)
        
        return draft
    
    def get_draft(self, draft_id: str) -> Optional[PublishDraft]:
        """获取草稿"""
        draft_path = os.path.join(self._get_draft_dir(draft_id), "draft.json")
        if not os.path.exists(draft_path):
            return None
        
        with open(draft_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return PublishDraft(**data)
    
    def update_draft(self, draft_id: str, updates: dict) -> Optional[PublishDraft]:
        """更新草稿"""
        draft = self.get_draft(draft_id)
        if not draft:
            return None
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        
        draft.updated_at = datetime.now().isoformat()
        
        self._save_draft(draft)
        return draft
    
    def delete_draft(self, draft_id: str) -> bool:
        """删除草稿"""
        import shutil
        draft_dir = self._get_draft_dir(draft_id)
        if os.path.exists(draft_dir):
            shutil.rmtree(draft_dir)
            return True
        return False
    
    def list_drafts(self, limit: int = 20) -> list[PublishDraft]:
        """列出所有草稿"""
        drafts = []
        
        if not os.path.exists(self.drafts_dir):
            return drafts
        
        for draft_id in os.listdir(self.drafts_dir):
            draft = self.get_draft(draft_id)
            if draft:
                drafts.append(draft)
        
        # 按更新时间排序
        drafts.sort(key=lambda d: d.updated_at, reverse=True)
        
        return drafts[:limit]
    
    def _get_draft_dir(self, draft_id: str) -> str:
        """获取草稿目录"""
        return os.path.join(self.drafts_dir, draft_id)
    
    def _save_draft(self, draft: PublishDraft):
        """保存草稿"""
        draft_dir = self._get_draft_dir(draft.id)
        Path(draft_dir).mkdir(parents=True, exist_ok=True)
        
        draft_path = os.path.join(draft_dir, "draft.json")
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(draft.model_dump(), f, ensure_ascii=False, indent=2)
    
    # ===== 图片生成 =====
    
    async def generate_images(
        self,
        draft_id: str,
        on_log: Callable[[str], None] = None
    ) -> PublishDraft:
        """
        为草稿生成图片（封面+章节图）
        
        Args:
            draft_id: 草稿ID
            on_log: 日志回调
            
        Returns:
            更新后的草稿
        """
        from .image_generator import get_image_generator
        
        draft = self.get_draft(draft_id)
        if not draft:
            raise ValueError(f"草稿不存在: {draft_id}")
        
        # 更新状态
        draft = self.update_draft(draft_id, {"status": "generating"})
        
        generator = get_image_generator()
        draft_dir = self._get_draft_dir(draft_id)
        images_dir = os.path.join(draft_dir, "images")
        Path(images_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. 生成封面图
            if on_log:
                on_log("📸 开始生成封面图...")
            
            cover_path = await generator.generate_cover(
                topic=draft.topic,
                key_findings=draft.key_findings,
                output_dir=images_dir,
                on_log=on_log
            )
            
            if cover_path:
                draft = self.update_draft(draft_id, {"cover_image": cover_path})
            
            # 2. 生成章节图
            if on_log:
                on_log("📸 开始生成章节配图...")
            
            section_images = await generator.generate_section_images(
                sections=draft.sections,
                topic=draft.topic,
                output_dir=images_dir,
                max_images=5,
                on_log=on_log
            )
            
            if section_images:
                draft = self.update_draft(draft_id, {"section_images": section_images})
            
            # 更新状态
            draft = self.update_draft(draft_id, {"status": "ready"})
            
            if on_log:
                total_images = (1 if cover_path else 0) + len(section_images)
                on_log(f"✅ 图片生成完成，共 {total_images} 张")
            
            return draft
            
        except Exception as e:
            self.update_draft(draft_id, {
                "status": "draft",
                "error": str(e)
            })
            raise
    
    # ===== 发布执行 =====
    
    async def publish(
        self,
        draft_id: str,
        on_log: Callable[[str], None] = None
    ) -> PublishDraft:
        """
        发布到小红书
        
        Args:
            draft_id: 草稿ID
            on_log: 日志回调
            
        Returns:
            更新后的草稿
        """
        from ..mcp.http_client import get_mcp_client
        
        draft = self.get_draft(draft_id)
        if not draft:
            raise ValueError(f"草稿不存在: {draft_id}")
        
        # 检查是否有图片
        all_images = []
        if draft.cover_image:
            all_images.append(draft.cover_image)
        all_images.extend(draft.section_images)
        
        if not all_images:
            raise ValueError("没有可用的图片，请先生成图片")
        
        # 更新状态
        draft = self.update_draft(draft_id, {"status": "publishing"})
        
        if on_log:
            on_log(f"🚀 开始发布到小红书...")
            on_log(f"📝 标题: {draft.title}")
            on_log(f"📸 图片: {len(all_images)} 张")
        
        try:
            # 转换路径（本地路径 → Docker 容器路径）
            docker_images = self._convert_to_docker_paths(all_images)
            
            if on_log:
                on_log(f"📦 路径转换完成")
            
            # 调用 MCP 发布
            client = get_mcp_client()
            await client.connect()
            
            result = await client.publish_content(
                title=draft.title,
                content=draft.content,
                images=docker_images,
                tags=draft.tags
            )
            
            if result.get("success"):
                draft = self.update_draft(draft_id, {
                    "status": "published",
                    "published_url": result.get("url"),
                    "error": None
                })
                
                if on_log:
                    on_log(f"✅ 发布成功！")
                    if result.get("url"):
                        on_log(f"🔗 链接: {result.get('url')}")
            else:
                draft = self.update_draft(draft_id, {
                    "status": "failed",
                    "error": result.get("error", "发布失败")
                })
                
                if on_log:
                    on_log(f"❌ 发布失败: {result.get('error')}")
            
            return draft
            
        except Exception as e:
            self.update_draft(draft_id, {
                "status": "failed",
                "error": str(e)
            })
            
            if on_log:
                on_log(f"❌ 发布错误: {str(e)}")
            
            raise
    
    def _convert_to_docker_paths(self, local_paths: list[str]) -> list[str]:
        """
        将本地路径转换为 Docker 容器路径
        
        规则：
        - 工作区路径挂载到 /app/workspace
        - 例：D:/work/workspace/1228_1/... → /app/workspace/...
        """
        docker_paths = []
        
        # 尝试从环境变量获取工作区映射
        workspace_mount = os.getenv("WORKSPACE_MOUNT_PATH", "/app/workspace")
        
        for path in local_paths:
            if not path:
                continue
            
            # 已经是容器路径
            if path.startswith("/app/"):
                docker_paths.append(path)
                continue
            
            # 是 URL
            if path.startswith("http://") or path.startswith("https://"):
                docker_paths.append(path)
                continue
            
            # 本地路径转换
            normalized = path.replace("\\", "/")
            
            # 尝试提取相对路径
            # 假设路径格式：D:/work/workspace/xxxx/output/publish/...
            if "/output/" in normalized:
                rel_path = normalized.split("/output/", 1)[1]
                docker_path = f"{workspace_mount}/output/{rel_path}"
                docker_paths.append(docker_path)
            else:
                # 无法转换，保持原样
                docker_paths.append(path)
        
        return docker_paths


# 全局实例
_publish_service: Optional[PublishService] = None


def get_publish_service() -> PublishService:
    """获取发布服务实例"""
    global _publish_service
    if _publish_service is None:
        _publish_service = PublishService()
    return _publish_service
