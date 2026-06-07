# VPN Stack: AmneziaWG + Xray Reality + Telegram Bot

**Готовое решение для развертывания приватного VPN-сервера с обходом DPI.**

## В состав входит

- **AmneziaWG Easy** — основной VPN-протокол с обфускацией (UDP, порт 51820)
- **Xray Reality** — резервный протокол с маскировкой под HTTPS (TCP, порт 443)
- **Telegram Bot** — управление клиентами и мониторинг трафика
- **Веб-интерфейс** — wg-easy для удобного управления (порт 51821)

## Быстрый старт
```
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
./setup.sh
```

Скрипт запросит необходимые параметры и автоматически:
- проверит наличие Docker
- создаст `.env` файл
- сгенерирует ключи для Xray Reality
- запустит все сервисы

## Переменные окружения (.env)

| Переменная | Описание | Пример |
|------------|----------|--------|
| WG_HOST | Публичный IP вашего сервера | 45.84.88.253 |
| WG_EASY_PASSWORD | Пароль для входа в веб-интерфейс | my_secure_password |
| WG_PORT | Порт WireGuard (по умолчанию 51820) | 51820 |
| XRAY_PORT | Порт Xray Reality (по умолчанию 443) | 443 |
| BOT_TOKEN | Токен Telegram бота (опционально) | 123456:ABCdef |
| ALLOWED_USERNAMES | Ваш Telegram username без @ (опционально) | sstpnk |

## Настройка Telegram бота (опционально)

1. Создайте бота у [@BotFather](https://t.me/BotFather) — команда `/newbot`
2. Скопируйте полученный **токен** в переменную `BOT_TOKEN`
3. Узнайте свой **username** у [@userinfobot](https://t.me/userinfobot) и укажите в `ALLOWED_USERNAMES`

## Структура проекта

```
vpn-stack/
├── .env.example # шаблон переменных
├── .gitignore
├── README.md
├── docker-compose.yml
├── setup.sh
├── bot/
│ ├── Dockerfile
│ ├── requirements.txt
│ └── src/
│ ├── bot.py
│ └── wgapi.py
├── data/
│ └── wg-easy/
│ ├── wg0.conf
│ └── wg0.json
└── xray-config/
├── config.template.json
└── config.json # генерируется автоматически

## Управление

| Команда | Описание |
|---------|----------|
| `docker compose ps` | Статус контейнеров |
| `docker compose logs -f` | Логи в реальном времени |
| `docker compose down` | Остановить всё |
| `docker compose up -d` | Запустить после остановки |

## Благодарности

- [AmneziaWG Easy](https://github.com/spcfox/amnezia-wg-easy)
- [wg-easy](https://github.com/wg-easy/wg-easy)
- [Xray-core](https://github.com/XTLS/Xray-core)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [wgeasy-tg-bot](https://github.com/illmouse/wgeasy-tg-bot)

## Лицензия

MIT
```
