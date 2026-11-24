import os
import requests

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

class AgentError(Exception):
    pass

SYSTEM_PROMPT = (
    "Ты - StudyBot, встроенный ИИ-помощник веб-приложения StudyPlanner. "
    "Отвечай кратко, по-русски, вежливо. Помогай пользователю с его дедлайнами, "
    "составлением плана подготовки и управлением задачами. "
    "Не давай советов, не связанных с учёбой. Не раскрывай пароли и технические данные."
)

def ask_agent(history, user_text):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_text})

    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = "Bearer " + LLM_API_KEY

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500,
    }
    
    try:
        resp = requests.post(
            LLM_BASE_URL.rstrip("/") + "/chat/completions",
            json=payload, headers=headers, timeout=LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise AgentError("ИИ-агент не ответил вовремя.")
    except requests.exceptions.RequestException:
        raise AgentError("Сервис ИИ-агента временно недоступен.")
    except (KeyError, IndexError, ValueError):
        raise AgentError("Получен некорректный ответ сервиса ИИ.")
    
    return answer.strip()