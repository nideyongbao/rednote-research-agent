# 图片处理流程说明

本文档详细说明 RedNote Research Agent 中图片从收集到最终使用的完整数据流程。

## 流程概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          图片处理数据流                                   │
└─────────────────────────────────────────────────────────────────────────┘

[笔记原始图片: N张]
         │
         ▼ 阶段1: 收集与去重 (ImageAnalyzer._collect_images)
[去重后图片: M张] ─── 去除重复URL
         │
         ▼ 阶段2: 下载转Base64 (ImageAnalyzer._download_image_to_base64)
[成功下载: K张] ─── 失败原因见下文
         │
         ▼ 阶段3: VLM批量分析 (ImageAnalyzer._analyze_images_batch)
[分析完成: K张] ─── 分类+评分+关键词提取
         │
         ▼ 阶段4: 可用性过滤 (should_use=true)
[可用图片: J张] ─── 过滤低质量和广告图
         │
         ▼ 阶段5: 章节匹配分配 (ImageAssigner.assign)
[已匹配: I张] ─── 按语义关键词匹配章节
         │
         ▼ 阶段6: 按需生成 (ImageAssigner._generate_images)
[生成补充: G张] ─── 匹配分数<8时AI生成
         │
         ▼ 最终结果
[报告使用: I+G张]
```

## 详细阶段说明

### 阶段1: 收集与去重

**位置**: `rednote_research/output/image_analyzer.py` - `_collect_images()`

**逻辑**:
1. 遍历所有笔记的 `note.detail.images` 列表
2. 使用 `dict.fromkeys()` 去除重复URL
3. 输出日志显示去重数量

**示例日志**:
```
[ImageAnalyzer] 图片去重: 32张 → 28张 (去除4张重复)
```

### 阶段2: 下载转Base64

**位置**: `rednote_research/output/image_analyzer.py` - `_download_image_to_base64()`

**逻辑**:
1. 使用 `aiohttp` 异步下载图片
2. 下载成功后转换为Base64 Data URI格式
3. 失败时返回None，后续使用原始URL尝试

**失败原因**:
| 原因 | 说明 |
|------|------|
| CDN防盗链 | 小红书CDN检测Referer，非官方请求被拒 |
| 链接过期 | 临时URL超过有效期 |
| 网络超时 | 下载超过设定时间限制 |
| 格式错误 | 非标准图片格式或损坏 |

**重试机制**:
- 最大重试次数: 2次
- 失败后使用原始URL作为fallback

**示例日志**:
```
[ImageAnalyzer] 下载完成: 19/28 成功
```

### 阶段3: VLM批量分析

**位置**: `rednote_research/output/image_analyzer.py` - `_analyze_images_batch()`

**逻辑**:
1. 按批次(每批10张)发送给VLM
2. VLM返回JSON格式分析结果
3. 解析并存储到 `state.image_analyses`

**VLM分析输出字段**:
```json
{
  "image_index": 0,
  "description": "图片描述",
  "tags": ["标签1", "标签2"],
  "category": "实景|攻略|装饰|广告",
  "content_keywords": ["关键词1", "关键词2"],
  "scene_type": "风格展示|数据展示|教程步骤|产品展示|真实场景",
  "quality_score": 8,
  "should_use": true
}
```

**示例日志**:
```
[ImageAnalyzer] 批次 1/2，图片 1-10
[ImageAnalyzer] VLM响应: [{"image_index":0,...}]
```

### 阶段4: 可用性过滤

**过滤条件** (should_use=false):
- `category == "广告"` - 营销推广图
- `quality_score < 6` - 低质量图片
- 模糊或无关内容

**示例统计**:
```
[ImageAnalyzer] 分析完成 | 总计: 19张 | 可用: 16张
[ImageAnalyzer] 分类统计: {'实景': 16, '攻略': 2, '广告': 1}
```

### 阶段5: 章节匹配分配

**位置**: `rednote_research/output/image_assigner.py` - `assign()`

**匹配算法**:
1. 提取章节标题和内容的关键词
2. 与图片的 `content_keywords` 和 `scene_type` 匹配
3. 计算匹配分数，选择最佳候选

**匹配分数计算**:
```python
score = keyword_matches * 3 + scene_type_bonus * 2 + category_bonus
```

**每章节图片数量**:
- 引言/总结: 1-2张
- 核心章节: 2-3张
- 避免重复使用同一图片

### 阶段6: 按需AI生成

**触发条件**:
- 章节匹配分数 < 8
- 且配置启用了图片生成 (`imageGen.enabled=true`)

**生成流程**:
1. LLM生成图片提示词 (`_build_smart_prompt`)
2. 调用图片生成API
3. 保存生成图片到本地
4. 添加到章节图片列表

**示例日志**:
```
[ImageAssigner] 章节'材料选择与维护策略' 匹配分数过低(7<8)，生成1张
```

## 日志示例解读

以日志文件中的实际案例为例：

```
📊 [统计] 共 28 张图片，总文本 1708 字，平均每篇 569 字
  ↓
🖼️ [ImageAnalyzer] 分析了 19 张图片，16 张可用
  ↓  
📐 [阶段4统计] 分类: 实景:16, 攻略:2, 未分类:1 | VLM调用: 3次
  ↓
🎯 [ImageAssigner] 分配了 15 张图片
  ↓
[ImageAssigner] 章节'材料选择与维护策略' 匹配分数过低(7<8)，生成1张
[ImageAssigner] 章节'常见陷阱与避雷指南' 匹配分数过低(7<8)，生成1张
```

**数据流解析**:
- 28张 → 19张: 9张下载失败（CDN防盗链或链接过期）
- 19张 → 16张: 3张被过滤（广告或低质量）
- 16张 → 15张: 1张未被任何章节选用
- 额外生成2张: 2个章节匹配分数不足

## 优化建议

### 1. 提高下载成功率
- 配置合适的User-Agent和Referer
- 增加下载超时时间
- 使用代理绕过CDN限制

### 2. 提高VLM分析准确性
- 优化prompt工程
- 调整批次大小
- 使用更强大的VLM模型

### 3. 提高匹配质量
- 扩展关键词词库
- 增加场景类型
- 优化匹配分数算法

## 配置参数

相关配置在 `settings.json` 中:

```json
{
  "vlm": {
    "enabled": true,
    "model": "qwen-vl-plus",
    "rate_limit_mode": true
  },
  "imageGen": {
    "enabled": true,
    "model": "wanx-v1"
  }
}
```
