FROM node:20-alpine

WORKDIR /app

# 依存関係のインストール
COPY package.json ./
RUN npm install

# アプリケーションコピー
COPY . .

# ビルド
RUN npm run build

# 起動コマンド
CMD ["npm", "start"]
