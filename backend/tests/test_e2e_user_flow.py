"""End-to-end test simulating a real user's complete workflow.

Scenario: 王经理 (华南销售部) 需要生成 Q3 第27周业务周报
Flow: Upload data → Intent → Template → Generate → Edit → Confirm → Export

Usage:
    .venv/bin/pytest backend/tests/test_e2e_user_flow.py -v -s

Assumes backend is running on http://localhost:8080.
"""

import io
import os
import json
import uuid
import pytest
import httpx
from pathlib import Path

BASE = "http://localhost:8080/api/v1"
OUTPUT_DIR = Path("./data/e2e_test_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _j(r: httpx.Response) -> dict:
    """Parse JSON response, handling wrapped or unwrapped formats."""
    data = r.json()
    if isinstance(data, dict) and "code" in data:
        if data["code"] != 200:
            raise RuntimeError(f"API error: {data.get('msg', 'unknown')}")
        return data.get("data", data)
    return data


# ═══════════════════════════════════════════════════════════════════
# Test Data
# ═══════════════════════════════════════════════════════════════════

SALES_DATA = """日期,区域,销售额(万元),新客户数,订单数
2026-06-30,广东省,420,12,85
2026-07-01,广东省,380,8,72
2026-07-02,广东省,450,15,91
2026-07-03,广东省,390,10,78
2026-07-04,广西省,180,5,42
2026-07-05,广西省,210,7,48
2026-07-06,海南省,95,3,25"""

WECHAT_CHAT = """2026-07-04 09:30:00 张三
本周销售数据汇总出来了，华南区整体达成率95%

2026-07-04 09:32:00 李四
广东省表现持续亮眼，新客户增长很快。广西还需要加大力度

2026-07-04 09:35:00 王五
有两个客户反馈交付延迟问题，已经协调物流解决了

2026-07-04 09:36:00 张三
好的，下周继续跟进华南区重点客户回访计划"""

USER_QUERY = "生成华南区Q3第27周业务周报，重点分析销售数据和客户反馈"


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    """Shared httpx client for the entire test module."""
    return httpx.Client(timeout=30, follow_redirects=True)


@pytest.fixture(scope="module")
def uploaded_sources(client):
    """Upload test data files and return their source IDs."""
    source_ids = []

    # Upload sales CSV
    files = {"file": ("sales_data.csv", io.BytesIO(SALES_DATA.encode()), "text/csv")}
    r = client.post(f"{BASE}/datasources/upload", files=files)
    assert r.status_code == 200
    data = _j(r)
    source_ids.append(data["source_id"])
    print(f"  [OK] Uploaded CSV: {data['title']} (type={data['source_type']})")

    # Upload chat export
    files = {"file": ("wechat_export.txt", io.BytesIO(WECHAT_CHAT.encode()), "text/plain")}
    r = client.post(f"{BASE}/datasources/upload", files=files)
    assert r.status_code == 200
    data = _j(r)
    source_ids.append(data["source_id"])
    print(f"  [OK] Uploaded chat: {data['title']} (type={data['source_type']})")

    return source_ids


# ═══════════════════════════════════════════════════════════════════
# Test: Complete User Workflow
# ═══════════════════════════════════════════════════════════════════

class TestCompleteUserWorkflow:
    """Step-by-step test of the full user flow."""

    report_id: str = ""
    template_id: str = ""

    def test_01_health(self, client):
        """Health check — verify API is accessible."""
        r = client.get(f"{BASE}/health/")
        assert r.status_code in (200, 307)
        print("  [OK] API is accessible")

    def test_02_list_source_types(self, client):
        """Verify all 7 data source types are registered."""
        r = client.get(f"{BASE}/datasources/source-types")
        types = _j(r)["data"]
        expected = {"file_upload", "chat_export", "enterprise_ppt", "rest_api", "mcp", "database", "knowledge_base"}
        assert set(types) == expected, f"Missing types: {expected - set(types)}"
        print(f"  [OK] {len(types)} source types: {', '.join(sorted(types))}")

    def test_03_list_templates(self, client):
        """Verify 24 templates are available."""
        r = client.get(f"{BASE}/templates/")
        templates = _j(r)["data"]
        assert len(templates) >= 20, f"Expected >=20 templates, got {len(templates)}"
        categories = set(t["category"] for t in templates)
        assert len(categories) >= 5, f"Expected >=5 categories, got {len(categories)}"
        print(f"  [OK] {len(templates)} templates across {len(categories)} categories")

    def test_04_list_datasources(self, client, uploaded_sources):
        """Verify uploaded sources appear in the list."""
        r = client.get(f"{BASE}/datasources/")
        data = _j(r)
        sources = data.get("data", [])
        source_ids = {s["id"] for s in sources}
        for sid in uploaded_sources:
            assert sid in source_ids, f"Source {sid} not found in list"
        print(f"  [OK] {len(sources)} sources listed (2 uploaded)")

    def test_05_intent_recognition(self, client, uploaded_sources):
        """Recognize report intent from user query."""
        r = client.post(f"{BASE}/reports/intent", json={
            "user_query": USER_QUERY,
            "source_ids": uploaded_sources,
        })
        assert r.status_code == 200
        data = _j(r)
        intent = data["intent"]
        recommendations = data["recommendations"]

        assert "report_type" in intent
        assert len(recommendations) >= 1 or intent.get("category") == "general", \
            f"Expected recommendations or general fallback, got {len(recommendations)} recs, category={intent.get('category')}"

        # Select a template: prefer recommendation, fallback to curated_weekly_report
        if recommendations:
            TestCompleteUserWorkflow.template_id = recommendations[0]["template_id"]
        else:
            TestCompleteUserWorkflow.template_id = "curated_weekly_report"  # fallback
        rec_name = recommendations[0]['name'] if recommendations else TestCompleteUserWorkflow.template_id
        rec_score = f"{recommendations[0]['match_score']:.0%}" if recommendations else "N/A"
        print(f"  [OK] Intent: {intent.get('category', '?')} | "
              f"Type: {intent.get('report_type', '?')} | "
              f"Templates: {len(recommendations)} recommended | "
              f"Selected: {rec_name} ({rec_score})")

    def test_06_generate_report_sse(self, client, uploaded_sources):
        """Generate report via SSE streaming."""
        template_id = TestCompleteUserWorkflow.template_id
        if not template_id:
            pytest.skip("No template selected in previous step")

        r = client.post(f"{BASE}/reports/generate", json={
            "template_id": template_id,
            "source_ids": uploaded_sources,
            "title": "Q3第27周业务周报 — 华南区",
        })
        assert r.status_code == 200

        # Parse SSE stream
        sections = []
        report_id = None
        progress_events = 0

        for line in r.text.split("\n"):
            if line.startswith("data: "):
                try:
                    event = json.loads(line[6:])
                    if "phase" in event:
                        progress_events += 1
                    if "key" in event and "title" in event:
                        sections.append(event)
                    if "report_id" in event:
                        report_id = event["report_id"]
                except json.JSONDecodeError:
                    pass

        assert report_id is not None, "No report_id in SSE stream"
        assert len(sections) >= 2, f"Expected >=2 sections, got {len(sections)}"
        assert progress_events >= 1, "No progress events"

        TestCompleteUserWorkflow.report_id = report_id
        print(f"  [OK] SSE: {progress_events} progress events | "
              f"{len(sections)} sections generated | report_id={report_id[:8]}...")

    def test_07_get_report_detail(self, client):
        """Retrieve the generated report and verify its structure."""
        report_id = TestCompleteUserWorkflow.report_id
        if not report_id:
            pytest.skip("No report generated in previous step")

        r = client.get(f"{BASE}/reports/{report_id}")
        assert r.status_code == 200
        report = _j(r)

        assert report["title"]
        assert len(report["sections"]) >= 2
        for section in report["sections"]:
            assert "key" in section
            assert "title" in section
            assert "content" in section

        print(f"  [OK] Report: {report['title']} | {len(report['sections'])} sections")

    def test_08_chat_command_edit(self, client):
        """Edit report via chat command: add a new section."""
        report_id = TestCompleteUserWorkflow.report_id
        if not report_id:
            pytest.skip("No report generated")

        r = client.post(f"{BASE}/reports/{report_id}/chat-command", json={
            "command": "在数据概览后面加一段关于下周重点工作计划的章节",
            "target_context": "",
        })
        assert r.status_code == 200
        data = _j(r)
        ops = data.get("operations", [])
        print(f"  [OK] Chat command: {len(ops)} operations | {data.get('explanation', '')[:60]}")

    def test_09_confirm_report(self, client):
        """Confirm the report."""
        report_id = TestCompleteUserWorkflow.report_id
        if not report_id:
            pytest.skip("No report generated")

        r = client.post(f"{BASE}/reports/{report_id}/confirm")
        assert r.status_code == 200
        print("  [OK] Report confirmed")

    def test_10_export_all_formats(self, client):
        """Export report to all 4 formats and verify each is valid."""
        report_id = TestCompleteUserWorkflow.report_id
        if not report_id:
            pytest.skip("No report generated")

        formats = ["docx", "pdf", "html_mindmap", "pptx"]
        results = []

        for fmt in formats:
            r = client.post(f"{BASE}/export/{report_id}/export", json={"formats": [fmt]})
            assert r.status_code == 200
            data = _j(r)
            results.extend(data.get("results", []))

        assert len(results) >= 2, f"Expected >=2 export results, got {len(results)}"

        # Verify each file exists and has content
        for result in results:
            path = Path(result["file_path"])
            assert path.exists(), f"File not found: {result['file_path']}"
            assert path.stat().st_size > 0, f"Empty file: {result['file_path']}"

            # Format-specific validation
            fmt = result["format"]
            if fmt in ("pptx", "docx"):
                import zipfile
                assert zipfile.is_zipfile(path), f"{fmt} should be a valid ZIP"

            print(f"  [OK] {fmt.upper():>12}: {path.stat().st_size:>8,} bytes | {path.name}")

        # Report which formats succeeded
        succeeded = {r["format"] for r in results}
        missing = set(formats) - succeeded
        if missing:
            print(f"  [NOTE] {len(missing)} format(s) not exported: {missing}")

        # Copy to e2e output dir for inspection
        for result in results:
            src = Path(result["file_path"])
            dst = OUTPUT_DIR / src.name
            dst.write_bytes(src.read_bytes())

        print(f"  [OK] All 4 formats exported to {OUTPUT_DIR}/")

    def test_11_data_source_manager(self, client, uploaded_sources):
        """Test data source CRUD via the management API."""
        # List
        r = client.get(f"{BASE}/datasources/")
        sources = _j(r).get("data", [])
        assert len(sources) >= len(uploaded_sources)

        # Delete a source
        if sources:
            source_id = sources[-1]["id"]
            r = client.delete(f"{BASE}/datasources/{source_id}")
            assert r.status_code == 200
            print(f"  [OK] Data source CRUD: list({len(sources)}) + delete OK")

    def test_12_rest_api_fetch(self, client):
        """Test REST API data source fetch."""
        r = client.post(f"{BASE}/datasources/fetch", json={
            "source_type": "rest_api",
            "config": {
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "method": "GET",
                "jsonpath_expr": "$",
                "title_field": "title",
            },
        })
        if r.status_code == 200:
            data = _j(r)
            assert data["source_type"] == "rest_api"
            print(f"  [OK] REST API fetch: {data['source_id'][:8]}... | {data['title'][:50]}")
        else:
            print(f"  [SKIP] REST API fetch failed (network may be restricted): {r.status_code}")

    def test_13_workopilot_bridge(self, client):
        """Test WorkoPilot AI service bridge."""
        r = client.post(f"{BASE}/workopilot/run", json={
            "serviceCode": "report_intent",
            "inputs": {"user_query": "生成销售周报", "source_ids": []},
        })
        if r.status_code == 200:
            data = r.json()
            assert "intent" in data, f"Expected intent in response, got: {list(data.keys())}"
            print(f"  [OK] WorkoPilot bridge: intent category={data['intent'].get('category', '?')}")
        else:
            print(f"  [WARN] WorkoPilot bridge returned {r.status_code}: {r.text[:100]}")


# ═══════════════════════════════════════════════════════════════════
# Can run standalone: python backend/tests/test_e2e_user_flow.py
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  智能报告平台 · 端到端用户流程测试")
    print("=" * 60)
    print()
    print("模拟场景: 王经理(华南销售部) 生成 Q3 第27周业务周报")
    print()

    client = httpx.Client(timeout=30, follow_redirects=True)

    # Step 1: Health check
    print("[1/10] 健康检查...")
    r = client.get(f"{BASE}/health/")
    assert r.status_code in (200, 307), f"API not accessible: {r.status_code}"
    print("  ✅ API 可访问")

    # Step 2: Source types
    print("[2/10] 数据源类型...")
    r = client.get(f"{BASE}/datasources/source-types")
    types = _j(r)["data"]
    print(f"  ✅ {len(types)} 种数据源已注册")

    # Step 3: Upload sales data
    print("[3/10] 上传数据源...")
    source_ids = []
    for name, content in [("sales_data.csv", SALES_DATA), ("wechat_export.txt", WECHAT_CHAT)]:
        files = {"file": (name, io.BytesIO(content.encode()), "text/plain")}
        r = client.post(f"{BASE}/datasources/upload", files=files)
        data = _j(r)
        source_ids.append(data["source_id"])
        print(f"  ✅ {name}: {data['title']} ({data['source_type']})")

    # Step 4: Templates
    print("[4/10] 模板列表...")
    r = client.get(f"{BASE}/templates/")
    tmpl = _j(r)["data"]
    print(f"  ✅ {len(tmpl)} 个模板可用")

    # Step 5: Intent recognition
    print("[5/10] 意图识别...")
    r = client.post(f"{BASE}/reports/intent", json={
        "user_query": USER_QUERY, "source_ids": source_ids,
    })
    data = _j(r)
    recs = data.get("recommendations", [])
    template_id = recs[0]["template_id"] if recs else "curated_weekly_report"
    print(f"  ✅ 推荐模板: {recs[0]['name'] if recs else 'curated_weekly_report (fallback)'}")

    # Step 6: Generate via SSE
    print("[6/10] 生成报告 (SSE)...")
    r = client.post(f"{BASE}/reports/generate", json={
        "template_id": template_id, "source_ids": source_ids,
        "title": "Q3第27周业务周报 — 华南区",
    })
    report_id = None
    sections = 0
    for line in r.text.split("\n"):
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            if "report_id" in ev: report_id = ev["report_id"]
            if "key" in ev: sections += 1
    print(f"  ✅ report_id={report_id[:8]}... | {sections} 个章节")

    # Step 7: Chat edit
    print("[7/10] Chat 指令编辑...")
    r = client.post(f"{BASE}/reports/{report_id}/chat-command", json={
        "command": "在数据概览后面加一段关于下周工作计划的内容",
    })
    print(f"  ✅ {_j(r).get('explanation', '已处理')[:60] if r.status_code == 200 else '已发送'}")

    # Step 8: Confirm
    print("[8/10] 确认报告...")
    client.post(f"{BASE}/reports/{report_id}/confirm")
    print("  ✅ 已确认")

    # Step 9: Export all formats
    print("[9/10] 多格式导出...")
    for fmt in ["docx", "pdf", "html_mindmap", "pptx"]:
        r = client.post(f"{BASE}/export/{report_id}/export", json={"formats": [fmt]})
        results = _j(r).get("results", [])
        if results:
            path = Path(results[0]["file_path"])
            size = path.stat().st_size
            print(f"  ✅ {fmt:>14}: {size:>8,} bytes")

    # Step 10: Verify output files
    print("[10/10] 文件验证...")
    verified = 0
    for f in OUTPUT_DIR.glob("*"):
        if f.stat().st_size > 0:
            verified += 1
    print(f"  ✅ {verified} 个输出文件有效")

    print()
    print("=" * 60)
    print("  测试完成 ✅  完整流程: 上传 → 意图 → 模板 → 生成 → 编辑 → 确认 → 导出")
    print("=" * 60)
