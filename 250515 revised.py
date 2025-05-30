import pandas as pd
import os
import openai # OpenAI SDK v1.x.x
import google.generativeai as genai # Gemini SDK
import openpyxl
import time
import json # 用于解析JSON响应
import sys # 用于退出脚本

# 配置部分
DEFAULT_CONFIG = {
    # AI服务配置
    'AI_SERVICE': 'openai',  # 可选: 'openai' 或 'gemini'
    'OPENAI_API_KEY': '',  # OpenAI API密钥
    'GEMINI_API_KEY': 'your_gemini_api_key',  # Gemini API密钥
    'OPENAI_MODEL_NAME': 'gpt-4o-mini',
    'GEMINI_MODEL_NAME': 'gemini-1.5-pro-latest',
    
    # 研究配置 (这些可以考虑从用户输入或单独的配置文件读取)
    'RESEARCH_QUESTION': '请在此处定义您的核心研究问题或理论模型。',
    'CRITERIA': [
        '筛选条件1：',
        '筛选条件2：',
        '筛选条件3：',
    ],

    # 通用细化分析问题配置
    # 用户可以定义任意数量和内容的细化问题
    # 每个问题由一个字典定义，包含:
    #   'prompt_key': 在发送给AI的JSON中使用的键名 (建议使用英文下划线命名法)
    #   'question_text': 向AI提出的具体问题文本 (中文)
    #   'df_column_name': 在输出Excel/CSV中对应的列名 (中文)
    'DETAILED_ANALYSIS_QUESTIONS': [
        {
            'prompt_key': 'q1_main_focus', # 示例键名
            'question_text': '这篇文献的核心研究焦点是什么？请用一句话概括。', # 示例问题
            'df_column_name': 'AI_核心焦点' # 示例列名
        },
        {
            'prompt_key': 'q2_methodology',
            'question_text': '文献采用了什么主要的研究方法（例如：实验、调查、案例分析、文献综述等）？',
            'df_column_name': 'AI_研究方法'
        },
        {
            'prompt_key': 'q3_key_findings',
            'question_text': '文献的主要发现或结论有哪些（列举1-2个最重要的）？',
            'df_column_name': 'AI_主要发现'
        },
        {
            'prompt_key': 'q4_relevance_to_rq',
            'question_text': '这篇文献与上述定义的“研究问题/理论模型”的关联性体现在哪些方面？',
            'df_column_name': 'AI_与RQ关联点'
        }
        # 用户可以根据需要添加更多或修改现有问题
        # 例如，针对特定研究问题："The influence of natural (vs. artificial) sweeteners in food/drink on consumers' purchase intention"
        # 可以这样配置：
        # {
        #     'prompt_key': 'sweetener_type_focus',
        #     'question_text': '这篇文献主要关注哪种类型的甜味剂（天然、人造、两者皆有、未区分）？',
        #     'df_column_name': 'AI_甜味剂类型焦点'
        # },
        # {
        #     'prompt_key': 'purchase_intention_link',
        #     'question_text': '文献是如何将甜味剂与消费者的“购买意愿”联系起来的？',
        #     'df_column_name': 'AI_购买意愿关联方式'
        # },
    ],

    # 数据文件配置
    'INPUT_FILE_PATH': '/Volumes/实验一定成功！/Dropbox/文献检索分析/test.xlsx', # 例如: 'data/scopus_export.xlsx'
    'OUTPUT_FILE_SUFFIX': '_analyzed',

    # 其他配置
    'API_REQUEST_DELAY': 1, 
    'TITLE_COLUMN_VARIANTS': ['Title', 'Article Title', '标题', '文献标题'],
    'ABSTRACT_COLUMN_VARIANTS': ['Abstract', '摘要', 'Summary'],
}

def initialize_ai_clients(config):
    clients = {}
    if config['AI_SERVICE'] == 'openai':
        if config['OPENAI_API_KEY'] == 'YOUR_OPENAI_API_KEY_HERE' or not config['OPENAI_API_KEY']:
            print("错误：OpenAI API密钥未配置。请在DEFAULT_CONFIG中设置或通过环境变量OPENAI_API_KEY设置。")
            sys.exit(1)
        clients['openai'] = openai.OpenAI(api_key=config['OPENAI_API_KEY'])
        print(f"OpenAI 客户端已使用模型 {config['OPENAI_MODEL_NAME']} 初始化。")
    elif config['AI_SERVICE'] == 'gemini':
        if config['GEMINI_API_KEY'] == 'YOUR_GEMINI_API_KEY_HERE' or not config['GEMINI_API_KEY']:
            print("错误：Gemini API密钥未配置。请在DEFAULT_CONFIG中设置或通过环境变量GEMINI_API_KEY设置。")
            sys.exit(1)
        genai.configure(api_key=config['GEMINI_API_KEY'])
        clients['gemini'] = genai.GenerativeModel(config['GEMINI_MODEL_NAME'])
        print(f"Gemini 客户端已使用模型 {config['GEMINI_MODEL_NAME']} 初始化。")
    else:
        print(f"错误：无效的AI服务 '{config['AI_SERVICE']}'。必须是 'openai' 或 'gemini'。")
        sys.exit(1)
    return clients

