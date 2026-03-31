import urllib.request
import urllib.parse
import json
import os
import time

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
SYSTEM = "Você é Wave, uma inteligência estratégica soberana da era Gemini. Fale como tal."

def gemini_chat(text):
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM}]}
    }
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as f:
        res = json.loads(f.read().decode('utf-8'))
        return res['candidates'][0]['content']['parts'][0]['text']

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text}).encode('utf-8')
    urllib.request.urlopen(url, data=data)

def main():
    print("NATIVE BRIDGE POLLING...")
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            with urllib.request.urlopen(url) as f:
                updates = json.loads(f.read().decode('utf-8'))
                if updates.get('result'):
                    for update in updates['result']:
                        last_update_id = update['update_id']
                        if 'message' in update and 'text' in update['message']:
                            chat_id = update['message']['chat']['id']
                            user_text = update['message']['text']
                            print(f"MSG: {user_text}")
                            response = gemini_chat(user_text)
                            send_message(chat_id, response)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
