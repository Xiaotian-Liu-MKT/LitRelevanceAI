import pandas as pd
import os

import google.generativeai as genai # Gemini SDK
from google.generativeai.types import HarmCategory, HarmBlockThreshold # For safety settings
import openpyxl
import time
import json # 用于解析JSON响应
import sys # 用于退出脚本

import mimetypes # To help guess MIME type for Gemini

# 配置部分
DEFAULT_CONFIG = {
    # AI服务配置
    'AI_SERVICE': 'openai',
    'GEMINI_API_KEY': 'AIzaSyAxKQxMSfqUPnvjcyMfvgAxW5xobvLVkmQ',  # Gemini API密钥
    'GEMINI_MODEL_NAME': 'gemini-2.0-flash',
    
    # 研究配置
    'RESEARCH_QUESTION': 'research regarding awe and meaning in life',
    'CRITERIA': [
        '筛选条件1：文献是否做了field study',
    ],

    # 通用细化分析问题配置
    'DETAILED_ANALYSIS_QUESTIONS': [
        {
            'prompt_key': 'q1_number_of_experiments',
            'question_text': '这篇文献做了几个实验。只要给我数字就行。',
            'df_column_name': 'AI_实验数量'
        },
        {
            'prompt_key': 'q2_number_of_samples ',
            'question_text': '这篇文献一共有多少样本',
            'df_column_name': 'AI_样本数量'
        }
        # Add more questions as needed
    ],

    # 数据文件配置 (MODIFIED)
    'INPUT_PDF_FOLDER_PATH': '/Users/xiaotian/Downloads/250520test', # *** NEW: Specify the folder containing PDF files ***
    # 'INPUT_FILE_PATH': '/Volumes/实验一定成功！/Dropbox/文献检索分析/250520 cited Gordon 2017.xlsx', # This is now replaced by INPUT_PDF_FOLDER_PATH
    'OUTPUT_FILE_SUFFIX': '_analyzed',
    'OUTPUT_FILE_TYPE': 'xlsx', # 'xlsx' or 'csv'

    # 其他配置
    'API_REQUEST_DELAY': 5, # Increased delay as direct file processing can be slower/more intensive
    # 'MAX_TEXT_LENGTH_FOR_PROMPT': 30000 # No longer needed as we are not extracting text manually
}

# --- AI Client Initialization ---
def initialize_ai_clients(config):
    """Initializes and returns AI clients based on the configuration."""
    clients = {}
    if config['AI_SERVICE'] == 'gemini':
        if not config['GEMINI_API_KEY'] or config['GEMINI_API_KEY'] == 'YOUR_GEMINI_API_KEY_HERE':
            print("错误：Gemini API密钥未配置。请在DEFAULT_CONFIG中设置或通过环境变量GEMINI_API_KEY设置。")
            sys.exit(1)
        genai.configure(api_key=config['GEMINI_API_KEY'])
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        clients['gemini'] = genai.GenerativeModel(
            config['GEMINI_MODEL_NAME'],
            safety_settings=safety_settings
            )
        print(f"Gemini 客户端已使用模型 {config['GEMINI_MODEL_NAME']} 初始化 (用于直接PDF处理)。")
    else:
        # This case should ideally not be reached if AI_SERVICE is hardcoded or validated to be 'gemini'
        print(f"错误：无效的AI服务 '{config['AI_SERVICE']}'。此脚本当前仅支持 'gemini'。")
        sys.exit(1)
    return clients

# --- User Input/Config Retrieval ---
def get_user_inputs_from_config(config):
    """Retrieves research questions, criteria, and detailed questions from config."""
    research_question = config['RESEARCH_QUESTION']
    criteria = config['CRITERIA']
    detailed_analysis_questions = config.get('DETAILED_ANALYSIS_QUESTIONS', [])

    if not research_question or research_question == '请在此处定义您的核心研究问题或理论模型。':
        print("错误：研究问题未在CONFIG中定义。")
        sys.exit(1)
    if not criteria or not all(isinstance(c, str) and c for c in criteria):
        print("错误：筛选条件列表为空或包含无效条目。请在CONFIG中定义。")
        sys.exit(1)
    if not detailed_analysis_questions:
        print("警告：未在CONFIG中定义细化分析问题 (DETAILED_ANALYSIS_QUESTIONS)。将不会进行细化分析。")
    elif not all(isinstance(q, dict) and 'prompt_key' in q and 'question_text' in q and 'df_column_name' in q for q in detailed_analysis_questions):
        print("错误：DETAILED_ANALYSIS_QUESTIONS 中的一个或多个条目格式不正确。每个条目应为包含 'prompt_key', 'question_text', 'df_column_name' 的字典。")
        sys.exit(1)
    
    return {
        'research_question': research_question,
        'criteria': criteria,
        'detailed_analysis_questions': detailed_analysis_questions
    }

