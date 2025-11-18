"""AI prompt builder for abstract screening.

This module provides a clean, reusable interface for building prompts
for the abstract screening module, replacing the monolithic construct_ai_prompt function.
"""

from typing import Dict, List


class PromptBuilder:
    """Responsible for constructing AI prompts for abstract screening.

    This class encapsulates the logic for building prompts from templates,
    making it easier to maintain and test prompt generation logic.
    """

    def __init__(self, prompts_config: dict):
        """Initialize prompt builder.

        Args:
            prompts_config: Prompt templates from prompts_config.json
        """
        self.prompts = prompts_config

    def build_screening_prompt(
        self,
        title: str,
        abstract: str,
        research_question: str,
        criteria: List[str],
        detailed_questions: List[Dict]
    ) -> str:
        """Build complete screening prompt.

        Args:
            title: Paper title
            abstract: Paper abstract
            research_question: Research question/topic
            criteria: List of yes/no screening criteria
            detailed_questions: List of detailed analysis questions

        Returns:
            Formatted prompt string
        """
        criteria_section = self._build_criteria_section(criteria)
        detailed_section = self._build_detailed_section(detailed_questions)
        template = self._select_template()

        return self._format_prompt(
            template,
            title=title,
            abstract=abstract,
            research_question=research_question,
            detailed_analysis_section=detailed_section,
            criteria_prompts_str=criteria_section
        )

    def build_flexible_prompt(
        self,
        title: str,
        abstract: str,
        open_questions: List[Dict],
        yes_no_questions: List[Dict],
        general_mode: bool = True
    ) -> str:
        """Build flexible prompt for quick screening.

        Args:
            title: Paper title
            abstract: Paper abstract
            open_questions: List of open-ended questions
            yes_no_questions: List of yes/no questions
            general_mode: Whether in general screening mode

        Returns:
            Formatted prompt string
        """
        open_q_str = self._build_open_questions_section(open_questions)
        yes_no_str = self._build_yes_no_section(yes_no_questions)
        template = self._select_quick_template()

        return self._format_quick_prompt(
            template,
            title=title,
            abstract=abstract,
            open_q_str=open_q_str,
            yes_no_str=yes_no_str
        )

    def _build_criteria_section(self, criteria: List[str]) -> str:
        """Build screening criteria section.

        Args:
            criteria: List of screening criteria

        Returns:
            Formatted criteria string
        """
        return ",\n".join([
            f'        "{c}": "请回答 \'是\', \'否\', 或 \'不确定\'"'
            for c in criteria
        ])

    def _build_detailed_section(self, questions: List[Dict]) -> str:
        """Build detailed analysis section.

        Args:
            questions: List of detailed question dictionaries

        Returns:
            Formatted detailed section string
        """
        if not questions:
            return ""

        prompts_list = [
            f'        "{q["prompt_key"]}": "{q["question_text"]}"'
            for q in questions
        ]
        detailed_str = ",\n".join(prompts_list)

        return f"""
    "detailed_analysis": {{
{detailed_str}
    }},"""

    def _build_open_questions_section(self, questions: List[Dict]) -> str:
        """Build open questions section for flexible prompt.

        Args:
            questions: List of open question dictionaries

        Returns:
            Formatted open questions string
        """
        return ",\n".join([
            f'        "{q["key"]}": "{q["question"]}"'
            for q in questions
        ])

    def _build_yes_no_section(self, questions: List[Dict]) -> str:
        """Build yes/no questions section for flexible prompt.

        Args:
            questions: List of yes/no question dictionaries

        Returns:
            Formatted yes/no questions string
        """
        return ",\n".join([
            f'        "{q["key"]}": "{q["question"]}"'
            for q in questions
        ])

    def _select_template(self) -> str:
        """Select appropriate template from config.

        Returns:
            Prompt template string
        """
        return self.prompts.get("detailed_prompt", self._get_default_detailed_template())

    def _select_quick_template(self) -> str:
        """Select quick screening template from config.

        Returns:
            Quick prompt template string
        """
        return self.prompts.get("quick_prompt", self._get_default_quick_template())

    def _format_prompt(self, template: str, **kwargs) -> str:
        """Format final prompt with variables.

        Args:
            template: Template string
            **kwargs: Variables to format into template

        Returns:
            Formatted prompt
        """
        return template.format(**kwargs)

    def _format_quick_prompt(self, template: str, **kwargs) -> str:
        """Format quick screening prompt with variables.

        Args:
            template: Template string
            **kwargs: Variables to format into template

        Returns:
            Formatted prompt
        """
        return template.format(**kwargs)

    @staticmethod
    def _get_default_detailed_template() -> str:
        """Get default detailed screening template.

        Returns:
            Default template string
        """
        return """请仔细阅读以下文献的标题和摘要,并结合给定的理论模型/研究问题进行分析。
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
"""

    @staticmethod
    def _get_default_quick_template() -> str:
        """Get default quick screening template.

        Returns:
            Default quick template string
        """
        return """请快速分析以下文献的标题和摘要,帮助进行每周文献筛选:

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
}}"""
