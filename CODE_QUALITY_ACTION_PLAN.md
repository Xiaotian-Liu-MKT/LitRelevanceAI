# 代码质量改进行动计划

**版本**: 1.0
**日期**: 2025-11-19
**基于**: 项目经理代码审查报告
**目标**: 系统性提升代码质量、安全性和可维护性

---

## 📊 执行摘要

**发现问题**: 共计 **30+** 个问题
- **严重 (CRITICAL)**: 4个
- **高优先级 (HIGH)**: 7个
- **中等优先级 (MEDIUM)**: 11个
- **低优先级 (LOW)**: 8个

**预计工作量**: 4-6周
**测试覆盖率目标**: 从 15% → 85%
**代码质量目标**: 从 2.3/5 → 4.2/5

---

## 🚨 第一阶段：紧急修复（Week 1-2）

### 1.1 异常处理系统性重构 (CRITICAL)

**问题描述**:
- 大量使用泛化 `Exception` 捕获
- 缺少异常链（`from e`）
- 库代码中使用 `sys.exit()`

**影响范围**:
- `litrx/csv_analyzer.py:113-114, 149-150`
- `litrx/abstract_screener.py:126-137`
- `litrx/ai_client.py:125-149`

#### 📝 详细修改方案

**Step 1: 创建异常层次结构（如果还没有）**

```python
# litrx/exceptions.py - 确保包含以下异常类

class LitRxError(Exception):
    """Base exception for all LitRx errors."""
    pass

class FileProcessingError(LitRxError):
    """Errors related to file I/O and processing."""
    pass

class APIError(LitRxError):
    """Errors related to AI API calls."""
    pass

class ConfigurationError(LitRxError):
    """Errors related to configuration."""
    def __init__(self, message: str, help_text: str = None):
        super().__init__(message)
        self.help_text = help_text

class ValidationError(LitRxError):
    """Errors related to data validation."""
    pass
```

**Step 2: 修改 csv_analyzer.py**

```python
# 修改前 (litrx/csv_analyzer.py:113-114)
except Exception as e:
    raise Exception(f"Failed to read CSV file: {str(e)}")

# ✅ 修改后
from .exceptions import FileProcessingError

except FileNotFoundError as e:
    raise FileProcessingError(
        f"CSV文件未找到: {file_path}"
    ) from e
except pd.errors.ParserError as e:
    raise FileProcessingError(
        f"CSV格式错误，请检查文件格式。错误详情: {str(e)}"
    ) from e
except pd.errors.EmptyDataError as e:
    raise FileProcessingError(
        f"CSV文件为空: {file_path}"
    ) from e
except Exception as e:
    logger.error(f"读取CSV时发生未预期错误: {e}", exc_info=True)
    raise FileProcessingError(
        f"无法读取CSV文件: {str(e)}"
    ) from e
```

**Step 3: 修改 abstract_screener.py 移除 sys.exit()**

```python
# 修改前 (litrx/abstract_screener.py:126-137)
def get_file_path_from_config(config):
    file_path = config['INPUT_FILE_PATH']
    if not file_path or file_path == 'your_input_file.xlsx':
        logger.error("错误：输入文件路径未在CONFIG中正确配置。")
        sys.exit(1)  # ❌ 不要在库代码中退出程序

# ✅ 修改后
from .exceptions import ConfigurationError

def get_file_path_from_config(config):
    file_path = config.get('INPUT_FILE_PATH', '')

    if not file_path or file_path == 'your_input_file.xlsx':
        raise ConfigurationError(
            "输入文件路径未配置",
            help_text=(
                "请通过以下方式之一配置 INPUT_FILE_PATH：\n"
                "1. 在GUI中选择文件\n"
                "2. 在 configs/config.yaml 中设置\n"
                "3. 在 .env 文件中添加：INPUT_FILE_PATH=/path/to/file.csv\n\n"
                "示例配置：\n"
                "INPUT_FILE_PATH: /home/user/papers.csv"
            )
        )

    return file_path
```

**Step 4: 改进 ai_client.py 的异常处理**

```python
# litrx/ai_client.py:125-149

# 修改前：复杂的异常重试逻辑
except Exception as e:
    msg = str(e)
    if "param":  # ❌ 这个条件总是True
        pass
    if ("temperature" in kwargs) and (...):
        # 重试逻辑

# ✅ 修改后
from .exceptions import APIError

except Exception as e:
    error_msg = str(e).lower()

    # 特定处理：temperature参数不被支持
    if "temperature" in kwargs and (
        "unsupported" in error_msg or
        "param" in error_msg and "temperature" in error_msg
    ):
        logger.warning(
            f"Model {self.model} rejected 'temperature' parameter, retrying without it"
        )
        try:
            retry_kwargs = dict(sanitized)
            retry_kwargs.pop("temperature", None)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=self.config.get("AI_TIMEOUT_SECONDS", 60),
                **retry_kwargs
            )
            logger.info("Retry succeeded without temperature parameter")
            return response.model_dump()
        except Exception as e2:
            logger.error(f"AI request failed after retry: {e2}", exc_info=True)
            raise APIError(
                f"AI请求失败，即使重试也失败了。错误: {str(e2)}"
            ) from e2

    # 其他错误直接抛出
    logger.error(f"AI request failed: {e}", exc_info=True)
    raise APIError(
        f"AI请求失败: {str(e)}\n\n"
        f"模型: {self.model}\n"
        f"请检查API密钥和网络连接"
    ) from e
```

**Step 5: GUI异常处理**

```python
# 在所有GUI标签页的主操作方法中添加顶层异常处理

# 示例: litrx/gui/tabs_qt/csv_tab.py
def start_analysis(self):
    """开始CSV分析（在后台线程中）"""
    try:
        # 验证输入
        if not self.df_file_path:
            raise ValidationError("请先选择CSV文件")

        # 启动后台任务
        self._start_background_analysis()

    except ConfigurationError as e:
        QMessageBox.critical(
            self,
            "配置错误",
            f"{str(e)}\n\n{e.help_text if hasattr(e, 'help_text') else ''}"
        )
    except ValidationError as e:
        QMessageBox.warning(self, "验证失败", str(e))
    except Exception as e:
        logger.error(f"启动分析失败: {e}", exc_info=True)
        QMessageBox.critical(
            self,
            "未知错误",
            f"启动分析时发生错误:\n{str(e)}\n\n"
            f"请查看日志文件获取详细信息：\n"
            f"~/.litrx/logs/litrx.log"
        )
```

