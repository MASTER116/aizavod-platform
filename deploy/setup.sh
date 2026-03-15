#!/bin/bash
# Первоначальная установка AIZAVOD на сервер (рядом с kwork_bot)
# Запускать от root на сервере

set -e

echo "=== AIZAVOD Initial Setup ==="

PROJECT_DIR="/opt/aizavod"

# 1. Клонируем репозиторий
if [ ! -d "$PROJECT_DIR" ]; then
    git clone https://github.com/MASTER116/aizavod.git "$PROJECT_DIR"
else
    echo "Directory already exists, pulling latest..."
    cd "$PROJECT_DIR" && git pull origin main
fi

cd "$PROJECT_DIR"

# 2. Создаем виртуальное окружение
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo "Python dependencies installed"

# 3. Создаем .env из шаблона
if [ ! -f .env ]; then
    cp .env.example .env
    echo ">>> ВАЖНО: Заполните .env файл ключами API <<<"
    echo ">>>   nano /opt/aizavod/.env                  <<<"
fi

# 4. Создаем директории для медиа
mkdir -p media/reference media/generated media/processed logs

# 5. Устанавливаем Node.js и собираем web-ui (если нужна веб-панель)
if command -v node &> /dev/null; then
    echo "Building web-ui..."
    cd web-ui
    npm install
    npm run build
    cd ..
else
    echo "Node.js not found. Skipping web-ui build."
    echo "Install: curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs"
fi

# 6. Устанавливаем FFmpeg (для обработки видео)
if ! command -v ffmpeg &> /dev/null; then
    apt install -y ffmpeg
    echo "FFmpeg installed"
fi

# 7. Устанавливаем systemd сервис
cp deploy/aizavod.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable aizavod
echo "Systemd service installed and enabled"

# 8. Настраиваем nginx (если установлен)
if command -v nginx &> /dev/null; then
    cp deploy/nginx-aizavod.conf /etc/nginx/sites-available/aizavod
    ln -sf /etc/nginx/sites-available/aizavod /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    echo "Nginx configured"
else
    echo "Nginx not found. Install: apt install -y nginx"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Следующие шаги:"
echo "  1. Заполните .env:  nano /opt/aizavod/.env"
echo "  2. Запустите:       systemctl start aizavod"
echo "  3. Проверьте:       systemctl status aizavod"
echo "  4. Логи:            journalctl -u aizavod -f"
echo ""
echo "Сервисы на сервере:"
echo "  - kwork-bot:  systemctl status kwork-bot"
echo "  - aizavod:    systemctl status aizavod"
