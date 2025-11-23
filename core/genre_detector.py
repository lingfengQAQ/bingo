"""小说风格检测器"""
import logging
from pathlib import Path

from config import GENRE_MAIN, GENRE_TAGS, STYLE_TAGS

logger = logging.getLogger(__name__)


class GenreDetector:
    """小说类型/风格检测器（基于关键词匹配）"""

    def __init__(self):
        self.genre_main = GENRE_MAIN
        self.genre_tags = GENRE_TAGS
        self.style_tags = STYLE_TAGS

    def detect_from_text(self, text: str, sample_size: int = 5000) -> str:
        """从文本内容检测类型

        Args:
            text: 小说文本
            sample_size: 采样大小（字符数）

        Returns:
            格式化的类型信息，如 "玄幻 | 修真, 穿越 | 热血, 爽文"
        """
        # 采样前 N 字符（开头通常包含关键信息）
        sample = text[:sample_size]

        # 检测主类型
        main_type = self._detect_main_type(sample)

        # 检测子类型/标签
        sub_tags = self._detect_sub_tags(sample)

        # 检测风格
        style_tags = self._detect_style(sample)

        # 格式化输出
        parts = [main_type]
        if sub_tags:
            parts.append(", ".join(sub_tags))
        if style_tags:
            parts.append(", ".join(style_tags))

        return " | ".join(parts)

    def detect_from_file(self, file_path: Path, sample_text: str | None = None) -> str:
        """从文件路径检测类型（通过文件名 + 内容采样）

        Args:
            file_path: EPUB 文件路径
            sample_text: 可选的文本样本（如果提供则用于内容分析）

        Returns:
            类型信息字符串
        """
        # 从文件名检测
        filename = file_path.stem
        main_from_name = self._detect_main_type(filename)

        # 如果文件名有明确类型，直接返回
        if main_from_name != "未分类":
            logger.info("从文件名检测到类型: %s", main_from_name)
            return f"{main_from_name} | 文件名推断"

        # 如果提供了文本样本，使用内容分析
        if sample_text:
            logger.info("文件名未包含类型信息，使用内容分析")
            return self.detect_from_text(sample_text)

        # 兜底：返回待分析标记
        logger.warning("文件名和内容均无法检测类型: %s", file_path.name)
        return "未分类 | 待分析"

    def _detect_main_type(self, text: str) -> str:
        """检测主类型

        Args:
            text: 文本样本

        Returns:
            主类型名称
        """
        scores = {}

        for genre, keywords in self.genre_main items...