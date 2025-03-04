# 导入模块部分可以按照标准库、第三方库、本地模块的顺序排列
import json
import os
import time
from datetime import datetime
from typing import Dict, List
from tqdm import tqdm

import pandas as pd
from openai import OpenAI

# 新增导入 Gemini API 库
import google.generativeai as genai

# 设置默认的配置
DEFAULT_API_KEY = ""  # 替换成您的 API key，现在支持 OpenAI 和 Gemini
DEFAULT_MODEL_OPENAI = "gpt-4o"  # 设置默认使用的 OpenAI 模型
DEFAULT_MODEL_GEMINI = "gemini-2.0-flash"  # 设置默认使用的 Gemini 模型
DEFAULT_TEMPERATURE = 0.3  # 设置默认的temperature值
DEFAULT_API_TYPE = "gemini" # 默认 API 类型设置为 gemini

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

    def read_scopus_csv(self, file_path: str) -> pd.DataFrame:
        """读取Scopus导出的CSV文件"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            # 确保必要的列存在
            required_columns = ['文献标题', '摘要']
            for col in required_columns:
                if col not in df.columns:
                    # 尝试寻找可能的替代列名
                    if col == '文献标题' and 'Title' in df.columns:
                        df['文献标题'] = df['Title']
                    elif col == '摘要' and 'Abstract' in df.columns:
                        df['摘要'] = df['Abstract']
                    else:
                        raise ValueError(f"CSV文件中缺少必要的列: {col}")

            # 添加分析结果的列
            if '相关性得分' not in df.columns:
                df['相关性得分'] = None
            if '分析结果' not in df.columns:
                df['分析结果'] = None
            if '文献综述建议' not in df.columns:
                df['文献综述建议'] = None

            return df
        except Exception as e:
            raise Exception(f"读取CSV文件失败: {str(e)}")

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
                # 添加安全提示以确保输出JSON格式
                formatted_prompt = prompt + "\n请确保返回有效的JSON格式，不要包含任何额外的文本、代码块标记或解释。"
                
                # 设置生成参数，明确要求结构化输出
                generation_config = {
                    "temperature": DEFAULT_TEMPERATURE,
                    "top_p": 0.95,
                    "top_k": 0,
                    "max_output_tokens": 2048,
                }
                
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]
                
                # 创建具有特定配置的模型
                model = genai.GenerativeModel(
                    model_name=DEFAULT_MODEL_GEMINI,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                response = model.generate_content(formatted_prompt)
                
                # 更健壮的响应解析
                response_text = ""
                try:
                    # 尝试从响应对象获取文本
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'parts'):
                        response_text = response.parts[0].text
                    elif hasattr(response, 'candidates') and response.candidates:
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text'):
                                        response_text = part.text
                                        break
                                if response_text:
                                    break
                    
                    # 清理响应文本，去除可能的代码块标记
                    response_text = response_text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    
                    response_text = response_text.strip()
                    
                    # 尝试解析JSON
                    return json.loads(response_text)
                    
                except (json.JSONDecodeError, AttributeError, IndexError) as e:
                    print(f"解析Gemini响应时出错: {str(e)}")
                    print(f"收到的原始响应: {response}")
                    print(f"提取的文本: {response_text}")
                    
                    # 如果无法解析JSON，尝试使用正则表达式提取关键信息
                    import re
                    try:
                        relevance_score_match = re.search(r'"relevance_score"\s*:\s*(\d+)', response_text)
                        relevance_score = int(relevance_score_match.group(1)) if relevance_score_match else 0
                        
                        analysis_match = re.search(r'"analysis"\s*:\s*"([^"]*)"', response_text)
                        analysis = analysis_match.group(1) if analysis_match else "无法从响应中提取分析结果"
                        
                        lit_review_match = re.search(r'"literature_review_suggestion"\s*:\s*"([^"]*)"', response_text)
                        lit_review = lit_review_match.group(1) if lit_review_match else ""
                        
                        return {
                            "relevance_score": relevance_score,
                            "analysis": analysis,
                            "literature_review_suggestion": lit_review
                        }
                    except Exception:
                        # 如果所有尝试都失败，返回一个基本的响应
                        return {
                            "relevance_score": 0,
                            "analysis": f"无法解析Gemini响应。原始响应: {response_text[:200]}...",
                            "literature_review_suggestion": ""
                        }
        except Exception as e:
            print(f"API调用出错: {str(e)}")
            return {"relevance_score": 0, "analysis": f"分析出错: {str(e)}", "literature_review_suggestion": ""}

    def batch_analyze(self, df: pd.DataFrame, original_file_path: str) -> List[Dict]:
        """批量分析多篇文献"""
        results = []
        total = len(df)

        try:
            for idx, row in tqdm(df.iterrows(), total=len(df), desc="正在分析文献"):
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

                # 保存每次分析结果后的状态
                self.save_results(df, original_file_path, is_interim=True)
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序被用户中断。正在保存已完成的分析结果...")
        finally:
            if len(results) > 0:
                self.save_results(df, original_file_path)  # 使用传入的文件路径

        return results

    def save_results(self, df: pd.DataFrame, original_file_path: str, is_interim=False):
        """保存分析结果到CSV文件"""
        try:
            # 生成新的文件名
            file_dir = os.path.dirname(original_file_path)
            file_name = os.path.splitext(os.path.basename(original_file_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if is_interim:
                # 临时保存用于中间状态，使用固定名称覆盖
                new_file_path = os.path.join(file_dir, f"{file_name}_analyzed_interim.csv")
            else:
                # 最终保存，使用时间戳
                new_file_path = os.path.join(file_dir, f"{file_name}_analyzed_{timestamp}.csv")

            # 保存到新的CSV文件
            df.to_csv(new_file_path, index=False, encoding='utf-8-sig')
            
            if not is_interim:
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
