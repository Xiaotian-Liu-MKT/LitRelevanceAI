import json  # 用于解析JSON响应
import os
from pathlib import Path
import sys  # 用于退出脚本
import time
from typing import Any, Dict, Optional, Tuple

import openpyxl
import pandas as pd
import yaml

from .config import (
    DEFAULT_CONFIG as BASE_CONFIG,
    load_env_file,
    load_config as base_load_config,
)
from .ai_client import AIClient


load_env_file()

# GUI 相关库在需要时才导入，避免在纯命令行环境中引入不必要依赖

# 配置部分
DEFAULT_CONFIG = {
    **BASE_CONFIG,
    # 研究配置 - 研究问题可为空
    'RESEARCH_QUESTION': '',  # 空表示通用筛选模式
    'GENERAL_SCREENING_MODE': True,  # 是否启用通用筛选模式

    # 数据文件配置
    'INPUT_FILE_PATH': 'C:/Users/91784/Downloads/scopus (8).csv',  # 例如: 'data/scopus_export.xlsx'
    'OUTPUT_FILE_SUFFIX': '_analyzed',

    # 其他配置
    'API_REQUEST_DELAY': 1,
    'ENABLE_VERIFICATION': True,
    'TITLE_COLUMN_VARIANTS': ['Title', 'Article Title', '标题', '文献标题'],
    'ABSTRACT_COLUMN_VARIANTS': ['Abstract', '摘要', 'Summary'],
}


def load_mode_questions(mode: str) -> Dict[str, Any]:
    """Load questions for a given screening mode from questions_config.json."""

    q_path = Path(__file__).resolve().parent.parent / "questions_config.json"
    try:
        with q_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(mode, {"open_questions": [], "yes_no_questions": []})
    except Exception:
        return {"open_questions": [], "yes_no_questions": []}


def load_prompts() -> Dict[str, str]:
    """Load prompt templates from prompts_config.json."""
    prompts_path = Path(__file__).resolve().parent.parent / "prompts_config.json"
    try:
        with prompts_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("abstract_screening", {})
    except Exception:
        return {}


