import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
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
    "mentor": "你是一个幽默、专业的 AI 全栈开发导师。请用简明、鼓励的口吻，结合通俗生动的比喻回答用户的技术问题。如果有代码，请用 Markdown 格式规范包裹。",
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

# 新增：清空数据库历史记录接口
@app.delete("/messages")
def clear_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE chat_messages;")
    conn.commit()
    cursor.close()
    conn.close()
    return {"code": 200, "message": "记忆已清空"}

class MessageInput(BaseModel):
    content: str
    persona: str = "mentor"

# 升级：打字机流式接口
@app.post("/chat")
def chat_with_ai(msg: MessageInput):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 读取最近 6 轮记忆
    cursor.execute("SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT 6;")
    history_rows = cursor.fetchall()
    history_rows.reverse()

    # 存入本次用户提问
    cursor.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("user", msg.content))
    conn.commit()
    cursor.close()
    conn.close()

    # 组装上下文
    system_prompt = PERSONAS.get(msg.persona, PERSONAS["mentor"])
    messages_payload = [{"role": "system", "content": system_prompt}]
    for r_role, r_content in history_rows:
        messages_payload.append({"role": r_role, "content": r_content})
    messages_payload.append({"role": "user", "content": msg.content})

    def event_stream():
        full_reply = []
        try:
            stream = client.chat.completions.create(
                model=AI_MODEL,
                messages=messages_payload,
                stream=True  # 开启大模型流式传输
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    full_reply.append(token)
                    yield token
        except Exception as e:
            err = f"\n[调用大模型出错：{str(e)}]"
            full_reply.append(err)
            yield err
        finally:
            # 流式传输完毕后，把整段回答完整入库持久化
            complete_text = "".join(full_reply)
            if complete_text:
                db = get_db_connection()
                c = db.cursor()
                c.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("assistant", complete_text))
                db.commit()
                c.close()
                db.close()

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
