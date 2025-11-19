# LitRelevanceAI 中文文档

AI 辅助的文献筛选工具，可评估学术论文与研究主题的相关性。项目现已封装为 `litrx` 包，通过统一的命令行接口提供 CSV 相关性分析、摘要筛选和 PDF 筛选功能，并提供基于 PyQt6 的现代图形界面。

[English README](README.md)

## 功能特点

- **CSV 相关性分析**：`litrx csv` 读取 Scopus 导出的文件，为每篇文章打出 0–100 的相关性分数，并给出解释。图形界面标签页以表格显示结果，可双击查看完整分析并导出表格。
- **摘要快速筛选**：`litrx abstract` 按 `questions_config.json` 中每种模式定义的是/否标准和开放式问题执行筛选。每个 AI 回答都可再经一次模型校验，确认标题或摘要是否支持该结论。可通过配置项 `ENABLE_VERIFICATION` 或界面勾选“启用验证”来切换。校验结果写入 `<列名>_verified` 字段（值为“支持/不支持”，禁用时为“未验证”），日志区会在答案后附上 ✔/✖ 标记。图形界面还提供 **“添加模式”**、**“编辑问题”**、**“中止任务”** 和导出表格等功能。
- **PDF 筛选**：`litrx pdf` 会先将 PDF 转为文本再发送给模型，依据研究问题和筛选标准输出结构化结果。图形界面标签页会列出所选文件夹的 PDF、显示匹配的元数据与处理状态，可设置研究问题、筛选条件和输出格式，支持仅匹配元数据模式，并在完成后提示打开结果目录。
- **PyQt6 标签式界面**：运行 `python run_gui.py`（或 `python -m litrx --gui`）可启动基于 PyQt6 的图形界面应用，包含 CSV 相关性分析、摘要筛选和 PDF 筛选标签页；首次启动会自动安装缺失依赖（包括 PyQt6）。
- **GPT-5 与 o1 模型支持**：AI 客户端自动检测并使用 OpenAI 的新 Responses API 来调用 GPT-5 和 o1 系列模型，支持 `verbosity`（详细程度）和 `reasoning_effort`（推理努力程度）等高级参数。与现有代码无缝集成的同时提供增强的推理能力。详见 [GPT-5 使用指南](docs/GPT5_GUIDE.md)。
- **灵活的模型配置**：可在脚本中自由切换 OpenAI 或 SiliconFlow，并调整温度、模型名称等参数。界面下拉菜单切换服务商时会自动更新 API 密钥字段并记住之前保存的密钥。
- **统一的配置管理**：通过 `.env` 与 JSON/YAML 配置文件合并生成 `DEFAULT_CONFIG`，命令行参数可覆盖默认值。
- **自动保存进度**：中间结果和最终结果都会写入带时间戳的 CSV 或 XLSX 文件，避免进度丢失。

## 安装步骤

1. 安装 Python 3.8 及以上版本。
2. 克隆本仓库并安装包：
   ```bash
   python -m pip install -e .
   ```
   如不需要编辑模式，可省略 `-e`。
3. 复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY` 或 `SILICONFLOW_API_KEY`。

## 快速开始

1. 在 Scopus 中导出包含标题和摘要的 CSV 文件。
2. 运行相关性分析命令：
   ```bash
   litrx csv
   ```
   （若无法直接使用 `litrx` 命令，可改用 `python -m litrx csv`）
   如需 PyQt6 图形界面，运行：
   ```bash
   python run_gui.py
   ```
   首次运行可能会自动下载安装所需依赖，请耐心等待片刻。
3. 根据提示选择 API、输入研究主题并提供 CSV 路径，结果将保存在同目录下。

### 首次启动引导
- 第一次打开 GUI 时，会弹出简易向导，提示选择服务商（OpenAI/SiliconFlow）并输入 API Key。
- 勾选“保存配置”后，非敏感配置会写入 `~/.litrx_gui.yaml`，API Key 会保存到系统密钥环（如可用）。

## 配置说明

所有命令会将 `.env` 与通过 `--config` 指定的 JSON/YAML 文件合并成 `DEFAULT_CONFIG`，命令行参数可进一步覆盖默认值。

图形界面提供 **“保存配置”** 按钮，可将当前的 `AI_SERVICE`、`MODEL_NAME`、`API_BASE` 等设置写入 `~/.litrx_gui.yaml`。应用启动时会依次加载 `configs/config.yaml`、该持久化文件与 `.env`，优先级从低到高为 `~/.litrx_gui.yaml` < `.env` < 运行时输入，界面会自动填充保存的偏好。

这些参数的基础默认值定义在 `configs/config.yaml`，如需调整启动时的初始设置，可修改此文件。

## 应用打包与分发（点开即用）

使用仓库自带的 PyInstaller 构建脚本生成可执行应用：

- Windows：运行 `packaging\\build_win.bat`
- macOS：运行 `bash packaging/build_mac.sh`

产物
- Windows：`dist/LitRelevanceAI/LitRelevanceAI.exe`（分发时请连同整个 `dist/LitRelevanceAI` 文件夹一起提供）
- macOS：`dist/LitRelevanceAI.app`

说明
- 应用已打包 `configs/`、`questions_config.json`、`prompts_config.json` 等资源；运行时通过 `litrx.resources.resource_path()` 在开发/打包环境均可正确读取。
- 如需单文件（`--onefile`）也可，但 GUI 首次解包略慢，推荐默认的文件夹结构以获得更流畅的启动体验。

## 高级工具

- **摘要筛选**
  ```bash
  litrx abstract            # 命令行模式
  litrx abstract --gui      # 图形界面模式
  ```
  可在 `questions_config.json` 中管理模式与题目，或在图形界面使用 **“添加模式”** 和 **“编辑问题”** 对话框自定义筛选问题与列名。通过在配置文件或 `.env` 中设置 `ENABLE_VERIFICATION=true`/`false`，或在界面勾选/取消 **“启用验证”**，可切换二次校验。结果表格会为每个问题生成 `<列名>` 和 `<列名>_verified` 两列，后者指示 AI 回答是否得到标题或摘要支持（禁用验证时显示“未验证”）。当启用验证时，日志会在答案后附带 ✔/✖ 标记。
- **PDF 筛选**
  ```bash
  litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
  ```
  JSON 或 YAML 配置文件用于指定研究问题、筛选标准和输出格式。所有题目模板（含 PDF 筛选标准）均在 `questions_config.json` 中管理。图形界面还可选择元数据文件、启用“仅匹配元数据”以提前核对，并在处理完成后打开结果目录。

## 自定义建议

- 在各脚本顶部修改默认模型或温度。
- 编辑 `csv_analyzer.py` 中的提示词或 `questions_config.json` 中的问题以收集不同信息。
- 通过 `.env` 或提供配置文件来设置 API 密钥和其他默认参数。

## 许可协议

本项目基于 [MIT 许可证](LICENSE) 开源。
