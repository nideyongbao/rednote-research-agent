"""图片分析器 Prompt"""

IMAGE_ANALYZER_PROMPT = """你是图片分析专家。请分析以下图片并以JSON数组格式输出分析结果。

## 输出要求
请输出一个JSON数组，每个元素包含以下字段：
- image_index: 图片序号（从0开始）
- description: 图片内容描述（20字以内）
- tags: 标签数组（2-3个关键词）
- category: 分类（只能是：实景、攻略、装饰、广告 之一）
- content_keywords: 图片核心内容关键词（3-5个），用于语义匹配章节内容
- scene_type: 场景类型（只能是以下之一）
- quality_score: 质量分数（1-10整数）
- should_use: 是否建议使用（true/false）

## 分类说明
- 实景: 真实场景拍摄
- 攻略: 包含文字说明的教程图
- 装饰: 通用装饰插图
- 广告: 明显的营销推广图

## 场景类型说明
- 风格展示: 装修风格、效果图、设计渲染
- 数据展示: 表格、清单、对比图、价格单
- 教程步骤: 操作流程、步骤说明、攻略图
- 产品展示: 具体产品、材料、工具
- 真实场景: 实拍照片、工地图、现场图

## content_keywords 示例
- 装修效果图 → ["北欧风", "客厅设计", "简约"]
- 预算表格 → ["装修预算", "费用明细", "价格对比"]
- 施工现场 → ["水电改造", "工地现场", "施工进度"]

请直接输出JSON数组，不要添加任何解释文字。"""


def build_image_analyzer_prompt(topic: str) -> str:
    """构建带研究主题的图片分析prompt"""
    return f"""你是图片分析专家。请分析以下图片并以JSON数组格式输出分析结果。

## 研究主题
{topic}

{IMAGE_ANALYZER_PROMPT.split("## 输出要求", 1)[1] if "## 输出要求" in IMAGE_ANALYZER_PROMPT else IMAGE_ANALYZER_PROMPT}"""
