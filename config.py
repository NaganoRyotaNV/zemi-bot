import os
from dotenv import load_dotenv

# .env ファイルの内容を読み込む
load_dotenv()

# 環境変数の取得
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")