# 关键坑点汇总

> 每次开始任务前必读。每一条都是深度调研后发现的真实问题。

---

## 坑1：思源黑体 OTF 无法嵌入 PPTX ⚠️ 高危

**现象**：Office 报"一般错误"拒绝嵌入，导出 PDF 后字体变位图。

**根因**：Office 不支持 OTF 格式字体嵌入，只支持 TTF。思源黑体官方只发布 OTF。

**解决**：
- 从 GitHub 获取社区转换的 TTF 版本（搜索"思源黑体 TTF"）
- 阿里巴巴普惠体官方提供 TTF，优先使用它
- 验证命令：`file fonts/*.ttf` 必须显示 `TrueType font data`

**检查**：写字体相关代码时，在代码注释里加 `# TTF only, NOT OTF`。

---

## 坑2：ppt-master SVG 生成不能并发 ⚠️ 高危

**现象**：并发生成多页导致跨页样式不一致（字体、颜色、元素尺寸漂移）。

**根因**：设计师智能体每页的视觉决策依赖前页的上下文（颜色选择、字号平衡等）。

**解决**：
```python
# 正确：顺序生成
for slide in slides:
    await designer.generate_svg(slide)

# 错误：禁止这样写
await asyncio.gather(*[designer.generate_svg(s) for s in slides])
```

---

## 坑3：python-pptx 不支持字体嵌入 ⚠️ 高危

**现象**：python-pptx 保存的 PPTX 在无字体环境中显示错误字体。

**根因**：python-pptx API 无字体嵌入功能。

**解决**：生成 PPTX 后，用 zipfile 手动操作 ZIP 结构：

```python
import zipfile, shutil
from pathlib import Path

def embed_fonts_in_pptx(pptx_path: str, font_files: list[str]) -> str:
    work_path = pptx_path.replace('.pptx', '_embedded.pptx')
    shutil.copy2(pptx_path, work_path)
    with zipfile.ZipFile(work_path, 'a') as zf:
        for font_path in font_files:
            font_name = Path(font_path).name
            zf.write(font_path, f'ppt/fonts/{font_name}')
        # 还需更新 [Content_Types].xml 和 ppt/_rels/presentation.xml.rels
    return work_path
```

**测试**：在没有安装字体的 Windows 机器上打开输出 PPTX 验证。

---

## 坑4：Fabric.js 中文字体未预加载 ⚠️ 高危

**现象**：Canvas 中中文显示为系统默认字体（通常是宋体）。

**根因**：`fabric.loadSVGFromURL` 不等待字体加载完成。

**解决**：
```javascript
// 必须先预加载字体，再渲染 canvas
const font = new FontFace('AlibabaPuHuiTi', 'url(/fonts/AlibabaPuHuiTi-Regular.ttf)');
await font.load();
document.fonts.add(font);
// 字体确认加载后才调用 fabric.loadSVGFromURL
await loadSlideToCanvas(svgUrl);
```

---

## 坑5：规划师诊断模式上下文膨胀 ⚠️ 高危

**现象**：20页×平均3KB SVG = 60KB+，加上对话历史超出上下文窗口。

**根因**：诊断时读取 SVG 文件内容过多。

**规则**：规划师的所有三种模式都**永远不读** `svg_output/` 目录下的文件。

诊断时只读 OUTLINE.md 的结构字段：
```python
# 只读这些字段
summary = [{
    "slide_id": s.slide_id,
    "title": s.title,
    "layout": s.layout,
    "status": s.status,
    "points_count": len(s.points),
    "has_chart": s.chart is not None,
    "has_media": s.media is not None,
} for s in outline.slides]
```

---

## 坑6：OUTLINE.md 多智能体并发写入冲突

**现象**：文案师和设计师同时更新不同页字段，导致文件损坏或数据丢失。

