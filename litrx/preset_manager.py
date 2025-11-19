"""文献矩阵方案管理器

提供用户友好的方案管理功能：
- 列出、加载、保存方案
- 复制、重命名、删除方案
- 文件名自动清理（支持中文）
- 保护默认模板
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from .logging_config import get_logger
from .resources import resource_path

logger = get_logger(__name__)


class MatrixPresetManager:
    """文献矩阵方案管理器

    管理configs/matrix/目录下的YAML配置文件，为非技术用户提供
    友好的方案管理接口。
    """

    DEFAULT_PRESET_NAME = "default"

    def __init__(self, presets_dir: Optional[Path] = None):
        """初始化方案管理器

        Args:
            presets_dir: 方案目录路径，默认使用 configs/matrix/
        """
        if presets_dir is None:
            self.presets_dir = Path(resource_path("configs", "matrix"))
        else:
            self.presets_dir = Path(presets_dir)

        # 确保目录存在
        self.presets_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Preset manager initialized: {self.presets_dir}")

    def list_presets(self) -> List[Tuple[str, str]]:
        """列出所有可用方案

        Returns:
            List[Tuple[str, str]]: 列表，每项为 (文件名不含扩展名, 显示名称)
            例如: [("default", "默认方案"), ("psychology", "心理学实证研究")]
        """
        presets = []

        for yaml_file in self.presets_dir.glob("*.yaml"):
            preset_key = yaml_file.stem
            display_name = self._get_display_name(yaml_file)
            presets.append((preset_key, display_name))

        # 确保 default 排在第一位
        presets.sort(key=lambda x: (x[0] != self.DEFAULT_PRESET_NAME, x[1]))

        logger.debug(f"Found {len(presets)} presets")
        return presets

    def load_preset(self, preset_key: str) -> Dict:
        """加载指定方案

        Args:
            preset_key: 方案文件名（不含扩展名）

        Returns:
            Dict: 方案配置字典

        Raises:
            FileNotFoundError: 方案不存在
            ValueError: YAML格式错误
        """
        preset_path = self.presets_dir / f"{preset_key}.yaml"

        if not preset_path.exists():
            raise FileNotFoundError(f"方案不存在: {preset_key}")

        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ValueError(f"方案格式错误: 应为字典类型")

            logger.info(f"Loaded preset: {preset_key}")
            return config

        except yaml.YAMLError as e:
            raise ValueError(f"方案文件格式错误: {e}")

    def save_preset(self, preset_key: str, config: Dict, display_name: Optional[str] = None) -> None:
        """保存方案

        Args:
            preset_key: 方案文件名（不含扩展名）
            config: 方案配置字典
            display_name: 显示名称（可选），会写入YAML注释

        Raises:
            ValueError: 方案名称不合法
        """
        if not preset_key or preset_key.startswith('.'):
            raise ValueError(f"方案名称不合法: {preset_key}")

        preset_path = self.presets_dir / f"{preset_key}.yaml"

        # 备份已存在的文件
        if preset_path.exists():
            backup_path = preset_path.with_suffix('.yaml.bak')
            shutil.copy2(preset_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")

        # 准备元数据注释
        metadata_lines = self._generate_metadata_header(config, display_name or preset_key)

        # 写入文件
        with open(preset_path, 'w', encoding='utf-8') as f:
            # 写入元数据注释
            f.write(metadata_lines)
            # 写入YAML内容
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        logger.info(f"Saved preset: {preset_key}")

    def delete_preset(self, preset_key: str) -> None:
        """删除方案

        Args:
            preset_key: 方案文件名（不含扩展名）

        Raises:
            ValueError: 试图删除默认方案
            FileNotFoundError: 方案不存在
        """
        if preset_key == self.DEFAULT_PRESET_NAME:
            raise ValueError("不能删除默认方案")

        preset_path = self.presets_dir / f"{preset_key}.yaml"

        if not preset_path.exists():
            raise FileNotFoundError(f"方案不存在: {preset_key}")

        # 创建备份到回收站
        trash_dir = self.presets_dir / ".trash"
        trash_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trash_path = trash_dir / f"{preset_key}_{timestamp}.yaml"
        shutil.move(str(preset_path), str(trash_path))

        logger.info(f"Deleted preset: {preset_key} (moved to {trash_path})")

    def rename_preset(self, old_key: str, new_key: str, new_display_name: Optional[str] = None) -> None:
        """重命名方案

        Args:
            old_key: 旧方案文件名
            new_key: 新方案文件名
            new_display_name: 新显示名称（可选）

        Raises:
            ValueError: 试图重命名默认方案或新名称已存在
            FileNotFoundError: 原方案不存在
        """
        if old_key == self.DEFAULT_PRESET_NAME:
            raise ValueError("不能重命名默认方案")

        old_path = self.presets_dir / f"{old_key}.yaml"
        new_path = self.presets_dir / f"{new_key}.yaml"

        if not old_path.exists():
            raise FileNotFoundError(f"方案不存在: {old_key}")

        if new_path.exists():
            raise ValueError(f"方案名称已存在: {new_key}")

        # 加载配置并用新名称保存
        config = self.load_preset(old_key)
        self.save_preset(new_key, config, new_display_name or new_key)

        # 删除旧文件
        old_path.unlink()

        logger.info(f"Renamed preset: {old_key} -> {new_key}")

    def duplicate_preset(self, source_key: str, new_key: str, new_display_name: Optional[str] = None) -> None:
        """复制方案

        Args:
            source_key: 源方案文件名
            new_key: 新方案文件名
            new_display_name: 新显示名称（可选）

        Raises:
            FileNotFoundError: 源方案不存在
            ValueError: 新名称已存在
        """
        source_path = self.presets_dir / f"{source_key}.yaml"
        new_path = self.presets_dir / f"{new_key}.yaml"

        if not source_path.exists():
            raise FileNotFoundError(f"方案不存在: {source_key}")

        if new_path.exists():
            raise ValueError(f"方案名称已存在: {new_key}")

        # 加载配置并保存为新方案
        config = self.load_preset(source_key)
        self.save_preset(new_key, config, new_display_name or f"{new_key} (副本)")

        logger.info(f"Duplicated preset: {source_key} -> {new_key}")

    def get_preset_info(self, preset_key: str) -> Dict:
        """获取方案信息

        Args:
            preset_key: 方案文件名

        Returns:
            Dict: 包含维度数量、创建时间等信息
        """
        preset_path = self.presets_dir / f"{preset_key}.yaml"

        if not preset_path.exists():
            return {"exists": False}

        config = self.load_preset(preset_key)
        dimensions = config.get("dimensions", [])

        info = {
            "exists": True,
            "display_name": self._get_display_name(preset_path),
            "dimension_count": len(dimensions),
            "file_size": preset_path.stat().st_size,
            "modified_time": datetime.fromtimestamp(preset_path.stat().st_mtime),
        }

        return info

    def generate_unique_key(self, base_name: str) -> str:
        """生成唯一的方案文件名

        Args:
            base_name: 基础名称（可以是中文）

        Returns:
            str: 唯一的文件名（不含扩展名）
        """
        # 清理文件名
        key = self._slugify(base_name)

        # 如果已存在，添加数字后缀
        if (self.presets_dir / f"{key}.yaml").exists():
            counter = 1
            while (self.presets_dir / f"{key}_{counter}.yaml").exists():
                counter += 1
            key = f"{key}_{counter}"

        return key

    def _slugify(self, text: str) -> str:
        """将文本转换为合法的文件名

        保留中文字符，移除特殊字符。

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文件名
        """
        if not text:
            return "unnamed"

        # 移除前后空格
        text = text.strip()

        # 替换空格为下划线
        text = text.replace(' ', '_')

        # 移除Windows/Linux文件名禁用字符
        text = re.sub(r'[<>:"/\\|?*]', '', text)

        # 移除连续的下划线
        text = re.sub(r'_+', '_', text)

        # 移除前后的下划线
        text = text.strip('_')

        return text or "unnamed"

    def _get_display_name(self, preset_path: Path) -> str:
        """从YAML文件中提取显示名称

        从文件的第一行注释中提取 "# 方案名称: xxx"

        Args:
            preset_path: YAML文件路径

        Returns:
            str: 显示名称，如果未找到则返回文件名
        """
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # 匹配 "# 方案名称: xxx" 或 "# Preset: xxx"
                match = re.match(r'#\s*(?:方案名称|Preset):\s*(.+)', first_line)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass

        # 如果是default，返回友好名称
        if preset_path.stem == self.DEFAULT_PRESET_NAME:
            return "默认方案"

        # 否则返回文件名（将下划线替换为空格）
        return preset_path.stem.replace('_', ' ')

    def _generate_metadata_header(self, config: Dict, display_name: str) -> str:
        """生成YAML文件头部的元数据注释

        Args:
            config: 配置字典
            display_name: 显示名称

        Returns:
            str: 元数据注释文本
        """
        dimensions = config.get("dimensions", [])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"# 方案名称: {display_name}",
            f"# 创建时间: {now}",
            f"# 维度数量: {len(dimensions)}",
            "#",
            "# 此文件由 LitRelevanceAI 自动生成",
            "# 支持7种维度类型: text, yes_no, single_choice, multiple_choice, number, rating, list",
            "#",
            ""  # 空行
        ]

        return '\n'.join(lines)
