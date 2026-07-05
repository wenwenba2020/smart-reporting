"""
Section Filler — populate each section of a report template with AI-generated content.
"""
import asyncio

from backend.core.models import (
    ReportTemplate,
    ReportMeta,
    ReportSection,
    SectionDef,
    SourceDocument,
    StructuredReport,
)
from backend.core.llm.client import get_llm_client
from backend.core.llm.prompts import SECTION_FILL_PROMPT


class SectionFiller:
    """Fill each leaf section of a report template with content from source documents."""

    def __init__(self):
        self.llm = get_llm_client()

    async def fill(
        self,
        template: ReportTemplate,
        source_docs: list[SourceDocument],
        report_meta: ReportMeta,
    ) -> StructuredReport:
        """Fill all leaf sections of the template and return a StructuredReport.

        Parameters
        ----------
        template : ReportTemplate
            The selected report template.
        source_docs : list[SourceDocument]
            Source documents providing content.
        report_meta : ReportMeta
            Metadata for the report being generated.

        Returns
        -------
        StructuredReport
            Fully populated structured report.
        """
        leaf_sections = self._collect_leaf_sections(template.sections)
        source_text = "\n\n---\n\n".join(
            f"### [{d.source_type}] {d.title}\n{d.content}" for d in source_docs
        )

        # Fill each leaf section in parallel
        tasks = [
            self._fill_section(section, template, source_text)
            for section in leaf_sections
        ]
        filled_sections = await asyncio.gather(*tasks)

        # Build full markdown
        full_markdown_parts = [f"# {template.name}"]
        for rs in filled_sections:
            full_markdown_parts.append(f"\n## {rs.section_def.title}\n{rs.markdown_content}")

        return StructuredReport(
            meta=report_meta,
            template=template,
            sections=filled_sections,
            full_markdown="\n".join(full_markdown_parts),
            report_json={},
        )

    def _collect_leaf_sections(self, sections: list[SectionDef]) -> list[SectionDef]:
        """Collect leaf sections (those without child subsections).

        A section is considered a leaf if no other section has a higher level
        (indicating it is a child of another section). In a flat section list,
        all sections are leaves.

        Parameters
        ----------
        sections : list[SectionDef]
            All sections from the template.

        Returns
        -------
        list[SectionDef]
            Leaf sections only.
        """
        if not sections:
            return []
        min_level = min(s.level for s in sections)
        # Sections at the minimum level are top-level; keep only those
        # In the current flat template model, all sections are at level 1
        leaves = [s for s in sections if s.level == min_level]
        return leaves

    async def _fill_section(
        self,
        section: SectionDef,
        template: ReportTemplate,
        source_text: str,
    ) -> ReportSection:
        """Fill a single section with content.

        For sections with source=="enterprise_ppt", a placeholder is returned
        (these will be matched against the slide library later).
        Otherwise, the LLM generates content based on source documents.

        Parameters
        ----------
        section : SectionDef
            The section definition to fill.
        template : ReportTemplate
            The parent template (for context).
        source_text : str
            Pre-formatted source document text.

        Returns
        -------
        ReportSection
            Filled section with markdown content.
        """
        if section.source == "enterprise_ppt":
            return ReportSection(
                section_def=section,
                markdown_content="[待从企业PPT案例库匹配]",
                data_sources=[],
            )

        prompt = SECTION_FILL_PROMPT.format(
            template_name=template.name,
            template_description=template.description,
            section_title=section.title,
            section_description=section.description,
            suggested_length=section.suggested_length,
            source_contents=source_text or "无可用数据",
        )
        try:
            content = await self.llm.chat(
                system_prompt=template.system_prompt or "Generate professional report content.",
                user_message=prompt,
                max_tokens=4096,
            )
        except Exception:
            content = f"[{section.title} 内容生成失败]"

        return ReportSection(
            section_def=section,
            markdown_content=content,
            data_sources=[],
        )