def get_user_inputs_from_config(config):
    research_question = config['RESEARCH_QUESTION']
    criteria = config['CRITERIA']
    detailed_analysis_questions = config.get('DETAILED_ANALYSIS_QUESTIONS', [])

    if not research_question or research_question == '请在此处定义您的核心研究问题或理论模型。':
        print("错误：研究问题未在CONFIG中定义。")
        sys.exit(1)
    if not criteria or not all(isinstance(c, str) and c for c in criteria): # 检查criteria是否有效
        print("错误：筛选条件列表为空或包含无效条目。请在CONFIG中定义。")
        sys.exit(1)
    if not detailed_analysis_questions: # 检查细化问题是否至少有一个
        print("警告：未在CONFIG中定义细化分析问题 (DETAILED_ANALYSIS_QUESTIONS)。将不会进行细化分析。")
    elif not all(isinstance(q, dict) and 'prompt_key' in q and 'question_text' in q and 'df_column_name' in q for q in detailed_analysis_questions):
        print("错误：DETAILED_ANALYSIS_QUESTIONS 中的一个或多个条目格式不正确。每个条目应为包含 'prompt_key', 'question_text', 'df_column_name' 的字典。")
        sys.exit(1)


    return {
        'research_question': research_question,
        'criteria': criteria,
        'detailed_analysis_questions': detailed_analysis_questions
    }

def get_file_path_from_config(config):
    file_path = config['INPUT_FILE_PATH']
    if not file_path or file_path == 'your_input_file.xlsx':
         print("错误：输入文件路径未在CONFIG中正确配置。")
         sys.exit(1)
    if not os.path.exists(file_path):
        print(f"错误：配置文件中指定的文件路径 '{file_path}' 不存在。")
        sys.exit(1)
    if not (file_path.endswith('.csv') or file_path.endswith('.xlsx')):
        print(f"错误：文件 '{file_path}' 不是支持的CSV或Excel格式。")
        sys.exit(1)
    return file_path

def load_and_validate_data(file_path, config):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
    except Exception as e:
        print(f"读取文件 '{file_path}' 时出错: {e}")
        sys.exit(1)

    title_column = None
    for col_name_variant in config['TITLE_COLUMN_VARIANTS']:
        if col_name_variant in df.columns:
            title_column = col_name_variant
            break
    abstract_column = None
    for col_name_variant in config['ABSTRACT_COLUMN_VARIANTS']:
        if col_name_variant in df.columns:
            abstract_column = col_name_variant
            break

    if not title_column:
        print(f"警告：无法自动识别标题列。尝试过的名称：{config['TITLE_COLUMN_VARIANTS']}")
        title_column_input = input("请手动输入标题列的准确名称: ").strip()
        if title_column_input not in df.columns:
            print(f"错误：输入的标题列 '{title_column_input}' 不存在于文件中。")
            sys.exit(1)
        title_column = title_column_input
    if not abstract_column:
        print(f"警告：无法自动识别摘要列。尝试过的名称：{config['ABSTRACT_COLUMN_VARIANTS']}")
        abstract_column_input = input("请手动输入摘要列的准确名称: ").strip()
        if abstract_column_input not in df.columns:
            print(f"错误：输入的摘要列 '{abstract_column_input}' 不存在于文件中。")
            sys.exit(1)
        abstract_column = abstract_column_input
    print(f"成功识别列 - 标题: '{title_column}', 摘要: '{abstract_column}'")
    return df, title_column, abstract_column