**测试清单**:
```bash
# 测试各种异常路径
pytest tests/test_exceptions.py -v

# 测试点：
# 1. FileNotFoundError → FileProcessingError
# 2. 配置缺失 → ConfigurationError（带help_text）
# 3. API错误 → APIError
# 4. sys.exit不再被调用
# 5. GUI显示友好错误消息
```

---

### 1.2 API密钥安全过滤 (CRITICAL)

**问题描述**:
- 日志可能包含API密钥
- 错误traceback可能暴露敏感信息
- 配置打印没有脱敏

**影响范围**:
- `litrx/ai_client.py:40-48`
- 所有使用logger的地方

#### 📝 详细修改方案

**Step 1: 创建安全日志工具**

```python
# litrx/security_utils.py (新建文件)

"""Security utilities for handling sensitive data."""

import re
from typing import Dict, Any

class SecureLogger:
    """工具类：安全地记录包含敏感信息的数据"""

    # 敏感字段列表
    SENSITIVE_KEYS = {
        'OPENAI_API_KEY',
        'SILICONFLOW_API_KEY',
        'GEMINI_API_KEY',
        'API_KEY',
        'api_key',
        'password',
        'secret',
        'token',
        'authorization'
    }

    @staticmethod
    def sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """创建配置的安全副本，隐藏敏感信息

        Args:
            config: 原始配置字典

        Returns:
            脱敏后的配置字典副本
        """
        safe_config = {}

        for key, value in config.items():
            if key in SecureLogger.SENSITIVE_KEYS:
                if value and isinstance(value, str):
                    # 保留前8个字符，其余用*替换
                    safe_config[key] = value[:8] + "***" if len(value) > 8 else "***"
                else:
                    safe_config[key] = "***"
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                safe_config[key] = SecureLogger.sanitize_config(value)
            else:
                safe_config[key] = value

        return safe_config

    @staticmethod
    def sanitize_string(text: str) -> str:
        """从字符串中移除可能的API密钥

        Args:
            text: 原始文本

        Returns:
            脱敏后的文本
        """
        # 匹配常见的API密钥格式
        patterns = [
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI格式
            r'[a-f0-9]{32}',         # 通用32位hex
            r'Bearer\s+[^\s]+',      # Bearer token
        ]

        result = text
        for pattern in patterns:
            result = re.sub(pattern, '***REDACTED***', result)

        return result

    @staticmethod
    def sanitize_error(error: Exception) -> str:
        """从异常消息中移除敏感信息

        Args:
            error: 异常对象

        Returns:
            脱敏后的错误消息
        """
        return SecureLogger.sanitize_string(str(error))
```

**Step 2: 修改 ai_client.py 使用安全日志**

```python
# litrx/ai_client.py

from .security_utils import SecureLogger
from .logging_config import get_logger

logger = get_logger(__name__)

class AIClient:
    def __init__(self, config: Dict[str, Any]) -> None:
        service = config.get("AI_SERVICE", "openai")
        model = config.get("MODEL_NAME", "gpt-4o")

        # ✅ 使用安全配置记录日志
        logger.info(
            f"Initializing AIClient with service={service}, model={model}"
        )
        logger.debug(
            f"Configuration: {SecureLogger.sanitize_config(config)}"
        )

        # ... 初始化逻辑 ...

        logger.info("AIClient initialized successfully")

    def request(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        """发送AI请求"""
        try:
            logger.info(
                "Dispatching AI request | model=%s, messages=%d, temperature=%s",
                self.model,
                len(messages),
                kwargs.get("temperature", "<omitted>")
            )

            response = self.client.chat.completions.create(...)

            logger.info("AI request completed | usage=%s", getattr(response, 'usage', None))
            return response.model_dump()

        except Exception as e:
            # ✅ 错误消息也要脱敏
            safe_error = SecureLogger.sanitize_error(e)
            logger.error(f"AI request failed: {safe_error}", exc_info=True)
            raise APIError(f"AI请求失败: {safe_error}") from e
```

**Step 3: 全局异常钩子（可选但推荐）**

```python
# litrx/logging_config.py - 添加

import sys
from .security_utils import SecureLogger

def setup_exception_hook():
    """设置全局异常钩子，确保所有未捕获的异常都被脱敏"""
    original_hook = sys.excepthook

    def secure_exception_hook(exc_type, exc_value, exc_traceback):
        """安全的异常钩子"""
        # 脱敏异常消息
        safe_message = SecureLogger.sanitize_error(exc_value)

        # 替换异常消息
        if hasattr(exc_value, 'args') and exc_value.args:
            exc_value.args = (safe_message,) + exc_value.args[1:]

        # 调用原始钩子
        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = secure_exception_hook

# 在应用启动时调用
# litrx/__main__.py 或 run_gui.py
from litrx.logging_config import setup_exception_hook
setup_exception_hook()
```

**测试清单**:
```python
# tests/test_security_utils.py (新建)

def test_sanitize_config():
    """测试配置脱敏"""
    config = {
        "OPENAI_API_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz",
        "MODEL_NAME": "gpt-4",
        "NESTED": {
            "API_KEY": "secret-key"
        }
    }

    safe = SecureLogger.sanitize_config(config)

    assert safe["OPENAI_API_KEY"] == "sk-12345***"
    assert safe["MODEL_NAME"] == "gpt-4"  # 非敏感字段不变
    assert safe["NESTED"]["API_KEY"] == "***"

def test_sanitize_string():
    """测试字符串脱敏"""
    text = "Error: API key sk-1234567890abcdefghijklmnopqrstuvwxyz is invalid"
    safe = SecureLogger.sanitize_string(text)

    assert "sk-" not in safe
    assert "***REDACTED***" in safe

def test_sanitize_error():
    """测试异常脱敏"""
    error = Exception("Invalid API key: sk-abcdefghijklmnop")
    safe = SecureLogger.sanitize_error(error)

    assert "sk-" not in safe
```

---

### 1.3 并发安全修复 (CRITICAL)

**问题描述**:
- `df.iterrows()` 在多线程中不安全
- 缺少worker异常处理
- 没有超时控制

**影响范围**:
- `litrx/abstract_screener.py:653-675`

#### 📝 详细修改方案

