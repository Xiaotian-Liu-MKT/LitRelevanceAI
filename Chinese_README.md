# LitRelevanceAI 中文文档

AI 辅助的文献筛选工具，可评估学术论文与研究主题的相关性。项目现已封装为 `litrx` 包，通过统一的命令行接口提供 CSV 相关性分析、摘要筛选和 PDF 筛选功能。

[English README](README.md)

## 功能特点

- **CSV 相关性分析**：`litrx csv` 读取 Scopus 导出的文件，为每篇文章打出 0–100 的相关性分数，并给出解释。图形界面标签页以表格显示结果，可双击查看完整分析并导出表格。
- **摘要快速筛选**：`litrx abstract` 根据 `configs/questions/abstract.yaml` 中的自定义问题进行是/否判定和开放式问题回答。图形界面提供 **“编辑问题”** 对话框可在运行中调整题目、只读日志区输出模型摘要、**“中止任务”** 按钮随时停止处理，并可将结果导出为 CSV 或 Excel。
- **PDF 筛选**：`litrx pdf` 会先将 PDF 转为文本再发送给模型，依据研究问题和筛选标准输出结构化结果。
- **模块化标签界面**：运行 `python -m litrx --gui` 可打开带有 CSV 相关性分析、摘要筛选和 PDF 筛选独立标签页的应用。
- **灵活的模型配置**：可在脚本中自由切换 OpenAI 或 Gemini，并调整温度、模型名称等参数。
- **统一的配置管理**：通过 `.env` 与 JSON/YAML 配置文件合并生成 `DEFAULT_CONFIG`，命令行参数可覆盖默认值。
- **自动保存进度**：中间结果和最终结果都会写入带时间戳的 CSV 或 XLSX 文件，避免进度丢失。

## 安装步骤

1. 安装 Python 3.7 及以上版本。
2. 克隆本仓库并安装包：
   ```bash
   python -m pip install -e .
   ```
   如不需要编辑模式，可省略 `-e`。
3. 复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY` 或 `GEMINI_API_KEY`。

## 快速开始

1. 在 Scopus 中导出包含标题和摘要的 CSV 文件。
2. 运行相关性分析命令：
   ```bash
   litrx csv
   ```
   （若无法直接使用 `litrx` 命令，可改用 `python -m litrx csv`）
   如需图形界面，运行：
   ```bash
   python -m litrx --gui
   ```
3. 根据提示选择 API、输入研究主题并提供 CSV 路径，结果将保存在同目录下。

## 配置说明

所有命令会将 `.env` 与通过 `--config` 指定的 JSON/YAML 文件合并成 `DEFAULT_CONFIG`，命令行参数可进一步覆盖默认值。

## 高级工具

- **摘要筛选**
  ```bash
  litrx abstract            # 命令行模式
  litrx abstract --gui      # 图形界面模式
  ```
  修改 `configs/questions/` 下的文件可自定义筛选问题与列名。
- **PDF 筛选**
  ```bash
  litrx pdf --config path/to/config.yml --pdf-folder path/to/pdfs
  ```
  JSON 或 YAML 配置文件用于指定研究问题、筛选标准和输出格式。

## 自定义建议

- 在各脚本顶部修改默认模型或温度。
- 编辑 `csv_analyzer.py` 中的提示词或 `configs/questions/` 中的问题以收集不同信息。
- 通过 `.env` 或提供配置文件来设置 API 密钥和其他默认参数。

## 许可协议

本项目基于 [MIT 许可证](LICENSE) 开源。
