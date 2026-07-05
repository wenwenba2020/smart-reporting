# 字体管理规范

> 写任何字体相关代码前必读。

---

## 核心原则：只用 TTF，永远不用 OTF

**原因**：Office（PowerPoint/WPS）不支持嵌入 OTF 格式字体。
- OTF 嵌入会报"一般错误"
- 用 OTF 导出 PDF 时字体变位图
- 在无字体环境打开 PPTX 时显示替换字体

**验证命令**：
```bash
file fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf
# 必须输出：TrueType font data
# 如果输出 OpenType/CFF，说明是 OTF，不能用
```

---

## 字体库目录结构

```
fonts/
├── AlibabaPuHuiTi/                      # 主力字体（9字重），永久免费商用
│   ├── AlibabaPuHuiTi-Thin.ttf
│   ├── AlibabaPuHuiTi-Light.ttf
│   ├── AlibabaPuHuiTi-Regular.ttf       # 正文默认
│   ├── AlibabaPuHuiTi-Medium.ttf
│   ├── AlibabaPuHuiTi-Semibold.ttf
│   ├── AlibabaPuHuiTi-Bold.ttf          # 标题默认
│   ├── AlibabaPuHuiTi-Extrabold.ttf
│   ├── AlibabaPuHuiTi-Heavy.ttf
│   └── AlibabaPuHuiTi-Black.ttf
├── HarmonyOSSans/                        # 科技风模板用（5字重），免费商用
│   ├── HarmonyOSSans-Thin.ttf
│   ├── HarmonyOSSans-Light.ttf
│   ├── HarmonyOSSans-Regular.ttf
│   ├── HarmonyOSSans-Bold.ttf
│   └── HarmonyOSSans-Black.ttf
├── SourceHanSans-TTF/                    # ⚠️ 必须是 TTF 版，不是官方 OTF
│   ├── SourceHanSansCN-Regular.ttf
│   ├── SourceHanSansCN-Bold.ttf
│   └── SourceHanSansCN-Heavy.ttf
├── SourceHanSerif-TTF/                   # 宋体，中国风模板专用
│   ├── SourceHanSerifCN-Regular.ttf
│   └── SourceHanSerifCN-Bold.ttf
├── Inter/                                # 英文配套字体
│   ├── Inter-Regular.ttf
│   ├── Inter-Medium.ttf
│   └── Inter-Bold.ttf
└── subsets/                              # fonttools 子集化后的裁剪版
    └── {project_id}/
        └── AlibabaPuHuiTi-Regular-subset.ttf
```

---

## 字体下载地址

| 字体 | 下载地址 | 授权 |
|------|----------|------|
| 阿里巴巴普惠体 | https://www.iconfont.cn/fonts/detail?cnid=pOvFIr086ADR | 永久免费商用 |
| HarmonyOS Sans | https://developer.harmonyos.com/cn/docs/design/font-0000001157868583 | 免费商用 |
| 思源黑体（TTF版） | 搜索"思源黑体TTF"或从 GitHub 社区转换版获取 | SIL OFL 1.1 |
| Inter | https://github.com/rsms/inter/releases | SIL OFL 1.1 |

**思源黑体特别说明**：Adobe 官方只发布 OTF，不能直接用。
需要从以下地址获取 TTF 转换版：
- https://github.com/adobe-fonts/source-han-sans（找 Variable TTF）
- 或搜索"思源黑体 TTF 版"获取社区转换版

---

## 模板字体配置

每个模板在 DESIGN.md 中声明使用的字体：

| 模板 | 中文字体 | 英文配套 |
|------|----------|----------|
| 商务蓝 (business-blue) | 阿里巴巴普惠体 | Inter |
| 科技感 (tech-dark) | HarmonyOS Sans | HarmonyOS Sans |
| 咨询顾问 (consulting) | 思源黑体（TTF） | Inter |
| 中国风 (chinese-style) | 思源宋体（TTF） | Adobe Garamond |
| 极简留白 (minimal) | 阿里巴巴普惠体 | DM Sans |

---

## font_manager.py 实现规范

