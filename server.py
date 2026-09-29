import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="真正接入大模型的 AI 全栈后端")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

PERSONAS = {
    "mentor": "你是一个幽默、专业的 AI 全栈开发导师。请用简明、鼓励的口吻，结合通俗生动的比喻回答用户的技术问题。",
    "english": "You are a friendly and patient native English coach. Always talk in English, give natural responses, and at the end of your reply, gently point out and correct any grammar or vocabulary mistakes in the user's input.",
    "interviewer": "你是一名严谨、专业的大厂技术面试官。请针对用户提出的概念进行深度考察，挖掘底层原理、边界场景，并给出专业且有深度的追问。",
    "roaster": "你是一个幽默犀利、毒舌但无恶意的脱口秀演员。用充满机智槽点、段子和吐槽的口吻回答用户，逗他们开心。"
}

def get_db_connection():
    return psycopg2.connect(
        host="localhost", port=5432, database="postgres", user="postgres",
        password=os.getenv("DB_PASSWORD", "mysecretpassword")
    )

@app.get("/", response_class=HTMLResponse)
def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/messages")
def read_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role, content, created_at FROM chat_messages ORDER BY id ASC;")
    rows = cursor.fetchall()
    data = [{"id": r[0], "role": r[1], "content": r[2], "created_at": str(r[3])} for r in rows]
    cursor.close()
    conn.close()
    return {"code": 200, "data": data}

class MessageInput(BaseModel):
    content: str
    persona: str = "mentor"

@app.post("/chat")
def chat_with_ai(msg: MessageInput):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 提取数据库最近 6 轮历史记忆
    cursor.execute("SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT 6;")
    history_rows = cursor.fetchall()
    history_rows.reverse()

    # 保存本次提问
    cursor.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("user", msg.content))
    conn.commit()

    # 组装完整上下文（人设 + 历史对话 + 本次提问）
    system_prompt = PERSONAS.get(msg.persona, PERSONAS["mentor"])
    messages_payload = [{"role": "system", "content": system_prompt}]
    for r_role, r_content in history_rows:
        messages_payload.append({"role": r_role, "content": r_content})
    messages_payload.append({"role": "user", "content": msg.content})

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages_payload
        )
        ai_reply = response.choices[0].message.content
    except Exception as e:
        ai_reply = f"调用大模型出错，请检查 API Key：{str(e)}"

    cursor.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("assistant", ai_reply))
    conn.commit()
    cursor.close()
    conn.close()

    return {"code": 200, "user_question": msg.content, "ai_answer": ai_reply}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