def load_config(path: Optional[str] = None, mode: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load module configuration and questions for the given mode."""

    default_cfg = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    config = base_load_config(str(path or default_cfg), DEFAULT_CONFIG)

    mode = mode or config.get("CONFIG_MODE", "weekly_screening")
    questions = load_mode_questions(mode)

    return config, questions

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

def prepare_dataframe(df, open_questions, yes_no_questions):
    for q in open_questions:
        df[q['column_name']] = ''
        df[f"{q['column_name']}_verified"] = ''
    for q in yes_no_questions:
        df[q['column_name']] = ''
        df[f"{q['column_name']}_verified"] = ''
    return df

def construct_ai_prompt(title, abstract, research_question, screening_criteria, detailed_analysis_questions, prompts=None):
    """Construct detailed analysis prompt using template."""
    if prompts is None:
        prompts = load_prompts()

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

    # Use template from prompts_config.json or fall back to default
    template = prompts.get("detailed_prompt", """请仔细阅读以下文献的标题和摘要,并结合给定的理论模型/研究问题进行分析。
请严格按照以下JSON格式返回您的分析结果,所有文本内容请使用中文:

文献标题:{title}
文献摘要:{abstract}

理论模型/研究问题:{research_question}

JSON输出格式要求:
{{
{detailed_analysis_section}
    "screening_results": {{
{criteria_prompts_str}
    }}
}}

重要提示:
1.  对于 "detailed_analysis" 内的每一个子问题(如果存在),请提供简洁、针对性的中文回答。如果摘要中信息不足以回答某个子问题,请注明"摘要未提供相关信息"。
2.  对于 "screening_results" 中的每一个筛选条件,请仅使用 "是"、"否" 或 "不确定" 作为回答。
3.  确保整个输出是一个合法的JSON对象。
""")

    return template.format(
        title=title,
        abstract=abstract,
        research_question=research_question,
        detailed_analysis_section=detailed_analysis_section,
        criteria_prompts_str=criteria_prompts_str
    )


def construct_flexible_prompt(title, abstract, config, open_questions, yes_no_questions):
    """Construct prompt using templates from prompts_config.json."""
    prompts = load_prompts()

    if config.get('GENERAL_SCREENING_MODE') or not config.get('RESEARCH_QUESTION'):
        open_q_str = ",\n".join([f'        "{q["key"]}": "{q["question"]}"' for q in open_questions])
        yes_no_str = ",\n".join([f'        "{q["key"]}": "{q["question"]}"' for q in yes_no_questions])

        # Use template from prompts_config.json or fall back to default
        template = prompts.get("quick_prompt", """请快速分析以下文献的标题和摘要,帮助进行每周文献筛选:

文献标题:{title}
文献摘要:{abstract}

请按以下JSON格式回答:
{{
    "quick_analysis": {{
{open_q_str}
    }},
    "screening_results": {{
{yes_no_str}
    }}
}}""")

        return template.format(title=title, abstract=abstract, open_q_str=open_q_str, yes_no_str=yes_no_str)
    else:
        screening_criteria = [q['question'] for q in yes_no_questions]
        detailed = [{'prompt_key': q['key'], 'question_text': q['question'], 'df_column_name': q['column_name']} for q in open_questions]
        return construct_ai_prompt(title, abstract, config['RESEARCH_QUESTION'], screening_criteria, detailed, prompts)

def get_ai_response_with_retry(prompt_text, client, config, open_questions, yes_no_questions, max_retries=3):
    def build_error_response(msg):
        data = {"quick_analysis": {}, "screening_results": {}}
        for q in open_questions:
            data["quick_analysis"][q['key']] = msg
        for q in yes_no_questions:
            data["screening_results"][q['key']] = msg
        return json.dumps(data)

    for attempt in range(max_retries):
        try:
            response = client.request(
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return build_error_response(f"重试{max_retries}次后仍失败: {e}")


def parse_ai_response_json(ai_json_string, open_questions, yes_no_questions):
    """Parse an AI JSON string into quick analysis and screening results.

    The model is expected to return a structure containing ``quick_analysis`` and
    ``screening_results`` sections.  When verifying previous answers, the model
    may wrap these sections inside ``verification_results``.  Missing entries are
    populated with a default "AI未提供此项信息或解析失败" message to simplify
    downstream logic.

    Parameters
    ----------
    ai_json_string:
        Raw JSON string returned by the model.
    open_questions / yes_no_questions:
        Question metadata used to align model keys with dataframe columns.

    Returns
    -------
    dict
        Normalised dictionary with ``quick_analysis`` and ``screening_results``
        subsections.
    """

    final_structure = {
        "quick_analysis": {q['key']: "AI未提供此项信息或解析失败" for q in open_questions},
        "screening_results": {q['key']: "AI未提供此项信息或解析失败" for q in yes_no_questions}
    }

    try:
        if not ai_json_string or not isinstance(ai_json_string, str):
            print("错误：AI响应为空或格式不正确。")
            return final_structure

        data = json.loads(ai_json_string)

        if "verification_results" in data:
            data = data.get("verification_results", {})

        qa = data.get("quick_analysis", {})
        sr = data.get("screening_results", {})
        for q in open_questions:
            final_structure["quick_analysis"][q['key']] = qa.get(q['key'], final_structure["quick_analysis"][q['key']])
        for q in yes_no_questions:
            final_structure["screening_results"][q['key']] = sr.get(q['key'], final_structure["screening_results"][q['key']])

        return final_structure

    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}。AI原始响应: '{ai_json_string[:500]}...'")
    except Exception as e:
        print(f"解析AI响应时发生未知错误: {e}")

    return final_structure


def verify_ai_response(title, abstract, initial_json, client, open_questions, yes_no_questions):
    """Verify that AI answers are supported by the supplied title and abstract.

    The function sends the model a summary of its previous answers and asks it
    to confirm whether each one is backed by the source text.  The model should
    respond with "是", "否" or "不确定" for each question.  The parsed results are
    returned in the same structure as ``parse_ai_response_json``.
    """
    prompts = load_prompts()

    verification_data = {
        "quick_analysis": {
            q["key"]: {
                "question": q["question"],
                "answer": initial_json.get("quick_analysis", {}).get(q["key"], "")
            }
            for q in open_questions
        },
        "screening_results": {
            q["key"]: {
                "question": q["question"],
                "answer": initial_json.get("screening_results", {}).get(q["key"], "")
            }
            for q in yes_no_questions
        },
    }

    open_keys = ", ".join([f'\"{q["key"]}\": \"\"' for q in open_questions])
    yes_no_keys = ", ".join([f'\"{q["key"]}\": \"\"' for q in yes_no_questions])

    # Use template from prompts_config.json or fall back to default
    template = prompts.get("verification_prompt", """请根据以下文献标题和摘要,核对AI之前的回答是否与文献内容一致。
文献标题:{title}
文献摘要:{abstract}

问题与AI初始回答如下:
{verification_data}

请判断每个回答是否得到标题或摘要支持。如支持回答\"是\",不支持回答\"否\",无法判断回答\"不确定\"。请按如下JSON格式返回:
{{
    \"quick_analysis\": {{{open_keys}}},
    \"screening_results\": {{{yes_no_keys}}}
}}""")

    prompt = template.format(
        title=title,
        abstract=abstract,
        verification_data=json.dumps(verification_data, ensure_ascii=False, indent=2),
        open_keys=open_keys,
        yes_no_keys=yes_no_keys
    )

    try:
        response = client.request(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response["choices"][0]["message"]["content"].strip()
        return parse_ai_response_json(content, open_questions, yes_no_questions)
    except Exception as e:
        print(f"验证AI响应失败: {e}")
        return {
            "quick_analysis": {q["key"]: "验证失败" for q in open_questions},
            "screening_results": {q["key"]: "验证失败" for q in yes_no_questions},
        }


def save_progress(df, output_path, current_index):
    temp_path = output_path.replace('.', '_temp.')
    if output_path.endswith('.csv'):
        df.to_csv(temp_path, index=False, encoding='utf-8-sig')
    else:
        df.to_excel(temp_path, index=False, engine='openpyxl')
    progress_info = {
        'last_processed_index': current_index,
        'timestamp': time.time()
    }
    with open(output_path.replace('.', '_progress.json'), 'w', encoding='utf-8') as f:
        json.dump(progress_info, f)


def resume_from_progress(output_path):
    progress_file = output_path.replace('.', '_progress.json')
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        return progress.get('last_processed_index', -1) + 1
    return 0


def generate_weekly_summary(df, criteria_columns):
    summary = {
        'total_articles': len(df),
        'screening_results': {}
    }
    for col in criteria_columns:
        if col in df.columns:
            value_counts = df[col].value_counts()
            summary['screening_results'][col] = {
                '是': int(value_counts.get('是', 0)),
                '否': int(value_counts.get('否', 0)),
                '不确定': int(value_counts.get('不确定', 0))
            }
    return summary

def analyze_article(df, index, row, title_col, abstract_col, open_questions, yes_no_questions, config, client):
    title = str(row[title_col]) if pd.notna(row[title_col]) else "无标题"
    abstract = str(row[abstract_col]) if pd.notna(row[abstract_col]) else "无摘要"

    if title == "无标题" and abstract == "无摘要":
        print("警告：文章标题和摘要均缺失，跳过此条目。")
        for q in open_questions:
            df.at[index, q['column_name']] = "标题和摘要均缺失"
        for q in yes_no_questions:
            df.at[index, q['column_name']] = "无法处理"
        return {}

    prompt = construct_flexible_prompt(title, abstract, config, open_questions, yes_no_questions)
    ai_response_json_str = get_ai_response_with_retry(prompt, client, config, open_questions, yes_no_questions)
    parsed_data = parse_ai_response_json(ai_response_json_str, open_questions, yes_no_questions)

    qa = parsed_data.get('quick_analysis', {})
    for q in open_questions:
        df.at[index, q['column_name']] = qa.get(q['key'], "信息缺失")

    sr = parsed_data.get('screening_results', {})
    for q in yes_no_questions:
        df.at[index, q['column_name']] = sr.get(q['key'], "信息缺失")

    verification = {}
    if config.get('ENABLE_VERIFICATION', True):
        verification = verify_ai_response(title, abstract, parsed_data, client, open_questions, yes_no_questions)
        vqa = verification.get('quick_analysis', {})
        for q in open_questions:
            df.at[index, f"{q['column_name']}_verified"] = vqa.get(q['key'], "验证失败")

        vsr = verification.get('screening_results', {})
        for q in yes_no_questions:
            df.at[index, f"{q['column_name']}_verified"] = vsr.get(q['key'], "验证失败")
    else:
        for q in open_questions:
            df.at[index, f"{q['column_name']}_verified"] = '未验证'
        for q in yes_no_questions:
            df.at[index, f"{q['column_name']}_verified"] = '未验证'

    return {"initial": parsed_data, "verification": verification}


# --- 主程序 ---
def main():
    print("--- AI辅助文献分析脚本启动 ---")

    config, questions = load_config()

    print("正在初始化AI客户端...")
    client = AIClient(config)

    open_questions = questions.get('open_questions', [])
    yes_no_questions = questions.get('yes_no_questions', [])

    print("正在加载数据文件...")
    input_file_path = get_file_path_from_config(config)
    df, title_col, abstract_col = load_and_validate_data(input_file_path, config)

    # 准备DataFrame以存储结果
    df = prepare_dataframe(df, open_questions, yes_no_questions)

    base, ext = os.path.splitext(input_file_path)
    output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
    temp_path = output_file_path.replace('.', '_temp.')
    if os.path.exists(temp_path):
        try:
            df = pd.read_csv(temp_path) if temp_path.endswith('.csv') else pd.read_excel(temp_path)
            print("已加载临时进度文件。")
        except Exception as e:
            print(f"加载临时文件失败: {e}")

    start_index = resume_from_progress(output_file_path)
    total_articles = len(df)
    print(f"共找到 {total_articles} 篇文章待处理。")

    for index, row in df.iloc[start_index:].iterrows():
        print(f"\n正在处理第 {index + 1}/{total_articles} 篇文章...")
        analyze_article(df, index, row, title_col, abstract_col, open_questions, yes_no_questions, config, client)
        save_progress(df, output_file_path, index)
        time.sleep(config['API_REQUEST_DELAY'])

    try:
        if output_file_path.endswith('.csv'):
            df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        elif output_file_path.endswith('.xlsx'):
            df.to_excel(output_file_path, index=False, engine='openpyxl')
        print(f"\n处理完成！结果已保存到: {output_file_path}")
    except Exception as e:
        print(f"保存结果文件时出错: {e}")

    if os.path.exists(temp_path):
        os.remove(temp_path)
    progress_file = output_file_path.replace('.', '_progress.json')
    if os.path.exists(progress_file):
        os.remove(progress_file)

    criteria_columns = [q['column_name'] for q in yes_no_questions]
    summary = generate_weekly_summary(df, criteria_columns)
    print("筛选摘要：", summary)

    print("--- 脚本执行完毕 ---")

def run_gui():
    """创建增强的GUI界面"""
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("文献快速筛选工具")

    file_path_var = tk.StringVar()
    status_var = tk.StringVar()
    q_path = Path(__file__).resolve().parent.parent / "questions_config.json"
    try:
        with q_path.open("r", encoding="utf-8") as f:
            mode_options = list(json.load(f).keys())
    except Exception:
        mode_options = ["weekly_screening"]
    mode_var = tk.StringVar(value=mode_options[0] if mode_options else "")
    progress_var = tk.DoubleVar()

    def browse_file():
        path = filedialog.askopenfilename(filetypes=[("CSV or Excel", ("*.csv", "*.xlsx"))])
        if path:
            file_path_var.set(path)

    def process_file(path, mode):
        config, questions = load_config(mode=mode)
        config['INPUT_FILE_PATH'] = path
        config['CONFIG_MODE'] = mode
        try:
            client = AIClient(config)
            open_q = questions.get('open_questions', [])
            yes_no_q = questions.get('yes_no_questions', [])
            df, title_col, abstract_col = load_and_validate_data(path, config)
            df = prepare_dataframe(df, open_q, yes_no_q)
            total = len(df)
            for index, row in df.iterrows():
                status_var.set(f"处理中: {index + 1}/{total}")
                progress_var.set((index + 1) / total * 100)
                analyze_article(df, index, row, title_col, abstract_col, open_q, yes_no_q, config, client)
                time.sleep(config['API_REQUEST_DELAY'])
            base, ext = os.path.splitext(path)
            output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
            if output_file_path.endswith('.csv'):
                df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(output_file_path, index=False, engine='openpyxl')
            messagebox.showinfo("完成", f"处理完成，结果已保存到: {output_file_path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))
        finally:
            status_var.set("")
            progress_var.set(0)

    def start_analysis():
        path = file_path_var.get()
        if not path:
            messagebox.showerror("错误", "请先选择文件")
            return
        threading.Thread(target=process_file, args=(path, mode_var.get()), daemon=True).start()

    config_frame = ttk.Frame(root)
    config_frame.pack(pady=10)
    ttk.Label(config_frame, text="筛选模式:").pack(side=tk.LEFT)
    ttk.Combobox(config_frame, textvariable=mode_var, values=mode_options).pack(side=tk.LEFT)

    tk.Label(root, text="选择CSV/XLSX文件:").pack(pady=5)
    tk.Entry(root, textvariable=file_path_var, width=40).pack(padx=5)
    tk.Button(root, text="浏览", command=browse_file).pack(pady=5)
    tk.Button(root, text="开始分析", command=start_analysis).pack(pady=5)
    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill=tk.X, padx=20, pady=10)
    tk.Label(root, textvariable=status_var).pack(pady=5)
    root.mainloop()
