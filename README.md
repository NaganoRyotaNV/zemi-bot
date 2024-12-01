# ローカル実行用 README

このガイドでは、ゼミの出席アンケートを管理するための Slack ボットをローカルで設定し実行する方法を説明します。以下の手順に従ってアプリケーションを設定してください。

## 必要条件

- Python 3.7 以上
- Slack アカウント
- 必要な権限を持つ Slack アプリ

## セットアップ手順

1. リポジトリをクローンする:

   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 依存関係をインストールする:

   ```
   pip install -r requirements.txt
   ```

3. プロジェクトのルートディレクトリに `.env` ファイルを作成し、Slack ボットのトークンとチャンネル ID を追加する:

   ```
   SLACK_APP_TOKEN=your_slack_app_token
   SLACK_BOT_TOKEN=your_slack_bot_token
   CHANNEL_ID=your_channel_id
   ```

   これらのトークンは Slack サイトから Slack ボットを作成すると取得できます。

4. Slack ボットに必要な権限:

   - channels:read
   - chat:write
   - groups:read
   - im:read
   - mpim:read
   - reactions:read
   - users:read
   - users:read.email

5. Socket Mode を有効にする:

   - Slack アプリの設定ページに移動し、Socket Mode をオンにします。

6. ローカルでアプリケーションを実行する:
   ```
   python main_local.py --interval 10
   ```
   `--interval` オプションで集計のタイミングを秒数で指定します。例えば、10 秒ごとに集計する場合は上記のようにします。

## アプリケーションの概要

このアプリケーションは、毎週金曜日の 20 時から日曜日の 20 時までの間にゼミの出席アンケートを行う Slack ボットです。ユーザーは各曜日のボタンをクリックして参加可能な曜日を選択できます。集計結果は画像として Slack に投稿されます。

