"""
Internationalization (i18n) module for LitRx Toolkit.
Provides language support for Chinese and English.
"""
import json
from pathlib import Path
from typing import Any, Callable, Dict, List

from .logging_config import get_logger

logger = get_logger(__name__)

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh": {
        # Window titles
        "app_title": "LitRx Toolkit - AI文献分析工具",
        "title_label": "LitRx Toolkit",
        "subtitle_label": "AI驱动的文献综述助手",

        # Configuration section
        "config_settings": " 配置设置 ",
        "ai_service": "AI服务:",
        "api_key": "API密钥:",
        "model": "模型:",
        "ai_assistant_model": "AI助手模型:",
        "ai_assistant_model_hint": "(可选，留空则使用主模型)",
        "language": "语言:",
        "save_config": "💾 保存配置",
        "prompt_settings": "⚙️ Prompt设置",
        "view_logs": "📋 查看日志",

        # Tab names
        "csv_tab": "CSV相关性分析",
        "abstract_tab": "摘要筛选",
        "matrix_tab": "文献矩阵",

        # Buttons
        "browse": "浏览",
        "start_analysis": "开始分析",
        "generate_config": "🧠 生成配置",
        "generate_dimensions": "🧠 生成维度",
        "apply_changes": "✅ 应用",
        "apply_selected": "✅ 应用选中",
        "overwrite": "⚠️ 覆盖",
        "rename": "✏️ 重命名",
        "save": "保存",
        "cancel": "取消",
        "reset_defaults": "恢复默认",

        # Messages
        "config_saved": "配置已保存到 {}",
        "prompt_saved": "Prompt设置已保存",
        "save_failed": "保存失败: {}",
        "api_keys_secured": "API密钥已安全保存到系统密钥环",
        "error": "错误",
        "success": "成功",
        "warning": "警告",
        "confirm": "确认",
        "saved": "已保存",
        "saved_with_backup": "已保存（备份: {path}）",

        # Prompt settings
        "prompt_settings_title": "Prompt设置",
        "csv_analysis": "CSV相关性分析",
        "abstract_screening": "摘要筛选",
        "pdf_screening": "PDF筛选",
        "reset_prompt_confirm": "确定要恢复默认Prompt设置吗？",
        "reset_success": "已恢复默认设置",
        "reset_failed": "恢复失败: {}",

        # CSV Tab
        "csv_input_file": "输入CSV文件:",
        "csv_research_topic": "研究主题:",
        "csv_output_folder": "输出文件夹:",
        "csv_placeholder_topic": "请输入您的研究主题...",

        # Abstract Tab
        "abstract_input_file": "输入Excel文件:",
        "abstract_screening_mode": "筛选模式:",
        "abstract_output_folder": "输出文件夹:",
        "abstract_enable_verification": "启用验证",

        # PDF Tab
        "pdf_input_folder": "PDF文件夹:",
        "pdf_screening_mode": "筛选模式:",
        "pdf_output_folder": "输出文件夹:",

        # Status
        "ready": "就绪",
        "processing": "处理中...",
        "completed": "已完成",
        "failed": "失败",

        # Language names
        "lang_chinese": "中文",
        "lang_english": "English",

        # Common UI elements
        "browse_file": "浏览",
        "start_analysis_btn": "开始分析",
        "start_screening_btn": "开始筛选",
        "stop_task": "中止任务",
        "export_results": "导出结果",
        "export_csv": "导出 CSV",
        "export_excel": "导出 Excel",
        "edit_questions": "编辑问题",
        "add_mode": "添加模式",
        "log_label": "日志:",
        "preview_label": "预览:",
        "describe_your_needs": "请描述您的需求:",
        "please_enter_description": "请先输入需求描述",
        "generating": "正在生成...",
        "generation_success": "生成成功",
        "generation_failed": "生成失败",
        "ai_mode_assistant_title": "AI 助手（创建模式）",
        "ai_mode_guide": "请用自然语言描述您的筛选需求：研究领域、需要判断的要点（是/否）、需要提取的信息（开放题）。",
        "ai_matrix_assistant_title": "AI 助手（生成维度）",
        "ai_dimension_guide": "请描述需要在矩阵中提取的信息：题型、候选选项、评分尺度等。",
        "choose_action": "发现重名模式，请选择处理方式：",
        "conflict_mode_key": "模式键名已存在：{key}",
        "conflict_preset_name": "Preset 名称已存在：{name}",

        # CSV Tab specific
        "research_topic_label": "研究主题:",
        "select_csv_file": "选择CSV文件:",
        "table_title": "标题",
        "table_score": "相关度",
        "table_analysis": "分析",

        # Abstract Tab specific
        "select_file_label": "选择CSV/XLSX文件:",
        "screening_mode_label": "筛选模式:",
        "enable_verification": "启用验证",
        "verification_tooltip": "启用AI验证答案（会使处理时间加倍，但提高准确性）",
        "verification_hint": "提示: 关闭验证可以更快地进行初步筛选",
        "column_selection_optional": "列名选择(可选):",
        "title_column": "标题列:",
        "abstract_column": "摘要列:",
        "processing_options": "处理选项",
        "concurrent_workers": "并发数:",
        "workers_tooltip": "并发线程数（推荐3-10，支持高速率的API可设置更高）",
        "api_delay_label": "API延迟 (秒):",
        "delay_tooltip": "API请求之间的延迟秒数（如果API支持高速率限制可减少）",
        "performance_info": "更高的并发数 + 更低的延迟 = 更快的处理速度（请检查API速率限制）",
        "start_screening": "开始筛选",
        "view_statistics": "查看统计",
        "results_preview": "结果预览",
        "no_data": "暂无数据",
        "processing_articles": "开始处理 {count} 篇文献...",
        "concurrent_verification": "并发数: {workers}, 验证: {verification}",
        "completed_status": "已完成: {completed}/{total}",
        "task_stopped": "任务已中止",
        "complete_saved": "完成! 结果已保存到: {path}",
        "total_count": "总计: {count} 篇",
        "column_recognition_failed": "列识别失败",
        "select_column": "选择列",
        "please_select_columns": "请选择标题列和摘要列:",
        "hint": "提示",
        "please_complete_screening": "请先完成筛选任务",
        "screening_statistics": "筛选统计",
        "statistics_summary": "筛选统计摘要 - 共 {count} 篇文献",
        "yes_no_questions_stats": "是/否问题统计",
        "question": "问题",
        "open_questions_stats": "开放问题统计",
        "close": "关闭",
        "csv_exported": "CSV 已导出",
        "excel_exported": "Excel 已导出",
        "new_mode": "新模式",
        "enter_mode_name": "请输入模式名称:",
        "mode_exists": "模式已存在",
        "description": "描述",
        "enter_description": "请输入模式描述:",
        "setup_question": "设置问题",
        "key_cannot_empty": "Key 不能为空",
        "question_cannot_empty": "Question 不能为空",
        "column_name_cannot_empty": "Column Name 不能为空",
        "please_select_question": "请先选择一个问题",
        "add": "添加",
        "edit": "编辑",
        "delete": "删除",
        "open_questions": "开放问题",
        "yes_no_questions": "是/否问题",
        "please_select_mode": "请先选择一个模式后再保存。",
        "save_question_config_failed": "保存问题配置失败: {error}",
        "question_config_saved": "问题配置已保存。",
        "cannot_read_file": "无法读取文件: {error}",
        "yes": "是",
        "no": "否",
        "manual_select_columns": "是否手动选择列?",
        "ok": "确定",
        "display_rows_cols": "显示 {displayed}/{total} 行, {display_cols}/{total_cols} 列",
        "entry_log": "条目 {index}: {summary}",

        # PDF Tab specific
        "select_pdf_folder": "选择PDF文件夹:",

        # Error messages
        "error_fill_fields": "请填写研究主题并选择文件",
        "error_select_file": "请先选择文件",
        "error_read_file": "读取文件失败: {error}",
        "error_no_results": "没有可导出的结果",
        "error_analysis": "错误 {error}",

        # AI Client error messages
        "error_openai_key_missing": "OpenAI API密钥未配置。请在环境变量、.env文件或配置文件中设置OPENAI_API_KEY。",
        "error_siliconflow_key_missing": "SiliconFlow API密钥未配置。请在环境变量、.env文件或配置文件中设置SILICONFLOW_API_KEY。",
        "error_invalid_service": "无效的AI服务 '{service}'。必须是 'openai' 或 'siliconflow'。",
        "error_ai_request_failed": "AI 请求失败: {error}",

        # Success messages
        "results_exported": "结果已导出",

        # File types
        "csv_files": "CSV 文件",

        # Matrix Analysis Prompts
        "matrix_answer_instruction": "请回答'是'、'否'或'不确定'",
        "matrix_select_instruction": "请从以下选项中选择一个：",
        "matrix_multi_select_instruction": "请从以下选项中选择所有适用的（多选），用分号分隔：",
        "matrix_number_instruction": "请回答具体数值",
        "matrix_unit_instruction": "（单位：{unit}）",
        "matrix_na_instruction": "，如无法确定请回答'N/A'",
        "matrix_rating_instruction": "请给出1-{scale}的评分（{scale_description}）",
        "matrix_list_instruction": "请列出多个条目，用'{separator}'分隔",
        "matrix_read_instruction": "请仔细阅读以下文献，并根据要求进行分析。",
        "matrix_format_instruction": "请严格按照以下JSON格式回答所有问题（使用中文）：",
        "matrix_note1": "1. 请确保输出是有效的JSON格式",
        "matrix_note2": "2. 所有问题都必须回答，如果文中未提及或无法确定，请回答\"N/A\"或\"不确定\"",
        "matrix_note3": "3. 对于选择题，请严格从给定选项中选择",
        "matrix_note4": "4. 对于数值题，只回答数字或\"N/A\"",
        "matrix_note5": "5. 保持回答简洁但完整",

        # Matrix Tab UI
        "matrix_config": "矩阵配置",
        "analysis_scheme": "分析方案",
        "select_scheme": "选择方案...",
        "new_scheme": "+ 新建方案...",
        "current_dimensions": "📊 当前方案包含 {count} 个分析维度",
        "edit_dimensions": "编辑",
        "ai_generate_dims": "AI",
        "more_options": "⋮",
        "import_config": "导入配置",
        "export_config": "导出配置",
        "save_preset": "另存为 Preset",
        "reset_default": "重置默认",
        "data_input": "数据输入",
        "pdf_folder_required": "PDF文件夹*",
        "metadata_file_optional": "元数据文件（可选）",
        "output_file_required": "输出文件*",
        "stop": "停止",
        "processing_log": "处理日志",

        # Preset Management
        "scheme_name": "方案名称",
        "scheme_description": "方案描述（可选）",
        "enter_scheme_name": "请输入方案名称",
        "create_new_scheme": "新建分析方案",
        "duplicate_scheme": "复制当前方案",
        "rename_scheme": "重命名方案",
        "delete_scheme": "删除方案",
        "load_from_file": "从文件加载...",
        "save_to_file": "保存到文件...",
        "restore_default_template": "恢复默认模板",
        "scheme_saved": "方案已保存",
        "scheme_loaded": "方案已加载",
        "scheme_deleted": "方案已删除",
        "scheme_exists": "方案名称已存在",
        "scheme_name_empty": "方案名称不能为空",
        "cannot_delete_default": "不能删除默认方案",
        "confirm_delete_scheme": "确定要删除方案 '{name}' 吗？此操作无法撤销。",
        "enter_new_name": "请输入新名称",
        "scheme_auto_saved": "✓ 方案已自动保存",
        "default_scheme_name": "默认方案",
    },
    "en": {
        # Window titles
        "app_title": "LitRx Toolkit - AI Literature Analysis Tool",
        "title_label": "LitRx Toolkit",
        "subtitle_label": "AI-powered Literature Review Assistant",

        # Configuration section
        "config_settings": " Configuration Settings ",
        "ai_service": "AI Service:",
        "api_key": "API Key:",
        "model": "Model:",
        "ai_assistant_model": "AI Assistant Model:",
        "ai_assistant_model_hint": "(optional, uses main model if empty)",
        "language": "Language:",
        "save_config": "💾 Save Config",
        "prompt_settings": "⚙️ Prompt Settings",
        "view_logs": "📋 View Logs",

        # Tab names
        "csv_tab": "CSV Relevance Analysis",
        "abstract_tab": "Abstract Screening",
        "matrix_tab": "Literature Matrix",

        # Buttons
        "browse": "Browse",
        "start_analysis": "Start Analysis",
        "generate_config": "🧠 Generate Config",
        "generate_dimensions": "🧠 Generate Dimensions",
        "apply_changes": "✅ Apply",
        "apply_selected": "✅ Apply Selected",
        "overwrite": "⚠️ Overwrite",
        "rename": "✏️ Rename",
        "save": "Save",
        "cancel": "Cancel",
        "reset_defaults": "Reset to Defaults",

        # Messages
        "config_saved": "Configuration saved to {}",
        "prompt_saved": "Prompt settings saved",
        "save_failed": "Save failed: {}",
        "api_keys_secured": "API keys securely saved to system keyring",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "confirm": "Confirm",
        "saved": "Saved",
        "saved_with_backup": "Saved with backup at {path}",

        # Prompt settings
        "prompt_settings_title": "Prompt Settings",
        "csv_analysis": "CSV Relevance Analysis",
        "abstract_screening": "Abstract Screening",
        "pdf_screening": "PDF Screening",
        "reset_prompt_confirm": "Are you sure you want to reset to default Prompt settings?",
        "reset_success": "Reset to default settings successfully",
        "reset_failed": "Reset failed: {}",

        # CSV Tab
        "csv_input_file": "Input CSV File:",
        "csv_research_topic": "Research Topic:",
        "csv_output_folder": "Output Folder:",
        "csv_placeholder_topic": "Enter your research topic...",

        # Abstract Tab
        "abstract_input_file": "Input Excel File:",
        "abstract_screening_mode": "Screening Mode:",
        "abstract_output_folder": "Output Folder:",
        "abstract_enable_verification": "Enable Verification",
        "select_file_label": "Select CSV/XLSX File:",
        "screening_mode_label": "Screening Mode:",
        "enable_verification": "Enable Verification",
        "verification_tooltip": "Enable AI verification of answers (doubles processing time but improves accuracy)",
        "verification_hint": "Tip: Disable verification for faster initial screening",
        "column_selection_optional": "Column Selection (Optional):",
        "title_column": "Title Column:",
        "abstract_column": "Abstract Column:",
        "processing_options": "Processing Options",
        "concurrent_workers": "Concurrent Workers:",
        "workers_tooltip": "Number of concurrent threads (3-10 recommended, higher for faster APIs)",
        "api_delay_label": "API Delay (s):",
        "delay_tooltip": "Delay between API requests in seconds (reduce if API supports high rate limits)",
        "performance_info": "Higher workers + lower delay = faster processing (check API rate limits)",
        "start_screening": "Start Screening",
        "view_statistics": "View Statistics",
        "results_preview": "Results Preview",
        "no_data": "No Data",
        "processing_articles": "Processing {count} articles...",
        "concurrent_verification": "Workers: {workers}, Verification: {verification}",
        "completed_status": "Completed: {completed}/{total}",
        "task_stopped": "Task Stopped",
        "complete_saved": "Complete! Results saved to: {path}",
        "total_count": "Total: {count} articles",
        "column_recognition_failed": "Column Recognition Failed",
        "select_column": "Select Column",
        "please_select_columns": "Please select title and abstract columns:",
        "hint": "Hint",
        "please_complete_screening": "Please complete screening task first",
        "screening_statistics": "Screening Statistics",
        "statistics_summary": "Screening Statistics Summary - {count} articles total",
        "yes_no_questions_stats": "Yes/No Questions Statistics",
        "question": "Question",
        "open_questions_stats": "Open Questions Statistics",
        "close": "Close",
        "csv_exported": "CSV Exported",
        "excel_exported": "Excel Exported",
        "new_mode": "New Mode",
        "enter_mode_name": "Please enter mode name:",
        "mode_exists": "Mode already exists",
        "description": "Description",
        "enter_description": "Please enter description:",
        "setup_question": "Setup Question",
        "key_cannot_empty": "Key cannot be empty",
        "question_cannot_empty": "Question cannot be empty",
        "column_name_cannot_empty": "Column Name cannot be empty",
        "please_select_question": "Please select a question first",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "open_questions": "Open Questions",
        "yes_no_questions": "Yes/No Questions",
        "please_select_mode": "Please select a mode before saving.",
        "save_question_config_failed": "Failed to save question config: {error}",
        "question_config_saved": "Question configuration saved.",
        "cannot_read_file": "Cannot read file: {error}",
        "yes": "Yes",
        "no": "No",
        "manual_select_columns": "Manually select columns?",
        "ok": "OK",
        "display_rows_cols": "Displaying {displayed}/{total} rows, {display_cols}/{total_cols} columns",
        "entry_log": "Entry {index}: {summary}",

        # PDF Tab
        "pdf_input_folder": "PDF Folder:",
        "pdf_screening_mode": "Screening Mode:",
        "pdf_output_folder": "Output Folder:",

        # Status
        "ready": "Ready",
        "processing": "Processing...",
        "completed": "Completed",
        "failed": "Failed",

        # Language names
        "lang_chinese": "中文",
        "lang_english": "English",

        # Common UI elements
        "browse_file": "Browse",
        "start_analysis_btn": "Start Analysis",
        "start_screening_btn": "Start Screening",
        "stop_task": "Stop Task",
        "export_results": "Export Results",
        "export_csv": "Export CSV",
        "export_excel": "Export Excel",
        "edit_questions": "Edit Questions",
        "add_mode": "Add Mode",
        "log_label": "Log:",
        "preview_label": "Preview:",
        "describe_your_needs": "Describe your needs:",
        "please_enter_description": "Please enter a description first",
        "generating": "Generating...",
        "generation_success": "Generation succeeded",
        "generation_failed": "Generation failed",
        "ai_mode_assistant_title": "AI Assistant (Create Mode)",
        "ai_mode_guide": "Describe your screening needs: domain, binary checks (yes/no), and extracted info (open questions).",
        "ai_matrix_assistant_title": "AI Assistant (Generate Dimensions)",
        "ai_dimension_guide": "Describe the dimensions to extract: types, candidate options, rating scales, etc.",
        "choose_action": "Found duplicate mode key. Choose an action:",
        "conflict_mode_key": "Mode key already exists: {key}",
        "conflict_preset_name": "Preset name already exists: {name}",

        # CSV Tab specific
        "research_topic_label": "Research Topic:",
        "select_csv_file": "Select CSV File:",
        "table_title": "Title",
        "table_score": "Relevance",
        "table_analysis": "Analysis",

        # Abstract Tab specific
        "select_file_label": "Select CSV/XLSX File:",
        "screening_mode_label": "Screening Mode:",
        "enable_verification": "Enable Verification",

        # PDF Tab specific
        "select_pdf_folder": "Select PDF Folder:",

        # Error messages
        "error_fill_fields": "Please enter research topic and select a file",
        "error_select_file": "Please select a file first",
        "error_read_file": "Failed to read file: {error}",
        "error_no_results": "No results to export",
        "error_analysis": "Error {error}",

        # AI Client error messages
        "error_openai_key_missing": "OpenAI API key is not configured. Please set OPENAI_API_KEY in environment variables, .env file, or config file.",
        "error_siliconflow_key_missing": "SiliconFlow API key is not configured. Please set SILICONFLOW_API_KEY in environment variables, .env file, or config file.",
        "error_invalid_service": "Invalid AI service '{service}'. Must be 'openai' or 'siliconflow'.",
        "error_ai_request_failed": "AI request failed: {error}",

        # Success messages
        "results_exported": "Results exported successfully",

        # File types
        "csv_files": "CSV Files",

        # Matrix Analysis Prompts
        "matrix_answer_instruction": "Please answer 'Yes', 'No', or 'Uncertain'",
        "matrix_select_instruction": "Please select one from the following options:",
        "matrix_multi_select_instruction": "Please select all applicable options (multiple choice), separated by semicolons:",
        "matrix_number_instruction": "Please provide a specific numerical value",
        "matrix_unit_instruction": "(Unit: {unit})",
        "matrix_na_instruction": ", if uncertain, answer 'N/A'",
        "matrix_rating_instruction": "Please provide a rating from 1 to {scale} ({scale_description})",
        "matrix_list_instruction": "Please list multiple items, separated by '{separator}'",
        "matrix_read_instruction": "Please carefully read the following literature and analyze it as required.",
        "matrix_format_instruction": "Please strictly answer all questions in the following JSON format:",
        "matrix_note1": "1. Ensure the output is valid JSON format",
        "matrix_note2": "2. All questions must be answered; if not mentioned or uncertain, answer \"N/A\" or \"Uncertain\"",
        "matrix_note3": "3. For multiple choice, strictly select from the given options",
        "matrix_note4": "4. For numerical values, only answer numbers or \"N/A\"",
        "matrix_note5": "5. Keep answers concise but complete",

        # Matrix Tab UI
        "matrix_config": "Matrix Configuration",
        "analysis_scheme": "Analysis Scheme",
        "select_scheme": "Select scheme...",
        "new_scheme": "+ New scheme...",
        "current_dimensions": "📊 Current scheme contains {count} analysis dimensions",
        "edit_dimensions": "Edit",
        "ai_generate_dims": "AI",
        "more_options": "⋮",
        "import_config": "Import Config",
        "export_config": "Export Config",
        "save_preset": "Save as Preset",
        "reset_default": "Reset Default",
        "data_input": "Data Input",
        "pdf_folder_required": "PDF Folder*",
        "metadata_file_optional": "Metadata File (Optional)",
        "output_file_required": "Output File*",
        "stop": "Stop",
        "processing_log": "Processing Log",

        # Preset Management
        "scheme_name": "Scheme Name",
        "scheme_description": "Scheme Description (Optional)",
        "enter_scheme_name": "Please enter scheme name",
        "create_new_scheme": "Create New Scheme",
        "duplicate_scheme": "Duplicate Current Scheme",
        "rename_scheme": "Rename Scheme",
        "delete_scheme": "Delete Scheme",
        "load_from_file": "Load from file...",
        "save_to_file": "Save to file...",
        "restore_default_template": "Restore Default Template",
        "scheme_saved": "Scheme saved",
        "scheme_loaded": "Scheme loaded",
        "scheme_deleted": "Scheme deleted",
        "scheme_exists": "Scheme name already exists",
        "scheme_name_empty": "Scheme name cannot be empty",
        "cannot_delete_default": "Cannot delete default scheme",
        "confirm_delete_scheme": "Are you sure you want to delete scheme '{name}'? This action cannot be undone.",
        "enter_new_name": "Please enter new name",
        "scheme_auto_saved": "✓ Scheme auto-saved",
        "default_scheme_name": "Default Scheme",
    }
}