# --- PDF Folder and File Handling ---
def get_pdf_folder_path_from_config(config):
    """Gets and validates the PDF input folder path from config."""
    folder_path = config['INPUT_PDF_FOLDER_PATH']
    if not folder_path or folder_path == '/path/to/your/pdf_folder': 
         print("错误：输入PDF文件夹路径未在CONFIG中正确配置 (INPUT_PDF_FOLDER_PATH)。")
         sys.exit(1)
    if not os.path.isdir(folder_path):
        print(f"错误：配置文件中指定的PDF文件夹路径 '{folder_path}' 不存在或不是一个目录。")
        sys.exit(1)
    return folder_path

def list_pdf_files(folder_path):
    """Lists all PDF files in the given folder."""
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"警告：在文件夹 '{folder_path}' 中未找到PDF文件。")
    return pdf_files

# --- PDF Text Extraction (Removed as it was for OpenAI) ---
# def extract_text_from_pdf(pdf_path, max_length=None): ...


# --- AI Prompt Construction ---
def construct_ai_prompt_instructions(research_question, screening_criteria, detailed_analysis_questions):
    """
    Constructs the textual instructions part of the prompt for the AI.
    """
    criteria_prompts_str = ",\n".join([f'        "{criterion}": "请回答 \'是\', \'否\', 或 \'不确定\'"' for criterion in screening_criteria])

    detailed_analysis_prompts_list = []
    if detailed_analysis_questions:
        for q_config in detailed_analysis_questions:
            detailed_analysis_prompts_list.append(f'        "{q_config["prompt_key"]}": "{q_config["question_text"]}"')
    detailed_analysis_prompts_str = ",\n".join(detailed_analysis_prompts_list)

    detailed_analysis_section = ""
    if detailed_analysis_prompts_str:
        detailed_analysis_section = f"""
    "detailed_analysis": {{
{detailed_analysis_prompts_str}
    }},"""

    prompt_instructions = f"""请仔细阅读所提供的文献内容，并结合给定的理论模型/研究问题进行分析。
请严格按照以下JSON格式返回您的分析结果，所有文本内容请使用中文：

理论模型/研究问题：{research_question}

JSON输出格式要求：
{{
{detailed_analysis_section}
    "screening_results": {{
{criteria_prompts_str}
    }}
}}

重要提示：
1.  对于 "detailed_analysis" 内的每一个子问题（如果存在），请提供简洁、针对性的中文回答。如果文献内容中信息不足以回答某个子问题，请注明“文献未提供相关信息”。
2.  对于 "screening_results" 中的每一个筛选条件，请仅使用 "是"、"否" 或 "不确定" 作为回答。
3.  确保整个输出是一个合法的JSON对象。
"""
    return prompt_instructions

