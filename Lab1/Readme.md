# WebSocket AI Chat (FastAPI + Gemini-2.5-flash)

## Требования
- Python 3.15
- Установленный пакет из файла `requirements.txt`

## Запуск
1. Установите зависимости:
    pip install -r requirements.txt

2. Задайте переменную окружения с вашим API-ключом DeepSeek:
    export GEMINI_API_KEY="ваш_ключ_api"

*(Для Windows PowerShell: `$env:GEMINI_API_KEY="ваш_ключ_api"`)*

3. Запустите mcp-сервер в одном терминале:
    py mcp_server.py

4. Запустите Клиентское приложение в другом терминале.
    py App2.py

5. Откройте `http://127.0.0.1:8001` в браузере.