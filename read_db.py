import psycopg2

# 1. 建立与刚刚 Docker 数据库的连接
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="postgres",
    user="postgres",
    password="mysecretpassword"
)

# 2. 创建游标
cursor = conn.cursor()

# 3. 向数据库发送查询指令
cursor.execute("SELECT id, role, content, created_at FROM chat_messages ORDER BY id ASC;")

# 4. 抓取所有查询结果
rows = cursor.fetchall()

print("\n" + "="*45)
print("  🚀 成功从本地数据库读取到 AI 聊天记录：")
print("="*45)

for row in rows:
    msg_id, role, content, created_at = row
    tag = "👤 [用户]" if role == "user" else "🤖 [AI助手]"
    print(f"\n{tag} (ID: {msg_id})")
    print(f"内容: {content}")
    print(f"时间: {created_at}")

print("\n" + "="*45 + "\n")

# 5. 关闭连接
cursor.close()
conn.close()
