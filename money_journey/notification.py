import os
import requests

def send_pushplus_notification(title, content, topic: str = None):
    pushplus_token = os.getenv('PUSHPLUS_TOKEN')
    if not pushplus_token:
        print("PUSHPLUS TOKEN is not set in environment variables.")
        return
    
    # 替换标题和内容
    url = f'https://www.pushplus.plus/send?token={pushplus_token}&title={title}&content={content}&template=html'
    url = url if not topic else f'{url}&topic={topic}'
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Notification sent successfully.")
        else:
            print(f"Failed to send notification. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")