def construct_ai_prompt(title, abstract, research_question, screening_criteria, detailed_analysis_questions):
    criteria_prompts_str = ",\n".join([f'        "{criterion}": "请回答 \'是\', \'否\', 或 \'不确定\'"' for criterion in screening_criteria])

    detailed_analysis_prompts_list = []
    if detailed_analysis_questions: # 仅当定义了细化问题时才构建这部分
        for q_config in detailed_analysis_questions:
            detailed_analysis_prompts_list.append(f'        "{q_config["prompt_key"]}": "{q_config["question_text"]}"')
    detailed_analysis_prompts_str = ",\n".join(detailed_analysis_prompts_list)

    # 构建 detailed_analysis 部分，仅当存在细化问题时
    detailed_analysis_section = ""
    if detailed_analysis_prompts_str:
        detailed_analysis_section = f"""
    "detailed_analysis": {{
{detailed_analysis_prompts_str}
    }},""" # 注意这里末尾的逗号，如果 screening_results 存在则需要

    prompt = f"""请仔细阅读以下文献的标题和摘要，并结合给定的理论模型/研究问题进行分析。
请严格按照以下JSON格式返回您的分析结果，所有文本内容请使用中文：

文献标题：{title}
文献摘要：{abstract}

理论模型/研究问题：{research_question}

JSON输出格式要求：
{{
{detailed_analysis_section}
    "screening_results": {{
{criteria_prompts_str}
    }}
}}

重要提示：
1.  对于 "detailed_analysis" 内的每一个子问题（如果存在），请提供简洁、针对性的中文回答。如果摘要中信息不足以回答某个子问题，请注明“摘要未提供相关信息”。
2.  对于 "screening_results" 中的每一个筛选条件，请仅使用 "是"、"否" 或 "不确定" 作为回答。
3.  确保整个输出是一个合法的JSON对象。
"""
    return prompt

def get_ai_response(prompt_text, ai_clients, config, detailed_analysis_questions_config, criteria_config):
    """调用选定的AI服务并获取响应。在出错时返回包含所有预期键的错误JSON。"""
    # 构建错误响应的辅助函数
    def _build_error_json(error_message):
        error_da = {}
        if detailed_analysis_questions_config:
            for q_conf in detailed_analysis_questions_config:
                error_da[q_conf['prompt_key']] = error_message
        
        error_sr = {criterion: error_message for criterion in criteria_config}
        
        error_dict = {}
        if error_da: # 只有在有细化问题时才添加detailed_analysis键
            error_dict["detailed_analysis"] = error_da
        error_dict["screening_results"] = error_sr
        
        return json.dumps(error_dict)

    try:
        if config['AI_SERVICE'] == 'openai':
            client = ai_clients['openai']
            response = client.chat.completions.create(
                model=config['OPENAI_MODEL_NAME'],
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.5, 
                response_format={"type": "json_object"} 
            )
            return response.choices[0].message.content.strip()
        
        elif config['AI_SERVICE'] == 'gemini':
            model = ai_clients['gemini']
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" 
            )
            response = model.generate_content(prompt_text, generation_config=generation_config)
            return response.text 
            
    except openai.APIError as e:
        print(f"OpenAI API 请求错误: {e}")
        return _build_error_json(f"错误：OpenAI API 请求错误 - {e}")
    except genai.types.generation_types.BlockedPromptException as e:
        print(f"Gemini API 请求错误 - Prompt被阻止: {e}")
        return _build_error_json("错误：Gemini Prompt被阻止")
    except Exception as e:
        print(f"调用AI服务时发生未知错误 ({config['AI_SERVICE']}): {e}")
        return _build_error_json(f"错误：调用AI服务时发生未知错误 - {e}")
    # return None # 不应该到达这里，因为上面已经返回了错误JSON


def parse_ai_response_json(ai_json_string, criteria_list, detailed_analysis_questions_config):
    """
    解析AI返回的JSON字符串。
    detailed_analysis_questions_config: 配置中定义的细化问题列表。
    """
    # 为所有预期的键设置默认错误/未提供信息的值
    parsed_detailed_analysis = {}
    if detailed_analysis_questions_config:
        for q_config in detailed_analysis_questions_config:
            parsed_detailed_analysis[q_config['prompt_key']] = "AI未提供此项信息或解析失败"
            
    parsed_criteria_answers = {criterion: "AI未提供此项信息或解析失败" for criterion in criteria_list}
    
    final_response_structure = {}
    if detailed_analysis_questions_config: # 仅当配置了细化问题时，最终结构才包含 detailed_analysis
        final_response_structure['detailed_analysis'] = parsed_detailed_analysis
    final_response_structure['screening_results'] = parsed_criteria_answers


    try:
        if not ai_json_string or not isinstance(ai_json_string, str):
            print(f"错误：AI响应为空或格式不正确。")
            # 更新错误信息
            if detailed_analysis_questions_config:
                for q_config in detailed_analysis_questions_config:
                    final_response_structure['detailed_analysis'][q_config['prompt_key']] = "AI响应为空或格式不正确"
            for criterion in criteria_list:
                final_response_structure['screening_results'][criterion] = "AI响应为空或格式不正确"
            return final_response_structure

        data = json.loads(ai_json_string)
        
        # 提取细化分析部分 (如果存在)
        if detailed_analysis_questions_config and "detailed_analysis" in data:
            detailed_analysis_data_from_ai = data.get("detailed_analysis", {})
            for q_config in detailed_analysis_questions_config:
                prompt_k = q_config['prompt_key']
                # 使用 get 获取值，如果键不存在于AI响应中，则保留默认的“未提供信息”
                final_response_structure['detailed_analysis'][prompt_k] = detailed_analysis_data_from_ai.get(prompt_k, parsed_detailed_analysis[prompt_k])
        
        # 提取筛选结果
        screening_results_data_from_ai = data.get("screening_results", {})
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = screening_results_data_from_ai.get(criterion, parsed_criteria_answers[criterion])

        return final_response_structure # 返回包含所有预期键的字典

    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}。AI原始响应: '{ai_json_string[:500]}...'")
        if detailed_analysis_questions_config:
            for q_config in detailed_analysis_questions_config:
                final_response_structure['detailed_analysis'][q_config['prompt_key']] = "JSON解析错误"
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = "JSON解析错误"
    except Exception as e:
        print(f"解析AI响应时发生未知错误: {e}")
        if detailed_analysis_questions_config:
            for q_config in detailed_analysis_questions_config:
                final_response_structure['detailed_analysis'][q_config['prompt_key']] = f"解析时发生未知错误"
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = f"解析时发生未知错误"
            
    return final_response_structure


