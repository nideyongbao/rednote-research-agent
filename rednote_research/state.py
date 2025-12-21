"""共享状态定义 - 所有智能体读写的统一数据结构"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NotePreview(BaseModel):
    """笔记预览信息（搜索结果）"""
    id: str = ""
    title: str = ""
    author: str = ""
    content_preview: str = ""
    likes: int = 0
    comments: int = 0
    url: str = ""


class NoteDetail(BaseModel):
    """笔记详细信息"""
    title: str = ""
    content: str = ""
    author: str = ""
    images: list[str] = []
    videos: list[str] = []
    tags: list[str] = []
    likes: int = 0
    comments: int = 0
    url: str = ""


class NoteData(BaseModel):
    """笔记完整数据（预览+详情）"""
    preview: NotePreview = NotePreview()
    detail: NoteDetail = NoteDetail()


class ResearchPlan(BaseModel):
    """研究计划"""
    understanding: str = Field(default="", description="对用户意图的理解")
    dimensions: list[str] = Field(default_factory=list, description="分析维度")
    keywords: list[str] = Field(default_factory=list, description="搜索关键词列表")


class ImageAnalysisResult(BaseModel):
    """图片分析结果"""
    image_url: str = ""
    description: str = ""
    tags: list[str] = []
    category: str = ""  # 实景/攻略/装饰/广告
    content_keywords: list[str] = []  # 新增：图片内容关键词，如["预算表", "费用明细"]
    scene_type: str = ""  # 新增：场景类型 (风格展示/数据展示/教程步骤/产品展示/真实场景)
    quality_score: int = 5
    should_use: bool = True
    matched_sections: list[str] = []  # 适合的章节标题列表


class ResearchState(BaseModel):
    """
    共享状态：所有智能体读写的统一数据结构
    
    设计思路：模仿LangGraph的State概念，但用纯Python实现
    """
    # 输入
    task: str = Field(default="", description="用户原始任务")
    
    # 规划阶段
    plan: Optional[ResearchPlan] = None
    search_keywords: list[str] = []
    additional_keywords: list[str] = []  # 反思后补充的关键词
    
    # 搜索阶段
    documents: list[NoteData] = []
    
    # 分析阶段
    insights: Optional[dict] = None
    final_report: str = ""
    
    # 图片分析阶段（新增）
    image_analyses: dict[str, ImageAnalysisResult] = Field(default_factory=dict, description="图片分析结果 {url: result}")
    
    # 控制流
    is_complete: bool = False
    iteration_count: int = 0
    logs: list[str] = []
    
    def add_log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
    
    def get_latest_log(self) -> str:
        """获取最新日志"""
        return self.logs[-1] if self.logs else ""
