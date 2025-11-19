# AI 助手功能测试指南

## 问题总结

### 原始问题
1. **摘要筛选 AI 助手**：点击按钮时直接闪退
2. **文献矩阵 AI 助手**：可以打开对话框，但关闭时闪退

### 根本原因
两个对话框在初始化时立即创建 `AIClient` 实例，如果 API key 未配置，`AIClient` 会抛出 `RuntimeError`，导致应用崩溃。

## 修复方案

### 修复内容
1. **延迟初始化**：将 AI 生成器的初始化从构造函数推迟到用户点击"生成"按钮时
2. **错误处理**：捕获所有异常并显示友好的错误消息
3. **用户指导**：在错误消息中提示用户如何配置 API 密钥

### 修改的文件
- `litrx/gui/tabs_qt/abstract_tab.py` (修复属性名错误)
- `litrx/gui/dialogs_qt/ai_mode_assistant_qt.py` (延迟初始化 + 错误处理)
- `litrx/gui/dialogs_qt/ai_matrix_assistant_qt.py` (延迟初始化 + 错误处理)

## 测试步骤

### 方法一：使用测试脚本（无需配置 API key）

```bash
cd /home/user/LitRelevanceAI
python test_ai_dialogs.py
```

**预期结果**：
- ✅ 窗口正常打开，显示两个测试按钮
- ✅ 点击任一按钮，对话框正常打开（不崩溃）
- ✅ 可以看到对话框界面和输入框
- ✅ 关闭对话框后应用继续运行（不崩溃）

### 方法二：在主 GUI 中测试

```bash
cd /home/user/LitRelevanceAI
python run_gui.py
```

**测试摘要筛选 AI 助手**：
1. 切换到"摘要筛选"标签页
2. 点击"AI Assistant"按钮
3. 预期：对话框正常打开
4. 在文本框中输入描述（例如："生成一个用于筛选机器学习相关文献的模式"）
5. 点击"Generate"按钮

**预期结果**：
- 如果 **未配置 API key**：
  - ✅ 显示错误对话框
  - ✅ 错误消息包含提示："请在主窗口配置 API 密钥"
  - ✅ 应用不崩溃，可以继续使用

- 如果 **已配置 API key**：
  - ✅ 显示"Generating..."状态
  - ✅ AI 生成筛选模式配置
  - ✅ 预览窗口显示 JSON 配置
  - ✅ 可以点击"Apply"应用配置

**测试文献矩阵 AI 助手**：
1. 切换到"文献矩阵"标签页
2. 点击"🤖 AI 生成维度 / AI Dims"按钮
3. 预期：对话框正常打开
4. 在文本框中输入描述（例如："提取研究方法、样本量、主要发现等维度"）
5. 点击"Generate"按钮

**预期结果**（同上）

### 方法三：配置 API key 后完整测试

**配置 API key**：
1. 在主窗口选择 AI 服务（OpenAI 或 SiliconFlow）
2. 在"API Key"输入框中输入有效的 API 密钥
3. 点击"保存配置"

**测试流程**：
1. 打开 AI 助手对话框
2. 输入自然语言描述
3. 点击"Generate"
4. 查看生成的配置预览
5. 点击"Apply"应用配置
6. 验证配置已正确保存

## 技术细节

### 修复前的代码流程
```python
class AIModeAssistantDialog(QDialog):
    def __init__(self, parent, config):
        # ...
        self._generator = AbstractModeGenerator(config)  # ❌ 立即初始化，可能抛出异常
```

### 修复后的代码流程
```python
class AIModeAssistantDialog(QDialog):
    def __init__(self, parent, config):
        # ...
        self._generator: Optional[AbstractModeGenerator] = None  # ✅ 延迟初始化

    def _on_generate(self):
        try:
            if self._generator is None:
                self._generator = AbstractModeGenerator(self._config)  # ✅ 首次使用时初始化
            # ... 执行生成
        except Exception as e:
            # ✅ 捕获所有异常并显示友好错误消息
```

## 预期改进

### 用户体验改进
1. **无崩溃**：即使未配置 API key，应用也不会崩溃
2. **清晰提示**：错误消息明确告知用户问题所在和解决方法
3. **优雅降级**：用户可以先查看对话框界面，了解功能后再配置 API key

### 开发者体验改进
1. **更好的错误处理**：所有异常都被捕获并妥善处理
2. **测试脚本**：提供独立测试脚本方便验证修复
3. **代码注释**：添加注释说明延迟初始化的原因

## 已知限制

1. **首次生成延迟**：延迟初始化可能导致首次点击"Generate"按钮时稍有延迟
2. **错误消息语言**：当前错误消息为中英双语，未完全国际化

## 后续优化建议

1. **预检查 API key**：在打开对话框前检查 API key 是否配置，显示警告
2. **配置状态指示**：在对话框中显示当前 API 配置状态
3. **示例提示**：在输入框中添加占位符文本，提供示例描述
4. **模板选择**：提供预设模板供用户快速开始

## 相关提交

- **Commit 1**: `4e2f20c` - 修复 abstract_tab.py 中的属性名错误
- **Commit 2**: `4eecfc9` - 防止 AI 助手对话框在无 API key 时崩溃

## 联系方式

如有问题或建议，请在 GitHub 上提交 issue。
