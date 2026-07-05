# PPT 生成流水线规范

> 写任何 SVG/PPTX 相关代码前必读。

---

## 整体流水线

```
用户文档（PDF/DOCX/URL）
    ↓ doc_parser.py
Markdown 文本
    ↓ 规划师
OUTLINE.md（大纲）+ DESIGN.md（设计规范）
    ↓ 文案师（逐页填充）
OUTLINE.md（内容完整）
    ↓ 设计师（顺序生成，不可并发）
svg_output/slide_01.svg ... slide_N.svg
    ↓ 效果师（图表/图片注入）
svg_output/slide_XX.svg（含图表和图片引用）
    ↓ 编辑师 Step1: total_md_split.py
notes/total.md（演讲者备注）
    ↓ 编辑师 Step2: finalize_svg.py
svg_final/（后处理优化后的 SVG）
    ↓ 编辑师 Step3: svg_to_pptx.py
exports/native.pptx（DrawingML 原生）
exports/reference_svg.pptx（SVG 图片参考版）
    ↓ 编辑师 Step4: embed_fonts_in_pptx()
exports/native_embedded.pptx（含嵌入字体，最终交付）
```

---

## SVG 规范

### 尺寸

所有幻灯片 SVG 必须使用统一尺寸：
```
viewBox="0 0 960 540"
```

这对应 PPT 16:9 标准（宽度 33.87cm × 高度 19.05cm，72 dpi 换算）。

**不得使用其他尺寸**，否则 svg_to_pptx.py 的坐标换算会出错。

### 文件命名

```
svg_output/slide_01.svg    # 封面
svg_output/slide_02.svg    # 第二页
svg_output/slide_10.svg    # 第十页（两位数补零）
```

### 必要的头部声明

每个 SVG 文件必须包含：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg 
  viewBox="0 0 960 540" 
  xmlns="http://www.w3.org/2000/svg"
  xmlns:xlink="http://www.w3.org/1999/xlink"
>
  <defs>
    <style>
      /* @font-face 声明（见 font-management.md）*/
    </style>
  </defs>
  
  <!-- 背景矩形（必须有，确保背景色正确）-->
  <rect width="960" height="540" fill="#FFFFFF"/>
  
  <!-- 幻灯片内容 -->
  
</svg>
```

### 文字元素规范

```xml
<!-- 标题 -->
<text 
  x="48" y="120"
  font-family="AlibabaPuHuiTi, sans-serif"
  font-weight="700"
  font-size="32"
  fill="#1A1A2E"
>标题文字</text>

<!-- 正文 -->
<text
  font-family="AlibabaPuHuiTi, sans-serif"
  font-weight="400"
  font-size="18"
  fill="#1A1A2E"
>正文文字</text>
```

**中文换行注意**：SVG `<text>` 不支持自动换行，必须用 `<tspan>` 手动换行：

```xml
<text x="48" font-family="AlibabaPuHuiTi" font-size="18" fill="#1A1A2E">
  <tspan x="48" dy="0">第一行文字内容</tspan>
  <tspan x="48" dy="1.5em">第二行文字内容</tspan>
  <tspan x="48" dy="1.5em">第三行文字内容</tspan>
</text>
```

---

## ppt-master 脚本使用

### 脚本位置

```
backend/skills/ppt-master/scripts/
├── pdf_to_md.py          # PDF → Markdown
├── doc_to_md.py          # DOCX → Markdown（需要 pandoc）
├── web_to_md.py          # URL → Markdown
├── project_manager.py    # 项目初始化/验证
├── total_md_split.py     # 提取演讲者备注
├── finalize_svg.py       # SVG 后处理
├── svg_to_pptx.py        # SVG → PPTX 转换（核心）
└── image_gen.py          # AI 图片生成（多后端）
```

### 调用方式

```python
import subprocess
import sys

def run_ppt_master_script(script_name: str, *args) -> tuple[int, str, str]:
    """
    调用 ppt-master 脚本。
    使用项目的 .venv Python，确保依赖一致。
    """
    python = "/Users/wenwenba2020/cc_workspace/ppt_agent/.venv/bin/python"
    script = f"/Users/wenwenba2020/cc_workspace/ppt_agent/backend/skills/ppt-master/scripts/{script_name}"
    
    result = subprocess.run(
        [python, script, *args],
        capture_output=True,
        text=True,
        cwd="/Users/wenwenba2020/cc_workspace/ppt_agent"
    )
    return result.returncode, result.stdout, result.stderr


# 使用示例
def finalize_svgs(project_path: str):
    code, stdout, stderr = run_ppt_master_script(
        "finalize_svg.py", project_path
    )
    if code != 0:
        raise RuntimeError(f"finalize_svg.py 失败: {stderr}")

def convert_to_pptx(project_path: str, stage: str = "final"):
    code, stdout, stderr = run_ppt_master_script(
        "svg_to_pptx.py", project_path, "-s", stage
    )
    if code != 0:
        raise RuntimeError(f"svg_to_pptx.py 失败: {stderr}")
