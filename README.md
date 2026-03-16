# Telegram-бот для мастера маникюра

## Локальный запуск

1. Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте `.env` на основе `.env.example` и заполните:
- `BOT_TOKEN`
- `ADMIN_ID`
- `CHANNEL_ID`
- `CHANNEL_LINK`

4. Запуск:

```bash
python bot.py
```

## Бесплатный деплой 24/7 (Oracle Cloud Free VM)

### 1. Подготовьте VM
- Создайте Oracle Always Free VM (Ubuntu 22.04/24.04).
- Откройте SSH (порт 22) в Security List.
- Подключитесь:

```bash
ssh ubuntu@<VM_PUBLIC_IP>
```

### 2. Автоустановка бота

На сервере выполните:

```bash
sudo apt update && sudo apt install -y git
git clone <URL_ВАШЕГО_РЕПО> /tmp/manik_bot_repo
cd /tmp/manik_bot_repo
sudo bash deploy/oracle/bootstrap.sh <URL_ВАШЕГО_РЕПО> main
```

Что делает `bootstrap.sh`:
- ставит Python/Git
- создает системного пользователя `manikbot`
- клонирует проект в `/opt/manik_bot`
- создает `.venv` и ставит зависимости
- создает `.env`, если его нет
- создает и включает `systemd` сервис `manik-bot`

### 3. Заполните переменные окружения

```bash
sudo nano /opt/manik_bot/.env
```

Минимум:
- `BOT_TOKEN`
- `ADMIN_ID`
- `CHANNEL_ID`
- `CHANNEL_LINK`

Пример: `deploy/oracle/.env.prod.example`

### 4. Перезапустите сервис

```bash
sudo systemctl restart manik-bot
sudo systemctl status manik-bot
```

### 5. Логи

```bash
sudo journalctl -u manik-bot -f
```

## Обновление после изменений в репозитории

```bash
ssh ubuntu@<VM_PUBLIC_IP>
cd /opt/manik_bot
sudo bash deploy/oracle/update.sh main
```

## Ручная установка systemd (если нужно)

Если не используете `bootstrap.sh`, можно вручную:

```bash
sudo cp deploy/oracle/manik-bot.service /etc/systemd/system/manik-bot.service
sudo systemctl daemon-reload
sudo systemctl enable manik-bot
sudo systemctl restart manik-bot
```
