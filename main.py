import os
import datetime
import pytz
import signal
import sys
from flask import Flask, request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.client import BaseSocketModeClient
from collections import defaultdict
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, CHANNEL_ID
from utils.visualization import visualize_attendance

app = Flask(__name__)

client = WebClient(token=SLACK_BOT_TOKEN)
attendance = defaultdict(int)
user_votes = defaultdict(list)  # ユーザーの投票履歴をリストで記録

@app.route("/")
def home():
    return "Slack Bot is running."

@app.route("/send_poll_message", methods=['POST'])
def trigger_send_poll_message():
    send_poll_message()
    return "Poll message sent", 200

@app.route("/end_poll_message", methods=['POST'])
def trigger_end_poll_message():
    end_poll_message()
    return "Poll ended", 200

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
        
        # 選択削除ボタンを追加
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
    # 送信後、集計データをクリアして次のサイクルに備える
    attendance.clear()
    user_votes.clear()
    print("出席データとユーザー投票履歴をクリアしました。")

def handle_interactive_message(client: BaseSocketModeClient, req: SocketModeRequest):
    print("メッセージを受信しました...")
    print(f"リクエストタイプ: {req.type}")
    if req.type == "events_api":
        event = req.payload["event"]
        print(f"イベント: {event}")
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
                    attendance[day] += 1
                    user_votes[user_id].append(day)
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"了解しました! {day} を記録しました。",
                        link_names=False  # 通知を抑制
                    )
                else:
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"{day} は既に選択されています。他の曜日を選択してください。",
                        link_names=False  # 通知を抑制
                    )
            elif action['action_id'] == 'remove_vote':
                if user_votes[user_id]:
                    print(f"{user_id} の投票を取り消します: {user_votes[user_id]}")
                    for voted_day in user_votes[user_id]:
                        attendance[voted_day] -= 1
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text=f"全ての選択を取り消しました。",
                        link_names=False  # 通知を抑制
                    )
                    user_votes[user_id] = []
                else:
                    response = client.web_client.chat_postMessage(
                        channel=payload['channel']['id'],
                        text="現在、選択されている曜日はありません。",
                        link_names=False  # 通知を抑制
                    )
        print(f"出席データの更新: {dict(attendance)}")

        # リクエストを確認
        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)

def signal_handler(sig, frame):
    print('割り込み信号を受信しました。終了します...')
    visualize_attendance(attendance)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    print("ボットを起動しています...")
    socket_mode_client = SocketModeClient(
        app_token=SLACK_APP_TOKEN,
        web_client=client
    )

    socket_mode_client.socket_mode_request_listeners.append(handle_interactive_message)
    socket_mode_client.connect()

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), use_reloader=False)
