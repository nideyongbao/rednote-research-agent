# RedNote Research Agent 数据持久化方案

为了确保研究数据的安全性、可恢复性和可迁移性，本项目采用了多层级的数据持久化策略。本文档详细说明了数据的存储位置、格式以及备份/恢复流程。

## 1. 数据存储架构

系统数据主要分为三类：历史记录、发布草稿、系统设置。

### 1.1 研究历史记录 (History Records)

存储所有研究任务的输入、过程状态和最终报告。

- **存储位置**: `rednote_research/services/history.json`
- **格式**: JSON Array
- **内容结构**:
  ```json
  [
    {
      "id": "uuid",
      "topic": "研究主题",
      "status": "completed",
      "created_at": "ISO8601时间",
      "updated_at": "ISO8601时间",
      "summary": "摘要",
      "key_findings": ["发现1", "发现2"],
      "notes_count": 10,
      "sections_count": 5,
      "outline": [...],  // 完整大纲（仅get_full时返回）
      "notes": [...],    // 完整原始笔记（仅get_full时返回）
      "insights": {...}  // 完整分析数据（仅get_full时返回）
    }
  ]
  ```
- **特点**: 单文件存储，便于检索，适合轻量级应用。

### 1.2 发布草稿 (Publish Drafts)

存储已转换为小红书发布格式的草稿内容及相关资源。

- **存储位置**: `output/publish/drafts/{draft_id}/`
- **结构**:
  - `draft.json`: 草稿元数据和内容
  - `images/`: 生成的封面图和配图（本地文件）
- **draft.json 格式**:
  ```json
  {
    "id": "short-uuid",
    "topic": "原主题",
    "title": "小红书标题",
    "content": "正文内容...",
    "tags": ["标签1", "标签2"],
    "cover_image": "/path/to/cover.jpg",
    "section_images": ["/path/to/img1.jpg"],
    "status": "draft",
    "created_at": "...",
    "updated_at": "..."
  }
  ```

### 1.3 系统设置 (Settings)

存储用户配置的API Key、模型参数等。

- **存储位置**: `rednote_research/config/settings.json` (或用户主目录)
- **格式**: Key-Value JSON

## 2. 数据备份与迁移

由于采用文件系统存储，备份非常简单。

### 2.1 手动备份

建议定期备份以下目录：
1. `rednote_research/services/history.json`
2. `output/publish/drafts/`

### 2.2 导出/导入功能 (Planned)

系统将提供统一的导出接口：

**导出 API**: `GET /api/history/export`
- 返回包含 `history.json` 和所有草稿数据的 ZIP 包。

**导入 API**: `POST /api/history/import`
- 上传 ZIP 包，覆盖或合并现有数据。

## 3. 持久化接口设计

为了支持未来扩展（如迁移到 SQLite 数据库），主要服务通过接口访问数据：

### HistoryService

```python
class HistoryService:
    def create(self, topic: str) -> ResearchRecord: ...
    def get(self, record_id: str) -> ResearchRecord: ...
    def update(self, record_id: str, updates: dict) -> ResearchRecord: ...
    def list(self, page: int, page_size: int) -> dict: ...
    # 新增
    def export_data(self) -> str: ... # 返回导出文件路径
    def import_data(self, file_path: str) -> bool: ...
```

### Unification Plan (统一化计划)

目前 Draft 和 History 是分离存储的。未来计划：
1. **统一 ID**: 让 Draft ID 与 Research ID 关联，或直接在 Research Record 中引用 Draft。
2. **统一存储**: 考虑使用 SQLite (`research.db`) 替换 `history.json`，特别是当记录数 > 1000 时。
