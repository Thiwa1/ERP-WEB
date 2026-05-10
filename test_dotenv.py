from dotenv import load_dotenv
import os

with open('.env.test', 'w') as f:
    f.write("DB_PASSWORD=gy$UP1.HsvuL\n")

load_dotenv('.env.test')
print("Parsed password:", os.getenv("DB_PASSWORD"))