**Step 1: 预处理DataFrame为线程安全的数据结构**

```python
# litrx/abstract_screener.py

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import List, Tuple, Dict, Any
import threading

class AbstractScreener:

    def batch_screen_parallel(
        self,
        df: pd.DataFrame,
        max_workers: int = 3,
        timeout_per_item: int = 120,
        stop_event: Optional[threading.Event] = None
    ) -> pd.DataFrame:
        """并发筛选文献（线程安全版本）

        Args:
            df: 输入DataFrame
            max_workers: 最大并发worker数
            timeout_per_item: 单个条目的超时时间（秒）
            stop_event: 停止信号

        Returns:
            处理后的DataFrame
        """
        # ✅ Step 1: 预先转换为列表（避免并发访问迭代器）
        rows_data: List[Tuple[int, Dict[str, Any]]] = [
            (idx, row.to_dict())
            for idx, row in df.iterrows()
        ]

        logger.info(f"Starting parallel screening: {len(rows_data)} items, {max_workers} workers")

        # 结果容器（线程安全）
        results_lock = threading.Lock()
        completed_count = 0
        failed_indices = []

        def process_single_article(index: int, row_dict: Dict[str, Any]) -> Tuple[int, Optional[Dict]]:
            """处理单篇文献（在worker线程中）

            Returns:
                (index, results) 或 (index, None) 如果失败
            """
            try:
                # 检查停止信号
                if stop_event and stop_event.is_set():
                    logger.info(f"Worker for index {index} stopped by user")
                    return (index, None)

                # 提取数据
                title = row_dict.get(self.title_col, "")
                abstract = row_dict.get(self.abstract_col, "")

                # 调用分析
                results = self._analyze_single(title, abstract)

                logger.debug(f"Successfully processed index {index}")
                return (index, results)

            except Exception as e:
                logger.error(
                    f"Failed to process index {index}: {e}",
                    exc_info=True
                )
                return (index, None)

        # ✅ Step 2: 使用ThreadPoolExecutor with timeout
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(process_single_article, idx, row_dict): idx
                for idx, row_dict in rows_data
            }

            # ✅ Step 3: 处理完成的任务（带超时）
            for future in as_completed(future_to_index, timeout=timeout_per_item * len(rows_data)):
                # 检查停止信号
                if stop_event and stop_event.is_set():
                    logger.info("Stop signal received, cancelling remaining tasks")
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                try:
                    # 获取结果（带超时）
                    index, results = future.result(timeout=timeout_per_item)

                    if results:
                        # ✅ 线程安全地更新DataFrame
                        with results_lock:
                            self._apply_results_to_dataframe(df, index, results)
                            completed_count += 1
                    else:
                        with results_lock:
                            failed_indices.append(index)

                    # 进度回调
                    if self.progress_callback:
                        with results_lock:
                            self.progress_callback(completed_count, len(rows_data), results)

                except TimeoutError:
                    index = future_to_index[future]
                    logger.error(f"Worker for index {index} timed out after {timeout_per_item}s")
                    with results_lock:
                        failed_indices.append(index)

                except Exception as e:
                    index = future_to_index[future]
                    logger.error(f"Worker for index {index} failed: {e}", exc_info=True)
                    with results_lock:
                        failed_indices.append(index)

        # ✅ Step 4: 报告结果
        logger.info(
            f"Parallel screening completed: "
            f"{completed_count} succeeded, {len(failed_indices)} failed"
        )

        if failed_indices:
            logger.warning(f"Failed indices: {failed_indices[:10]}...")  # 只显示前10个

        return df
```

**Step 2: 添加重试机制（可选）**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class AbstractScreener:

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _analyze_single_with_retry(self, title: str, abstract: str) -> Dict[str, Any]:
        """带重试的单篇分析

        自动重试最多3次，等待时间指数增长（2s, 4s, 8s）
        """
        try:
            return self.analyzer.analyze(title, abstract)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Retryable error analyzing '{title[:50]}...': {e}")
            raise  # 让tenacity重试
        except Exception as e:
            logger.error(f"Non-retryable error: {e}")
            raise  # 不重试，直接失败
```

**测试清单**:
```python
# tests/test_concurrent_screening.py (新建)

import pytest
import pandas as pd
from litrx.abstract_screener import AbstractScreener
import threading

def test_parallel_screening_basic(mock_config):
    """测试基本并发筛选"""
    screener = AbstractScreener(mock_config)

    df = pd.DataFrame({
        'Title': ['Paper 1', 'Paper 2', 'Paper 3'],
        'Abstract': ['Abstract 1', 'Abstract 2', 'Abstract 3']
    })

    result = screener.batch_screen_parallel(df, max_workers=2)

    assert len(result) == 3
    assert 'screening_result' in result.columns

def test_parallel_screening_with_stop(mock_config):
    """测试停止信号"""
    screener = AbstractScreener(mock_config)
    stop_event = threading.Event()

    def delayed_stop():
        time.sleep(1)
        stop_event.set()

    threading.Thread(target=delayed_stop, daemon=True).start()

    df = pd.DataFrame({'Title': ['P1'] * 100, 'Abstract': ['A1'] * 100})
    result = screener.batch_screen_parallel(df, stop_event=stop_event)

    # 应该提前停止，不会处理全部100条
    assert len(result) < 100

def test_parallel_screening_timeout(mock_config, mock_slow_analyzer):
    """测试超时处理"""
    screener = AbstractScreener(mock_config)
    screener.analyzer = mock_slow_analyzer  # 模拟慢速分析器

    df = pd.DataFrame({'Title': ['P1'], 'Abstract': ['A1']})

    with pytest.raises(TimeoutError):
        screener.batch_screen_parallel(df, timeout_per_item=1)
