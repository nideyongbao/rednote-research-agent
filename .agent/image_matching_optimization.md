# 图片与章节内容匹配优化设计文档

## 问题描述

当前系统生成的报告中，图片与章节内容经常不匹配。例如：
- "预算控制策略：分项透明化与动态跟踪" 章节配了"装修风格"类的图片
- 章节内容讨论的是预算管理，但配图是意式风、北欧风等装修风格展示图
- **图片生成模型几乎未被调用**

---

## 当前流程分析

### 完整流程图
```
阶段4: ImageAnalyzer (VLM分析图片)
    ↓ 输出: state.image_analyses (每张图片的分类、描述、quality_score)
阶段5: OutlineGenerator (LLM生成大纲)
    ↓ 输出: structured_outline (含source_notes，图片是从笔记索引提取)
阶段6: ImageAssigner (分配图片到章节)
    ↓ 输出: structured_outline (添加images字段)
阶段7: HTMLGenerator (生成报告)
```

### 关键代码位置

| 文件 | 职责 | 问题 |
|------|------|------|
| `output/image_analyzer.py` | 分析图片并分类 | 分类过于粗糙（只有实景/攻略/装饰/广告4类） |
| `output/outline_generator.py` | 生成大纲 | `_parse_outline`从`source_notes`索引提取图片，无语义匹配 |
| `output/image_assigner.py` | 分配图片到章节 | `_find_candidates`的匹配逻辑过于简单 |
| `output/image_processor.py` | 更完整的处理器 | 有更好的设计但未被当前流程使用 |

---

## 问题根因

### 1. ImageAnalyzer 分类维度不足
```python
# 当前分类
category: 分类（只能是：实景、攻略、装饰、广告 之一）
```
- 只有4个笼统分类，无法区分"装修风格图"和"预算表格图"
- 缺少与章节主题的语义关联

### 2. OutlineGenerator 图片来源机制有问题
```python
# outline_generator.py:262-266
for note_idx in section_dict["source_notes"]:
    if 0 <= note_idx < len(state.documents):
        note = state.documents[note_idx]
        if note.detail.images:
            section_dict["images"].extend(note.detail.images[:2])
```
- 直接从笔记索引提取图片，没有语义筛选
- 如果笔记同时包含风格图和表格图，会混在一起

### 3. ImageAssigner 匹配逻辑弱
```python
# image_assigner.py:112-123
score = result.quality_score

# 章节标题匹配加分
if section_title in result.matched_sections:
    score += 5
elif any(section_title in s or s in section_title for s in result.matched_sections):
    score += 3

# 分类匹配加分
if result.category in preferred_types:
    score += 2
```
- `result.matched_sections` 几乎总是空的（未被正确填充）
- 分类匹配只能选"实景"或"攻略"等，无法精确匹配内容

### 4. 图片生成模型几乎不会被调用
```python
# image_assigner.py:80
if len(selected_urls) < MIN_IMAGES and self.settings.imageGen.enabled:
    needed = MIN_IMAGES - len(selected_urls)
    generated = await self._generate_images(section, state.task, needed)
```

**问题分析**：
- 只有当 `selected_urls < MIN_IMAGES (=1)` 时才触发生成
- 由于匹配逻辑弱，即使图片语义不匹配也会被选中
- 只要有足够数量的图片（即使不相关），就不会触发生成
- 结果：图片生成模型几乎永远不会被调用

---

## 优化方案

### 方案A：增强 ImageAnalyzer 语义分析（推荐）

#### 改动点
1. **扩展分类维度**：添加更细粒度的内容标签
2. **提取图片关键词**：让VLM提取图片的核心主题词
3. **添加场景类型**：区分数据展示、风格展示、教程步骤等

#### 新的分析输出结构
```python
class ImageAnalysisResult(BaseModel):
    image_url: str
    description: str           # 现有
    tags: list[str]            # 现有，扩展为更细的标签
    category: str              # 保留粗分类
    content_keywords: list[str] # 新增：图片内容关键词，如["预算表", "费用明细"]
    scene_type: str            # 新增：场景类型，如"数据展示"、"风格展示"、"教程步骤"
    quality_score: int
    should_use: bool
```

#### 新的VLM Prompt
```
请分析图片并输出：
- content_keywords: 图片的核心内容关键词（3-5个），如"北欧风格"、"预算明细"、"材料对比"
- scene_type: 图片场景类型：
  - 风格展示：装修风格、效果图
  - 数据展示：表格、清单、对比图
  - 教程步骤：操作流程、步骤说明
  - 产品展示：具体产品、材料
  - 真实场景：实拍照片、工地图
```

---

### 方案B：增强 ImageAssigner 语义匹配

