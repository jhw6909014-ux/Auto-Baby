import os
import smtplib
import feedparser
import time
import urllib.parse
import random
import google.generativeai as genai
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
BLOGGER_EMAIL = os.environ.get("BLOGGER_EMAIL")

SHOPEE_LINKS = {
    "default": "https://s.shopee.tw/5L4eMZYBES", 
    "diaper": "https://s.shopee.tw/5VO4YsXXtV", "pampers": "https://s.shopee.tw/5VO4YsXXtV", "huggies": "https://s.shopee.tw/5VO4YsXXtV",
    "milk": "https://s.shopee.tw/5fhUlBWuYY", "formula": "https://s.shopee.tw/5fhUlBWuYY", "food": "https://s.shopee.tw/5fhUlBWuYY",
    "toy": "https://s.shopee.tw/5q0uxUWHDb", "game": "https://s.shopee.tw/5q0uxUWHDb", "lego": "https://s.shopee.tw/5q0uxUWHDb",
    "baby": "https://s.shopee.tw/9zqTv9GPlQ", "clothes": "https://s.shopee.tw/9zqTv9GPlQ", "mom": "https://s.shopee.tw/9zqTv9GPlQ", "stroller": "https://s.shopee.tw/9zqTv9GPlQ"
}

genai.configure(api_key=GOOGLE_API_KEY)
def get_valid_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name: return genai.GenerativeModel(m.name)
    except: return None
model = get_valid_model()
RSS_URL = "https://news.google.com/rss/search?q=parenting+tips+newborn&hl=en-US&gl=US&ceid=US:en"

def get_baby_image(title):
    magic_prompt = f"{title}, cute baby and parents, soft pastel colors, warm lighting, disney pixar style 3d render, 8k resolution"
    safe_prompt = urllib.parse.quote(magic_prompt)
    seed = int(time.time())
    img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=600&nologo=true&seed={seed}&model=flux"
    return f'<div style="text-align:center; margin-bottom:20px;"><img src="{img_url}" style="width:100%; max-width:800px; border-radius:12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>'

def get_best_link(title, content):
    text_to_check = (title + " " + content).lower()
    for keyword, link in SHOPEE_LINKS.items():
        if keyword in text_to_check and keyword != "default": return link
    return SHOPEE_LINKS["default"]

def ai_process_article(title, summary, shopee_link):
    if not model: return None, None
    
    # === 母嬰人格轉盤 ===
    styles = [
        "風格：一位『崩潰的新手媽媽』，帶小孩很累但很幸福，語氣充滿『又哭又笑』的真實感，很容易引起共鳴。",
        "風格：一位『經驗豐富的淡定阿嬤』，看過各種大風大浪，語氣溫柔且充滿智慧，給出過來人的建議。",
        "風格：一位『科普型爸爸』，喜歡研究成分、材質、安全性，用科學數據來說服大家。",
        "風格：一位『愛買的敗家媽咪』，看到可愛的童裝或玩具就受不了，一直喊『太可愛了吧』！"
    ]
    selected_style = random.choice(styles)
    print(f"🤖 AI 今日人格：{selected_style}")

    prompt = f"""
    任務：將以下英文新聞改寫成「育兒知識」部落格文章。
    【標題】{title}
    【摘要】{summary}
    
    【寫作指令】
    1. **請嚴格扮演此角色**：{selected_style}
    2. **SEO標題**：必須包含「育兒神器、媽媽社團推薦、寶寶健康、懶人包」其中之一。
    3. **中段導購**：在第二段結束後，自然插入一句「💡 媽咪們都在搶的育兒好物 (點此查看)」，並設為超連結({shopee_link})。
    
    【回傳 JSON】：{{"category": "育兒日記", "html_body": "HTML內容"}}
    【文末按鈕】：<br><div style="text-align:center;margin:30px;"><a href="{shopee_link}" style="background:#FF69B4;color:white;padding:15px 30px;text-decoration:none;border-radius:50px;font-weight:bold;">👶 媽咪推薦好物 (限時優惠)</a></div>
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        import json
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        data = json.loads(raw_text[start:end])
        return data.get("category", "育兒日記"), data.get("html_body", "")
    except: return "育兒快訊", f"<p>{summary}</p><br><div style='text-align:center'><a href='{shopee_link}'>點此查看詳情</a></div>"

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
        print(f"✅ 發布成功：{category}")
    except: pass

if __name__ == "__main__":
    if not GMAIL_APP_PASSWORD or not model: exit(1)
    feed = feedparser.parse(RSS_URL)
    if feed.entries:
        entry = feed.entries[0]
        my_link = get_best_link(entry.title, getattr(entry, 'summary', ''))
        img_html = get_baby_image(entry.title)
        category, text_html = ai_process_article(entry.title, getattr(entry, 'summary', ''), my_link)
        if text_html: send_email(entry.title, category, img_html + text_html)
    else: print("📭 無新文章")