```

---

### 1.4 GUI线程阻塞修复 (CRITICAL)

**问题描述**:
- 长时间操作在主线程执行
- UI冻结
- 无法取消

**影响范围**:
- `litrx/gui/tabs_qt/*.py` 所有标签页

#### 📝 详细修改方案

**标准模式：后台线程 + 信号通知**

```python
# litrx/gui/tabs_qt/csv_tab.py

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QMessageBox
from ...task_manager import CancellableTask, TaskCancelledException
from ...exceptions import *

class AnalysisWorker(QObject):
    """后台分析worker"""

    # 定义信号
    progress_updated = pyqtSignal(int, int, str)  # (current, total, status)
    analysis_completed = pyqtSignal(object)  # (results_df)
    analysis_failed = pyqtSignal(str)  # (error_message)

    def __init__(self, analyzer, df, config):
        super().__init__()
        self.analyzer = analyzer
        self.df = df
        self.config = config
        self.task = CancellableTask()

    def run(self):
        """在后台线程中运行分析"""
        try:
            self.task.start()

            def progress_callback(current, total, result):
                """进度回调（在worker线程中）"""
                if self.task.is_cancelled():
                    raise TaskCancelledException("用户取消了分析")

                status = f"正在分析第 {current}/{total} 篇..."
                self.progress_updated.emit(current, total, status)

            # 执行分析
            results = self.analyzer.batch_analyze(
                self.df,
                progress_callback=progress_callback,
                stop_event=self.task.cancelled
            )

            # 发射完成信号
            self.analysis_completed.emit(results)

        except TaskCancelledException as e:
            logger.info(f"Analysis cancelled: {e}")
            self.analysis_failed.emit("分析已取消")

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            self.analysis_failed.emit(str(e))

        finally:
            self.task.finish()

    def cancel(self):
        """取消分析"""
        self.task.cancel()


class CsvTab(QWidget):
    """CSV分析标签页（线程安全版本）"""

    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window

        # 后台线程和worker
        self.analysis_thread = None
        self.analysis_worker = None

        self._setup_ui()

    def start_analysis(self):
        """开始分析（在后台线程）"""
        try:
            # 1. 验证输入
            if not self.df_file_path:
                QMessageBox.warning(self, "警告", "请先选择CSV文件")
                return

            if not self.df or self.df.empty:
                QMessageBox.warning(self, "警告", "CSV文件为空")
                return

            # 2. 禁用开始按钮，启用停止按钮
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("准备开始分析...")

            # 3. 创建analyzer
            config = self.parent_window.build_config()
            analyzer = LiteratureAnalyzer(config, research_topic=self.research_topic)

            # 4. 创建worker和线程
            self.analysis_worker = AnalysisWorker(analyzer, self.df, config)
            self.analysis_thread = QThread()

            # 5. 移动worker到线程
            self.analysis_worker.moveToThread(self.analysis_thread)

            # 6. 连接信号
            self.analysis_thread.started.connect(self.analysis_worker.run)
            self.analysis_worker.progress_updated.connect(self._on_progress_updated)
            self.analysis_worker.analysis_completed.connect(self._on_analysis_completed)
            self.analysis_worker.analysis_failed.connect(self._on_analysis_failed)
            self.analysis_thread.finished.connect(self._on_thread_finished)

            # 7. 启动线程
            self.analysis_thread.start()

        except Exception as e:
            logger.error(f"Failed to start analysis: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "启动失败",
                f"无法启动分析:\n{str(e)}"
            )
            self._reset_ui()

    def stop_analysis(self):
        """停止分析"""
        if self.analysis_worker:
            reply = QMessageBox.question(
                self,
                "确认停止",
                "确定要停止当前分析吗？\n已完成的结果将保留。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.status_label.setText("正在停止...")
                self.analysis_worker.cancel()

    def _on_progress_updated(self, current: int, total: int, status: str):
        """处理进度更新（在主线程）"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(status)

    def _on_analysis_completed(self, results_df):
        """处理分析完成（在主线程）"""
        self.df = results_df
        self.status_label.setText(f"分析完成！共 {len(results_df)} 条结果")
        self.progress_bar.setValue(self.progress_bar.maximum())

        # 显示结果
        self._update_results_table(results_df)

        # 自动保存
        self._auto_save_results(results_df)

        QMessageBox.information(
            self,
            "完成",
            f"分析完成！\n共处理 {len(results_df)} 条文献。"
        )

        self._reset_ui()

    def _on_analysis_failed(self, error_message: str):
        """处理分析失败（在主线程）"""
        self.status_label.setText("分析失败")

        QMessageBox.critical(
            self,
            "分析失败",
            f"分析过程中发生错误:\n{error_message}\n\n"
            f"请查看日志文件获取详细信息：\n"
            f"~/.litrx/logs/litrx.log"
        )

        self._reset_ui()

    def _on_thread_finished(self):
        """线程结束清理（在主线程）"""
        if self.analysis_thread:
            self.analysis_thread.quit()
            self.analysis_thread.wait()
            self.analysis_thread = None
        self.analysis_worker = None

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        """标签页关闭时清理"""
        if self.analysis_thread and self.analysis_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "确认关闭",
                "分析正在进行中，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # 停止worker
            if self.analysis_worker:
                self.analysis_worker.cancel()

            # 等待线程结束
            if self.analysis_thread:
                self.analysis_thread.quit()
                self.analysis_thread.wait(3000)  # 最多等3秒

        event.accept()
```

**测试清单**:
```python
# tests/test_gui_threading.py (新建)

import pytest
from PyQt6.QtWidgets import QApplication
from litrx.gui.tabs_qt.csv_tab import CsvTab
import time

@pytest.fixture
def app():
    """创建QApplication"""
    app = QApplication([])
    yield app
    app.quit()

def test_analysis_in_background(app, qtbot, mock_config):
    """测试分析在后台线程运行"""
    tab = CsvTab(mock_parent_window(mock_config))

    # 加载测试数据
    tab.df = pd.DataFrame({'Title': ['P1'], 'Abstract': ['A1']})
    tab.df_file_path = '/test/path.csv'

    # 开始分析
    tab.start_analysis()

    # 验证：
    # 1. 开始按钮被禁用
    assert not tab.start_btn.isEnabled()
    # 2. 停止按钮被启用
    assert tab.stop_btn.isEnabled()
    # 3. 主线程不阻塞（UI仍可响应）
    assert QApplication.instance().processEvents() >= 0

    # 等待完成
    qtbot.waitUntil(lambda: tab.start_btn.isEnabled(), timeout=10000)

def test_cancel_analysis(app, qtbot, mock_config):
    """测试取消分析"""
    tab = CsvTab(mock_parent_window(mock_config))
    tab.df = pd.DataFrame({'Title': ['P1'] * 100, 'Abstract': ['A1'] * 100})
    tab.df_file_path = '/test/path.csv'

    # 开始分析
    tab.start_analysis()

    # 等待一点时间
    qtbot.wait(1000)

    # 取消
    tab.stop_analysis()

    # 验证UI恢复
    qtbot.waitUntil(lambda: tab.start_btn.isEnabled(), timeout=5000)
```

---

## 🔧 第二阶段：架构优化（Week 3-4）

### 2.1 单一职责原则重构 (HIGH)

**问题**: `LiteratureAnalyzer` 类承担太多职责

**修改方案**: 分离为多个专注的类

```python
# 新建文件: litrx/data_loader.py
"""数据加载和验证"""

from pathlib import Path
import pandas as pd
from .exceptions import FileProcessingError, ValidationError
from .utils import ColumnDetector

class DataLoader:
    """仅负责数据加载和验证"""

    def __init__(self, max_file_size_mb: int = 500):
        self.max_file_size_mb = max_file_size_mb

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """加载CSV文件

        Args:
            file_path: CSV文件路径

        Returns:
            加载的DataFrame

        Raises:
            FileProcessingError: 文件读取失败
            ValidationError: 文件验证失败
        """
        path = Path(file_path)

        # 1. 文件存在性检查
        if not path.exists():
            raise FileProcessingError(f"文件不存在: {file_path}")

        # 2. 文件大小检查
        file_size = path.stat().st_size
        max_bytes = self.max_file_size_mb * 1024 * 1024

        if file_size > max_bytes:
            raise FileProcessingError(
                f"文件过大: {file_size / 1024 / 1024:.1f}MB "
                f"(最大允许: {self.max_file_size_mb}MB)"
            )

        # 3. 读取文件
        try:
            if file_size > 50 * 1024 * 1024:  # > 50MB
                # 大文件分块读取
                chunks = pd.read_csv(
                    file_path,
                    encoding='utf-8-sig',
                    chunksize=10000
                )
                df = pd.concat(chunks, ignore_index=True)
            else:
                df = pd.read_csv(file_path, encoding='utf-8-sig')

        except pd.errors.ParserError as e:
            raise FileProcessingError(f"CSV格式错误: {str(e)}") from e
        except UnicodeDecodeError as e:
            raise FileProcessingError(f"文件编码错误: {str(e)}") from e

        # 4. 验证数据
        self._validate_dataframe(df, file_path)

        return df

    def _validate_dataframe(self, df: pd.DataFrame, file_path: str) -> None:
        """验证DataFrame内容

        Raises:
            ValidationError: 验证失败
        """
        if df.empty:
            raise ValidationError(f"文件为空: {file_path}")

        # 检查必需列
        required_columns = ['Title', 'Abstract']
        title_col = ColumnDetector.get_column(df, 'title')
        abstract_col = ColumnDetector.get_column(df, 'abstract')

        if not title_col:
            raise ValidationError(
                f"未找到标题列。可用列: {', '.join(df.columns)}\n"
                f"支持的标题列名: Title, 标题, Article Title"
            )

        if not abstract_col:
            raise ValidationError(
                f"未找到摘要列。可用列: {', '.join(df.columns)}\n"
                f"支持的摘要列名: Abstract, 摘要, Abstract Note"
            )

# 新建文件: litrx/paper_analyzer.py
"""单篇文献分析（核心AI逻辑）"""

from typing import Dict, Any
from .ai_client import AIClient
from .cache import ResultCache

class PaperAnalyzer:
    """仅负责单篇文献的AI分析"""

    def __init__(
        self,
        ai_client: AIClient,
        prompt_template: str,
        cache: ResultCache = None
    ):
        self.client = ai_client
        self.prompt_template = prompt_template
        self.cache = cache

        # 统计
        self.cache_hits = 0
        self.cache_misses = 0

    def analyze(
        self,
        title: str,
        abstract: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """分析单篇文献

        Args:
            title: 论文标题
            abstract: 论文摘要
            context: 额外上下文（如研究主题）

        Returns:
            分析结果字典
        """
        # 1. 检查缓存
        if self.cache:
            cache_key = self._build_cache_key(title, abstract, context)
            cached = self.cache.get(title, abstract, cache_key)

            if cached:
                self.cache_hits += 1
                logger.debug(f"Cache hit for '{title[:50]}...'")
                return cached

            self.cache_misses += 1

        # 2. 构建prompt
        prompt = self._build_prompt(title, abstract, context)

        # 3. 调用AI
        try:
            req_kwargs = {
                "messages": [{"role": "user", "content": prompt}]
            }

            if getattr(self.client, "supports_temperature", True):
                req_kwargs["temperature"] = 0.3

            response = self.client.request(**req_kwargs)
            content = response["choices"][0]["message"]["content"]

            # 4. 解析结果
            result = self._parse_response(content)

            # 5. 缓存结果
            if self.cache:
                self.cache.set(title, abstract, result, cache_key)

            return result

        except Exception as e:
            logger.error(f"Analysis failed for '{title[:50]}...': {e}")
            raise

    def _build_cache_key(self, title: str, abstract: str, context: Dict) -> str:
        """构建缓存键"""
        import json
        context_str = json.dumps(context or {}, sort_keys=True)
        return f"{self.prompt_template[:50]}|{context_str}"

    def _build_prompt(self, title: str, abstract: str, context: Dict) -> str:
        """构建分析prompt"""
        return self.prompt_template.format(
            title=title,
            abstract=abstract,
            **(context or {})
        )

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """解析AI响应"""
        from .utils import AIResponseParser
        return AIResponseParser.parse_relevance_response(content)

# 修改后的 litrx/csv_analyzer.py
"""CSV相关性分析（组合器）"""

from .data_loader import DataLoader
from .paper_analyzer import PaperAnalyzer
from .progress_manager import ProgressManager
from .cache import get_cache
from .ai_client import AIClient

class LiteratureAnalyzer:
    """文献分析器（组合多个专注的组件）"""

    def __init__(
        self,
        config: Dict[str, Any],
        research_topic: str = "",
        questions: Dict[str, Any] = None
    ):
        self.research_topic = research_topic
        self.config = config
        self.questions = questions or {}

        # 组合依赖
        self.loader = DataLoader(
            max_file_size_mb=config.get("MAX_FILE_SIZE_MB", 500)
        )

        ai_client = AIClient(config)
        prompt_template = self._load_prompt_template()
        cache = get_cache() if config.get("ENABLE_CACHE", True) else None

        self.analyzer = PaperAnalyzer(ai_client, prompt_template, cache)

    def analyze_file(
        self,
        file_path: str,
        progress_callback: Callable = None
    ) -> pd.DataFrame:
        """分析整个CSV文件

        Args:
            file_path: CSV文件路径
            progress_callback: 进度回调

        Returns:
            包含分析结果的DataFrame
        """
        # 1. 加载数据（委托给DataLoader）
        df = self.loader.load_csv(file_path)

        # 2. 批量分析
        results_df = self._batch_analyze(df, progress_callback)

        # 3. 保存结果（委托给ProgressManager）
        output_path = self._generate_output_path(file_path)
        progress_mgr = ProgressManager(output_path)
        progress_mgr.finalize_results(results_df)

        return results_df

    def _batch_analyze(
        self,
        df: pd.DataFrame,
        progress_callback: Callable = None
    ) -> pd.DataFrame:
        """批量分析（使用PaperAnalyzer）"""
        # 添加结果列
        df['Relevance Score'] = None
        df['Analysis Result'] = None
        df['Literature Review Suggestion'] = None

        total = len(df)

        for idx, row in df.itertuples():
            # 分析单篇
            result = self.analyzer.analyze(
                title=row.Title,
                abstract=row.Abstract,
                context={"research_topic": self.research_topic}
            )

            # 应用结果
            df.at[idx, 'Relevance Score'] = result.get('relevance_score')
            df.at[idx, 'Analysis Result'] = result.get('analysis')
            df.at[idx, 'Literature Review Suggestion'] = result.get('literature_review_suggestion')

            # 进度回调
            if progress_callback:
                progress_callback(idx + 1, total, result)

        return df
```

**好处**:
- 每个类职责单一，易于测试
- 依赖注入，易于mock
- 可以独立演进每个组件

---

### 2.2 代码重复消除 (MEDIUM)

**问题**: 配置加载逻辑在多个模块重复

**修改方案**: 创建统一的配置工厂

```python
# litrx/config_factory.py (新建)
"""统一的配置加载工厂"""

from typing import Tuple, Dict, Any, Optional
from pathlib import Path
import json
import yaml

from .config import load_config as base_load_config, DEFAULT_CONFIG
from .resources import resource_path

class ConfigFactory:
    """配置工厂：统一加载各模块的配置"""

    @staticmethod
    def load_for_csv(
        config_path: Optional[str] = None,
        questions_path: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """加载CSV分析模块配置

        Args:
            config_path: 配置文件路径（可选）
            questions_path: 问题模板路径（可选）

        Returns:
            (config, questions) 元组
        """
        # 加载基础配置
        default_cfg = resource_path("configs", "config.yaml")
        config = base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)

        # 加载问题模板
        q_path = questions_path or resource_path("configs", "questions", "csv.yaml")

        if q_path.exists():
            with open(q_path, 'r', encoding='utf-8') as f:
                questions = yaml.safe_load(f) or {}
        else:
            questions = {}

        return config, questions

    @staticmethod
    def load_for_abstract(
        config_path: Optional[str] = None,
        mode: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """加载摘要筛选模块配置

        Args:
            config_path: 配置文件路径（可选）
            mode: 筛选模式名称（可选）

        Returns:
            (config, questions) 元组
        """
        # 加载基础配置
        default_cfg = resource_path("configs", "config.yaml")
        config = base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)

        # 加载模式问题
        questions = ConfigFactory._load_mode_questions(mode or config.get("CONFIG_MODE", "default"))

        return config, questions

    @staticmethod
    def load_for_matrix(
        config_path: Optional[str] = None,
        dimensions_file: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """加载文献矩阵模块配置

        Args:
            config_path: 配置文件路径（可选）
            dimensions_file: 维度配置文件（可选）

        Returns:
            (config, dimensions) 元组
        """
        # 加载基础配置
        default_cfg = resource_path("configs", "config.yaml")
        config = base_load_config(str(config_path or default_cfg), DEFAULT_CONFIG)

        # 加载维度配置
        dim_path = dimensions_file or resource_path("configs", "matrix", "default.yaml")

        if Path(dim_path).exists():
            with open(dim_path, 'r', encoding='utf-8') as f:
                dimensions = yaml.safe_load(f) or {}
        else:
            dimensions = {"dimensions": []}

        return config, dimensions

    @staticmethod
    def _load_mode_questions(mode: str) -> Dict[str, Any]:
        """加载筛选模式问题（私有方法）"""
        # 尝试新格式
        unified_path = resource_path("configs", "abstract", f"{mode}.yaml")

        if unified_path.exists():
            with open(unified_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        # 回退到旧格式
        legacy_path = resource_path("questions_config.json")

        if legacy_path.exists():
            with open(legacy_path, 'r', encoding='utf-8') as f:
                all_modes = json.load(f)
            return all_modes.get(mode, {
                "open_questions": [],
                "yes_no_questions": []
            })

        return {"open_questions": [], "yes_no_questions": []}

# 使用示例：
# 在 csv_analyzer.py 中：
from .config_factory import ConfigFactory

config, questions = ConfigFactory.load_for_csv()
analyzer = LiteratureAnalyzer(config, questions=questions)

# 在 abstract_screener.py 中：
config, questions = ConfigFactory.load_for_abstract(mode="psychology_empirical")
screener = AbstractScreener(config, questions)

# 在 matrix_analyzer.py 中：
config, dimensions = ConfigFactory.load_for_matrix(dimensions_file="custom.yaml")
matrix = MatrixAnalyzer(config, dimensions)
```

---

## 📈 测试覆盖率提升计划（Week 5-6）

目标：从 15% → 85%

### 3.1 关键模块测试优先级

**Priority 1 (Week 5)**:
```
✅ ai_client.py         - 目标 90% 覆盖
✅ cache.py            - 目标 85% 覆盖
✅ progress_manager.py - 目标 80% 覆盖
✅ exceptions.py       - 目标 95% 覆盖 (简单模块)
```

**Priority 2 (Week 6)**:
```
✅ csv_analyzer.py     - 目标 75% 覆盖
✅ abstract_screener.py - 目标 70% 覆盖
✅ matrix_analyzer.py  - 目标 70% 覆盖
```

**Priority 3 (持续)**:
```
□ GUI components      - 目标 60% 覆盖
□ Utilities           - 目标 85% 覆盖
```

### 3.2 测试文件结构

```
tests/
├── unit/                      # 单元测试
│   ├── test_ai_client.py      # AI客户端测试
│   ├── test_cache.py          # 缓存系统测试
│   ├── test_progress_manager.py # 进度管理测试
│   ├── test_exceptions.py     # 异常类测试
│   ├── test_data_loader.py    # 数据加载测试
│   ├── test_paper_analyzer.py # 文献分析测试
│   └── test_security_utils.py # 安全工具测试
│
├── integration/               # 集成测试
│   ├── test_csv_workflow.py  # CSV完整流程测试
│   ├── test_abstract_workflow.py # 摘要筛选流程测试
│   └── test_matrix_workflow.py # 矩阵分析流程测试
│
├── gui/                       # GUI测试
│   ├── test_csv_tab.py
│   ├── test_abstract_tab.py
│   └── test_matrix_tab.py
│
├── fixtures/                  # 测试fixtures
│   ├── mock_data.py           # Mock数据生成器
│   ├── mock_ai_client.py      # Mock AI客户端
│   └── sample_files/          # 示例文件
│       ├── sample.csv
│       ├── sample.xlsx
│       └── sample_config.yaml
│
└── conftest.py                # pytest配置
```

### 3.3 示例测试文件

```python
# tests/unit/test_ai_client.py
"""AI客户端单元测试"""

import pytest
from unittest.mock import Mock, patch
from litrx.ai_client import AIClient
from litrx.exceptions import APIError

@pytest.fixture
def mock_config():
    """基础配置fixture"""
    return {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-4",
        "OPENAI_API_KEY": "sk-test1234567890",
        "AI_TIMEOUT_SECONDS": 60
    }

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI客户端"""
    with patch('litrx.ai_client.OpenAI') as mock:
        yield mock

class TestAIClientInit:
    """测试AIClient初始化"""

    def test_init_with_openai(self, mock_config, mock_openai_client):
        """测试OpenAI服务初始化"""
        client = AIClient(mock_config)

        assert client.service == "openai"
        assert client.model == "gpt-4"
        assert mock_openai_client.called

    def test_init_with_siliconflow(self, mock_config, mock_openai_client):
        """测试SiliconFlow服务初始化"""
        mock_config["AI_SERVICE"] = "siliconflow"
        mock_config["SILICONFLOW_API_KEY"] = "sf-test1234"

        client = AIClient(mock_config)

        assert client.service == "siliconflow"
        # 验证使用了正确的base_url
        mock_openai_client.assert_called_with(
            api_key="sf-test1234",
            base_url="https://api.siliconflow.cn/v1"
        )

    def test_init_missing_api_key(self, mock_config):
        """测试缺少API密钥时抛出异常"""
        del mock_config["OPENAI_API_KEY"]

        with pytest.raises(RuntimeError, match="API key not configured"):
            AIClient(mock_config)

class TestAIClientRequest:
    """测试AIClient请求方法"""

    def test_request_success(self, mock_config, mock_openai_client):
        """测试成功的请求"""
        # 设置mock返回值
        mock_response = Mock()
        mock_response.model_dump.return_value = {
            "choices": [{
                "message": {"content": "Test response"}
            }],
            "usage": {"total_tokens": 100}
        }

        mock_instance = Mock()
        mock_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_instance

        # 执行测试
        client = AIClient(mock_config)
        result = client.request(
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.5
        )

        # 验证
        assert result["choices"][0]["message"]["content"] == "Test response"
        assert result["usage"]["total_tokens"] == 100

    def test_request_with_unsupported_temperature(self, mock_config, mock_openai_client):
        """测试模型不支持temperature参数时的重试"""
        # 第一次调用失败（temperature不支持）
        # 第二次调用成功（无temperature）

        mock_instance = Mock()

        # 第一次调用抛异常
        mock_instance.chat.completions.create.side_effect = [
            Exception("Unsupported value: param 'temperature'"),
            Mock(model_dump=lambda: {"choices": [{"message": {"content": "OK"}}]})
        ]

        mock_openai_client.return_value = mock_instance

        client = AIClient(mock_config)
        result = client.request(
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.5
        )

        # 验证成功重试
        assert result["choices"][0]["message"]["content"] == "OK"
        # 验证调用了两次（第一次失败，第二次成功）
        assert mock_instance.chat.completions.create.call_count == 2

    def test_request_timeout(self, mock_config, mock_openai_client):
        """测试请求超时"""
        mock_instance = Mock()
        mock_instance.chat.completions.create.side_effect = TimeoutError("Request timeout")
        mock_openai_client.return_value = mock_instance

        client = AIClient(mock_config)

        with pytest.raises(APIError, match="AI请求失败"):
            client.request(messages=[{"role": "user", "content": "Test"}])

# tests/integration/test_csv_workflow.py
"""CSV分析完整流程集成测试"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile

from litrx.csv_analyzer import LiteratureAnalyzer
from litrx.exceptions import FileProcessingError

@pytest.fixture
def sample_csv(tmp_path):
    """创建示例CSV文件"""
    csv_path = tmp_path / "sample.csv"

    df = pd.DataFrame({
        'Title': [
            'Machine Learning in Healthcare',
            'Deep Learning Applications',
            'Natural Language Processing'
        ],
        'Abstract': [
            'This paper discusses the use of ML in healthcare...',
            'We present a novel deep learning architecture...',
            'NLP techniques for text analysis...'
        ]
    })

    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    return csv_path

@pytest.fixture
def mock_ai_config():
    """测试用AI配置（使用mock）"""
    return {
        "AI_SERVICE": "openai",
        "MODEL_NAME": "gpt-4",
        "OPENAI_API_KEY": "sk-test",
        "ENABLE_CACHE": False  # 测试时禁用缓存
    }

def test_end_to_end_csv_analysis(sample_csv, mock_ai_config, mocker):
    """测试完整的CSV分析流程"""
    # Mock AIClient返回
    mock_response = {
        "choices": [{
            "message": {
                "content": '''
                {
                    "relevance_score": 85,
                    "analysis": "Highly relevant to ML research",
                    "literature_review_suggestion": "Should be included"
                }
                '''
            }
        }]
    }

    mocker.patch(
        'litrx.ai_client.AIClient.request',
        return_value=mock_response
    )

    # 创建分析器
    analyzer = LiteratureAnalyzer(
        config=mock_ai_config,
        research_topic="Machine Learning Applications"
    )

    # 执行分析
    results = analyzer.analyze_file(str(sample_csv))

    # 验证结果
    assert len(results) == 3
    assert 'Relevance Score' in results.columns
    assert 'Analysis Result' in results.columns
    assert results['Relevance Score'].iloc[0] == 85

def test_csv_analysis_with_invalid_file(mock_ai_config):
    """测试无效文件处理"""
    analyzer = LiteratureAnalyzer(mock_ai_config)

    with pytest.raises(FileProcessingError, match="文件不存在"):
        analyzer.analyze_file("/nonexistent/file.csv")
```

### 3.4 CI/CD集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .
        pip install pytest pytest-cov pytest-qt pytest-mock

    - name: Run tests with coverage
      run: |
        pytest --cov=litrx --cov-report=xml --cov-report=html tests/

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

    - name: Check coverage threshold
      run: |
        # 要求最低80%覆盖率
        coverage report --fail-under=80
```

---

## 📚 文档改进（贯穿整个过程）

### 4.1 代码文档标准

**所有公共函数必须有docstring**:

```python
def analyze_paper(
    self,
    title: str,
    abstract: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """分析单篇文献的相关性。

    使用AI模型评估文献与研究主题的相关程度，并生成详细的分析报告。

    Args:
        title: 文献标题，用于初步判断相关性
        abstract: 文献摘要，主要的分析来源
        context: 额外上下文信息，包含：
            - research_topic (str): 研究主题
            - additional_criteria (List[str], optional): 额外筛选标准

    Returns:
        分析结果字典，包含：
        - relevance_score (int): 相关性分数（0-100）
        - analysis (str): 详细分析说明
        - literature_review_suggestion (str): 文献综述建议
        - keywords (List[str]): 提取的关键词

    Raises:
        APIError: AI服务调用失败
        ValidationError: 输入数据验证失败

    Examples:
        >>> analyzer = PaperAnalyzer(client, template)
        >>> result = analyzer.analyze(
        ...     title="Machine Learning in Healthcare",
        ...     abstract="This paper presents...",
        ...     context={"research_topic": "AI in Medicine"}
        ... )
        >>> print(result['relevance_score'])
        85

    Note:
        - 结果会自动缓存，相同输入会直接返回缓存
        - 分析时间取决于AI模型响应速度（通常5-15秒）
        - 分数算法基于语义相似度和关键词匹配

    See Also:
        - :func:`batch_analyze`: 批量分析多篇文献
        - :class:`AIClient`: AI客户端配置
    """
    pass
```

### 4.2 CHANGELOG维护

```markdown
# CHANGELOG.md

## [Unreleased]

### Added
- 安全日志工具（SecureLogger）防止API密钥泄露
- 完整的异常层次结构（LitRxError及子类）
- ConfigFactory统一配置加载
- 数据加载器（DataLoader）独立模块
- 文献分析器（PaperAnalyzer）独立模块

### Changed
- **BREAKING**: LiteratureAnalyzer现在使用组合而非继承
- 所有GUI操作改为后台线程执行
- 异常处理使用自定义异常类而非泛化Exception
- 并发筛选使用线程安全的数据结构

### Fixed
- 修复GUI线程阻塞导致"无响应"问题
- 修复并发场景下DataFrame迭代器不安全
- 修复库代码中使用sys.exit()导致程序崩溃
- 修复API密钥可能在日志中泄露的安全问题

### Security
- API密钥在所有日志输出中自动脱敏
- 添加全局异常钩子确保异常消息安全
- 文件路径验证防止路径遍历攻击

## [0.2.0] - 2024-11-19

### Added
- AI辅助配置生成功能
- 结果缓存系统
- 进度管理系统
- 安全密钥管理

...
```

---

## ✅ 验收标准

### 阶段1完成标准（Week 2结束）:
- [ ] 无任何`sys.exit()`在库代码中
- [ ] 所有异常使用自定义异常类
- [ ] API密钥不出现在日志中（通过测试验证）
- [ ] GUI不会在长操作时冻结（通过手动测试）
- [ ] 并发筛选通过100+条目的压力测试

### 阶段2完成标准（Week 4结束）:
- [ ] LiteratureAnalyzer分离为3个独立类
- [ ] 配置加载统一使用ConfigFactory
- [ ] 代码重复度从24% → <10%
- [ ] 所有新代码有单元测试

### 最终验收标准（Week 6结束）:
- [ ] 测试覆盖率达到85%
- [ ] 所有CRITICAL和HIGH问题已修复
- [ ] CI/CD流水线运行通过
- [ ] 文档更新到最新
- [ ] 代码质量评分从2.3/5 → 4.2/5

---

## 📅 详细时间表

### Week 1
**Monday-Tuesday**: 异常处理重构
- 创建exceptions.py完整层次
- 修改csv_analyzer.py
- 修改abstract_screener.py
- 编写异常测试

**Wednesday-Thursday**: API密钥安全
- 创建security_utils.py
- 修改ai_client.py
- 添加全局异常钩子
- 编写安全测试

**Friday**: 并发安全修复
- 重构abstract_screener并发逻辑
- 添加超时和异常处理
- 编写并发测试

### Week 2
**Monday-Tuesday**: GUI线程修复
- 重构csv_tab.py
- 重构abstract_tab.py
- 重构matrix_tab.py
- 添加QThread示例

**Wednesday-Thursday**: 集成测试
- 测试所有修复
- 修复发现的问题
- 性能测试

**Friday**: 代码审查和文档
- 团队代码审查
- 更新CHANGELOG
- 更新README

### Week 3-4
**架构优化** (按计划执行)

### Week 5-6
**测试覆盖率提升** (按计划执行)

---

## 🔄 持续改进

### 每周检查清单
```markdown
- [ ] 运行全部测试套件
- [ ] 检查测试覆盖率趋势
- [ ] 代码审查新增代码
- [ ] 更新文档（如有API变更）
- [ ] 检查性能指标
- [ ] 审查新增依赖
```

### 每月审计
```markdown
- [ ] 代码质量评分
- [ ] 技术债务评估
- [ ] 安全漏洞扫描
- [ ] 依赖版本更新
- [ ] 文档一致性检查
```

---

**文档版本**: 1.0
**最后更新**: 2025-11-19
**维护者**: 开发团队
**下次审查**: 2025-12-03 (Week 2结束)
