import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import httpx
from google import genai
from google.genai import types

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8002/mcp")

SYSTEM_PROMPT = (
    "Ты полезный и умный AI помощник. "
    "У тебя есть доступ к локальным файлам расширения Markdown (.md) через инстурменты MCP. "
    "Используй эти инструменты, по требованию пользователя, когда он захочет расспросить про содержимое файлов или когда он захочет их изменить/создать файлы Markdown."
)

if not API_KEY:
    print("Ошибка: переменная окружения GEMINI_API_KEY не задана!")
    client = None
else:
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input="Привет! Это тестовый запрос к API.",
        )
        print("Тест API успешен:", interaction.output_text)
    except Exception as e:
        print("Ошибка при тестовом запросе API:", e)


async def mcp_request(method: str, params: dict | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(MCP_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["result"]


async def get_llm_tools() -> list[dict]:
    res = await mcp_request("tools/list")
    return [
        {
            "type": "function",
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("inputSchema", {"type": "object", "properties": {}, "required": []}),
        }
        for t in res.get("tools", [])
    ]


async def call_mcp_tool(name: str, arguments: dict) -> str:
    res = await mcp_request("tools/call", {"name": name, "arguments": arguments})
    parts = [c.get("text", "") for c in res.get("content", []) if c.get("type") == "text"]
    return "\n".join(parts) if parts else str(res)


@app.get("/")
async def get():
    with open("index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    prev_id = None

    try:
        while True:
            user_msg = await websocket.receive_text()
            if client is None:
                await websocket.send_text("Ошибка: переменная GEMINI_API_KEY не задана.")
                continue

            try:
                tools = await get_llm_tools()
                kwargs = {"model": MODEL_NAME, "input": user_msg, "tools": tools, "stream": False}
                if prev_id is None:
                    kwargs["system_instruction"] = SYSTEM_PROMPT
                else:
                    kwargs["previous_interaction_id"] = prev_id

                interaction = await client.aio.interactions.create(**kwargs)
                prev_id = getattr(interaction, "id", None)

                # Обработка function_call от LLM -> вызов MCP -> возврат function_result в LLM
                while True:
                    steps = getattr(interaction, "steps", None) or getattr(interaction, "outputs", None) or []
                    calls = [s for s in steps if getattr(s, "type", None) == "function_call"]
                    if not calls:
                        break

                    tool_results = []
                    for fc in calls:
                        result_text = await call_mcp_tool(fc.name, fc.arguments or {})
                        tool_results.append({
                            "type": "function_result",
                            "name": fc.name,
                            "call_id": fc.id,
                            "result": result_text,
                        })

                    interaction = await client.aio.interactions.create(
                        model=MODEL_NAME,
                        input=tool_results,
                        previous_interaction_id=prev_id,
                        tools=tools,
                    )
                    prev_id = getattr(interaction, "id", None)

                reply = getattr(interaction, "output_text", "") or ""
            except Exception as e:
                reply = f"Ошибка: {e}"

            await websocket.send_text(reply)

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("App2:app", host="0.0.0.0", port=8001, reload=True)