"""报告引擎 — 智能填报 + 多格式输出"""
from backend.report_engine.output_engine import output_engine
from backend.report_engine.pptx_output import PptOutputAdapter
from backend.report_engine.docx_output import DocxOutputAdapter
from backend.report_engine.pdf_output import PdfOutputAdapter

output_engine.register(PptOutputAdapter())
output_engine.register(DocxOutputAdapter())
output_engine.register(PdfOutputAdapter())