#### 改动点
1. **章节关键词提取**：从章节标题和内容提取关键词
2. **关键词相似度匹配**：图片关键词 vs 章节关键词
3. **场景类型匹配**：预算章节 → 数据展示图

#### 匹配算法
```python
def _calculate_match_score(self, section, image_result):
    score = image_result.quality_score
    
    # 1. 提取章节关键词
    section_keywords = extract_keywords(section["title"] + section["content"])
    
    # 2. 计算关键词重叠度
    image_keywords = set(image_result.content_keywords or [])
    overlap = len(section_keywords & image_keywords)
    score += overlap * 3
    
    # 3. 场景类型匹配
    if "预算|费用|价格" in section and image.scene_type == "数据展示":
        score += 5
    if "风格|设计|效果" in section and image.scene_type == "风格展示":
        score += 5
    
    return score
```

---

### 方案C：更合理地调用图片生成模型（关键优化）

#### 问题
当前只在"图片数量不足"时生成，但应该在"图片语义不匹配"时也生成

#### 改动点
1. **修改触发条件**：除了数量不足，匹配分数过低时也触发生成
2. **优化生成Prompt**：根据章节内容构建精确的生成提示词

#### 新的触发逻辑
```python
# 修改前
if len(selected_urls) < MIN_IMAGES and self.settings.imageGen.enabled:

# 修改后
best_score = max([c[2] for c in candidates[:MAX_IMAGES]], default=0)
SCORE_THRESHOLD = 6  # 匹配分数阈值

should_generate = (
    # 条件1：图片数量不足
    len(selected_urls) < MIN_IMAGES or 
    # 条件2：有图片但匹配度太低
    (len(selected_urls) > 0 and best_score < SCORE_THRESHOLD)
)

if should_generate and self.settings.imageGen.enabled:
    # 构建语义化生成提示词
    prompt = self._build_smart_prompt(section, section_keywords)
    generated = await self._generate_images(section, state.task, needed, prompt)
```

#### 智能生成Prompt
```python
def _build_smart_prompt(self, section, keywords):
    """根据章节内容构建精确的图片生成提示词"""
    section_title = section.get("title", "")
    
    # 根据章节类型选择风格
    if any(kw in section_title for kw in ["预算", "费用", "价格"]):
        style = "信息图表风格，清晰的数据可视化，表格清单"
    elif any(kw in section_title for kw in ["风格", "设计", "效果"]):
        style = "室内设计渲染图，高质量3D效果"
    elif any(kw in section_title for kw in ["避坑", "问题", "注意"]):
        style = "警示提醒风格，对比图，问题示意"
    else:
        style = "小红书博主风格，温馨有质感"
    
    return f"""
主题：{section_title}
关键词：{', '.join(keywords)}
风格要求：{style}
"""
```

---

### 方案D：OutlineGenerator 主动指定图片需求

#### 改动点
让LLM在生成大纲时主动说明每章节需要什么类型的图片

#### 新的大纲结构
```json
{
  "title": "预算控制策略",
  "content": "...",
  "required_image_keywords": ["预算表", "费用清单", "对比数据"],
  "exclude_image_types": ["风格展示", "装修效果图"]
}
```

---

## 推荐实施顺序

### 第一阶段：快速修复（1-2小时）
1. 修改 `state.py` 添加 `content_keywords` 和 `scene_type` 字段
2. 修改 `ImageAnalyzer` 的VLM提示词，提取更细粒度的关键词
3. 修改 `ImageAssigner` 使用关键词匹配

### 第二阶段：图片生成优化（1小时）
1. 修改 `ImageAssigner` 的生成触发条件
2. 实现智能生成 Prompt 构建
3. 添加匹配分数阈值逻辑

### 第三阶段：结构优化（可选，2-3小时）
1. 修改 `OutlineGenerator` 让LLM指定 `required_image_keywords`
2. 考虑统一 `ImageProcessor` 和 `ImageAssigner`

---

## 文件修改清单

| 文件 | 修改内容 | 优先级 |
|------|----------|--------|
| `state.py` | 扩展 `ImageAnalysisResult` 添加 `content_keywords`, `scene_type` | 高 |
| `output/image_analyzer.py` | 修改VLM提示词提取关键词和场景类型 | 高 |
| `output/image_assigner.py` | 实现关键词匹配 + 智能触发生成 | 高 |
| `output/outline_generator.py` | 让LLM输出 `required_image_keywords`（可选） | 中 |

---

## 验证方法

1. 搜索"家居装修"话题
2. 检查最终报告：
   - "预算控制" 章节应配 "表格/清单" 类图片
   - "风格选择" 章节应配 "效果图/风格展示" 类图片
   - "避坑指南" 章节应配 "对比图/问题展示" 类图片
3. 如果原图不匹配且开启了图片生成，应该触发 AI 生成更合适的图片
