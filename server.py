import os
from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

# 从本地安全加载 .env 文件里的敏感变量
load_dotenv()

app = FastAPI(title="真正接入大模型的 AI 全栈后端")

# 安全地从环境变量中读取，代码中不再包含任何真实密码或密钥
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

client = OpenAI(
    api_key=AI_API_KEY,
    base_url=AI_BASE_URL
)

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password=os.getenv("DB_PASSWORD", "mysecretpassword")
    )

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

@app.post("/chat")
def chat_with_ai(msg: MessageInput):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("user", msg.content))
    conn.commit()

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个幽默、专业的 AI 全栈开发导师。请用简炼、鼓励的口吻回答。"},
                {"role": "user", "content": msg.content}
            ]
        )
        ai_reply = response.choices[0].message.content
    except Exception as e:
        ai_reply = f"调用大模型出错，请检查 API Key：{str(e)}"

    cursor.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("assistant", ai_reply))
    conn.commit()

    cursor.close()
    conn.close()

    return {
        "code": 200,
        "user_question": msg.content,
        "ai_answer": ai_reply
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
