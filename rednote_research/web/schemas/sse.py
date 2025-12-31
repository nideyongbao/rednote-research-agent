from typing import Optional, Any
from pydantic import BaseModel, Field
import json

class SSEMessage(BaseModel):
    """标准 SSE 消息模型"""
    type: str = Field(..., description="消息类型: log, stage, stats, progress, report, error, complete")
    record_id: Optional[str] = Field(None, alias="recordId")
    level: Optional[str] = Field(None, description="log level: info, success, warning, error")
    message: Optional[str] = None
    stage: Optional[str] = None
    stats: Optional[dict] = None
    percent: Optional[int] = None
    data: Optional[Any] = None

    class Config:
        populate_by_name = True

    def to_event(self) -> dict:
        """转换为 SSE 格式"""
        return {
            "data": json.dumps(
                self.model_dump(exclude_none=True, by_alias=True),
                ensure_ascii=False
            )
        }
