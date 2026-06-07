# VPN Stack: AmneziaWG + Xray Reality + Telegram Bot

**Готовое решение для развертывания приватного VPN-сервера с обходом DPI.**

## В состав входит

- **AmneziaWG Easy** — основной VPN-протокол с обфускацией (UDP, порт 51820)
- **Xray Reality** — резервный протокол с маскировкой под HTTPS (TCP, порт 443)
- **Telegram Bot** — управление клиентами и мониторинг трафика
- **Веб-интерфейс** — wg-easy для удобного управления (порт 51821)

## Быстрый старт

Клонируйте репозиторий:

`git clone https://github.com/sstpnk/vpn-stack.git cd vpn-stack`

Скопируйте и заполните переменные окружения:

`cp .env.example .env nano .env`

Запустите стек:

`docker compose up -d`

## Переменные окружения (.env)

| Переменная | Описание | Пример |
|------------|----------|--------|
| WG_HOST | Публичный IP сервера | 45.84.88.253 |
| WG_EASY_PASSWORD | Пароль веб-интерфейса | my_secure_password |
| WG_PORT | Порт WireGuard (по умолчанию 51820) | 51820 |
| XRAY_PORT | Порт Xray (по умолчанию 443) | 443 |

## Настройка Telegram бота

Создайте бота у [@BotFather](https://t.me/BotFather)

Получите токен вида `123456789:ABCdefGHIjkl`

Узнайте свой Telegram username у [@userinfobot](https://t.me/userinfobot)

Добавьте в `.env`:

`BOT_TOKEN=ваш_токен ALLOWED_USERNAMES=ваш_username`

## Генерация ключей для Xray Reality

`docker run --rm teddysun/xray:latest xray x25519 docker run --rm teddysun/xray:latest xray uuid`

Полученные значения вставьте в `xray-config/config.template.json`.

## Структура проекта

`vpn-stack/ ├── docker-compose.yml ├── .env.example ├── README.md ├── data/ │   └── wg-easy/ ├── xray-config/ └── bot/`

## Благодарности

Этот проект использует следующие открытые решения:

- [AmneziaWG Easy](https://github.com/spcfox/amnezia-wg-easy) — Web UI + Docker образ для AmneziaWG
- [wg-easy](https://github.com/wg-easy/wg-easy) — оригинальный веб-интерфейс для WireGuard
- [Xray-core](https://github.com/XTLS/Xray-core) — платформа для построения приватных сетей
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — библиотека для создания ботов
- [wgeasy-tg-bot](https://github.com/illmouse/wgeasy-tg-bot) — основа для Telegram бота

## Лицензия

MIT License

**Важно:** Данный проект является сборкой сторонних открытых компонентов. Каждый компонент распространяется под своей лицензией (MIT, GPL, MPL и др.). Использование подразумевает соблюдение условий лицензий всех включенных проектов.
