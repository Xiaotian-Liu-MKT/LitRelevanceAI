"""
Internationalization (i18n) module for LitRx Toolkit.
Provides language support for Chinese and English.
"""
import json
from pathlib import Path
from typing import Dict, Any

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
        "language": "语言:",
        "save_config": "💾 保存配置",
        "prompt_settings": "⚙️ Prompt设置",

        # Tab names
        "csv_tab": "CSV相关性分析",
        "abstract_tab": "摘要筛选",
        "pdf_tab": "PDF筛选",

        # Buttons
        "browse": "浏览",
        "start_analysis": "开始分析",
        "save": "保存",
        "cancel": "取消",
        "reset_defaults": "恢复默认",

        # Messages
        "config_saved": "配置已保存到 {}",
        "prompt_saved": "Prompt设置已保存",
        "save_failed": "保存失败: {}",
        "error": "错误",
        "success": "成功",
        "warning": "警告",
        "confirm": "确认",
        "saved": "已保存",

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

        # PDF Tab specific
        "select_pdf_folder": "选择PDF文件夹:",

        # Error messages
        "error_fill_fields": "请填写研究主题并选择文件",
        "error_select_file": "请先选择文件",
        "error_read_file": "读取文件失败: {}",
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
        "language": "Language:",
        "save_config": "💾 Save Config",
        "prompt_settings": "⚙️ Prompt Settings",

        # Tab names
        "csv_tab": "CSV Relevance Analysis",
        "abstract_tab": "Abstract Screening",
        "pdf_tab": "PDF Screening",

        # Buttons
        "browse": "Browse",
        "start_analysis": "Start Analysis",
        "save": "Save",
        "cancel": "Cancel",
        "reset_defaults": "Reset to Defaults",

        # Messages
        "config_saved": "Configuration saved to {}",
        "prompt_saved": "Prompt settings saved",
        "save_failed": "Save failed: {}",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "confirm": "Confirm",
        "saved": "Saved",

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
        "error_read_file": "Failed to read file: {}",
    }
}

class I18n:
    """Internationalization manager."""

    def __init__(self, default_language: str = "en"):
        """
        Initialize i18n manager.

        Args:
            default_language: Default language code ('zh' or 'en'), defaults to 'en' (English)
        """
        self._current_language = default_language
        self._observers = []

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
                print(f"Error notifying observer: {e}")

# Global i18n instance
_i18n_instance = None

def get_i18n(default_language: str = "en") -> I18n:
    """
    Get the global i18n instance.

    Args:
        default_language: Default language code (used only on first call), defaults to 'en' (English)

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
