import json
from pathlib import Path
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI(title="MCP Markdown Server")
MD_DIR = Path(__file__).parent / "md_files"
MD_DIR.mkdir(exist_ok=True)

TOOLS = [
    {
        "name": "list_md_files",
        "description": "Получить список всех .md файлов в локальной папке сервера",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_md_file",
        "description": "Прочитать содержимое одного .md файла по имени",
        "inputSchema": {
            "type": "object",
            "properties": {"filename": {"type": "string", "description": "Имя .md файла"}},
            "required": ["filename"],
        },
    },
    {
        "name": "create_md_file",
        "description": "Создать новый .md файл с указанным именем и содержимым",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Имя нового .md файла"},
                "content": {"type": "string", "description": "Текст файла в формате Markdown"},
            },
            "required": ["filename", "content"],
        },
    },
]


def safe_md_path(filename: str) -> Path:
    name = Path(filename).name
    return MD_DIR / (name if name.endswith(".md") else f"{name}.md")


def call_tool(name: str, args: dict) -> str:
    if name == "list_md_files":
        return json.dumps(sorted(p.name for p in MD_DIR.glob("*.md") if p.is_file()), ensure_ascii=False)
    if name == "read_md_file":
        path = safe_md_path(args["filename"])
        return path.read_text(encoding="utf-8") if path.is_file() else f"Ошибка: файл '{path.name}' не найден."
    if name == "create_md_file":
        path = safe_md_path(args["filename"])
        if path.exists():
            return f"Ошибка: файл '{path.name}' уже существует."
        path.write_text(args.get("content", ""), encoding="utf-8")
        return f"Файл '{path.name}' успешно создан."
    raise ValueError(f"Неизвестная операция: {name}")


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    body = await request.json()
    req_id, method, params = body.get("id"), body.get("method"), body.get("params", {})

    if method == "initialize":
        res = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "md-mcp", "version": "1.0"}}
    elif method == "tools/list":
        res = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            text = call_tool(params["name"], params.get("arguments", {}))
            res = {"content": [{"type": "text", "text": text}], "isError": False}
        except Exception as e:
            res = {"content": [{"type": "text", "text": str(e)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    return {"jsonrpc": "2.0", "id": req_id, "result": res}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)