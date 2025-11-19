# AI Assistant UI Freeze Fix - Testing Guide

## 修复概述 | Fix Summary

本次修复针对 AI 模式助手和矩阵助手在生成过程中 UI 冻结（"正在生成…"无响应）的问题。

This fix addresses the UI freeze issue ("Generating..." without response) in AI Mode Assistant and Matrix Assistant dialogs.

## 关键改进 | Key Improvements

### 1. 线程通信机制改进 | Improved Thread Communication

**之前 | Before:**
- 使用 `QTimer.singleShot(0, callback)` 从后台线程更新 UI
- 在某些情况下可能不可靠，尤其在 macOS 上

**现在 | Now:**
- 使用 PyQt6 的 `pyqtSignal` + 槽函数机制
- 这是 Qt 推荐的线程间通信方式，更可靠

**代码变化:**
```python
# 之前 (Before)
def _invoke(self, fn):
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(0, fn)

# 现在 (Now)
class WorkerSignals(QObject):
    success = pyqtSignal(dict)  # 或 list for matrix
    error = pyqtSignal(str)

# 在 __init__ 中连接信号
self._signals = WorkerSignals()
self._signals.success.connect(self._on_generation_success)
self._signals.error.connect(self._on_generation_error)

# 在 worker 线程中发射信号
self._signals.success.emit(data)
```

### 2. 全面的日志记录 | Comprehensive Logging

每个关键步骤都添加了日志记录，方便诊断问题：

- 用户点击生成按钮
- Worker 线程启动
- AI 请求发送/完成
- 响应数据提取和验证
- JSON/YAML 解析
- UI 更新

**日志级别:**
- `INFO`: 关键流程节点
- `DEBUG`: 详细数据（需要设置 `LITRX_LOG_LEVEL=DEBUG`）
- `ERROR`: 错误和异常

### 3. 类型检查和验证 | Type Checking and Validation

在 `ai_config_generator.py` 中添加了严格的类型检查：

```python
# 验证响应结构
if not isinstance(resp, dict):
    raise TypeError(f"Expected dict from AI client, got {type(resp).__name__}")
if "choices" not in resp:
    raise KeyError(f"Response missing 'choices' key. Keys: {list(resp.keys())}")

# 验证 content 类型
if not isinstance(content, str):
    raise TypeError(f"Expected string content, got {type(content).__name__}")
```

### 4. 异常处理增强 | Enhanced Exception Handling

所有 UI 回调函数都包裹在 try-except 中，防止静默失败：

```python
def _on_generation_success(self, data: Dict[str, Any]) -> None:
    try:
        logger.info("_on_generation_success called in UI thread")
        # ... UI 更新逻辑
    except Exception as e:
        logger.error("Exception in _on_generation_success: %s", e, exc_info=True)
        # 显示错误对话框
        QMessageBox.critical(self, "Error", f"UI 更新时发生错误: {e}")
```

## 测试步骤 | Testing Steps

### 前提条件 | Prerequisites

1. 确保已安装最新代码:
   ```bash
   cd /home/user/LitRelevanceAI
   python -m pip install -e .
   ```

2. 确保 API 密钥已配置（OpenAI 或 SiliconFlow）

3. 设置日志级别为 DEBUG（可选但推荐）:
   ```bash
   export LITRX_LOG_LEVEL=DEBUG
   ```

### 测试场景 1: 正常生成流程 | Normal Generation Flow

**目标**: 验证 AI 助手可以成功生成配置

**步骤**:
1. 运行 GUI:
   ```bash
   python run_gui.py
   ```

2. 打开 "摘要筛选" 或 "文献矩阵" 标签

3. 点击 "AI 模式助手" 或 "🤖 AI 生成维度" 按钮

4. 输入中文描述，例如:
   ```
   我想筛选心理学实证研究，需要知道是否使用实验方法、样本量、是否有对照组
   ```

5. 点击 "生成" 按钮

