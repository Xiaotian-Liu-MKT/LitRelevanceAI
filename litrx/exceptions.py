"""Custom exceptions for LitRelevanceAI.

This module defines specific exception types to provide clear error messages
and better error handling throughout the application.
"""

from __future__ import annotations
from typing import List, Optional


class LitRxError(Exception):
    """Base exception for all LitRelevanceAI errors."""
    pass


class ConfigurationError(LitRxError):
    """Configuration-related errors."""
    pass


class APIKeyMissingError(ConfigurationError):
    """API key is missing or not configured."""

    def __init__(self, service: str = "AI"):
        self.service = service
        message = (
            f"{service} API密钥未配置。\n"
            f"\n"
            f"请执行以下操作之一：\n"
            f"1. 在GUI配置中设置API密钥\n"
            f"2. 在项目根目录创建 .env 文件并添加密钥\n"
            f"3. 设置环境变量\n"
            f"\n"
            f"示例 .env 文件内容：\n"
            f"OPENAI_API_KEY=sk-your-key-here\n"
            f"SILICONFLOW_API_KEY=your-key-here"
        )
        super().__init__(message)


class APIRequestError(LitRxError):
    """AI API request failed."""

    def __init__(self, original_error: Exception, service: str = "AI"):
        self.original_error = original_error
        self.service = service
        message = (
            f"{service} 请求失败: {str(original_error)}\n"
            f"\n"
            f"可能的原因：\n"
            f"1. API密钥无效或已过期\n"
            f"2. 网络连接问题\n"
            f"3. API配额已耗尽\n"
            f"4. API服务暂时不可用\n"
            f"\n"
            f"建议：\n"
            f"- 检查API密钥是否正确\n"
            f"- 检查网络连接\n"
            f"- 查看API服务状态\n"
            f"- 检查账户余额或配额"
        )
        super().__init__(message)


class FileFormatError(LitRxError):
    """File format is invalid or unsupported."""

    def __init__(self, file_path: str, expected_format: Optional[str] = None, details: Optional[str] = None):
        self.file_path = file_path
        self.expected_format = expected_format
        message = f"文件格式错误: {file_path}\n"
        if expected_format:
            message += f"期望格式: {expected_format}\n"
        if details:
            message += f"详细信息: {details}"
        super().__init__(message)


class ColumnNotFoundError(FileFormatError):
    """Required column not found in DataFrame."""

    def __init__(self, column_name: str, available_columns: list):
        self.column_name = column_name
        self.available_columns = available_columns
        message = (
            f"未找到必需的列: {column_name}\n"
            f"\n"
            f"可用列: {', '.join(available_columns)}\n"
            f"\n"
            f"请确保：\n"
            f"1. 输入文件格式正确\n"
            f"2. 列名拼写正确（区分大小写）\n"
            f"3. 文件是从正确的数据源导出的"
        )
        super().__init__(message, expected_format=f"包含 '{column_name}' 列的文件")


class InvalidFileFormatError(FileFormatError):
    """File format is not supported."""

    def __init__(self, file_path: str, supported_formats: Optional[List[str]] = None):
        supported = supported_formats or ['.csv', '.xlsx', '.xls']
        message = (
            f"不支持的文件格式: {file_path}\n"
            f"\n"
            f"支持的格式: {', '.join(supported)}\n"
            f"\n"
            f"请转换文件到支持的格式后重试。"
        )
        super().__init__(message, expected_format=' 或 '.join(supported))


class DataValidationError(LitRxError):
    """Data validation failed."""

    def __init__(self, message: str, row_index: Optional[int] = None):
        self.row_index = row_index
        if row_index is not None:
            full_message = f"数据验证失败 (行 {row_index + 1}): {message}"
        else:
            full_message = f"数据验证失败: {message}"
        super().__init__(full_message)


class TaskCancelledException(LitRxError):
    """Task was cancelled by user."""

    def __init__(self):
        super().__init__("任务已被用户取消")


class ProgressRecoveryError(LitRxError):
    """Failed to recover progress from checkpoint."""

    def __init__(self, checkpoint_path: str, details: Optional[str] = None):
        message = f"无法恢复进度: {checkpoint_path}\n"
        if details:
            message += f"详细信息: {details}\n"
        message += "\n建议: 删除损坏的检查点文件并重新开始。"
        super().__init__(message)


class ModelNotSupportedError(ConfigurationError):
    """AI model is not supported by the current service."""

    def __init__(self, model: str, service: str, supported_models: Optional[List[str]] = None):
        self.model = model
        self.service = service
        message = f"模型 '{model}' 不支持 {service} 服务\n"
        if supported_models:
            message += f"\n支持的模型: {', '.join(supported_models)}"
        super().__init__(message)


class RateLimitError(APIRequestError):
    """API rate limit exceeded."""

    def __init__(self, service: str = "AI", retry_after: Optional[int] = None):
        self.retry_after = retry_after
        message = (
            f"{service} API 速率限制已达到\n"
            f"\n"
            f"建议：\n"
            f"- 减少并发请求数\n"
            f"- 在请求之间添加延迟\n"
        )
        if retry_after:
            message += f"- 等待 {retry_after} 秒后重试\n"
        else:
            message += f"- 稍后重试\n"

        # Create a fake exception for the parent class
        class RateLimitException(Exception):
            pass

        super().__init__(RateLimitException(message), service)
