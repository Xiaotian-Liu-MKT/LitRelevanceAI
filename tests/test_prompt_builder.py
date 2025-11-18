#!/usr/bin/env python
"""测试 PromptBuilder"""

import sys
sys.path.insert(0, '/home/user/LitRelevanceAI')

from litrx.prompt_builder import PromptBuilder

print("=== 测试 PromptBuilder ===\n")

# 测试数据
prompts_config = {}
builder = PromptBuilder(prompts_config)

# 测试 1: 构建详细筛选 prompt
print("1. 测试详细筛选 prompt:")
criteria = ["是否与机器学习相关", "是否包含实验数据"]
detailed_questions = [
    {"prompt_key": "method", "question_text": "使用了什么研究方法?"},
    {"prompt_key": "findings", "question_text": "主要发现是什么?"}
]

prompt = builder.build_screening_prompt(
    title="A Survey of Machine Learning",
    abstract="This paper surveys recent advances in machine learning...",
    research_question="机器学习的最新进展",
    criteria=criteria,
    detailed_questions=detailed_questions
)

assert "A Survey of Machine Learning" in prompt
assert "machine learning" in prompt
assert "机器学习的最新进展" in prompt
assert "是否与机器学习相关" in prompt
assert "使用了什么研究方法" in prompt
print("   ✓ 详细筛选 prompt 构建成功")
print(f"   Prompt 长度: {len(prompt)} 字符\n")

# 测试 2: 构建快速筛选 prompt
print("2. 测试快速筛选 prompt:")
open_questions = [
    {"key": "summary", "question": "请总结文献的主要内容"}
]
yes_no_questions = [
    {"key": "relevant", "question": "是否与研究主题相关?"}
]

quick_prompt = builder.build_flexible_prompt(
    title="Deep Learning Basics",
    abstract="An introduction to deep learning...",
    open_questions=open_questions,
    yes_no_questions=yes_no_questions
)

assert "Deep Learning Basics" in quick_prompt
assert "introduction to deep learning" in quick_prompt
assert "请总结文献的主要内容" in quick_prompt
assert "是否与研究主题相关" in quick_prompt
print("   ✓ 快速筛选 prompt 构建成功")
print(f"   Prompt 长度: {len(quick_prompt)} 字符\n")

# 测试 3: 空问题列表
print("3. 测试空问题列表:")
empty_prompt = builder.build_screening_prompt(
    title="Test Paper",
    abstract="Test abstract",
    research_question="Test question",
    criteria=[],
    detailed_questions=[]
)

assert "Test Paper" in empty_prompt
assert "Test abstract" in empty_prompt
print("   ✓ 空问题列表处理正确\n")

# 测试 4: 使用自定义模板
print("4. 测试自定义模板:")
custom_prompts = {
    "quick_prompt": "标题: {title}\n摘要: {abstract}\n\n问题:\n{open_q_str}"
}
custom_builder = PromptBuilder(custom_prompts)

custom_prompt = custom_builder.build_flexible_prompt(
    title="Custom Title",
    abstract="Custom abstract",
    open_questions=[{"key": "q1", "question": "问题1"}],
    yes_no_questions=[]
)

assert "标题: Custom Title" in custom_prompt
assert "摘要: Custom abstract" in custom_prompt
print("   ✓ 自定义模板工作正常\n")

# 测试 5: 私有方法
print("5. 测试私有方法:")

# 测试 criteria section
criteria_str = builder._build_criteria_section(["条件1", "条件2"])
assert "条件1" in criteria_str
assert "条件2" in criteria_str
assert "请回答" in criteria_str
print("   ✓ _build_criteria_section 工作正常")

# 测试 detailed section
detailed_str = builder._build_detailed_section([
    {"prompt_key": "key1", "question_text": "问题1"}
])
assert "key1" in detailed_str
assert "问题1" in detailed_str
assert "detailed_analysis" in detailed_str
print("   ✓ _build_detailed_section 工作正常")

# 测试空 detailed section
empty_detailed = builder._build_detailed_section([])
assert empty_detailed == ""
print("   ✓ 空 detailed section 返回空字符串\n")

print("✅ 所有 PromptBuilder 测试通过")
