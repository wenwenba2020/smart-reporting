from dataclasses import dataclass, field
from typing import Any, Optional


# ---------- data-source layer ----------

@dataclass
class SourceDocument:
    """A single document retrieved from a data source."""
    id: str
    title: str
    content: str
    source_type: str                          # e.g. "knowledge_base", "case_library", "chat"
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0


# ---------- report-structure layer ----------

@dataclass
class SectionDef:
    """Definition of one section within a report template."""
    id: str = ""
    heading: str = ""
    level: int = 1                            # 1=h1, 2=h2, ...
    prompt_hint: str = ""                     # LLM prompt guidance
    min_slides: int = 1
    max_slides: int = 3
    key_points: list[str] = field(default_factory=list)
    data_hints: list[str] = field(default_factory=list)
    # Template-store oriented fields (Tasks 7-8)
    key: str = ""
    title: str = ""
    required: bool = True
    description: str = ""
    source: str = "generated"
    match_keywords: list[str] = field(default_factory=list)
    max_matches: int = 3
    fallback: str = "generated"
    suggested_length: str = "medium"

    def __post_init__(self):
        # Backward compatibility: if id/heading are set but key/title aren't, sync them
        if self.id and not self.key:
            self.key = self.id
        if self.heading and not self.title:
            self.title = self.heading
        if self.key and not self.id:
            self.id = self.key
        if self.title and not self.heading:
            self.heading = self.title


@dataclass
class ReportTemplate:
    """A reusable report template with typed sections."""
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    sections: list[SectionDef] = field(default_factory=list)
    style_profile_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # Template-store oriented fields (Tasks 7-8)
    template_id: str = ""
    parent_meta: Optional[str] = None
    suggested_charts: list[str] = field(default_factory=list)
    system_prompt: str = ""

    def __post_init__(self):
        # Backward compatibility: if id is set but template_id isn't, sync them
        if self.id and not self.template_id:
            self.template_id = self.id
        if self.template_id and not self.id:
            self.id = self.template_id


@dataclass
class ReportMeta:
    """High-level metadata describing a generated report."""
    id: str
    title: str
    template_id: str
    created_at: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    slide_count: int = 0


# ---------- slide-match layer ----------

@dataclass
class SlideRef:
    """Reference to a reusable slide asset in the case library."""
    id: str
    title: str
    slide_index: int
    source_file: str
    tags: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    thumbnail_url: str = ""


# ---------- structured-report layer ----------

@dataclass
class ReportSection:
    """A fully populated section with resolved content and slide matches."""
    section_def: SectionDef
    markdown_content: str
    slide_refs: list[SlideRef] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)


@dataclass
class StructuredReport:
    """The complete structured report before export."""
    meta: ReportMeta
    template: ReportTemplate
    sections: list[ReportSection] = field(default_factory=list)
    full_markdown: str = ""
    report_json: dict[str, Any] = field(default_factory=dict)


# ---------- slide-library layer ----------

@dataclass
class SlideAsset:
    """A reusable slide with full metadata."""
    id: str
    title: str
    description: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    source_type: str = "uploaded"             # "uploaded", "curated", "generated"
    is_premium: bool = False
    file_path: str = ""
    thumbnail_path: str = ""
    slide_index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------- deck-builder layer ----------

@dataclass
class ContentDeck:
    """A content-only deck ready for visual styling."""
    id: str
    title: str
    slides: list[dict[str, Any]] = field(default_factory=list)
    outline: dict[str, Any] = field(default_factory=dict)


@dataclass
class StyleProfile:
    """Visual style configuration for a deck."""
    id: str
    name: str
    color_palette: list[str] = field(default_factory=list)
    font_heading: str = "Arial"
    font_body: str = "Arial"
    slide_width_inches: float = 13.333
    slide_height_inches: float = 7.5
    background_color: str = "#FFFFFF"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateDeck:
    """A full template deck bundling ContentDeck + StyleProfile."""
    id: str
    name: str
    description: str = ""
    content_deck: Optional[ContentDeck] = None
    style_profile: Optional[StyleProfile] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------- intent + recommendation layer ----------

@dataclass
class ReportIntent:
    """Parsed user intent for report generation."""
    raw_query: str = ""
    report_type: str = "general"
    topic: str = ""
    audience: str = ""
    tone: str = "professional"
    key_requirements: list[str] = field(default_factory=list)
    data_sources_needed: list[str] = field(default_factory=list)
    estimated_length: str = "medium"           # "short", "medium", "long"
    language: str = "zh-CN"
    # Intent recognition fields (Task 9)
    category: str = ""
    period: str = ""
    scope: str = ""
    key_themes: list[str] = field(default_factory=list)


@dataclass
class TemplateRecommendation:
    """A template recommendation result."""
    template: Optional[ReportTemplate] = None
    match_score: float = 0.0
    match_reasons: list[str] = field(default_factory=list)
    # Template-matcher oriented fields (Task 9)
    template_id: str = ""
    name: str = ""
    match_reason: str = ""
    is_selected: bool = False


# ---------- export layer ----------

@dataclass
class ExportResult:
    """Result of exporting a structured report to a file format."""
    file_path: str
    format: str                               # "pptx", "docx", "pdf", "md"
    file_size_bytes: int = 0
    download_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------- configurable data-source layer (Phase 2A) ----------

@dataclass
class RestApiSourceConfig:
    """Configuration for a REST API data source."""
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    auth_type: str = "none"                    # "none" | "bearer" | "basic"
    auth_token: str = ""
    auth_username: str = ""
    auth_password: str = ""
    jsonpath_expr: str = "$"                   # JSONPath expression to extract data
    title_field: str = ""                      # response field to use as document title


@dataclass
class McpSourceConfig:
    """Configuration for an MCP (Model Context Protocol) data source via WorkoPilot."""
    robot_id: int                              # WorkoPilot digital employee ID (with MCP tools configured)
    user_id: str                               # end-user identifier
    tool_prompt: str                           # natural-language prompt that triggers the MCP tool
    session_id: str = ""                       # optional: reuse an existing chat session


@dataclass
class DatabaseSourceConfig:
    """Configuration for a direct database connection data source."""
    connection_string: str                     # SQLAlchemy connection string
    query: str                                 # SQL query to execute
    db_type: str = "sqlite"                    # "sqlite" | "mysql" | "postgresql"