# --- 主程序 ---
def main():
    print("--- AI辅助文献分析脚本启动 ---")
    
    config = DEFAULT_CONFIG 

    print("正在初始化AI客户端...")
    ai_clients = initialize_ai_clients(config)

    print("正在获取分析参数...")
    analysis_params = get_user_inputs_from_config(config)
    research_question = analysis_params['research_question']
    criteria_list = analysis_params['criteria']
    detailed_analysis_questions_config = analysis_params.get('detailed_analysis_questions', []) # 这是问题配置的列表

    print("正在加载数据文件...")
    input_file_path = get_file_path_from_config(config)
    df, title_col, abstract_col = load_and_validate_data(input_file_path, config)

    # 准备DataFrame以存储结果
    if detailed_analysis_questions_config:
        for q_config in detailed_analysis_questions_config:
            df[q_config['df_column_name']] = '' # 使用配置中定义的列名
    
    for criterion_text in criteria_list:
        df[f'筛选_{criterion_text}'] = '' 

    total_articles = len(df)
    print(f"共找到 {total_articles} 篇文章待处理。")

    for index, row in df.iterrows():
        print(f"\n正在处理第 {index + 1}/{total_articles} 篇文章...")
        
        title = str(row[title_col]) if pd.notna(row[title_col]) else "无标题"
        abstract = str(row[abstract_col]) if pd.notna(row[abstract_col]) else "无摘要"

        if title == "无标题" and abstract == "无摘要":
            print("警告：文章标题和摘要均缺失，跳过此条目。")
            if detailed_analysis_questions_config:
                for q_config in detailed_analysis_questions_config:
                    df.at[index, q_config['df_column_name']] = "标题和摘要均缺失"
            for criterion_text in criteria_list:
                df.at[index, f'筛选_{criterion_text}'] = "无法处理"
            continue

        prompt = construct_ai_prompt(title, abstract, research_question, criteria_list, detailed_analysis_questions_config)
        ai_response_json_str = get_ai_response(prompt, ai_clients, config, detailed_analysis_questions_config, criteria_list)

        # 解析响应，即使是错误JSON，也会返回包含所有预期键的结构
        parsed_data = parse_ai_response_json(ai_response_json_str, criteria_list, detailed_analysis_questions_config)
            
        # 填充细化分析结果 (如果配置了)
        if detailed_analysis_questions_config and 'detailed_analysis' in parsed_data:
            da_responses = parsed_data['detailed_analysis']
            for q_config in detailed_analysis_questions_config:
                # da_responses 的键是 prompt_key, q_config['df_column_name'] 是要写入的列名
                df.at[index, q_config['df_column_name']] = da_responses.get(q_config['prompt_key'], "信息缺失或键不匹配")
        
        # 填充筛选结果
        if 'screening_results' in parsed_data:
            sr_responses = parsed_data['screening_results']
            for criterion_text in criteria_list:
                df.at[index, f'筛选_{criterion_text}'] = sr_responses.get(criterion_text, "信息缺失或键不匹配")
        else: # 如果连 screening_results 都没有，说明解析非常失败
             for criterion_text in criteria_list:
                df.at[index, f'筛选_{criterion_text}'] = "AI响应严重错误"
            
        time.sleep(config['API_REQUEST_DELAY'])

    base, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
    
    try:
        if output_file_path.endswith('.csv'):
            df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        elif output_file_path.endswith('.xlsx'):
            df.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"\n处理完成！结果已保存到: {output_file_path}")
    except Exception as e:
        print(f"保存结果文件时出错: {e}")

    print("--- 脚本执行完毕 ---")

if __name__ == '__main__':
    main()
