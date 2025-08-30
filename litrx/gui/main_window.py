import os
import io
import sys
import threading
from typing import Dict
from contextlib import redirect_stdout
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ..config import DEFAULT_CONFIG as BASE_CONFIG, load_env_file
from ..ai_client import AIClient
from ..csv_analyzer import LiteratureAnalyzer
from ..abstract_screener import (
    get_user_inputs_from_config,
    load_and_validate_data,
    prepare_dataframe,
    analyze_article,
    DEFAULT_CONFIG as ABSTRACT_CONFIG,
)
from ..pdf_screener import main as pdf_main, DEFAULT_CONFIG as PDF_CONFIG

load_env_file()

class MainWindow:
    """Main application window with tabs for different tools."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("LitRx Toolkit")
        self.base_config: Dict[str, str] = BASE_CONFIG.copy()

        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.api_key_var, width=40, show="*").pack(side=tk.LEFT, padx=5)
        ttk.Label(top, text="Model:").pack(side=tk.LEFT, padx=(10, 0))
        self.model_var = tk.StringVar(value=self.base_config.get("MODEL_NAME", ""))
        ttk.Entry(top, textvariable=self.model_var, width=20).pack(side=tk.LEFT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.init_csv_tab(notebook)
        self.init_abstract_tab(notebook)
        self.init_pdf_tab(notebook)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def build_config(self) -> Dict[str, str]:
        config = self.base_config.copy()
        api_key = self.api_key_var.get().strip()
        if api_key:
            config["OPENAI_API_KEY"] = api_key
            config["AI_SERVICE"] = config.get("AI_SERVICE", "openai")
        model = self.model_var.get().strip()
        if model:
            config["MODEL_NAME"] = model
        return config

    def browse_file(self, var: tk.StringVar, filetypes):
        path = filedialog.askopenfilename(filetypes=[filetypes])
        if path:
            var.set(path)

    def browse_folder(self, var: tk.StringVar) -> None:
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    # ------------------------------------------------------------------
    # CSV relevance tab
    # ------------------------------------------------------------------
    def init_csv_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="CSV 相关性分析")

        ttk.Label(frame, text="研究主题:").pack(anchor=tk.W, padx=5, pady=2)
        self.csv_topic_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.csv_topic_var, width=40).pack(fill=tk.X, padx=5)

        ttk.Label(frame, text="选择CSV文件:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5)
        self.csv_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.csv_file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="浏览", command=lambda: self.browse_file(self.csv_file_var, ("CSV 文件", "*.csv"))).pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="开始分析", command=self.start_csv_analysis).pack(pady=5)

        self.csv_progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.csv_progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)

        self.csv_result = tk.Text(frame, height=10)
        self.csv_result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    def start_csv_analysis(self) -> None:
        path = self.csv_file_var.get()
        topic = self.csv_topic_var.get()
        if not path or not topic:
            messagebox.showerror("错误", "请填写研究主题并选择文件")
            return
        threading.Thread(target=self.process_csv, args=(path, topic), daemon=True).start()

    def process_csv(self, path: str, topic: str) -> None:
        config = self.build_config()
        analyzer = LiteratureAnalyzer(config, topic)
        try:
            df = analyzer.read_scopus_csv(path)
        except Exception as e:
            self.csv_result.insert(tk.END, f"读取文件失败: {e}\n")
            return
        total = len(df)
        for i, (idx, row) in enumerate(df.iterrows(), start=1):
            try:
                res = analyzer.analyze_paper(row['Title'], row['Abstract'])
                df.at[idx, 'Relevance Score'] = res['relevance_score']
                df.at[idx, 'Analysis Result'] = res['analysis']
                df.at[idx, 'Literature Review Suggestion'] = res.get('literature_review_suggestion', '')
                self.csv_result.insert(tk.END, f"{row['Title']}: {res['relevance_score']}\n")
            except Exception as e:
                self.csv_result.insert(tk.END, f"{row['Title']}: 错误 {e}\n")
            self.csv_progress.set(i / total * 100)
        analyzer.save_results(df, path)
        self.csv_result.insert(tk.END, "分析完成\n")

    # ------------------------------------------------------------------
    # Abstract screening tab
    # ------------------------------------------------------------------
    def init_abstract_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="摘要筛选")

        ttk.Label(frame, text="选择CSV/XLSX文件:").pack(anchor=tk.W, padx=5, pady=2)
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5)
        self.abs_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.abs_file_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="浏览", command=lambda: self.browse_file(self.abs_file_var, ("CSV or Excel", "*.csv *.xlsx"))).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="筛选模式:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        self.abs_mode_var = tk.StringVar(value=ABSTRACT_CONFIG.get('CONFIG_MODE', 'weekly_screening'))
        ttk.Combobox(frame, textvariable=self.abs_mode_var, values=["weekly_screening", "specific_research"]).pack(fill=tk.X, padx=5)

        ttk.Button(frame, text="开始筛选", command=self.start_abstract_screen).pack(pady=5)

        self.abs_progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.abs_progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)
        self.abs_status = tk.StringVar()
        ttk.Label(frame, textvariable=self.abs_status).pack(pady=(0, 5))

        self.abs_result = tk.Text(frame, height=10)
        self.abs_result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    def start_abstract_screen(self) -> None:
        path = self.abs_file_var.get()
        if not path:
            messagebox.showerror("错误", "请先选择文件")
            return
        mode = self.abs_mode_var.get()
        threading.Thread(target=self.process_abstract, args=(path, mode), daemon=True).start()

    def process_abstract(self, path: str, mode: str) -> None:
        config = ABSTRACT_CONFIG.copy()
        config.update(self.build_config())
        config['INPUT_FILE_PATH'] = path
        config['CONFIG_MODE'] = mode
        try:
            client = AIClient(config)
            params = get_user_inputs_from_config(config)
            open_q = params['open_questions']
            yes_no_q = params['yes_no_questions']
            df, title_col, abstract_col = load_and_validate_data(path, config)
            df = prepare_dataframe(df, open_q, yes_no_q)
            total = len(df)
            for index, row in df.iterrows():
                self.abs_status.set(f"处理中: {index + 1}/{total}")
                self.abs_progress.set((index + 1) / total * 100)
                analyze_article(df, index, row, title_col, abstract_col, open_q, yes_no_q, config, client)
            base, ext = os.path.splitext(path)
            output_file_path = f"{base}{config['OUTPUT_FILE_SUFFIX']}{ext}"
            if output_file_path.endswith('.csv'):
                df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(output_file_path, index=False, engine='openpyxl')
            self.abs_result.insert(tk.END, f"完成! 结果已保存到: {output_file_path}\n")
        except Exception as e:
            self.abs_result.insert(tk.END, f"错误: {e}\n")
        finally:
            self.abs_status.set("")
            self.abs_progress.set(0)

    # ------------------------------------------------------------------
    # PDF screening tab
    # ------------------------------------------------------------------
    def init_pdf_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="PDF 筛选")

        ttk.Label(frame, text="选择PDF文件夹:").pack(anchor=tk.W, padx=5, pady=2)
        folder_frame = ttk.Frame(frame)
        folder_frame.pack(fill=tk.X, padx=5)
        self.pdf_folder_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.pdf_folder_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(folder_frame, text="浏览", command=lambda: self.browse_folder(self.pdf_folder_var)).pack(side=tk.LEFT, padx=5)

        ttk.Label(frame, text="可选元数据文件:").pack(anchor=tk.W, padx=5, pady=(8, 2))
        meta_frame = ttk.Frame(frame)
        meta_frame.pack(fill=tk.X, padx=5)
        self.pdf_meta_var = tk.StringVar()
        ttk.Entry(meta_frame, textvariable=self.pdf_meta_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(meta_frame, text="浏览", command=lambda: self.browse_file(self.pdf_meta_var, ("CSV or Excel", "*.csv *.xlsx"))).pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="开始筛选", command=self.start_pdf_screen).pack(pady=5)

        self.pdf_progress = tk.DoubleVar()
        ttk.Progressbar(frame, variable=self.pdf_progress, maximum=100).pack(fill=tk.X, padx=5, pady=5)
        self.pdf_result = tk.Text(frame, height=10)
        self.pdf_result.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

    def start_pdf_screen(self) -> None:
        folder = self.pdf_folder_var.get()
        if not folder:
            messagebox.showerror("错误", "请先选择PDF文件夹")
            return
        metadata = self.pdf_meta_var.get()
        threading.Thread(target=self.process_pdf, args=(folder, metadata), daemon=True).start()

    def process_pdf(self, folder: str, metadata: str) -> None:
        config = PDF_CONFIG.copy()
        config.update(self.build_config())
        argv_backup = sys.argv
        sys.argv = ["pdf_screener", "--pdf-folder", folder]
        if metadata:
            sys.argv += ["--metadata-file", metadata]
        output = io.StringIO()
        try:
            with redirect_stdout(output):
                pdf_main()
            self.pdf_result.insert(tk.END, output.getvalue())
        except Exception as e:
            self.pdf_result.insert(tk.END, f"错误: {e}\n")
        finally:
            sys.argv = argv_backup
            self.pdf_progress.set(100)


def launch_gui() -> None:
    """Launch the GUI application."""
    MainWindow().run()
