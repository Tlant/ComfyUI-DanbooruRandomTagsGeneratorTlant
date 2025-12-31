
# ComfyUI-DanbooruRandomTagsGeneratorTlant

一个为 ComfyUI 设计的高级 Prompt 灵感生成器节点。它基于 **Danbooru 2024** 数据集 ([deepghs/danbooru2024](https://huggingface.co/datasets/deepghs/danbooru2024))（约 800 万张图片的元数据），根据分数、评级、包含/排除标签等条件，随机提取高质量的 Tag 组合。

此节点非常适合作为 **LLM (ChatGPT/Claude/Local LLM)** 的“参考素材”，或者用于寻找随机的构图与光影灵感。

## ✨ 核心特性 (Features)

*   **智能标签清洗**: 自动将原始数据的下划线 (`looking_back`) 转换为标准空格 (`looking back`)，并使用逗号分隔 (`1girl, solo, ...`)，完美适配 ComfyUI 的 CLIP 编码器或 LLM 输入。
*   **源链接回溯**: 生成结果不仅包含 Prompt，还直接提供该图片的 **Danbooru URL**，方便你点击查看原图，分析构图。
*   **稳定下载**: 集成 `huggingface_hub` 官方库，支持断点续传、Token 认证，解决了旧版本 401 报错问题。
*   **本地极速查询**: 数据加载至内存后，基于 Pandas 进行毫秒级查询。
*   **Seed 兼容**: 完美支持 ComfyUI 的 Global Seed。Seed 固定时，提取的 Prompt 绝对固定（可复现）。
*   **内存管理**: 内置“卸载内存”功能，生成结束后可一键释放占用的 RAM。

## 📖 使用指南 (Usage)

在 ComfyUI 中搜索节点名称：`Danbooru Tags Generator (Tlant)`

### 数据准备 (Data Setup)

本插件需要 `metadata.parquet` 数据文件才能运行。你有两种方式获取它：

1.  **自动下载 (推荐)**
    *   插件在首次运行时会自动从 Hugging Face 下载所需的数据集文件。你只需启动 ComfyUI 并使用该节点，等待下载完成即可。

2.  **手动下载**
    *   如果你的网络环境受限或希望手动管理文件，请按以下步骤操作：
        1.  从 [Hugging Face Datasets](https://huggingface.co/datasets/deepghs/danbooru2024/blob/main/metadata.parquet) 下载 `metadata.parquet` 文件。
        2.  将其放入 ComfyUI 的 `models/danbooru/` 目录下。
        3.  如果 `danbooru` 文件夹不存在，请手动创建它。

### 输入参数说明

| 参数名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `operation` | 选项 | `Load & Generate`: 正常加载数据并生成 Tag。<br>`Unload Memory`: 清空内存中的数据（释放 RAM），不生成 Tag。 |
| `seed` | INT | 随机种子。控制随机抽取的确定性。 |
| `min_score` | INT | 最低分数阈值。建议设置为 `20` 或 `50` 以筛选高质量画作。 |
| `allowed_ratings` | STRING | 允许的评级。默认 `g, s, q, e`。<br>• `g`: General<br>• `s`: Sensitive<br>• `q`: Questionable<br>• `e`: Explicit |
| `include_tags` | STRING | 必须包含的标签。例如 `scenery` 或 `1girl`。留空则不限制。 |
| `exclude_tags` | STRING | 必须排除的标签。例如 `comic`, `monochrome`。 |
| `hf_repo_id` | STRING | (可选) 数据集仓库ID，默认为 `deepghs/danbooru2024`。 |
| `hf_token` | STRING | (可选) 如果你遇到网络限制或下载私有模型，可在此填入 HuggingFace Token。 |

### 输出说明

| 输出项 | 类型 | 说明 |
| :--- | :--- | :--- |
| `final_prompt` | STRING | 清洗后的完整 Tag 字符串，逗号分隔。<br>例如: `1girl, solo, looking back, blue sky` |
| `score` | INT | 该图片在 Danbooru 上的原始分数。 |
| `danbooru_url` | STRING | 该图片的原始链接 (例如 `https://danbooru.donmai.us/posts/123456`)。 |
| `rating` | STRING | 该图片的评级 (`g`/`s`/`q`/`e`)。 |