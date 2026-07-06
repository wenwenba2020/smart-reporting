"""
Report Validator — validate generated report content for quality and consistency.
"""
from backend.core.llm.client import get_llm_client
from backend.core.llm.prompts import VALIDATION_PROMPT


class ReportValidator:
    """Validate generated report content against source documents."""

    def __init__(self):
        self.llm = get_llm_client()

    async def validate(self, report_content: str, source_contents: str) -> dict:
        """Validate report content for accuracy, consistency, and quality.

        Parameters
        ----------
        report_content : str
            The generated report markdown content.
        source_contents : str
            The original source data used for generation.

        Returns
        -------
        dict
            Validation result with keys:
            - is_consistent: bool — whether report is consistent with sources
            - issues: list[str] — list of identified issues
            - overall_quality: str — e.g. "good", "needs_revision", "poor"
        """
        try:
            prompt = VALIDATION_PROMPT.format(
                report_content=report_content[:8000],
                source_contents=source_contents[:8000],
            )
            result = await self.llm.chat_json(
                system_prompt="Validate report quality and consistency.",
                user_message=prompt,
            )
            # Normalize the response into the expected shape
            issues = []
            checks = result.get("checks", {})
            for check_name, check_data in checks.items():
                if isinstance(check_data, dict) and check_data.get("issues"):
                    issues.extend(check_data["issues"])

            overall_score = result.get("overall_score", 7)
            if overall_score >= 8:
                overall_quality = "good"
            elif overall_score >= 5:
                overall_quality = "needs_revision"
            else:
                overall_quality = "poor"

            return {
                "is_consistent": overall_score >= 5,
                "issues": issues,
                "overall_quality": overall_quality,
            }
        except Exception as e:
            return {
                "is_consistent": False,
                "issues": [{"section": "global", "severity": "high",
                            "description": f"一致性校验未能完成 (LLM调用失败: {str(e)[:100]})",
                            "suggestion": "请检查 LLM API 配置后重新生成报告"}],
                "overall_quality": "unvalidated",
                "error": str(e)[:200],
            }
