"""阶段计时器服务 - 用于统计各阶段耗时"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StageTimer:
    """
    阶段计时器
    
    用于记录研究流程中各阶段的耗时，便于识别性能瓶颈。
    
    使用方法:
        timer = StageTimer()
        timer.start_stage("规划")
        # ... 执行规划逻辑 ...
        timer.end_stage()
        
        timer.start_stage("搜索")
        # ... 执行搜索逻辑 ...
        timer.end_stage()
        
        print(timer.get_summary())
    """
    
    stages: dict = field(default_factory=dict)
    current_stage: Optional[str] = None
    stage_start: Optional[datetime] = None
    total_start: Optional[datetime] = None
    
    def start_stage(self, name: str) -> None:
        """
        开始一个新阶段
        
        Args:
            name: 阶段名称
        """
        # 如果有未结束的阶段，先结束它
        if self.current_stage and self.stage_start:
            self.end_stage()
        
        # 记录总开始时间
        if self.total_start is None:
            self.total_start = datetime.now()
        
        self.current_stage = name
        self.stage_start = datetime.now()
    
    def end_stage(self) -> Optional[float]:
        """
        结束当前阶段
        
        Returns:
            当前阶段的耗时（秒），如果没有活动阶段返回None
        """
        if self.current_stage and self.stage_start:
            elapsed = (datetime.now() - self.stage_start).total_seconds()
            self.stages[self.current_stage] = elapsed
            
            result = elapsed
            self.current_stage = None
            self.stage_start = None
            return result
        return None
    
    def get_current_elapsed(self) -> Optional[float]:
        """获取当前阶段已用时间（秒）"""
        if self.stage_start:
            return (datetime.now() - self.stage_start).total_seconds()
        return None
    
    def get_total_elapsed(self) -> Optional[float]:
        """获取总耗时（秒）"""
        if self.total_start:
            return (datetime.now() - self.total_start).total_seconds()
        return None
    
    def get_summary(self) -> str:
        """
        获取耗时统计摘要
        
        Returns:
            格式化的耗时统计字符串
        """
        if not self.stages:
            return "📊 暂无阶段耗时数据"
        
        lines = ["📊 各阶段耗时统计："]
        total = sum(self.stages.values())
        
        # 按执行顺序排列（使用OrderedDict特性，Python 3.7+字典保持插入顺序）
        for name, secs in self.stages.items():
            pct = (secs / total * 100) if total > 0 else 0
            
            # 格式化时间显示
            if secs >= 60:
                time_str = f"{secs/60:.1f}m"
            else:
                time_str = f"{secs:.1f}s"
            
            # 添加性能标识
            perf_icon = ""
            if pct > 30:
                perf_icon = " ⚠️"  # 可能需要优化
            
            lines.append(f"  - {name}: {time_str} ({pct:.1f}%){perf_icon}")
        
        # 总计
        if total >= 60:
            total_str = f"{total/60:.1f}m ({total:.0f}s)"
        else:
            total_str = f"{total:.1f}s"
        lines.append(f"  ⏱ 总计: {total_str}")
        
        return "\n".join(lines)
    
    def get_recommendations(self) -> list[str]:
        """
        根据耗时统计给出优化建议
        
        Returns:
            优化建议列表
        """
        if not self.stages:
            return []
        
        recommendations = []
        total = sum(self.stages.values())
        
        for name, secs in self.stages.items():
            pct = (secs / total * 100) if total > 0 else 0
            
            if "搜索" in name and pct > 40:
                recommendations.append(f"💡 [{name}] 占用 {pct:.0f}%，建议减少关键词数量或并行搜索")
            elif "图片" in name and pct > 25:
                recommendations.append(f"💡 [{name}] 占用 {pct:.0f}%，建议减少图片数量或启用缓存")
            elif "生成" in name and pct > 30:
                recommendations.append(f"💡 [{name}] 占用 {pct:.0f}%，建议使用更快的模型或减少章节数")
        
        return recommendations
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "stages": self.stages.copy(),
            "total_seconds": sum(self.stages.values()) if self.stages else 0
        }
