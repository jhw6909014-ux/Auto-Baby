import os
import smtplib
import feedparser
import time
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 讀取密碼 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

# ================= 2. 【賺錢核心】母嬰親子蝦皮連結 =================
SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/5L4eMZYBES", 
    "diaper": "https://s.shopee.tw/5VO4YsXXtV",
    "pampers": "https://s.shopee.tw/5VO4YsXXtV",
    "huggies": "https://s.shopee.tw/5VO4YsXXtV",
    "milk": "https://s.shopee.tw/5fhUlBWuYY",
    "formula": "https://s.shopee.tw/5fhUlBWuYY",
    "food": "https://s.shopee.tw/5fhUlBWuYY",
    "toy": "https://s.shopee.tw/5q0uxUWHDb",
    "game": "https://s.shopee.tw/5q0uxUWHDb",
    "lego": "https://s.shopee.tw/5q0uxUWHDb",
    "baby": "https://s.shopee.tw/9zqTv9GPlQ",
    "clothes": "https://s.shopee.tw/9zqTv9GPlQ",
    "mom": "https://s.shopee.tw/9zqTv9GPlQ",
    "stroller": "https://s.shopee.tw/9zqTv9GPlQ"
}

# ================= 3. AI 設定 =================
genai.configure(api_key=GOOGLE_API_KEY)

def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    return genai.GenerativeModel(m.name)
        return None
    except:
        return None

model = get_valid_model()

# 🔥 修改重點：換成 Google News RSS (育兒關鍵字)
RSS_URL = "https://news.google.com/rss/search?q=parenting+tips+newborn&hl=en-US&gl=US&ceid=US:en"

# ================= 4. 親子風格圖片生成 =================
def get_baby_image(title):
    magic_prompt = f"{title}, cute baby and parents, soft pastel colors, warm lighting, disney pixar style 3d render, 8k resolution, high quality"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>'

# ================= 5. 智慧選連結 =================
def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default":
            print(f"💰 偵測到親子商機：[{keyword}]")
            return link
    return SHOPEE_LINKS["default"]

# ================= 6. AI 寫作 =================
def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    print(f"🤖 AI 正在撰寫育兒文章：{title}...")
    
    prompt = f"""
    任務：將以下英文新聞改寫成「繁體中文」的「育兒知識」部落格文章。
    
    【標題】{title}
    【摘要】{summary}
    
    【要求】
    1. **分類標籤**：請判斷類別（例如：新手爸媽、寶寶健康、育兒神器、親子教育）。
    2. **內文撰寫**：分成三段，語氣要溫柔、充滿同理心，像是有經驗的媽媽在分享。
    3. **推銷植入**：文末加入按鈕。
    
    【回傳格式 (JSON)】：
    {{
        "category": "這裡填分類",
        "html_body": "這裡填 HTML 內容"
    }}
    
    【按鈕格式 (粉紅色系)】：
    <br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#FF69B4;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;box-shadow: 0 4px 6px rgba(0,0,0,0.1);">👶 媽咪推薦好物 (限時優惠)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "育兒日記"), data.get("html_body", "")
    except Exception as e:
        print(f"❌ AI 處理失敗: {e}")
        return "育兒快訊", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

# ================= 7. 寄信 =================
def send_email(subject, category, body_html):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body_html, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ 親子文章已發布！分類：{category}")
    except Exception as e:
        print(f"❌ 寄信失敗: {e}")

# ================= 8. 主程式 =================
if __name__ == "__main__":
    print(">>> 系統啟動 (3號店：母嬰親子版)...")
    if not GMAIL_APP_PASSWORD or not model:
        exit(1)

    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        print(f"📄 處理文章：{entry.title}")
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_baby_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html:
            send_email(entry.title, category, img_html + text_html)
    else:
        print("📭 無新文章 (請檢查 RSS)")
