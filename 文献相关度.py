# 导入模块部分可以按照标准库、第三方库、本地模块的顺序排列
import json
import os
import time
from datetime import datetime
from typing import Dict, List

import pandas as pd
from openai import OpenAI

# 新增导入 Gemini API 库
import google.generativeai as genai

# 设置默认的配置
DEFAULT_API_KEY = ""  # 替换成您的 API key，现在支持 OpenAI 和 Gemini
DEFAULT_MODEL_OPENAI = "gpt-4o"  # 设置默认使用的 OpenAI 模型
DEFAULT_MODEL_GEMINI = "Gemini 2.0 Flash"  # 设置默认使用的 Gemini 模型
DEFAULT_TEMPERATURE = 0.3  # 设置默认的temperature值
DEFAULT_API_TYPE = "gemini" # 默认 API 类型设置为 openai，用户可以选择 "gemini"

class LiteratureAnalyzer:
    def __init__(self, api_key: str, research_topic: str, api_type: str = DEFAULT_API_TYPE):
        self.research_topic = research_topic
        self.api_type = api_type
        if api_type == "openai":
            self.client = OpenAI(api_key=api_key)
        elif api_type == "gemini":
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(DEFAULT_MODEL_GEMINI)
        else:
            raise ValueError("不支持的 API 类型，目前仅支持 'openai' 或 'gemini'")

    def analyze_paper(self, title: str, abstract: str) -> Dict:
        """分析单篇文献与研究课题的相关性"""
        prompt = f"""请分析以下文献与研究课题"{self.research_topic}"的相关性:

文献标题: {title}
摘要: {abstract}

请提供以下信息:
1. 相关性分析（详细说明该文献与研究课题的关联点）
2. 给出一个0-100的相关性评分，其中0表示完全无关，100表示高度相关
3. 如果要把这篇文章写入关于该研究课题的文献综述中，这篇文章应该如何被引用和讨论？请直接告诉我你会怎么写。

请用以下JSON格式返回:
{{
    "relevance_score": <数字>,
    "analysis": "<分析文本>",
    "literature_review_suggestion": "<文献综述建议>"
}}"""

        try:
            if self.api_type == "openai":
                response = self.client.chat.completions.create(
                    model=DEFAULT_MODEL_OPENAI,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=DEFAULT_TEMPERATURE
                )
                return json.loads(response.choices[0].message.content)
            else:  # gemini
                response = self.client.generate_content(prompt)
                # 修复 Gemini 响应解析
                try:
                    # 尝试直接解析响应文本
                    return json.loads(response.text)
                except (json.JSONDecodeError, AttributeError):
                    # 如果失败，尝试从 response 对象获取内容
                    try:
                        if hasattr(response, 'candidates') and response.candidates:
                            return json.loads(response.candidates[0].content.parts[0].text)
                        else:
                            return {"relevance_score": 0, "analysis": "无法解析 Gemini API 响应"}
                    except Exception:
                        return {"relevance_score": 0, "analysis": "无法解析 Gemini API 响应"}
        except Exception as e:
            print(f"API调用出错: {str(e)}")
            return {"relevance_score": 0, "analysis": f"分析出错: {str(e)}", "literature_review_suggestion": ""}

    def batch_analyze(self, df: pd.DataFrame, original_file_path: str) -> List[Dict]:
        """批量分析多篇文献"""
        results = []
        total = len(df)

        try:
            for idx, row in df.iterrows():
                print(f"\n正在分析第 {idx + 1}/{total} 篇文献...")
                print(f"标题: {row['文献标题']}")

                if pd.isna(row['文献标题']) or pd.isna(row['摘要']):
                    print(f"警告: 该文献的标题或摘要为空，已跳过")
                    continue

                result = self.analyze_paper(row['文献标题'], row['摘要'])
                result['title'] = row['文献标题']
                results.append(result)

                print(f"相关性得分: {result['relevance_score']}")
                print(f"分析结果: {result['analysis'][:200]}...")

                # 实时更新原CSV文件
                df.at[idx, '相关性得分'] = result['relevance_score']
                df.at[idx, '分析结果'] = result['analysis']
                df.at[idx, '文献综述建议'] = result.get('literature_review_suggestion', '')

                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序被用户中断。正在保存已完成的分析结果...")
        finally:
            if len(results) > 0:
                self.save_results(df, original_file_path)  # 使用传入的文件路径

        return results

    def save_results(self, df: pd.DataFrame, original_file_path: str):
        """保存分析结果到原CSV文件"""
        try:
            # 生成新的文件名
            file_dir = os.path.dirname(original_file_path)
            file_name = os.path.splitext(os.path.basename(original_file_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_file_path = os.path.join(file_dir, f"{file_name}_analyzed_{timestamp}.csv")

            # 保存到新的CSV文件
            df.to_csv(new_file_path, index=False, encoding='utf-8-sig')
            print(f"\n分析结果已保存到: {os.path.abspath(new_file_path)}")
        except Exception as e:
            print(f"保存结果时出错: {str(e)}")


def get_user_input():
    """获取用户输入的配置信息"""
    print("欢迎使用文献相关性分析工具!\n")

    # 选择 API 类型
    while True:
        api_type = input("请选择要使用的 API 类型 (1: OpenAI, 2: Gemini): ").strip()
        if api_type == "1":
            api_type = "openai"
            break
        elif api_type == "2":
            api_type = "gemini"
            break
        print("无效的选择，请输入 1 或 2")

    # 使用默认API密钥
    print(f"使用默认API密钥")
    api_key = DEFAULT_API_KEY

    # 获取研究课题
    research_topic = input("\n请输入您的研究课题: ").strip()
    while not research_topic:
        research_topic = input("研究课题不能为空，请重新输入: ").strip()

    # 获取CSV文件路径
    while True:
        file_path = input("\n请输入Scopus导出的CSV文件路径（可直接拖拽文件到此处）: ").strip()

        # 处理用户输入的路径
        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]  # 去除引号

        abs_path = os.path.abspath(file_path)
        if os.path.exists(abs_path):
            break
        else:
            print(f"找不到文件: {abs_path}")
            print("请确保：")
            print("1. 文件路径正确")
            print("2. 文件确实存在")
            print("3. 如果路径包含空格，请用引号括起来")
            print("提示：可以直接将文件拖拽到终端窗口中\n")

    return api_key, research_topic, abs_path, api_type


def main():
    try:
        # 获取用户输入
        api_key, research_topic, file_path, api_type = get_user_input()

        print("\n正在初始化分析器...")
        analyzer = LiteratureAnalyzer(api_key, research_topic, api_type)

        print("正在读取文献数据...")
        df = analyzer.read_scopus_csv(file_path)

        print(f"\n共找到 {len(df)} 篇文献，开始分析...\n")
        results = analyzer.batch_analyze(df, file_path)  # 传入实际的文件路径而非字符串常量

        # 打印统计摘要
        relevance_scores = [r['relevance_score'] for r in results]
        print("\n分析完成!")
        print(f"文献总数: {len(results)}")
        if relevance_scores:
            print(f"平均相关性得分: {sum(relevance_scores) / len(relevance_scores):.2f}")
            print(f"高相关文献数量 (得分>=80): {len([s for s in relevance_scores if s >= 80])}")

    except Exception as e:
        print(f"\n程序运行出错: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        print(traceback.format_exc())

    input("\n按回车键退出程序...")


if __name__ == "__main__":
    main()
