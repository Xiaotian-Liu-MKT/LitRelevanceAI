# LitRelevanceAI 中文文档

AI 辅助的文献筛选工具，可评估学术论文与研究主题的相关性。项目包含用于处理 Scopus CSV 导出的脚本、可配置的摘要与 PDF 筛选器，并支持 OpenAI 与 Gemini 模型。

[English README](README.md)

## 功能特点

- **CSV 相关性分析**：`LitRelevance.py` 读取 Scopus 导出的文件，为每篇文章打出 0–100 的相关性分数，并给出解释。
- **摘要快速筛选**：`abstractScreener.py` 根据 `questions_config.json` 中的自定义问题进行是/否判定和开放式问题回答，可在命令行或 `--gui` 图形界面运行。
- **PDF 筛选**：`pdfScreener.py` 将整篇论文发送给模型，依据研究问题和筛选标准输出结构化结果。
- **灵活的模型配置**：可在脚本中自由切换 OpenAI 或 Gemini，并调整温度、模型名称等参数。
- **自动保存进度**：中间结果和最终结果都会写入带时间戳的 CSV 或 XLSX 文件，避免进度丢失。

## 安装步骤

1. 安装 Python 3.7 及以上版本。
2. 克隆本仓库并安装依赖：
   ```bash
   pip install pandas openai google-generativeai litellm tqdm openpyxl
   ```
3. 复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY` 或 `GEMINI_API_KEY`。

## 快速开始

1. 在 Scopus 中导出包含标题和摘要的 CSV 文件。
2. 运行相关性分析脚本：
   ```bash
   python LitRelevance.py
   ```
3. 根据提示选择 API、输入研究主题并提供 CSV 路径，结果将保存在同目录下。

## 高级工具

- **摘要筛选**
  ```bash
  python abstractScreener.py            # 命令行模式
  python abstractScreener.py --gui      # 图形界面模式
  ```
  修改 `questions_config.json` 可自定义筛选问题与列名。
- **PDF 筛选**
  ```bash
  python pdfScreener.py --config path/to/config.json --pdf-folder path/to/pdfs
  ```
  JSON 配置文件用于指定研究问题、筛选标准和输出格式。

## 自定义建议

- 在各脚本顶部修改默认模型或温度。
- 编辑 `LitRelevance.py` 的提示词或 `questions_config.json` 中的问题以收集不同信息。
- 通过 `.env` 或直接修改脚本设置 API 密钥。

## 许可协议

本项目基于 [MIT 许可证](LICENSE) 开源。