```python
# backend/pipeline/font_manager.py

from fontTools import subset as ft_subset  # ⚠️ 大写T
from fontTools.ttLib import TTFont
import zipfile
import shutil
from pathlib import Path


FONTS_DIR = Path("./fonts")

# 模板ID → 需要的字体文件列表
TEMPLATE_FONTS = {
    "business-blue": [
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf",
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Bold.ttf",
        "AlibabaPuHuiTi/AlibabaPuHuiTi-Light.ttf",
        "Inter/Inter-Regular.ttf",
        "Inter/Inter-Bold.ttf",
    ],
    "tech-dark": [
        "HarmonyOSSans/HarmonyOSSans-Regular.ttf",
        "HarmonyOSSans/HarmonyOSSans-Bold.ttf",
        "HarmonyOSSans/HarmonyOSSans-Light.ttf",
    ],
}


def get_fonts_for_template(template_id: str) -> list[Path]:
    """返回模板需要的字体文件完整路径列表"""
    font_names = TEMPLATE_FONTS.get(template_id, TEMPLATE_FONTS["business-blue"])
    return [FONTS_DIR / name for name in font_names]


def create_font_subset(
    font_path: Path,
    text_content: str,
    output_path: Path
) -> Path:
    """
    按实际用字裁剪字体文件。
    单字重从 ~15MB 压缩到 2-3MB。
    
    text_content: 该项目所有幻灯片文本内容的合集。
    """
    options = ft_subset.Options()
    options.layout_features = ['*']       # 保留所有 OpenType 特性
    options.name_IDs = [1, 2, 3, 4, 6]  # 保留必要的名称记录
    
    font = ft_subset.load_font(str(font_path), options)
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(text=text_content)
    subsetter.subset(font)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ft_subset.save_font(font, str(output_path), options)
    return output_path


def embed_fonts_in_pptx(pptx_path: str, font_files: list[Path]) -> str:
    """
    将 TTF 字体文件嵌入 PPTX。
    python-pptx 不支持此功能，必须直接操作 ZIP 结构。
    
    ⚠️ 必须在副本上操作，避免原文件损坏。
    """
    work_path = pptx_path.replace('.pptx', '_embedded.pptx')
    shutil.copy2(pptx_path, work_path)
    
    with zipfile.ZipFile(work_path, 'a') as zf:
        # 读取现有的 Content_Types.xml
        content_types_xml = zf.read('[Content_Types].xml').decode('utf-8')
        
        font_overrides = []
        for font_path in font_files:
            if not font_path.exists():
                raise FileNotFoundError(f"字体文件不存在: {font_path}")
            
            font_name = font_path.name
            
            # 写入字体文件到 ppt/fonts/
            zf.write(str(font_path), f'ppt/fonts/{font_name}')
            
            # 准备 Content_Types 条目
            font_override = (
                f'<Override PartName="/ppt/fonts/{font_name}" '
                f'ContentType="application/x-fontdata"/>'
            )
            if font_override not in content_types_xml:
                font_overrides.append(font_override)
        
        # 更新 Content_Types.xml
        if font_overrides:
            insert_before = '</Types>'
            updated = content_types_xml.replace(
                insert_before,
                '\n'.join(font_overrides) + '\n' + insert_before
            )
            # ZipFile 的 'a' 模式不能更新已有文件，需要重建
            # 实际实现需要完整重建 ZIP（见下方注意事项）
    
    return work_path


def verify_ttf(font_path: Path) -> bool:
    """验证字体文件确实是 TTF 格式（不是 OTF）"""
    try:
        font = TTFont(str(font_path))
        # TTF 包含 'glyf' 表，OTF/CFF 包含 'CFF ' 表
        return 'glyf' in font
    except Exception:
        return False
```

**`embed_fonts_in_pptx` 的注意事项**：

ZipFile 的 `'a'` 模式可以添加新文件，但不能更新已有文件（Content_Types.xml 已存在）。实际实现需要：
1. 解压全部到临时目录
2. 修改 Content_Types.xml 和 presentation.xml.rels
3. 重新打包为 zip 并重命名为 .pptx

---

## SVG 中的字体声明

设计师生成的每个 SVG 文件顶部必须包含 @font-face 声明：

```svg
<svg viewBox="0 0 960 540" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @font-face {
        font-family: 'AlibabaPuHuiTi';
        src: url('/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf');
        font-weight: 400;
      }
      @font-face {
        font-family: 'AlibabaPuHuiTi';
        src: url('/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Bold.ttf');
        font-weight: 700;
      }
      @font-face {
        font-family: 'Inter';
        src: url('/fonts/Inter/Inter-Regular.ttf');
        font-weight: 400;
      }
    </style>
  </defs>
  <!-- 幻灯片内容 -->
</svg>
```

字体路径必须与 Web 服务器静态文件路径一致：
- 服务端静态文件：`GET /fonts/{FontName}/{FileName}.ttf`
- FastAPI 配置：`app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")`

---

## 前端字体预加载（Fabric.js 必须）

```typescript
// frontend/src/components/Canvas/index.tsx

async function preloadFonts(templateId: string): Promise<void> {
  const fontsToLoad = [
    { family: 'AlibabaPuHuiTi', weight: '400', url: '/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Regular.ttf' },
    { family: 'AlibabaPuHuiTi', weight: '700', url: '/fonts/AlibabaPuHuiTi/AlibabaPuHuiTi-Bold.ttf' },
    { family: 'Inter', weight: '400', url: '/fonts/Inter/Inter-Regular.ttf' },
  ]
  
  await Promise.all(
    fontsToLoad.map(async ({ family, weight, url }) => {
      const font = new FontFace(family, `url(${url})`, { weight })
      await font.load()
      document.fonts.add(font)
    })
  )
}

// 必须在渲染 Canvas 前调用
await preloadFonts(templateId)
// 然后才能加载 SVG
fabric.loadSVGFromURL(svgUrl, callback)
```

**不做预加载的后果**：中文在 Canvas 中显示为系统默认字体（宋体），
与 SVG 文件和 PPTX 输出不一致，造成三端渲染不一致。