**预期结果**:
- 按钮变为禁用状态
- 状态显示 "正在生成..." 或 "Generating..."
- 日志中看到:
  ```
  User clicked Generate button, description length=XX
  Worker thread started for AI mode generation
  Lazy initializing AbstractModeGenerator
  AIModeAssistant: generation started (lang=zh)
  Sending AI request with response_format=json_object
  Dispatching AI request | model=gpt-5 ...
  AI request completed | usage=...
  AI request returned, response type=dict
  Extracted content, type=str, length=XXXX
  Parsing JSON response
  JSON parsed successfully, result type=dict, keys=[...]
  Validating mode structure
  Mode validation passed
  generate_mode completed successfully
  AIModeAssistant: generator returned, data type=dict
  Emitting success signal to UI thread
  _on_generation_success called in UI thread
  Updating UI with generated data
  JSON preview generated, length=XXX
  UI update completed successfully
  ```
- 预览窗口显示生成的 JSON/YAML
- "Apply" 按钮变为可用
- "Generate" 按钮重新启用

### 测试场景 2: API 错误处理 | API Error Handling

**目标**: 验证 API 错误能被正确捕获和显示

**步骤**:
1. 临时移除或修改 API 密钥（使其无效）
2. 重复测试场景 1 的步骤

**预期结果**:
- 显示错误对话框，包含有用的错误信息
- 日志中看到:
  ```
  Worker thread caught exception: ...
  Emitting error signal to UI thread
  _on_generation_error called in UI thread
  Error handling completed
  ```
- "Generate" 按钮重新启用
- "Apply" 按钮保持禁用状态

### 测试场景 3: 超长响应处理 | Long Response Handling

**目标**: 验证能处理较大的 AI 响应

**步骤**:
1. 使用更复杂的描述（要求生成多个问题/维度）:
   ```
   请帮我生成一个详细的文献筛选模式，包含以下维度：
   1. 研究类型（实证研究、理论综述、元分析等）
   2. 研究方法（实验、问卷、访谈、观察等）
   3. 样本量（具体数字）
   4. 是否有对照组
   5. 数据分析方法
   6. 研究局限
   7. 主要发现
   8. 理论贡献
   ```

2. 点击 "生成"

**预期结果**:
- 即使响应较大，UI 也应该正常更新
- 日志显示内容长度（可能是几千个字符）
- 预览窗口正确显示所有内容

### 测试场景 4: 对话框关闭时的处理 | Dialog Close Handling

**目标**: 验证在生成过程中关闭对话框不会导致崩溃

**步骤**:
1. 打开 AI 助手对话框
2. 输入描述并点击 "生成"
3. 在状态显示 "正在生成..." 时，点击 "取消" 或关闭窗口

**预期结果**:
- 对话框正常关闭
- 日志显示:
  ```
  Dialog rejected/closed by user
  ```
- 如果生成完成，日志显示:
  ```
  Dialog closed or not visible, skipping UI update
  ```
- 不应该有异常或崩溃

### 测试场景 5: 模型兼容性 | Model Compatibility

**目标**: 验证 gpt-5 和其他模型的兼容性

**步骤**:
1. 在主窗口切换到 `gpt-5` 模型
2. 运行测试场景 1

**预期结果**:
- 日志显示:
  ```
  Initializing AIClient with service=openai, model=gpt-5
  Model does not support 'temperature'; removing it from requests
  Dispatching AI request | model=gpt-5, ... temperature=<omitted>, response_format={'type': 'json_object'}
  ```
- 生成正常完成

## 日志文件位置 | Log File Location

日志保存在: `~/.litrx/logs/litrx.log`

**查看最新日志**:
```bash
tail -f ~/.litrx/logs/litrx.log
```

**查看特定模块的日志**:
```bash
grep "AIModeAssistant\|AIMatrixAssistant" ~/.litrx/logs/litrx.log
```

**查看错误日志**:
```bash
grep "ERROR\|Exception" ~/.litrx/logs/litrx.log
```

## 常见问题排查 | Troubleshooting

### 问题 1: 仍然卡在 "正在生成..."

