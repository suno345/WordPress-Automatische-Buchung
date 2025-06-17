# Python 3.9をベースイメージとして使用
FROM python:3.9-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルのコピー
COPY requirements.txt .

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# キャッシュディレクトリとログディレクトリの作成
RUN mkdir -p cache/images cache/api logs \
    && chmod 755 cache logs

# 環境変数の設定
ENV PYTHONUNBUFFERED=1

# エントリーポイントの設定
ENTRYPOINT ["python", "src/main.py"]

# デフォルトのコマンド（日次スケジュール）
CMD ["--daily"] 