**解决**：
```python
import fcntl

def update_outline_slide(outline_path: str, slide_id: str, updates: dict):
    with open(outline_path, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # 排他锁
        try:
            content = f.read()
            outline = parse_outline(content)
            # 修改对应 slide
            slide = outline.get_slide(slide_id)
            slide.update(updates)
            f.seek(0)
            f.write(serialize_outline(outline))
            f.truncate()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

---

## 坑7：SSE 在 Nginx 代理后被缓冲

**现象**：所有 SSE 事件积累后一次性发出，失去实时性。

**解决**：FastAPI 响应头加 `X-Accel-Buffering: no`：
```python
return StreamingResponse(
    event_generator(project_id),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
)
```

Nginx 配置：
```nginx
location /api/stream {
    proxy_buffering off;
    proxy_pass http://backend;
}
```

---

## 坑8：Celery 任务与 SSE 事件关联

**现象**：Celery worker 中触发的事件无法到达特定用户的 SSE 连接。

**解决**：用 Redis pub/sub 作事件总线。

```python
# Celery worker 中发布事件
import redis
r = redis.Redis.from_url(settings.REDIS_URL)
r.publish(f"project:{project_id}:events", json.dumps(event))

# SSE endpoint 中订阅
async def event_generator(project_id: str):
    r = redis.asyncio.Redis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"project:{project_id}:events")
    async for message in pubsub.listen():
        if message['type'] == 'message':
            yield f"data: {message['data'].decode()}\n\n"
```

---

## 坑9：PPTX 增量回写后页序乱

**现象**：删除一页 XML 后重新插入，页面顺序与预期不符。

**根因**：删除 slide 对象后索引偏移，重新插入位置不对。

**解决**：不删除 slide 对象，清空内容后在原位置更新：
```python
def update_single_slide(pptx_path: str, slide_index: int, new_svg_path: str):
    prs = Presentation(pptx_path)
    slide = prs.slides[slide_index]
    
    # 清空该页所有形状（不删除 slide 对象本身）
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        sp_tree.remove(shape.element)
    
    # 在原位置插入新内容
    new_shapes = svg_to_drawingml(new_svg_path)
    for shape_xml in new_shapes:
        sp_tree.append(shape_xml)
    
    prs.save(pptx_path)
```

---

## 坑10：图表 SVG 嵌入后不可编辑

**现象**：pyecharts 生成的 SVG 在 PPTX 里变成图片，无法编辑数据。

**根因**：SVG 以图片形式插入时被光栅化。

**解决**：数据图表用 python-pptx 的 `add_chart()` 方法，生成 DrawingML chart XML，而不是插入 SVG 图片：
```python
from pptx.util import Inches
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE

chart_data = ChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('营收', (1200, 1500, 1800, 2100))

slide.shapes.add_chart(
    XL_CHART_TYPE.BAR_CLUSTERED,
    Inches(1), Inches(2), Inches(6), Inches(4),
    chart_data
)
```

---

## 坑11：fontTools import 名称

**现象**：`import fonttools` 报 `ModuleNotFoundError`。

**根因**：包名是 `fonttools`，但 import 名是 `fontTools`（大写 T）。

**解决**：
```python
# 正确
from fontTools import subset as ft_subset
from fontTools.ttLib import TTFont

# 错误
import fonttools  # ModuleNotFoundError
```

---

## 坑12：FastAPI lifespan 写法（不用已废弃的 on_event）

**现象**：使用 `@app.on_event("startup")` 会收到 DeprecationWarning，未来版本移除。

**解决**：使用 `lifespan` context manager：
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    await create_all_tables()
    init_checkpointer()
    yield
    # 关闭时执行
    await cleanup()

app = FastAPI(lifespan=lifespan)
```

---

## 坑13：Celery 与 LangGraph 的职责边界

**不要混淆**：Celery 负责异步执行外壳，LangGraph 负责智能体内部编排。

```python
# backend/tasks/generate.py
@celery_app.task(bind=True)
def run_ppt_generation(self, project_id: str, user_message: str):
    """Celery task：异步外壳"""
    import asyncio
    from backend.graph.workflow import get_graph
    
    graph = get_graph()
    config = {"configurable": {"thread_id": project_id}}
    
    # LangGraph 在 Celery worker 中同步运行
    result = asyncio.run(
        graph.ainvoke(
            {"project_id": project_id, "user_message": user_message},
            config=config
        )
    )
    return result
```

不要在 Celery task 里自己管理状态机，那是 LangGraph 的职责。
不要在 LangGraph node 里用 Celery delay，那是 Celery 的职责。
