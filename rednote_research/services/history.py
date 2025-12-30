"""
历史记录服务

管理研究任务的历史记录存储和检索
支持保存完整报告数据以便历史恢复编辑
"""

import json
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any
from pydantic import BaseModel


class ResearchRecord(BaseModel):
    """研究记录（元数据）"""
    id: str
    topic: str
    status: str  # pending, running, completed, failed
    created_at: str
    updated_at: str
    summary: Optional[str] = None
    key_findings: List[str] = []
    notes_count: int = 0
    sections_count: int = 0
    report_path: Optional[str] = None
    draft_id: Optional[str] = None  # 关联的发布草稿ID


class FullResearchRecord(ResearchRecord):
    """完整研究记录（包含报告数据，用于历史恢复编辑）"""
    outline: List[dict] = []   # 完整大纲数据
    notes: List[dict] = []     # 完整笔记数据
    insights: dict = {}        # 分析洞察数据


class HistoryService:
    """
    历史记录服务
    
    功能：
    - 创建、更新、删除研究记录
    - 持久化到 JSON 文件
    - 支持分页查询
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            # 优先使用环境变量
            env_path = os.getenv("HISTORY_STORAGE_PATH")
            if env_path:
                storage_path = Path(env_path)
            else:
                # 默认存储在 data 目录（容器中为 /app/data）
                # 回退兼容：如果 data 目录不存在，则使用旧路径
                project_root = Path(__file__).parent.parent.parent
                data_dir = project_root / "data"
                if data_dir.exists():
                    storage_path = data_dir / "history.json"
                else:
                    storage_path = Path(__file__).parent / "history.json"
        
        self.storage_path = storage_path
        self._ensure_storage()
    
    def _ensure_storage(self):
        """确保存储文件存在"""
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")
    
    def _load_all(self) -> List[dict]:
        """加载所有记录"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_all(self, records: List[dict]):
        """保存所有记录"""
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    def create(self, topic: str) -> ResearchRecord:
        """创建新的研究记录"""
        now = datetime.now().isoformat()
        record = ResearchRecord(
            id=str(uuid.uuid4()),
            topic=topic,
            status="pending",
            created_at=now,
            updated_at=now
        )
        
        records = self._load_all()
        records.insert(0, record.model_dump())  # 新记录放在最前面
        self._save_all(records)
        
        return record
    
    def get(self, record_id: str) -> Optional[ResearchRecord]:
        """获取单个记录（元数据）"""
        records = self._load_all()
        for r in records:
            if r["id"] == record_id:
                # 只返回元数据字段
                return ResearchRecord(**{k: v for k, v in r.items() 
                    if k in ResearchRecord.model_fields})
        return None
    
    def get_full(self, record_id: str) -> Optional[FullResearchRecord]:
        """获取完整记录（包含报告数据）"""
        records = self._load_all()
        for r in records:
            if r["id"] == record_id:
                return FullResearchRecord(**r)
        return None
    
    def update(self, record_id: str, updates: dict) -> Optional[ResearchRecord]:
        """更新记录"""
        records = self._load_all()
        for i, r in enumerate(records):
            if r["id"] == record_id:
                r.update(updates)
                r["updated_at"] = datetime.now().isoformat()
                records[i] = r
                self._save_all(records)
                return ResearchRecord(**{k: v for k, v in r.items() 
                    if k in ResearchRecord.model_fields})
        return None
    
    def save_report_data(
        self, 
        record_id: str, 
        outline: List[dict],
        notes: List[dict],
        insights: dict,
        draft_id: Optional[str] = None
    ) -> Optional[FullResearchRecord]:
        """保存完整报告数据（用于历史恢复编辑）"""
        records = self._load_all()
        for i, r in enumerate(records):
            if r["id"] == record_id:
                r["outline"] = outline
                r["notes"] = notes
                r["insights"] = insights
                r["notes_count"] = len(notes)
                r["sections_count"] = len(outline)
                if draft_id:
                    r["draft_id"] = draft_id
                # 从insights提取key_findings
                if insights and "key_findings" in insights:
                    r["key_findings"] = insights["key_findings"]
                r["updated_at"] = datetime.now().isoformat()
                records[i] = r
                self._save_all(records)
                return FullResearchRecord(**r)
        return None
    
    def delete(self, record_id: str) -> bool:
        """删除记录"""
        records = self._load_all()
        original_len = len(records)
        records = [r for r in records if r["id"] != record_id]
        
        if len(records) < original_len:
            self._save_all(records)
            return True
        return False
    
    def list(
        self, 
        page: int = 1, 
        page_size: int = 10,
        status: Optional[str] = None
    ) -> dict:
        """
        分页获取记录列表
        
        Returns:
            {
                "items": [...],
                "total": int,
                "page": int,
                "page_size": int,
                "total_pages": int
            }
        """
        records = self._load_all()
        
        # 过滤状态
        if status:
            records = [r for r in records if r.get("status") == status]
        
        total = len(records)
        total_pages = (total + page_size - 1) // page_size
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        items = records[start:end]
        
        return {
            "items": [ResearchRecord(**r).model_dump() for r in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    
    def get_recent(self, limit: int = 5) -> List[ResearchRecord]:
        """获取最近的记录"""
        records = self._load_all()[:limit]
        return [ResearchRecord(**r) for r in records]
    
    def search(self, keyword: str, limit: int = 10) -> List[ResearchRecord]:
        """按关键词搜索"""
        records = self._load_all()
        results = []
        
        keyword_lower = keyword.lower()
        for r in records:
            if keyword_lower in r.get("topic", "").lower():
                results.append(ResearchRecord(**r))
                if len(results) >= limit:
                    break
        
        return results

    def export_json(self) -> str:
        """导出所有数据为JSON字符串"""
        records = self._load_all()
        return json.dumps(records, ensure_ascii=False, indent=2)
    
    def import_json(self, json_data: str) -> dict:
        """
        从JSON导入数据
        
        Returns:
            {"added": int, "updated": int, "total": int}
        """
        try:
            new_records = json.loads(json_data)
            if not isinstance(new_records, list):
                raise ValueError("Format error: root must be a list")
            
            current_records = {r["id"]: r for r in self._load_all()}
            added = 0
            updated = 0
            
            for r in new_records:
                if "id" not in r:
                    continue
                
                if r["id"] in current_records:
                    # 更新现有记录（如果导入的更新时间较新）
                    curr = current_records[r["id"]]
                    if r.get("updated_at", "") > curr.get("updated_at", ""):
                        current_records[r["id"]] = r
                        updated += 1
                else:
                    # 添加新记录
                    current_records[r["id"]] = r
                    added += 1
            
            # 保存合并后的结果
            final_records = list(current_records.values())
            # 按更新时间倒序排序
            final_records.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            self._save_all(final_records)
            
            return {"added": added, "updated": updated, "total": len(final_records)}
            
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")


# 全局单例
_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    """获取历史记录服务单例"""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