class I18n:
    """Internationalization manager."""

    def __init__(self, default_language: str = "en"):
        """
        Initialize i18n manager.

        Args:
            default_language: Default language code ('zh' or 'en')
        """
        self._current_language = default_language
        self._observers: List[Callable[[], None]] = []

    @property
    def current_language(self) -> str:
        """Get current language code."""
        return self._current_language

    @current_language.setter
    def current_language(self, lang: str) -> None:
        """
        Set current language and notify observers.

        Args:
            lang: Language code ('zh' or 'en')
        """
        if lang not in TRANSLATIONS:
            raise ValueError(f"Unsupported language: {lang}")

        self._current_language = lang
        self._notify_observers()

    def get(self, key: str, **kwargs) -> str:
        """
        Get translated text for the given key.

        Args:
            key: Translation key
            **kwargs: Format parameters for the translation string

        Returns:
            Translated text
        """
        text = TRANSLATIONS.get(self._current_language, {}).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def add_observer(self, callback) -> None:
        """
        Add an observer to be notified when language changes.

        Args:
            callback: Function to call when language changes
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback) -> None:
        """
        Remove an observer.

        Args:
            callback: Function to remove from observers
        """
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notify all observers that language has changed."""
        for callback in self._observers:
            try:
                callback()
            except Exception as e:
                # 使用 logger 而不是 print，包含完整堆栈跟踪
                callback_name = getattr(callback, '__name__', repr(callback))
                logger.error(
                    f"Observer callback failed: {callback_name}",
                    exc_info=True  # 包含完整堆栈跟踪
                )

# Global i18n instance
_i18n_instance = None

def get_i18n(default_language: str = "en") -> I18n:
    """
    Get the global i18n instance.

    Args:
        default_language: Default language code (used only on first call)

    Returns:
        Global I18n instance
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n(default_language)
    return _i18n_instance

def t(key: str, **kwargs) -> str:
    """
    Shorthand for translating a key.

    Args:
        key: Translation key
        **kwargs: Format parameters

    Returns:
        Translated text
    """
    return get_i18n().get(key, **kwargs)