```

---

## 单页增量更新流程

当用户修改单页时，只需重新生成该页，不需要重跑整个流水线：

```
用户修改指令（AI 或手动）
    ↓
设计师重新生成 svg_output/slide_XX.svg
    ↓
finalize_svg.py（只处理该页）
    ↓
svg_to_pptx.py（单页更新模式）
或
editor.py: update_single_slide()
    ↓
OUTLINE.md 该页 status → done
    ↓
前端 Canvas 重新加载该页 SVG
```

**增量更新不需要重跑 total_md_split.py**（备注未变时）。

---

## 图表插入规范

### 数据图表（可编辑）

用 python-pptx 的 `add_chart()` 方法，生成 DrawingML chart XML：

```python
from pptx.util import Inches, Pt
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.dml.color import RGBColor

def add_bar_chart(slide, chart_config: dict, design: dict):
    """在幻灯片中添加可编辑的柱状图"""
    chart_data = ChartData()
    chart_data.categories = chart_config['categories']
    
    for series in chart_config['series']:
        chart_data.add_series(series['name'], series['values'])
    
    # 位置和尺寸（根据 layout 决定）
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(5),    # left
        Inches(1.5),  # top
        Inches(7.5),  # width
        Inches(5),    # height
        chart_data
    ).chart
    
    # 应用 DESIGN.md 的配色
    primary_color = RGBColor.from_string(
        design['colors']['secondary'].lstrip('#')
    )
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = primary_color
    
    return chart
```

### 图片插入（背景/配图）

```python
from pptx.util import Inches

def add_image(slide, image_path: str, position: str = "full"):
    """插入图片"""
    if position == "full":
        # 全图背景
        slide.shapes.add_picture(
            image_path, 0, 0,
            width=Inches(13.33),
            height=Inches(7.5)
        )
    elif position == "right-half":
        # 右半边
        slide.shapes.add_picture(
            image_path,
            Inches(6.67), 0,
            width=Inches(6.67),
            height=Inches(7.5)
        )
```

---

## 版本快照

### 触发时机

1. 用户确认大纲后（全局生成开始前）
2. 全局生成完成后
3. 用户确认诊断修改方案后
4. 用户手动点击"保存版本"

### 快照数据结构

```python
import json
from datetime import datetime

def create_snapshot(project_id: str, trigger: str, outline: OutlineDoc) -> str:
    """创建版本快照，返回快照文件路径"""
    snapshots_dir = Path(f"projects/{project_id}/snapshots")
    snapshots_dir.mkdir(exist_ok=True)
    
    # 获取版本号
    existing = list(snapshots_dir.glob("v*.json"))
    version_num = len(existing) + 1
    version = f"v{version_num:03d}"
    
    snapshot = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "outline": outline.model_dump(),
        "svg_refs": {
            slide.slide_id: f"svg_output/slide_{slide.slide_id}.svg"
            for slide in outline.slides
            if slide.status == "done"
        }
    }
    
    path = snapshots_dir / f"{version}_{trigger}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return str(path)


def rollback_to_snapshot(project_id: str, version: str):
    """回退到指定版本"""
    snapshots_dir = Path(f"projects/{project_id}/snapshots")
    snapshot_files = list(snapshots_dir.glob(f"{version}_*.json"))
    
    if not snapshot_files:
        raise ValueError(f"快照 {version} 不存在")
    
    snapshot = json.loads(snapshot_files[0].read_text())
    outline = OutlineDoc.model_validate(snapshot['outline'])
    
    # 恢复 OUTLINE.md
    save_outline(outline, f"projects/{project_id}/OUTLINE.md")
    
    # 通知前端哪些页需要用历史 SVG 重新加载
    return {
        "restored_slides": list(snapshot['svg_refs'].keys()),
        "outline": outline
    }
```

---

## 错误处理与断点续传

### LangGraph 断点续传

```python
# 生成中途失败时，可以从最后一个 checkpoint 恢复
config = {"configurable": {"thread_id": project_id}}

# 第一次运行（到 human_confirm 节点时自动暂停）
graph.invoke(initial_state, config=config)

# 用户确认后继续
graph.invoke({"user_confirmed": True}, config=config)

# 如果中途报错，重新 invoke 会从最后一个成功的 checkpoint 继续
# LangGraph 自动处理，不需要手动管理
```

### Celery 重试

```python
@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30
)
def run_ppt_generation(self, project_id: str, ...):
    try:
        # ... 执行
    except (APITimeoutError, RateLimitError) as exc:
        # LLM API 超时/限流时重试
        raise self.retry(exc=exc)
    except Exception as exc:
        # 发布错误事件到 SSE
        publish_event(project_id, {
            "type": "error",
            "message": str(exc),
            "recoverable": False
        })
        raise
```
