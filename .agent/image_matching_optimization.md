# 图片与章节内容匹配优化设计文档

> **状态**: ✅ 已实施完成

## 问题描述

当前系统生成的报告中，图片与章节内容经常不匹配。例如：
- "预算控制策略：分项透明化与动态跟踪" 章节配了"装修风格"类的图片
- 章节内容讨论的是预算管理，但配图是意式风、北欧风等装修风格展示图
- 图片生成模型几乎未被调用

---

## 当前流程（已优化）

### 完整流程图
```
阶段4: ImageAnalyzer (VLM分析图片)
    │ 1. 收集所有笔记图片
    │ 2. 图片去重（日志显示去重前后数量）
    │ 3. VLM批量分析，提取：
    │    - category: 粗分类（实景/攻略/装饰/广告）
    │    - content_keywords: 语义关键词（如"北欧风"、"预算表"）
    │    - scene_type: 场景类型（风格展示/数据展示/教程步骤等）
    ↓ 输出: state.image_analyses

阶段5: OutlineGenerator (LLM生成大纲)
    ↓ 输出: structured_outline

阶段6: ImageAssigner (分配图片到章节)
    │ 1. 提取章节关键词
    │ 2. 语义匹配打分：
    │    - content_keywords 关键词重叠 (+3分/词)
    │    - scene_type 场景匹配 (+4分)
    │    - 原有匹配逻辑 (+2-5分)
    │ 3. 智能图片生成触发：
    │    - 图片不足时触发
    │    - 匹配分数 < 阈值(8)时也触发
    ↓ 输出: enriched_outline (添加images字段)

阶段7: HTMLGenerator (生成报告)
```

### 关键代码文件

| 文件 | 职责 | 状态 |
|------|------|------|
| `state.py` | 定义 ImageAnalysisResult | ✅ 已添加 content_keywords, scene_type |
| `output/image_analyzer.py` | VLM分析图片 | ✅ 已更新Prompt提取新字段 |
| `output/image_assigner.py` | 分配图片到章节 | ✅ 已实现语义匹配+智能生成触发 |

---

## 已实施的改进

### 1. state.py - 扩展数据结构

```python
class ImageAnalysisResult(BaseModel):
    image_url: str = ""
    description: str = ""
    tags: list[str] = []
    category: str = ""  # 实景/攻略/装饰/广告
    content_keywords: list[str] = []  # 新增：语义关键词
    scene_type: str = ""              # 新增：场景类型
    quality_score: int = 5
    should_use: bool = True
    matched_sections: list[str] = []
```

### 2. image_analyzer.py - 增强VLM Prompt

```python
prompt = """你是图片分析专家。请分析以下图片并以JSON数组格式输出分析结果。

## 输出要求
- image_index: 图片序号
- description: 图片内容描述（20字以内）
- tags: 标签数组（2-3个关键词）
- category: 分类（实景、攻略、装饰、广告）
- content_keywords: 图片核心内容关键词（3-5个），用于语义匹配章节内容
- scene_type: 场景类型（风格展示/数据展示/教程步骤/产品展示/真实场景）
- quality_score: 质量分数（1-10）
- should_use: 是否建议使用（true/false）

## 场景类型说明
- 风格展示: 装修风格、效果图、设计渲染
- 数据展示: 表格、清单、对比图、价格单
- 教程步骤: 操作流程、步骤说明、攻略图
- 产品展示: 具体产品、材料、工具
- 真实场景: 实拍照片、工地图、现场图

## content_keywords 示例
- 装修效果图 → ["北欧风", "客厅设计", "简约"]
- 预算表格 → ["装修预算", "费用明细", "价格对比"]
"""
```

**新增日志**：显示图片去重前后数量
```
[ImageAnalyzer] 图片去重: 48张 → 31张 (去除17张重复)
```

### 3. image_assigner.py - 语义匹配算法

```python
def _find_candidates(self, analyses, section_title, section_content, preferred_types):
    candidates = []
    section_keywords = self._extract_keywords(section_title + " " + section_content)
    
    for url, result in analyses.items():
        if url in self.used_images or not result.should_use:
            continue
        
        score = result.quality_score
        
        # 1. 语义关键词匹配（核心改进）
        image_keywords = set(result.content_keywords or [])
        keyword_overlap = len(section_keywords & image_keywords)
        score += keyword_overlap * 3
        
        # 2. 场景类型匹配（通用方案，无硬编码）
        scene_match = self._match_scene_type(section_title, result.scene_type)
        score += scene_match * 4
        
        # 3. 原有匹配逻辑
        if result.category in preferred_types:
            score += 2
        
        candidates.append((url, result, score))
    
    return sorted(candidates, key=lambda x: x[2], reverse=True)

def _match_scene_type(self, section_title, scene_type):
    """通用场景匹配：基于关键词重叠，无预设映射"""
    if not scene_type:
        return 0
    
    scene_keywords = self._extract_keywords(scene_type)
    title_keywords = self._extract_keywords(section_title)
    overlap = len(scene_keywords & title_keywords)
    
    if overlap >= 2:
        return 2  # 高度匹配
    elif overlap >= 1:
        return 1  # 部分匹配
    return 0
```

### 4. 智能图片生成触发

```python
# 选取图片
MIN_IMAGES = 1
MAX_IMAGES = min(suggested_count + 1, 4)
SCORE_THRESHOLD = 8  # 匹配分数阈值

selected_urls = []
best_score = 0
for url, result, score in candidates[:MAX_IMAGES]:
    selected_urls.append(url)
    self.used_images.add(url)
    if score > best_score:
        best_score = score

# 改进的触发条件
should_generate = (
    len(selected_urls) < MIN_IMAGES or 
    (len(selected_urls) > 0 and best_score < SCORE_THRESHOLD)
)

if should_generate and self.settings.imageGen.enabled:
    needed = max(MIN_IMAGES - len(selected_urls), 1)
    reason = "图片不足" if len(selected_urls) < MIN_IMAGES else f"匹配分数过低({best_score}<{SCORE_THRESHOLD})"
    logger.info(f"[ImageAssigner] 章节'{section_title}' {reason}，生成{needed}张")
    
    generated = await self._generate_images(section, state.task, needed)
    selected_urls.extend(generated)
```

**新增日志**：显示匹配分数
```
[ImageAssigner] '预算控制策略' | 候选: 28 | 最高分: 12 | 分配: 3
```

---

## 验证方法

1. 重启后端服务器
2. 搜索任意话题（如"家居装修"、"旅游攻略"等）
3. 观察日志：
   - `图片去重: X张 → Y张`
   - `最高分: N`（越高表示匹配度越好）
   - 若分数低于8且开启图片生成，应触发生成
4. 检查最终报告图片与章节内容的匹配度

---

## 未来优化方向（可选）

1. **OutlineGenerator 主动指定图片需求**
   - 让LLM在生成大纲时输出 `required_image_keywords`
   
2. **LLM动态生成图片Prompt**
   - 让LLM根据章节内容推断最合适的图片风格

3. **Embedding语义相似度**
   - 使用向量模型计算图片描述与章节内容的相似度
