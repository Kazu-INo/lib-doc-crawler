FROM python:3.11-slim

WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && \
    apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Poetryのインストール
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=1.5.1
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# 依存関係のインストール
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# アプリケーションのコピー
COPY . .

# コンテナ起動時のコマンド
CMD ["bash"]