**可能原因**:
1. AI 请求本身超时（网络问题）
2. 响应格式异常

**排查步骤**:
1. 检查日志，找到最后一条日志消息
2. 如果看到 "Dispatching AI request" 但没有 "AI request completed"，说明是 AI 请求超时
3. 如果看到 "AI request completed" 但没有后续日志，说明在数据提取阶段出错

**解决方案**:
- 检查网络连接
- 尝试更换 AI 服务或模型
- 增加超时时间（在配置中设置 `AI_TIMEOUT_SECONDS`）

### 问题 2: 显示 "解析AI返回失败"

**可能原因**:
- AI 返回的内容不是有效的 JSON/YAML
- 内容被截断

**排查步骤**:
1. 查看日志中的 "Payload preview"
2. 检查是否有语法错误

**解决方案**:
- 简化描述，减少生成复杂度
- 在 prompt 中强调输出格式要求

### 问题 3: pyqtSignal 相关错误

**错误示例**:
```
TypeError: signal signature does not match
```

**可能原因**:
- PyQt6 版本不兼容

**解决方案**:
```bash
pip install --upgrade PyQt6
```

## 性能优化建议 | Performance Optimization

如果生成速度慢，可以：

1. **使用更快的模型**:
   - `gpt-4o-mini` 比 `gpt-4o` 快
   - `gpt-5` 可能比 `gpt-4` 系列快（取决于 OpenAI 的实现）

2. **减少描述复杂度**:
   - 避免要求生成过多问题/维度
   - 分批生成，每次生成一部分

3. **调整超时设置**:
   在配置文件中设置:
   ```yaml
   AI_TIMEOUT_SECONDS: 120  # 默认是 60 秒
   ```

## 反馈问题 | Report Issues

如果问题仍未解决，请提供以下信息：

1. **系统信息**:
   - 操作系统和版本
   - Python 版本
   - PyQt6 版本

2. **完整日志**:
   - 从 "User clicked Generate button" 开始
   - 到卡住或出错为止的所有日志

3. **重现步骤**:
   - 使用的模型
   - 输入的描述
   - 预期结果 vs 实际结果

## 相关文件 | Related Files

修改的文件：
- `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py` - AI 模式助手对话框
- `litrx/gui/dialogs_qt/ai_matrix_assistant_qt.py` - AI 矩阵助手对话框
- `litrx/ai_config_generator.py` - AI 配置生成器

参考文档：
- `CLAUDE.md` - 项目开发指南
- `TEST_AI_ASSISTANTS.md` - AI 助手测试指南（如果存在）
- `docs/AI_ASSISTED_CONFIG_DESIGN.md` - AI 辅助配置设计文档

---

## 技术细节 | Technical Details

### PyQt6 信号/槽机制优势

1. **线程安全**: Qt 自动处理跨线程的信号传递
2. **事件队列**: 信号通过事件队列传递，保证按序执行
3. **类型安全**: 信号声明了参数类型，编译时检查
4. **解耦**: 信号发送者不需要知道接收者的实现

### QTimer.singleShot 的问题

虽然 `QTimer.singleShot(0, fn)` 理论上应该工作，但在以下情况可能失败：

1. **对话框模态性**: 模态对话框可能阻止事件循环处理某些事件
2. **线程生命周期**: daemon 线程可能在 timer 触发前结束
3. **事件循环状态**: 如果事件循环繁忙，timer 可能被延迟
4. **平台差异**: macOS 的事件循环实现与 Linux/Windows 有细微差别

使用 signal/slot 避免了这些问题，因为 Qt 内部使用了更底层、更可靠的机制。

### 日志级别选择

- **DEBUG**: 开发和诊断阶段使用，包含详细的数据预览
- **INFO**: 生产环境使用，记录关键流程节点
- **ERROR**: 始终记录，包含完整的异常栈

在用户报告问题时，建议先设置 `LITRX_LOG_LEVEL=DEBUG` 再复现，以获取完整信息。