# --- AI Interaction and Response Parsing ---
def get_ai_response(pdf_file_path, base_prompt_instructions, ai_clients, config, detailed_analysis_questions_config, criteria_config):
    """
    Calls the Gemini AI service with the PDF file and gets the response.
    Returns a JSON string (either valid AI response or an error JSON).
    """
    def _build_error_json(error_message_detail):
        error_da = {}
        if detailed_analysis_questions_config:
            for q_conf in detailed_analysis_questions_config:
                error_da[q_conf['prompt_key']] = error_message_detail
        
        error_sr = {criterion: error_message_detail for criterion in criteria_config}
        
        error_dict = {}
        if error_da: 
            error_dict["detailed_analysis"] = error_da
        error_dict["screening_results"] = error_sr
        
        return json.dumps(error_dict)

    try:
        if config['AI_SERVICE'] == 'gemini': # This should be the only path now
            print(f"  Gemini: 正在准备和上传 PDF '{os.path.basename(pdf_file_path)}' 进行分析...")
            model = ai_clients['gemini']
            
            mime_type, _ = mimetypes.guess_type(pdf_file_path)
            if mime_type is None:
                mime_type = 'application/pdf'
            
            print(f"  Gemini: 使用MIME类型 '{mime_type}' 上传文件 '{os.path.basename(pdf_file_path)}'.")
            pdf_file_for_api = genai.upload_file(path=pdf_file_path, mime_type=mime_type, display_name=os.path.basename(pdf_file_path))
            print(f"  Gemini: 文件 '{os.path.basename(pdf_file_path)}' 上传中...资源名称初步为: {pdf_file_for_api.name}")

            while pdf_file_for_api.state.name == "PROCESSING":
                print(f"  Gemini: 文件 '{os.path.basename(pdf_file_path)}' ({pdf_file_for_api.name}) 仍在处理中，请稍候...")
                time.sleep(5) 
                pdf_file_for_api = genai.get_file(name=pdf_file_for_api.name) 
                if pdf_file_for_api.state.name == "FAILED":
                    print(f"  Gemini: 文件 '{os.path.basename(pdf_file_path)}' ({pdf_file_for_api.name}) 处理失败。")
                    try:
                        genai.delete_file(name=pdf_file_for_api.name)
                        print(f"  Gemini: 已尝试删除处理失败的文件 '{pdf_file_for_api.name}'.")
                    except Exception as delete_e:
                        print(f"  Gemini: 删除处理失败的文件 '{pdf_file_for_api.name}' 时出错: {delete_e}")
                    return _build_error_json(f"错误：Gemini 文件处理失败 - {pdf_file_for_api.name}")

            if pdf_file_for_api.state.name != "ACTIVE":
                 print(f"  Gemini: 文件 '{os.path.basename(pdf_file_path)}' ({pdf_file_for_api.name}) 未激活。当前状态: {pdf_file_for_api.state.name}")
                 return _build_error_json(f"错误：Gemini 文件未激活 - {pdf_file_for_api.name}, 状态: {pdf_file_for_api.state.name}")

            print(f"  Gemini: 文件 '{os.path.basename(pdf_file_path)}' ({pdf_file_for_api.name}) 已激活，准备发送分析请求。")
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json" 
            )
            contents = [
                pdf_file_for_api, 
                base_prompt_instructions 
            ]
            response = model.generate_content(contents, generation_config=generation_config)
            
            try:
                genai.delete_file(name=pdf_file_for_api.name)
                print(f"  Gemini: 已成功处理并删除上传的文件 '{pdf_file_for_api.name}'.")
            except Exception as e_delete:
                print(f"  Gemini: 删除文件 '{pdf_file_for_api.name}' 时出错: {e_delete}")

            return response.text 
        else:
            # This case should not be reached if config is correctly managed
            print(f"严重错误：AI 服务配置不为 'gemini' ({config['AI_SERVICE']})。")
            return _build_error_json(f"严重配置错误：AI 服务不是 'gemini'")
            
    except genai.types.generation_types.BlockedPromptException as e:
        print(f"Gemini API 请求错误 - Prompt被阻止: {e}")
        return _build_error_json("错误：Gemini Prompt被阻止")
    except genai.types.generation_types.StopCandidateException as e: 
        print(f"Gemini API 请求错误 - 内容生成提前停止: {e}")
        return _build_error_json(f"错误：Gemini 内容生成提前停止 - {e}")
    except Exception as e:
        print(f"调用AI服务时发生未知错误 ({config['AI_SERVICE']}): {e}")
        return _build_error_json(f"错误：调用AI服务时发生未知错误 - {e}")

def parse_ai_response_json(ai_json_string, criteria_list, detailed_analysis_questions_config):
    """
    Parses the AI's JSON response string.
    Ensures all expected keys are present in the output, even if parsing fails.
    """
    parsed_detailed_analysis = {}
    if detailed_analysis_questions_config:
        for q_config in detailed_analysis_questions_config:
            parsed_detailed_analysis[q_config['prompt_key']] = "AI未提供此项信息或解析失败"
            
    parsed_criteria_answers = {criterion: "AI未提供此项信息或解析失败" for criterion in criteria_list}
    
    final_response_structure = {}
    if detailed_analysis_questions_config:
        final_response_structure['detailed_analysis'] = parsed_detailed_analysis
    final_response_structure['screening_results'] = parsed_criteria_answers

    try:
        if not ai_json_string or not isinstance(ai_json_string, str):
            error_msg = "AI响应为空或非字符串格式"
            print(f"错误：{error_msg}。")
            if detailed_analysis_questions_config:
                for q_config in detailed_analysis_questions_config:
                    final_response_structure['detailed_analysis'][q_config['prompt_key']] = error_msg
            for criterion in criteria_list:
                final_response_structure['screening_results'][criterion] = error_msg
            return final_response_structure

        data = json.loads(ai_json_string)
        
        if detailed_analysis_questions_config and "detailed_analysis" in data:
            detailed_analysis_data_from_ai = data.get("detailed_analysis", {})
            for q_config in detailed_analysis_questions_config:
                prompt_k = q_config['prompt_key']
                final_response_structure['detailed_analysis'][prompt_k] = detailed_analysis_data_from_ai.get(prompt_k, parsed_detailed_analysis[prompt_k])
        
        screening_results_data_from_ai = data.get("screening_results", {})
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = screening_results_data_from_ai.get(criterion, parsed_criteria_answers[criterion])

        return final_response_structure

    except json.JSONDecodeError as e:
        error_msg = "JSON解析错误"
        print(f"{error_msg}: {e}。AI原始响应: '{ai_json_string[:500]}...'")
        if detailed_analysis_questions_config:
            for q_config in detailed_analysis_questions_config:
                final_response_structure['detailed_analysis'][q_config['prompt_key']] = error_msg
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = error_msg
    except Exception as e:
        error_msg = f"解析时发生未知错误"
        print(f"解析AI响应时发生未知错误: {e}")
        if detailed_analysis_questions_config:
            for q_config in detailed_analysis_questions_config:
                final_response_structure['detailed_analysis'][q_config['prompt_key']] = error_msg
        for criterion in criteria_list:
            final_response_structure['screening_results'][criterion] = error_msg
            
    return final_response_structure

