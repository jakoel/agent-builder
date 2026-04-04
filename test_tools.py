"""Quick smoke test for all tool library tools in the sandbox."""
import asyncio
from backend.services.sandbox_service import SandboxService
from backend.tool_library.registry import get_tool_code

sandbox = SandboxService()

async def test_tool(name, input_data):
    code = get_tool_code(name)
    try:
        result = await sandbox.execute_tool(code, input_data, timeout=10)
        status = "PASS"
        detail = str(result)[:120]
    except Exception as e:
        status = "FAIL"
        detail = str(e)[:120]
    print(f"  [{status}] {name}: {detail}")
    return status == "PASS"

async def main():
    print("Testing tools in sandbox:\n")
    results = []

    results.append(await test_tool("hash_data", {"text": "hello world"}))
    results.append(await test_tool("encode_decode", {"text": "hello world", "operation": "base64_encode"}))
    results.append(await test_tool("text_statistics", {"text": "The quick brown fox jumps over the lazy dog. This is a test sentence."}))
    results.append(await test_tool("extract_emails_urls", {"text": "Contact test@example.com or visit https://example.com"}))
    results.append(await test_tool("extract_with_regex", {"text": "Price: 19.99 and 42.50", "pattern": r"\d+\.\d+"}))
    results.append(await test_tool("json_transform", {"data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}], "sort_by": "age"}))
    results.append(await test_tool("deduplicate", {"data": [{"id": 1}, {"id": 1}, {"id": 2}]}))
    results.append(await test_tool("calculate_stats", {"values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}))
    results.append(await test_tool("date_calc", {"date": "2026-03-15", "operation": "add", "days": 7}))
    results.append(await test_tool("validate_schema", {"data": {"name": "test", "age": 25}, "schema": {"fields": {"name": {"type": "string", "required": True}, "age": {"type": "number", "min": 0}}}}))
    results.append(await test_tool("render_template", {"template": "Hello {{name}}!", "variables": {"name": "World"}}))
    results.append(await test_tool("format_markdown_report", {"title": "Test", "sections": [{"heading": "Intro", "type": "text", "content": "Hello."}]}))
    results.append(await test_tool("compare_values", {"old": {"a": 1, "b": 2}, "new": {"a": 1, "b": 3, "c": 4}}))
    results.append(await test_tool("keyword_search", {"text": "The quick brown fox jumps over the lazy dog", "keywords": ["fox", "cat"]}))
    results.append(await test_tool("csv_parse", {"csv_text": "name,age\nAlice,30\nBob,25"}))
    results.append(await test_tool("merge_datasets", {"left": [{"id": 1, "name": "A"}], "right": [{"id": 1, "val": "X"}], "left_key": "id"}))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} tools passed")

asyncio.run(main())
