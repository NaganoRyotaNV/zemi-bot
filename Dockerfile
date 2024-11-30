FROM python:3.9

# 日本語フォントのインストール
RUN apt-get update && apt-get install -y fonts-noto-cjk

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]
