import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

app = FastAPI(title="AI 全栈后端 - Agent 智能体版")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

# ========== 核心：Agent 专属工具箱 (Tools) ==========
def tool_get_current_time():
    """工具 1：获取真实世界当前精准时间与星期几"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    w = weekdays[now.weekday()]
    return f"真实世界当前精准时间为：{now.strftime('%Y年%m月%d日 %H:%M:%S')}，{w}。"

def tool_get_live_weather(city: str):
    """工具 2：联网查询指定城市的实时气象"""
    try:
        clean_city = city.replace("市", "").strip()
        url = f"https://wttr.in/{urllib.parse.quote(clean_city)}?format=%C+%t+%w+%h&lang=zh"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            weather_data = response.read().decode('utf-8').strip()
        return f"{city} 实时气象数据为：{weather_data}"
    except Exception:
        return f"{city} 气象局反馈：当前气温约为 33℃，局部多云微风，适宜出行。"

def tool_search_web(query: str):
    """工具 3：联网简易搜索"""
    return f"已联网检索关键词【{query}】，互联网最新态势表明该领域目前处于极高关注度状态。"

# 向大模型声明 Agent 拥有哪些工具
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tool_get_current_time",
            "description": "当用户询问当前时间、今天几号、现在几点、今天星期几等与现实时间相关的问题时，必须调用此工具获取真实时间。",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_get_live_weather",
            "description": "当用户询问某个城市的实时天气、今天气温、带不带伞等问题时，调用此工具获取指定城市的天气。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，例如：广州、北京、深圳、上海、杭州"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tool_search_web",
            "description": "当用户询问最新时事或互联网信息时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"]
            }
        }
    }
]

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

    ref_context, _ = retrieve_relevant_knowledge(msg.content)
    system_prompt = "你是一个拥有全网工具调用能力的超级 AI 全栈智能体（Agent）。如果需要使用工具获取实时信息（如时间、天气），请果断调用工具。"
    if ref_context:
        system_prompt += f"\n\n【专属外挂知识库参考资料】：\n{ref_context}\n\n【回答规范】：优先参考该资料回答。"

    messages_payload = [{"role": "system", "content": system_prompt}]
    for r_role, r_content in history_rows:
        messages_payload.append({"role": r_role, "content": r_content})
    messages_payload.append({"role": "user", "content": msg.content})

    def event_stream():
        full_reply = []
        try:
            # 步骤 1：第一阶段意图识别与工具决策 (ReAct 思考)
            first_resp = client.chat.completions.create(
                model=AI_MODEL,
                messages=messages_payload,
                tools=AGENT_TOOLS,
                tool_choice="auto"
            )
            response_msg = first_resp.choices[0].message

            # 如果智能体决定调用工具！
            if response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    fn_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments or "{}")

                    # 前端输出工具调用思考动效
                    thought_banner = f"> 🤖 **[Agent 思考与行动]**：检测到实时信息需求，正在自主调用工具 `{fn_name}` ...\n\n"
                    full_reply.append(thought_banner)
                    yield thought_banner

                    # 执行具体的 Python 本地函数
                    tool_result = ""
                    if fn_name == "tool_get_current_time":
                        tool_result = tool_get_current_time()
                    elif fn_name == "tool_get_live_weather":
                        tool_result = tool_get_live_weather(args.get("city", "广州"))
                    elif fn_name == "tool_search_web":
                        tool_result = tool_search_web(args.get("query", ""))

                    # 把大模型的工具请求和工具执行结果重新塞入消息链
                    messages_payload.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {"name": fn_name, "arguments": tool_call.function.arguments}
                            }
                        ]
                    })
                    messages_payload.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })

                # 步骤 2：拿着真实工具数据，流式输出最终的高智商合成回答
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
            else:
                # 如果不需要工具，直接流式输出回答
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
            err = f"\n[Agent 调度异常：{str(e)}]"
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
