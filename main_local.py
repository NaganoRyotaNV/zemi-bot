import os
import datetime
import time
import signal
import sys
import argparse
import threading
import pytz
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.client import BaseSocketModeClient
from collections import defaultdict
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, CHANNEL_ID
from utils.visualization import visualize_attendance
from threading import Lock

app = Flask(__name__)

client = WebClient(token=SLACK_BOT_TOKEN)
attendance = defaultdict(int)
user_votes = defaultdict(list)
attendance_lock = Lock()
user_votes_lock = Lock()
stop_event = threading.Event()

@app.route("/")
def home():
    return "Slack Bot is running."

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.json
    user_id = data.get("user_id")
    text = data.get("text")
    channel_id = CHANNEL_ID  # 固定のチャンネルIDに送信する

    if user_id and text:
        try:
            response = client.chat_postMessage(
                channel=channel_id,
                text=f"Hello <@{user_id}>, you said: {text}"
            )
            return jsonify({"status": "success", "message": response["message"]["text"]}), 200
        except SlackApiError as e:
            return jsonify({"status": "error", "message": e.response["error"]}), 500
    return jsonify({"status": "error", "message": "Invalid input"}), 400

def send_poll_message():
    print("アンケートメッセージを送信中...")
    try:
        blocks = []
        for day in ['月曜', '火曜', '水曜', '木曜', '金曜']:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{day}*"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "選択"
                    },
                    "value": day,
                    "action_id": f"select_{day.lower()}"
                }
            })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "選択を削除したい場合は以下のボタンをクリックしてください。"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "選択削除"
                },
                "value": "remove_vote",
                "action_id": "remove_vote"
            }
        })
        
        response = client.chat_postMessage(
            channel=CHANNEL_ID,
            text="来週のゼミに参加できる曜日を選んでください:",
            blocks=blocks
        )
        print("アンケートメッセージを送信しました。")
    except SlackApiError as e:
        print(f"メッセージの送信エラー: {e.response['error']}")

def end_poll_message():
    print(f"スケジュールされたジョブを終了中: {datetime.datetime.now(pytz.timezone('Asia/Tokyo'))}")
    print(f"最終的な出席データ: {dict(attendance)}")
    visualize_attendance(attendance)
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'attendance.png')
        response = client.files_upload_v2(
            channel=CHANNEL_ID,
            initial_comment="出席結果はこちらです。",
            file=file_path
        )
        print("出席結果をSlackに送信しました。")
    except SlackApiError as e:
        print(f"ファイルの送信エラー: {e.response['error']}")
    
    with attendance_lock:
        attendance.clear()
    with user_votes_lock:
        user_votes.clear()
    print("出席データとユーザー投票履歴をクリアしました。")

def handle_interactive_message(client: BaseSocketModeClient, req: SocketModeRequest):
    print("メッセージを受信しました...")
    print(f"リクエストタイプ: {req.type}")
    if req.type == "events_api":
        event = req.payload["event"]
        print(f"イベント: {event}")
        if event["type"] == "message" and "subtype" not in event:
            user_id = event["user"]
            channel_id = event["channel"]
            text = event["text"]
            bot_user_id = client.web_client.auth_test()["user_id"]
            
            if user_id != bot_user_id:
                try:
                    response = client.web_client.chat_postMessage(
                        channel=channel_id,
                        text=f"Hello <@{user_id}>, you said: {text}"
                    )
                    print(f"応答メッセージを送信しました: {response['message']['text']}")
                except SlackApiError as e:
                    print(f"メッセージの送信エラー: {e.response['error']}")
            else:
                print("自分自身のメッセージを無視しました")
                
        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)
    elif req.type == "interactive":
        payload = req.payload
        print(f"インタラクティブペイロード: {payload}")
        user_id = payload['user']['id']
        if 'actions' in payload:
            action = payload['actions'][0]
            day = action['value']

            if action['action_id'].startswith('select_'):
                if day not in user_votes[user_id]:
                    print(f"ボタンがクリックされました: {day}")
                    with attendance_lock:
                        attendance[day] += 1
                    with user_votes_lock:
                        user_votes[user_id].append(day)
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"了解しました! {day} を記録しました。"
                    )
                else:
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"{day} は既に選択されています。他の曜日を選択してください。"
                    )
            elif action['action_id'] == 'remove_vote':
                if user_votes[user_id]:
                    print(f"{user_id} の投票を取り消します: {user_votes[user_id]}")
                    with attendance_lock:
                        for voted_day in user_votes[user_id]:
                            attendance[voted_day] -= 1
                    with user_votes_lock:
                        user_votes[user_id] = []
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"全ての選択を取り消しました。"
                    )
                else:
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text="現在、選択されている曜日はありません。"
                    )
        print(f"出席データの更新: {dict(attendance)}")

        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)

def signal_handler(sig, frame):
    print('割り込み信号を受信しました。終了します...')
    stop_event.set()
    visualize_attendance(attendance)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def schedule_polling(interval):
    while not stop_event.is_set():
        print(f"Sending poll message at {datetime.datetime.now(pytz.timezone('Asia/Tokyo'))}")
        send_poll_message()
        if stop_event.wait(interval):
            break
        print(f"Ending poll message at {datetime.datetime.now(pytz.timezone('Asia/Tokyo'))}")
        end_poll_message()
        if stop_event.wait(interval):
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Slack Bot for attendance management.')
    parser.add_argument('--interval', type=int, help='Interval in seconds between poll messages and results', default=0)
    args = parser.parse_args()

    if args.interval > 0:
        poll_thread = threading.Thread(target=schedule_polling, args=(args.interval,))
        poll_thread.start()

    print("ボットを起動しています...")
    socket_mode_client = SocketModeClient(
        app_token=SLACK_APP_TOKEN,
        web_client=client
    )

    socket_mode_client.socket_mode_request_listeners.append(handle_interactive_message)
    socket_mode_client.connect()

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), use_reloader=False)
