"""
历史记录服务

管理研究任务的历史记录存储和检索
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel


class ResearchRecord(BaseModel):
    """研究记录"""
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
        """获取单个记录"""
        records = self._load_all()
        for r in records:
            if r["id"] == record_id:
                return ResearchRecord(**r)
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
                return ResearchRecord(**r)
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


# 全局单例
_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    """获取历史记录服务单例"""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
