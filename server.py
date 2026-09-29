import os
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

app = FastAPI(title="AI 全栈后端 - RAG 增强版")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

PERSONAS = {
    "mentor": "你是一个幽默、专业的 AI 全栈开发导师。请依据参考知识库资料严谨、亲切地回答用户的问题。",
    "english": "You are a friendly English coach. Always talk in English and reference the uploaded knowledge.",
    "interviewer": "你是一名严谨的大厂面试官。结合参考资料进行深度考察与技术追问。",
    "roaster": "你是一个幽默犀利的脱口秀大师，用风趣的段子结合资料回答。"
}

def get_db_connection():
    return psycopg2.connect(
        host="localhost", port=5432, database="postgres", user="postgres",
        password=os.getenv("DB_PASSWORD", "mysecretpassword")
    )

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            role VARCHAR(20),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pdf_knowledge (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255),
            chunk_id INT,
            page_num INT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    c.close()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/messages")
def read_messages():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, role, content, created_at FROM chat_messages ORDER BY id ASC;")
    rows = c.fetchall()
    data = [{"id": r[0], "role": r[1], "content": r[2], "created_at": str(r[3])} for r in rows]
    c.close()
    conn.close()
    return {"code": 200, "data": data}

@app.delete("/messages")
def clear_messages():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("TRUNCATE TABLE chat_messages;")
    conn.commit()
    c.close()
    conn.close()
    return {"code": 200, "message": "记忆已清空"}

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    chunks = []
    chunk_size = 350
    filename = file.filename

    if filename.lower().endswith(".pdf"):
        reader = PdfReader(file.file)
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            clean_text = re.sub(r'\s+', ' ', text).strip()
            for i in range(0, len(clean_text), chunk_size):
                chunk = clean_text[i:i + chunk_size]
                if len(chunk) > 15:
                    chunks.append((page_idx + 1, chunk))
    else:
        # 支持 txt / md
        raw_bytes = await file.read()
        text = raw_bytes.decode("utf-8", errors="ignore")
        clean_text = re.sub(r'\s+', ' ', text).strip()
        for i in range(0, len(clean_text), chunk_size):
            chunk = clean_text[i:i + chunk_size]
            if len(chunk) > 15:
                chunks.append((1, chunk))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("TRUNCATE TABLE pdf_knowledge;")
    for idx, (page_num, chunk_content) in enumerate(chunks):
        c.execute(
            "INSERT INTO pdf_knowledge (filename, chunk_id, page_num, content) VALUES (%s, %s, %s, %s);",
            (filename, idx + 1, page_num, chunk_content)
        )
    conn.commit()
    c.close()
    conn.close()

    return {"code": 200, "filename": filename, "total_chunks": len(chunks)}

@app.get("/knowledge/status")
def get_knowledge_status():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT filename, COUNT(*) FROM pdf_knowledge GROUP BY filename LIMIT 1;")
    row = c.fetchone()
    c.close()
    conn.close()
    if row:
        return {"loaded": True, "filename": row[0], "chunks": row[1]}
    return {"loaded": False}

@app.delete("/knowledge")
def delete_knowledge():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("TRUNCATE TABLE pdf_knowledge;")
    conn.commit()
    c.close()
    conn.close()
    return {"code": 200, "message": "知识库已卸载"}

def retrieve_relevant_knowledge(query: str, top_k: int = 3):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT filename, page_num, content FROM pdf_knowledge;")
    all_chunks = c.fetchall()
    c.close()
    conn.close()

    if not all_chunks:
        return "", []

    keywords = set(re.findall(r'[\w\u4e00-\u9fa5]+', query.lower()))
    scored_chunks = []
    for filename, page_num, content in all_chunks:
        score = sum(1 for kw in keywords if kw in content.lower())
        if score > 0:
            scored_chunks.append((score, filename, page_num, content))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_results = scored_chunks[:top_k]

    if not top_results:
        top_results = [(0, all_chunks[0][0], all_chunks[0][1], all_chunks[0][2])]

    ref_text = "\n\n".join([f"【摘录来源：《{fn}》第{pn}页】：\n{txt}" for _, fn, pn, txt in top_results])
    sources = [f"《{fn}》P{pn}" for _, fn, pn, txt in top_results]
    return ref_text, list(set(sources))

class MessageInput(BaseModel):
    content: str
    persona: str = "mentor"

@app.post("/chat")
def chat_with_ai(msg: MessageInput):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_messages ORDER BY id DESC LIMIT 4;")
    history_rows = c.fetchall()
    history_rows.reverse()

    c.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("user", msg.content))
    conn.commit()
    c.close()
    conn.close()

    ref_context, sources = retrieve_relevant_knowledge(msg.content)

    system_prompt = PERSONAS.get(msg.persona, PERSONAS["mentor"])
    if ref_context:
        system_prompt += f"\n\n【专属外挂知识库参考资料】：\n{ref_context}\n\n【回答规范】：请严格根据上方参考资料回答用户问题，并在回答中自然提及资料来源。如果资料中未提及，请如实说明资料中没有记载。"

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
                stream=True
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
            complete_text = "".join(full_reply)
            if complete_text:
                db = get_db_connection()
                cur = db.cursor()
                cur.execute("INSERT INTO chat_messages (role, content) VALUES (%s, %s);", ("assistant", complete_text))
                db.commit()
                cur.close()
                db.close()

    return StreamingResponse(event_stream(), media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
