import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="postgres",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# 获取用户输入的提问内容
user_text = input("请输入你想对 AI 说的话：")

# 插入到数据库表中
insert_sql = "INSERT INTO chat_messages (role, content) VALUES (%s, %s);"
cursor.execute(insert_sql, ("user", user_text))

# 提交事务（真正保存进数据库）
conn.commit()

print(f"\n✅ 成功将数据写入数据库：'{user_text}'！请去 Navicat 刷新查看！\n")

cursor.close()
conn.close()
