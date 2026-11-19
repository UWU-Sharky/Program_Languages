import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
import uvicorn

app = FastAPI()

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash" 

if not API_KEY:
    print("Ошибка: переменная окружения GEMINI_API_KEY не задана!")
    client = None
else:
    client = genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    # Тестовый запрос при старте
    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input="Привет! Это тестовый запрос к API.",
        )
        print("Тест API успешен:", interaction.output_text)
    except Exception as e:
        print("Ошибка при тестовом запросе API:", e)


@app.get("/")
async def get():
    with open("index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    prev_id = None  # Сохранение ID предыдущего шага

    try:
        while True:
            user_msg = await websocket.receive_text()
            if client is None:
                await websocket.send_text("Ошибка: не задана переменная GEMINI_API_KEY.")
                continue

            try:
                if prev_id is None:
                    interaction = await client.aio.interactions.create(
                        model=MODEL_NAME,
                        input=user_msg,
                        system_instruction="You are a helpful AI assistant.",
                    )
                else:
                    interaction = await client.aio.interactions.create(
                        model=MODEL_NAME,
                        input=user_msg,
                        previous_interaction_id=prev_id,
                    )
                prev_id = interaction.id
                reply = interaction.output_text or ""
            except Exception as e:
                reply = f"Ошибка API: {e}"

            await websocket.send_text(reply)

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run("App1:app", host="0.0.0.0", port=8001, reload=True)