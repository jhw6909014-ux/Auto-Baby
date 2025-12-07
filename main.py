import os
import smtplib
import feedparser
import time
import urllib.parse
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= 1. 設定區 =================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/5L4eMZYBES", 
    "diaper": "https://s.shopee.tw/5VO4YsXXtV", "milk": "https://s.shopee.tw/5fhUlBWuYY",
    "toy": "https://s.shopee.tw/5q0uxUWHDb", "baby": "https://s.shopee.tw/9zqTv9GPlQ"
}

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
RSS_URL = "https://news.google.com/rss/search?q=parenting+tips+newborn&hl=en-US&gl=US&ceid=US:en"

# ================= 2. 功能區 =================
def get_baby_image(title):
    safe_prompt = urllib.parse.quote(f"{title}, cute baby, soft pastel colors, disney style, 8k")
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={int(time.time())}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px;"></div>'

def get_best_link(title, content):
    text = (title + " " + content).lower()
    for k, v in SHOPEE_LINKS.items():
        if k in text and k != "default": return v
    return SHOPEE_LINKS["default"]

def ai_process_article(title, summary, link):
    if not model: return None, None
    
    # 🔥 SEO 優化 Prompt
    prompt = f"""
    任務：將以下新聞改寫成「繁體中文」的「育兒知識/媽咪推薦」風格文章。
    
    【新聞標題】{title}
    【新聞摘要】{summary}
    
    【SEO 關鍵字策略 (標題必填)】
    1. 標題必須包含：育兒神器、媽媽社團推薦、寶寶健康、懶人包 (擇一使用)。
    2. 標題範例：「{title}？新手爸媽必看的3個重點」。

    【內文結構】
    1. **同理心開頭**：理解帶小孩的辛苦。
    2. **知識分享**：提供育兒建議。
    3. **中段廣告**：在第二段結束後，插入一句「💡 媽咪們都在搶的育兒好物 (點此查看)」，並設為超連結({link})。
    4. **實用建議**：如何解決問題。
    5. **結尾**：為爸媽加油打氣。

    【回傳 JSON】: {{"category": "育兒日記", "html_body": "HTML內容"}}
    【文末按鈕】: <br><div style="text-align:center;margin:30px;"><a href="{link}" style="background:#FF69B4;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">👶 媽咪推薦好物 (限時優惠)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        data = json.loads(text[text.find('{'):text.rfind('}')+1])
        return data["category"], data["html_body"]
    except: return None, None

def send_email(subject, category, body):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = BLOGGER_EMAIL
    msg['Subject'] = f"{subject} #{category}"
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ 發送成功")
    except: pass

if __name__ == "__main__":
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        print(f"📄 {entry.title}")
        link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img = get_baby_image(entry.title)
        cat, html = ai_process_article(entry.title, getattr(entry, 'summary', ''), link)
        if html: send_email(entry.title, cat, img + html)
