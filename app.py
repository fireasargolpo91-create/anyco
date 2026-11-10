import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secret_token_123")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# জেমিনাই এআই-এর জন্য আপনার শপের নিয়ম
SYSTEM_INSTRUCTION = """
তুমি একটি ফেসবুক পেজের কাস্টমার কেয়ার সহকারী।
- ক্রেতার সাথে সবসময় অত্যন্ত বিনম্র, মিষ্টি ও প্রফেশনাল ভাষায় বাংলায় কথা বলবে।
- স্পষ্টভাবে জানাবে: ঢাকার মধ্যে ডেলিভারি চার্জ ৮০ টাকা, ঢাকার বাইরে ১৫০ টাকা।
- উত্তর সবসময় সংক্ষিপ্ত এবং টু-দ্য-পয়েন্ট ৩-৪ লাইনের মধ্যে রাখবে।
- ক্রেতা পণ্য অর্ডার করতে চাইলে তার নাম, মোবাইল নম্বর এবং সম্পূর্ণ ঠিকানা চেয়ে নেবে।
"""

@app.route("/", methods=["GET"])
def home():
    return "Bot server is running successfully!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    if data and data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    message = messaging_event["message"]
                    # বট যেন নিজের পাঠানো মেসেজে নিজে উত্তর না দেয়
                    if message.get("is_echo"):
                        continue

                    sender_id = messaging_event["sender"]["id"]
                    user_text = message.get("text")

                    if user_text:
                        reply_text = get_gemini_reply(user_text)
                        send_facebook_message(sender_id, reply_text)

        return "EVENT_RECEIVED", 200
    return "Not Found", 404

def get_gemini_reply(user_message):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "generationConfig": {
                "maxOutputTokens": 300,
                "temperature": 0.7
            }
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res_json = res.json()
        reply = res_json["candidates"][0]["content"]["parts"][0]["text"]
        return reply.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        return "ধন্যবাদ আপনার মেসেজের জন্য! আমাদের একজন প্রতিনিধি খুব শীঘ্রই আপনার সাথে যোগাযোগ করবেন।"

def send_facebook_message(recipient_id, text):
    try:
        url = f"https://graph.facebook.com/v21.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        headers = {"Content-Type": "application/json"}
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"Facebook Send Error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
