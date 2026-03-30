import os
import requests

def send_pushplus_notification(title, content, topic: str = None):
    pushplus_url = os.getenv('PUSHPLUS')
    if not pushplus_url:
        print("PUSHPLUS URL is not set in environment variables.")
        return
    
    # 替换标题和内容
    url = pushplus_url.replace("XXX", title, 1).replace("XXX", content, 1)
    url = f'{pushplus_url}&title={title}&content={content}&template=html'
    url = url if not topic else f'{url}&topic={topic}'
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Notification sent successfully.")
        else:
            print(f"Failed to send notification. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")