# --- Main Program ---
def main():
    print("--- AI辅助PDF文献分析脚本启动 (仅限Gemini直接PDF处理) ---") # Title updated
    
    config = DEFAULT_CONFIG 
    # Ensure AI_SERVICE is 'gemini' if it's not already hardcoded
    if config.get('AI_SERVICE') != 'gemini':
        print("警告：AI_SERVICE 配置不是 'gemini'。此脚本已修改为仅支持 Gemini。将强制使用 Gemini。")
        config['AI_SERVICE'] = 'gemini'


    print("正在初始化AI客户端...")
    ai_clients = initialize_ai_clients(config)

    print("正在获取分析参数...")
    analysis_params = get_user_inputs_from_config(config)
    research_question = analysis_params['research_question']
    criteria_list = analysis_params['criteria']
    detailed_analysis_questions_config = analysis_params.get('detailed_analysis_questions', [])

    print("正在扫描PDF文件...")
    input_pdf_folder = get_pdf_folder_path_from_config(config)
    pdf_files_names = list_pdf_files(input_pdf_folder)

    if not pdf_files_names:
        print("在指定文件夹中没有找到PDF文件。脚本将退出。")
        sys.exit(0)

    results_data = []
    total_pdfs = len(pdf_files_names)
    print(f"共找到 {total_pdfs} 个PDF文件待处理。")

    base_prompt_instructions = construct_ai_prompt_instructions(
        research_question, 
        criteria_list, 
        detailed_analysis_questions_config
    )

    for index, pdf_filename in enumerate(pdf_files_names):
        print(f"\n正在处理第 {index + 1}/{total_pdfs} 个PDF文件: {pdf_filename}...")
        
        full_pdf_path = os.path.join(input_pdf_folder, pdf_filename)
        current_result = {'PDF文件名': pdf_filename}

        ai_response_json_str = get_ai_response(
            full_pdf_path, 
            base_prompt_instructions, 
            ai_clients, 
            config, 
            detailed_analysis_questions_config, 
            criteria_list
        )
        
        parsed_data = parse_ai_response_json(ai_response_json_str, criteria_list, detailed_analysis_questions_config)
            
        if detailed_analysis_questions_config and 'detailed_analysis' in parsed_data:
            da_responses = parsed_data['detailed_analysis']
            for q_config in detailed_analysis_questions_config:
                current_result[q_config['df_column_name']] = da_responses.get(q_config['prompt_key'], "信息缺失或键不匹配")
        
        if 'screening_results' in parsed_data:
            sr_responses = parsed_data['screening_results']
            for criterion_text in criteria_list:
                current_result[f'筛选_{criterion_text}'] = sr_responses.get(criterion_text, "信息缺失或键不匹配")
        else: 
             for criterion_text in criteria_list:
                current_result[f'筛选_{criterion_text}'] = "AI响应严重错误或解析失败"
        
        results_data.append(current_result)
        print(f"  完成处理: {pdf_filename}")
        time.sleep(config['API_REQUEST_DELAY'])

    df_results = pd.DataFrame(results_data)
    folder_name = os.path.basename(os.path.normpath(input_pdf_folder))
    output_file_base = f"{folder_name}{config['OUTPUT_FILE_SUFFIX']}"
    output_file_ext = f".{config.get('OUTPUT_FILE_TYPE', 'xlsx')}"
    output_folder = input_pdf_folder 
    output_file_path = os.path.join(output_folder, f"{output_file_base}{output_file_ext}")

    try:
        if output_file_ext == '.csv':
            df_results.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        elif output_file_ext == '.xlsx':
            df_results.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"\n处理完成！结果已保存到: {output_file_path}")
    except Exception as e:
        print(f"保存结果文件时出错: {e}")

    print("--- 脚本执行完毕 ---")

if __name__ == '__main__':
    main()
