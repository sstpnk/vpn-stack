# VPN Stack: AmneziaWG + Xray Reality + Telegram Bot

[Русский](#русский) | [English](#english) | [简体中文](#简体中文)

Current release: **v1.0.0**. See [CHANGELOG.md](CHANGELOG.md) and
[release notes](docs/releases/v1.0.0.md).

## Русский

Готовая Docker-сборка для развёртывания личного VPN на VPS. Основной
протокол — AmneziaWG с обфускацией UDP-трафика; Xray Reality можно
использовать как резервный вариант.

## Что входит в стек

- **AmneziaWG Easy** — VPN-сервер и веб-интерфейс управления peer-ами.
- **Xray Reality** — резервный VLESS Reality-сервер на TCP-порту 8443.
- **Telegram-бот** — создание, поиск и удаление peer-ов, выдача готовых
  клиентских конфигураций.
- **Split tunneling** — клиентский конфиг направляет публичный IPv4-трафик
  через VPN, но не перехватывает локальные сети `10.0.0.0/8`,
  `172.16.0.0/12` и `192.168.0.0/16`.

## Требования

- VPS с публичным IPv4-адресом.
- Ubuntu 22.04/24.04 или Debian 12.
- Доступ по SSH с пользователем, имеющим `sudo`.
- Рекомендуемый минимум: 1 vCPU, 1 ГБ RAM, 10 ГБ диска.
- Открытые порты:

| Порт | Протокол | Назначение |
|------|----------|------------|
| `22` | TCP | SSH; замените, если SSH работает на другом порту |
| `51820` | UDP | AmneziaWG |
| `8443` | TCP | Xray Reality |
| `51821` | TCP | веб-интерфейс; рекомендуется только локальный доступ через SSH |

Публичные порты `22/tcp`, `51820/udp` и `8443/tcp` нужно разрешить и в firewall
операционной системы, и в firewall/security group панели VPS-провайдера.

> Веб-интерфейс на порту `51821` работает по HTTP. Не оставляйте его открытым
> всему интернету. Рекомендуемый вариант — привязать порт к `127.0.0.1` и
> использовать SSH-туннель.

## Пошаговое развёртывание на VPS

### 1. Подключитесь к серверу

```bash
ssh root@SERVER_IP
```

Если используется обычный пользователь:

```bash
ssh username@SERVER_IP
sudo -i
```

### 2. Настройте firewall

Пример для UFW с портами по умолчанию:

```bash
apt update
apt install -y ufw
ufw allow OpenSSH
ufw allow 51820/udp
ufw allow 8443/tcp
ufw enable
ufw status
```

Docker может самостоятельно добавлять правила перенаправления трафика, поэтому
для опубликованных контейнерных портов не следует полагаться только на UFW.
Если нужен прямой доступ к панели, ограничьте TCP-порт `51821` также в
firewall/security group VPS-провайдера.

### 3. Клонируйте репозиторий

```bash
apt update
apt install -y git curl
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
```

До первого запуска измените публикацию веб-интерфейса в
`docker-compose.yml`:

```yaml
ports:
  - "${WG_PORT:-51820}:${WG_PORT:-51820}/udp"
  - "127.0.0.1:51821:51821/tcp"
```

### 4. Запустите установку

```bash
./setup.sh
```

Скрипт:

1. Проверит Docker и при необходимости установит его.
2. Запросит IP сервера, пароль веб-интерфейса и порты.
3. Опционально запросит токен Telegram-бота и разрешённый username.
4. Создаст `.env`.
5. Сгенерирует конфигурацию Xray Reality.
6. Соберёт и запустит контейнеры.

Если Docker был установлен впервые, скрипт может попросить выйти из SSH-сессии
и войти снова. После повторного входа снова выполните:

```bash
cd vpn-stack
./setup.sh
```

### 5. Проверьте запуск

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
```

Все контейнеры должны иметь состояние `Up`. Для проверки открытых портов:

```bash
ss -lntup | grep -E ':(8443|51820|51821)\b'
```

Чтобы открыть закрытый веб-интерфейс, создайте SSH-туннель со своего
компьютера:

```bash
ssh -L 51821:127.0.0.1:51821 username@SERVER_IP
```

Пока SSH-сессия открыта, панель доступна по адресу
`http://127.0.0.1:51821`.

## Настройка `.env`

`setup.sh` создаёт базовый `.env`. Дополнительные параметры можно дописать
вручную:

```dotenv
# Публичный адрес и порты VPS
WG_HOST=203.0.113.10
WG_EASY_PASSWORD=replace_with_a_long_random_password
WG_PORT=51820
WG_MTU=1280
WG_PERSISTENT_KEEPALIVE=25
# Пустое значение использует split-маршруты из локального fork-а
WG_ALLOWED_IPS=
XRAY_PORT=8443
XRAY_PUBLIC_HOST=
XRAY_SERVER_NAME=www.google.com
XRAY_FINGERPRINT=randomized

# Параметры AmneziaWG
AMNEZIA_JC=10
AMNEZIA_JMIN=64
AMNEZIA_JMAX=200
AMNEZIA_S1=64
AMNEZIA_S2=64
AMNEZIA_H1=1000-12999
AMNEZIA_H2=13000-24999
AMNEZIA_H3=25000-36999
AMNEZIA_H4=37000-50000
AMNEZIA_I1='<b 0x160301>'
AMNEZIA_I2='<r 3><b 0x0303><r 32>'
AMNEZIA_I3='<b 0x00><r 5>'
AMNEZIA_I4='<r 40>'
AMNEZIA_I5='<b 0xC0000000><r 8><b 0x04><r 100>'

# Telegram-бот
BOT_TOKEN=123456789:replace_with_botfather_token
ALLOWED_USERNAMES=your_telegram_username

# Убирает предупреждение buildx в некоторых версиях Docker Compose
DOCKER_COMPOSE_EXPERIMENTAL=false
```

После изменения `.env` пересоздайте контейнеры:

```bash
docker compose up -d --build --force-recreate
```

### Что означают параметры

| Переменная | Значение по умолчанию | Назначение |
|------------|-----------------------|------------|
| `WG_HOST` | нет | публичный IPv4 или доменное имя VPS |
| `WG_EASY_PASSWORD` | нет | пароль веб-интерфейса |
| `WG_PORT` | `51820` | внешний UDP-порт AmneziaWG; после изменения проверьте `Endpoint` |
| `WG_MTU` | `1280` | MTU, добавляемый сервером в клиентский конфиг |
| `WG_PERSISTENT_KEEPALIVE` | `25` | интервал keepalive клиента в секундах |
| `WG_ALLOWED_IPS` | split-маршруты | переопределение маршрутов клиента; пустое значение исключает RFC1918 |
| `XRAY_PORT` | `8443` | внешний TCP-порт Xray Reality |
| `XRAY_PUBLIC_HOST` | `WG_HOST` | адрес, используемый в VLESS-ссылках |
| `XRAY_SERVER_NAME` | `www.google.com` | предпочтительный Reality SNI, если он разрешён серверным конфигом |
| `XRAY_FINGERPRINT` | `randomized` | uTLS fingerprint в клиентских VLESS-профилях |
| `AMNEZIA_JC` | `10` | количество мусорных пакетов перед handshake |
| `AMNEZIA_JMIN` | `64` | минимальный размер мусорного пакета в байтах |
| `AMNEZIA_JMAX` | `200` | максимальный размер мусорного пакета в байтах |
| `AMNEZIA_S1`, `AMNEZIA_S2` | `64`, `64` | padding пакетов Init и Response |
| `AMNEZIA_H1`...`AMNEZIA_H4` | см. пример | непересекающиеся диапазоны заголовков пакетов |
| `AMNEZIA_I1`...`AMNEZIA_I5` | см. пример | CPS-пакеты с байтами и случайными фрагментами |
| `BOT_TOKEN` | пусто | токен, полученный у `@BotFather` |
| `ALLOWED_USERNAMES` | пусто | Telegram username без `@`; несколько имён через запятую |

Локальный fork AmneziaWG Easy получает глобальные значения из `.env` через
`docker-compose.yml`. При создании peer-а через веб-панель можно оставить
глобальные значения, выбрать готовый профиль или задать собственные `H1-H4`,
`I1-I5` и `Init_Packet_Delay`. Индивидуальные значения сохраняются в записи
peer-а внутри `wg0.json` и используются при генерации `.conf` и QR-кода.

Параметры `J*` и `S*`, MTU и split `AllowedIPs` остаются серверными. Telegram-
бот создаёт peer-ы с глобальными `H/I`, а веб-панель поддерживает per-peer
профили. `Init_Packet_Delay` добавляется только при явном выборе профиля или
ручном вводе. Клиентское приложение должно поддерживать эту директиву.

Параметры сервера сохраняются в `data/wg-easy/wg0.json` при первом запуске.
Если изменить `Jc`, `Jmin`, `Jmax`, `S1`, `S2` или `H1`–`H4` для уже
инициализированного сервера, одного пересоздания контейнера недостаточно:
старые серверные значения останутся в сохранённой конфигурации. Не удаляйте
`wg0.json` без резервной копии, поскольку там находятся ключи и peer-ы.

## Настройка Telegram-бота

1. Откройте [@BotFather](https://t.me/BotFather).
2. Выполните `/newbot` и сохраните выданный токен.
3. Укажите токен в `BOT_TOKEN`.
4. Укажите свой Telegram username без `@` в `ALLOWED_USERNAMES`.
5. Перезапустите сервис:

```bash
docker compose up -d --build vpn-bot
docker compose logs -f vpn-bot
```

После запуска отправьте боту `/start`. Через меню можно управлять peer-ами
AmneziaWG и VLESS Reality-подключениями.

Команды VLESS:

| Команда | Действие |
|---------|----------|
| `/vless_create [имя]` | создать подключение; без имени бот запросит его отдельно |
| `/vless_list` | показать существующие VLESS-ссылки |
| `/vless_delete` | выбрать и удалить подключение |

При создании бот отправляет стандартную `vless://` ссылку и отдельный
клиентский JSON для Xray/NekoBox с рекомендуемыми параметрами Mux.

## Создание клиентской конфигурации

Для каждого устройства создавайте отдельный peer. Не используйте один и тот же
файл одновременно на телефоне и компьютере: у них будет одинаковый ключ и
внутренний адрес, что приводит к нестабильным подключениям.

### Рекомендуемый способ: через Telegram-бота

1. Отправьте боту `/start`.
2. Нажмите **Create Peer**.
3. Введите понятное имя, например `sergey-windows` или `iphone`.
4. Бот создаст peer и отправит файл `.conf`.
5. Бот скачает готовый серверный конфиг с `MTU`, `I1`–`I5` и маршрутами,
   исключающими частные локальные сети.

Пример основных частей полученного файла:

```ini
[Interface]
PrivateKey = CLIENT_PRIVATE_KEY
Address = 10.8.0.2/24
DNS = 1.1.1.1
MTU = 1280

# --- Транспортная маскировка ---
Jc = 10
Jmin = 64
Jmax = 200
S1 = 64
S2 = 64

# --- Динамические заголовки пакетов ---
H1 = 1000-12999
H2 = 13000-24999
H3 = 25000-36999
H4 = 37000-50000

# --- Маскировочные CPS-пакеты ---
I1 = <b 0x160301>
I2 = <r 3><b 0x0303><r 32>
I3 = <b 0x00><r 5>
I4 = <r 40>
I5 = <b 0xC0000000><r 8><b 0x04><r 100>

[Peer]
PublicKey = SERVER_PUBLIC_KEY
AllowedIPs = 0.0.0.0/5, 8.0.0.0/7, 11.0.0.0/8, ...
Endpoint = 203.0.113.10:51820
PersistentKeepalive = 25
```

Фактические ключи, адрес и набор серверных параметров будут другими.

### Через веб-интерфейс

1. Откройте `http://SERVER_IP:51821` либо
   `http://127.0.0.1:51821` через SSH-туннель.
2. Войдите с паролем `WG_EASY_PASSWORD`.
3. Нажмите **New Client** и введите имя.
4. Выберите **System defaults** или один из 11 профилей.
5. При необходимости измените заполненные значения вручную.
6. Создайте peer и скачайте `.conf` либо покажите QR-код.

**System defaults** заполняет форму текущими значениями `AMNEZIA_H1-H4` и
`AMNEZIA_I1-I5` сервера. Выбор профиля полностью заменяет поля его значениями.
После выбора любое поле можно изменить: итоговая комбинация будет сохранена
только для создаваемого peer-а.

### Профили маскировки трафика

| Профиль | Назначение | Delay |
|---------|------------|-------|
| YouTube Consumer — Потоковое видео | длинные TLS-сессии, QUIC-подобный старт, крупные видео- и аудиобуферы | `500` |
| Zoom Meeting — Видеоконференция | STUN-подобный запрос и частые аудио/видео-фреймы | `150` |
| Discord Voice — VoIP + текст | TLS/WebSocket-подобный старт, голосовые и короткие текстовые пакеты | `300` |
| Cloudflare WARP / 1.1.1.1 — DNS-over-TLS | короткие частые сессии системного резолвера | `50` |
| Steam Download — Игровая платформа | крупные пакеты и высокая пропускная способность | `200` |
| Госуслуги / ЕСИА — Короткие защищённые REST-запросы | TLS- и REST-подобная последовательность | `600` |
| Почта Mail.ru / VK Почта — IMAP/SMTP через TLS | фоновая синхронизация почты | `400` |
| Яндекс.Погода / Новости — Короткие всплески | периодические запросы мобильного виджета | `200` |
| ВТБ / Сбербанк Онлайн — Финансовый трафик | пакеты разного размера и увеличенная задержка старта | `800` |
| Wildberries / Ozon — E-commerce | смешанный профиль картинок, цен и отзывов | `350` |
| GitHub / Хабр — Трафик разработчика | Git, API и длинные сессии | `500` |

Полные значения профилей находятся в
[`awg-easy/src/lib/MaskingPresets.js`](awg-easy/src/lib/MaskingPresets.js).
Формат полей:

```ini
H1 = 1010101010
I1 = <b 0x160303>
I2 = <b 0x160303><r 64>
Init_Packet_Delay = 500
```

- `H1-H4` принимают целое значение или диапазон `MIN-MAX`.
- `<b 0x...>` добавляет указанные байты.
- `<r N>` добавляет `N` случайных байтов.
- В одном `I`-поле можно последовательно использовать несколько выражений.
- `Init_Packet_Delay` должен быть целым неотрицательным числом.
- Пустая задержка означает, что директива не добавляется в конфигурацию.

Профили формируют характеристики начальных пакетов, но не гарантируют
доступность конкретного сервиса или обход ограничений в любой сети.

<details>
<summary>Полные значения 11 профилей</summary>

#### YouTube Consumer — Потоковое видео

```ini
H1 = 1010101010
H2 = 2020202020
H3 = 3030303030
H4 = 4040404040
Init_Packet_Delay = 500
I1 = <b 0x00100100000100000000000103646e7306676f6f676c6500>
I2 = <r 0>
I3 = <b 0xC0000000><r 8><b 0x04><r 100>
I4 = <r 1350>
I5 = <r 400>
```

#### Zoom Meeting — Видеоконференция

```ini
H1 = 1111111111
H2 = 2222222222
H3 = 3333333333
H4 = 4444444444
Init_Packet_Delay = 150
I1 = <b 0x00010000><r 16>
I2 = <r 0>
I3 = <r 30>
I4 = <r 120>
I5 = <r 800>
```

#### Discord Voice — VoIP + текст

```ini
H1 = 5555555555
H2 = 6666666666
H3 = 7777777777
H4 = 8888888888
Init_Packet_Delay = 300
I1 = <b 0x160303>
I2 = <b 0x474554202f3f656e636f64696e673d6a736f6e>
I3 = <r 40>
I4 = <r 300>
I5 = <r 5>
```

#### Cloudflare WARP / 1.1.1.1 — DNS-over-TLS

```ini
H1 = 1212121212
H2 = 3434343434
H3 = 5656565656
H4 = 7878787878
Init_Packet_Delay = 50
I1 = <b 0x160303>
I2 = <r 80>
I3 = <r 120>
I4 = <r 0>
I5 = <r 0>
```

#### Steam Download — Игровая платформа

```ini
H1 = 9999999999
H2 = 1010101010
H3 = 1111111111
H4 = 1212121212
Init_Packet_Delay = 200
I1 = <b 0x160303>
I2 = <r 64>
I3 = <b 0x505249202a20485454502f322e300d0a>
I4 = <r 1400>
I5 = <r 1400>
```

#### Госуслуги / ЕСИА — Короткие защищённые REST-запросы

```ini
H1 = 7010101010
H2 = 7010101011
H3 = 7010101012
H4 = 7010101013
Init_Packet_Delay = 600
I1 = <b 0x160303>
I2 = <r 64>
I3 = <b 0x474554202f6170692f76312f>
I4 = <r 30>
I5 = <b 0x0d0a0d0a>
```

#### Почта Mail.ru / VK Почта — IMAP/SMTP через TLS

```ini
H1 = 8020202020
H2 = 8020202021
H3 = 8020202022
H4 = 8020202023
Init_Packet_Delay = 400
I1 = <b 0x160303>
I2 = <r 40>
I3 = <r 0>
I4 = <r 500>
I5 = <r 15>
```

#### Яндекс.Погода / Новости — Короткие всплески

```ini
H1 = 9030303030
H2 = 9030303031
H3 = 9030303032
H4 = 9030303033
Init_Packet_Delay = 200
I1 = <b 0x0010010000010000000000010479616e64657802727500>
I2 = <r 0>
I3 = <b 0x160303>
I4 = <r 60>
I5 = <r 20>
```

#### ВТБ / Сбербанк Онлайн — Финансовый трафик

```ini
H1 = 1040404040
H2 = 1040404041
H3 = 1040404042
H4 = 1040404043
Init_Packet_Delay = 800
I1 = <b 0x160303>
I2 = <r 128>
I3 = <r 256>
I4 = <r 400>
I5 = <r 0>
```

#### Wildberries / Ozon — E-commerce

```ini
H1 = 2050505050
H2 = 2050505051
H3 = 2050505052
H4 = 2050505053
Init_Packet_Delay = 350
I1 = <r 32>
I2 = <b 0x160303><r 64>
I3 = <r 40>
I4 = <b 0xFFD8FFE0><r 500>
I5 = <r 200>
```

#### GitHub / Хабр — Трафик разработчика

```ini
H1 = 3060606060
H2 = 3060606061
H3 = 3060606062
H4 = 3060606063
Init_Packet_Delay = 500
I1 = <b 0x160303>
I2 = <b 0x417574686f72697a6174696f6e3a2042656172657220><r 20>
I3 = <r 100>
I4 = <r 700>
I5 = <r 0>
```

</details>

> Файл `.conf` содержит приватный ключ. Не публикуйте его, не отправляйте
> через открытые чаты и удалите peer в случае утечки.

## Подключение Windows

### VeilBox

[VeilBox](https://www.veilbox.site/) поддерживает Windows 10/11, VLESS Reality
и AmneziaWG.

1. Скачайте установщик с официального сайта или со страницы
   [GitHub Releases](https://github.com/artem4150/VeilBox/releases).
2. Установите и запустите VeilBox.
3. Выберите импорт конфигурации/профиля.
4. Укажите полученный `.conf` либо вставьте его содержимое.
5. Выберите созданный профиль и включите подключение.
6. Разрешите создание VPN/TUN-интерфейса, если Windows запросит права
   администратора.

Маршруты для локальных сетей уже исключены из `AllowedIPs` в конфиге,
полученном от бота. Не включайте дополнительный full-tunnel override, если
нужен доступ к принтерам, NAS и другим устройствам LAN.

Альтернативный клиент:
[официальный AmneziaWG для Windows](https://github.com/amnezia-vpn/amneziawg-windows-client/releases).
В нём выберите **Import tunnel(s) from file**, укажите `.conf` и активируйте
туннель.

## Подключение macOS

Для macOS доступны два варианта:

- [VeilBox](https://www.veilbox.site/) — beta-версия для Mac с Apple Silicon.
- [AmneziaWG в App Store](https://apps.apple.com/us/app/amneziawg/id6478942365)
  — официальный клиент для macOS 12 и новее.

### VeilBox на Apple Silicon

1. Скачайте `.dmg` с сайта VeilBox.
2. Перенесите приложение в `Applications` и запустите его.
3. Импортируйте файл `.conf`.
4. Разрешите macOS добавить VPN-конфигурацию.
5. Выберите профиль и включите подключение.

На Intel Mac используйте официальный AmneziaWG, поскольку desktop beta
VeilBox предназначена для Apple Silicon.

### Официальный AmneziaWG

1. Установите приложение из App Store.
2. Передайте `.conf` на Mac безопасным способом.
3. Импортируйте туннель из файла.
4. Подтвердите добавление VPN-конфигурации в macOS.
5. Активируйте туннель.

## Подключение iPhone и iPad

1. Установите
   [AmneziaWG из App Store](https://apps.apple.com/us/app/amneziawg/id6478942365).
2. Скачайте `.conf` из Telegram прямо на устройство либо передайте его через
   AirDrop.
3. Откройте файл в AmneziaWG или выберите импорт туннеля из файла внутри
   приложения.
4. Разрешите iOS добавить VPN-конфигурацию.
5. Включите переключатель туннеля.

Можно импортировать конфигурацию по QR-коду из веб-интерфейса, но показывайте
QR только в доверенной среде: он содержит тот же приватный ключ, что и `.conf`.

## Подключение Android через WG Tunnel

[WG Tunnel](https://wgtunnel.com/) — открытый клиент WireGuard/AmneziaWG для
Android с импортом `.conf`, QR-кодов и настройками автоподключения.

1. Установите приложение с
   [официальной страницы загрузки](https://wgtunnel.com/download/) или из
   Google Play.
2. На главном экране нажмите `+`.
3. Выберите импорт из `.conf` и укажите файл, полученный от бота. Также можно
   использовать QR-код или вставку из буфера обмена.
4. Оставьте режим **VPN/Userspace**: root для обычной работы не нужен.
5. Включите туннель и подтвердите системный запрос Android на создание VPN.

WG Tunnel автоматически использует AmneziaWG backend, если в конфигурации есть
параметры Amnezia. Не включайте **Kernel mode** для AmneziaWG: этот режим
предназначен для kernel WireGuard и требует root.

Для автоподключения можно назначить туннель основным, включить **Start on
Boot**, **Always-on VPN** или правила Auto-Tunneling. Настройки split tunneling
по приложениям в WG Tunnel дополняют IP-маршруты из `AllowedIPs`.

## Проверка подключения

После включения VPN на клиенте:

1. Откройте сайт проверки IP, например `https://ifconfig.me`.
2. Убедитесь, что отображается публичный IP вашего VPS.
3. Проверьте доступ к локальному роутеру, NAS или принтеру.
4. На сервере проверьте состояние контейнера:

```bash
docker compose logs --tail=100 wg-easy
```

Состояние peer-ов, последний handshake и счётчики трафика смотрите в
Telegram-боте или веб-интерфейсе.

## Обновление и обслуживание

Обновить исходный код и пересоздать контейнеры:

```bash
cd vpn-stack
git pull --ff-only
docker compose pull --ignore-buildable
docker compose up -d --build
docker image prune -f
```

Основные команды:

| Команда | Описание |
|---------|----------|
| `docker compose ps` | состояние контейнеров |
| `docker compose logs -f` | логи всех сервисов |
| `docker compose restart vpn-bot` | перезапустить бота |
| `docker compose down` | остановить стек |
| `docker compose up -d` | запустить стек |

Данные AmneziaWG хранятся в `data/wg-easy`. Для резервной копии сохраните
`.env`, `data/wg-easy` и `xray-config/config.json` в защищённом месте.

## Диагностика

### Клиент импортируется, но не подключается

- Проверьте, что UDP-порт `WG_PORT` открыт у VPS-провайдера и в UFW.
- Сверьте `Endpoint` в `.conf` с публичным IP и портом сервера.
- Проверьте, что клиент поддерживает все директивы выбранного профиля и что
  значения в импортированном конфиге не были изменены приложением.
- Проверьте время на VPS: `timedatectl status`.
- Посмотрите логи: `docker compose logs -f wg-easy`.

### VPN подключён, но сайты не открываются

- Попробуйте уменьшить `WG_MTU`, например до `1240`, и пересоздать сервер:

```bash
sed -i 's/^WG_MTU=.*/WG_MTU=1240/' .env
docker compose up -d --build --force-recreate wg-easy
```

- Скачайте конфиг заново через web или бота, чтобы новое значение попало
  в `.conf`.
- Проверьте DNS в секции `[Interface]`.

### Не открывается локальная сеть

- Проверьте, что `AllowedIPs` не содержит `0.0.0.0/0`.
- В WG Tunnel не включайте Lockdown без опции **Allow LAN Traffic**.
- Проверьте, не пересекается ли VPN-подсеть с домашней подсетью.

### Telegram-бот не отвечает

- Проверьте `BOT_TOKEN`.
- Проверьте точное значение `ALLOWED_USERNAMES` без `@`.
- У пользователя Telegram должен быть задан публичный username.
- Выполните `docker compose logs -f vpn-bot`.

## Xray Reality

Xray Reality работает как резервный транспорт. Клиент должен поддерживать
VLESS Reality и flow `xtls-rprx-vision`.

Новая установка использует `www.google.com:443` как Reality target и разрешает SNI
`www.google.com`. Для уже существующей установки бот читает
фактический `serverNames` из `xray-config/config.json` и использует разрешённое
значение в ссылке. Это не ломает ранее созданные подключения при обновлении
бота.

`www.google.com` является настраиваемым default, а не универсально лучшим target.
Официальная рекомендация Xray — выбирать доступный TLS-сайт по возможности в
том же ASN, что и VPS. Не меняйте `target/serverNames` у работающего сервера без
плана обновления существующих клиентов.

Пример генерируемой ссылки:

```text
vless://UUID@SERVER_IP:8443?encryption=none&type=tcp&security=reality&flow=xtls-rprx-vision&fp=randomized&sni=www.google.com&pbk=PUBLIC_KEY&sid=SHORT_ID&spx=%2F#NAME
```

Для каждого подключения бот:

- создаёт отдельный UUID с flow `xtls-rprx-vision`;
- создаёт отдельный 8-символьный hex `shortId`;
- вычисляет public key из существующего Reality private key, не меняя пару;
- формирует ссылку с согласованным SNI;
- использует `spiderX=/`, как в клиентском шаблоне;
- формирует клиентский JSON с `concurrency=8`, `xudpConcurrency=8` и
  `xudpProxyUDP443=reject`.

Перед изменением бот сохраняет старый `config.json`, проверяет новый командой
`xray run -test`, атомарно заменяет файл и перезапускает только контейнер
`vpn-xray`. Если проверка или запуск не удались, прежняя конфигурация
восстанавливается.

Поле `mux` не входит в формат стандартной VLESS-ссылки. Поэтому оно содержится
только в отдельном JSON-файле, который бот отправляет при создании подключения.
Повторный запуск `setup.sh` сохраняет существующие Reality-ключи и VLESS-клиентов.

## Структура проекта

```text
vpn-stack/
├── .env.example
├── docker-compose.yml
├── setup.sh
├── awg-easy/             # локальный fork генератора AmneziaWG-конфигов
│   ├── Dockerfile
│   ├── LICENSE
│   └── src/
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── bot.py
│       └── wgapi.py
├── data/
│   └── wg-easy/
└── xray-config/
    ├── config.template.json
    └── config.json
```

## Полезные ссылки

- [VeilBox](https://www.veilbox.site/)
- [WG Tunnel: документация по импорту](https://wgtunnel.com/docs/tunnels/)
- [WG Tunnel: загрузка](https://wgtunnel.com/download/)
- [AmneziaWG для iOS и macOS](https://apps.apple.com/us/app/amneziawg/id6478942365)
- [AmneziaWG для Windows](https://github.com/amnezia-vpn/amneziawg-windows-client/releases)
- [AmneziaWG Easy](https://github.com/spcfox/amnezia-wg-easy)
- [Xray-core](https://github.com/XTLS/Xray-core)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)

## Лицензия

MIT License.

Проект является сборкой сторонних открытых компонентов. Использование
подразумевает соблюдение лицензий каждого компонента.

---

## English

This repository provides a Docker stack for deploying a personal VPN on a
VPS. AmneziaWG is the primary UDP transport; Xray Reality is available as a
fallback.

### Components

- **AmneziaWG Easy**: AmneziaWG server and web-based peer administration.
- **Xray Reality**: fallback VLESS Reality server on TCP port `8443`.
- **Telegram bot**: creates, searches, renames, deletes, and exports
  AmneziaWG peers and manages VLESS Reality clients.
- **Split tunneling**: public IPv4 traffic goes through the VPN while RFC1918
  private networks remain directly reachable.

### Requirements and ports

- A VPS with a public IPv4 address.
- Ubuntu 22.04/24.04 or Debian 12.
- SSH access and a user with `sudo`.
- Recommended minimum: 1 vCPU, 1 GB RAM, 10 GB disk.

| Port | Protocol | Purpose |
|------|----------|---------|
| `22` | TCP | SSH; replace it if the server uses another port |
| `51820` | UDP | AmneziaWG |
| `8443` | TCP | Xray Reality |
| `51821` | TCP | web UI; local access through SSH is recommended |

Allow the public ports both in the operating-system firewall and in the VPS
provider firewall/security group.

> The web UI uses plain HTTP. Bind it to `127.0.0.1` and use an SSH tunnel
> instead of exposing it to the Internet.

### Step-by-step deployment

1. Connect to the server:

```bash
ssh username@SERVER_IP
sudo -i
```

2. Configure UFW:

```bash
apt update
apt install -y ufw
ufw allow OpenSSH
ufw allow 51820/udp
ufw allow 8443/tcp
ufw enable
ufw status
```

Docker may add forwarding rules itself. Do not rely solely on UFW for
published container ports.

3. Clone the repository:

```bash
apt install -y git curl
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
```

For a private web UI, change its port mapping in `docker-compose.yml`:

```yaml
ports:
  - "${WG_PORT:-51820}:${WG_PORT:-51820}/udp"
  - "127.0.0.1:51821:51821/tcp"
```

4. Run setup:

```bash
./setup.sh
```

The script checks Docker, asks for the public address, passwords and ports,
optionally configures the Telegram bot, creates `.env`, generates the Reality
configuration, and starts the containers.

5. Verify the deployment:

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
ss -lntup | grep -E ':(8443|51820|51821)\b'
```

Open a tunnel to the private panel:

```bash
ssh -L 51821:127.0.0.1:51821 username@SERVER_IP
```

Then browse to `http://127.0.0.1:51821`.

### Environment configuration

Example `.env`:

```dotenv
WG_HOST=203.0.113.10
WG_EASY_PASSWORD=replace_with_a_long_random_password
WG_PORT=51820
WG_MTU=1280
WG_PERSISTENT_KEEPALIVE=25
WG_ALLOWED_IPS=

XRAY_PORT=8443
XRAY_PUBLIC_HOST=
XRAY_SERVER_NAME=www.google.com
XRAY_FINGERPRINT=randomized

AMNEZIA_JC=10
AMNEZIA_JMIN=64
AMNEZIA_JMAX=200
AMNEZIA_S1=64
AMNEZIA_S2=64
AMNEZIA_H1=1000-12999
AMNEZIA_H2=13000-24999
AMNEZIA_H3=25000-36999
AMNEZIA_H4=37000-50000
AMNEZIA_I1='<b 0x160301>'
AMNEZIA_I2='<r 3><b 0x0303><r 32>'
AMNEZIA_I3='<b 0x00><r 5>'
AMNEZIA_I4='<r 40>'
AMNEZIA_I5='<b 0xC0000000><r 8><b 0x04><r 100>'

BOT_TOKEN=123456789:replace_with_botfather_token
ALLOWED_USERNAMES=your_telegram_username
DOCKER_COMPOSE_EXPERIMENTAL=false
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `WG_HOST` | none | public IPv4 address or hostname |
| `WG_EASY_PASSWORD` | none | web UI password |
| `WG_PORT` | `51820` | external AmneziaWG UDP port |
| `WG_MTU` | `1280` | MTU written to client configurations |
| `WG_PERSISTENT_KEEPALIVE` | `25` | client keepalive interval |
| `WG_ALLOWED_IPS` | split routes | override client routes |
| `XRAY_PORT` | `8443` | external Xray Reality TCP port |
| `XRAY_PUBLIC_HOST` | `WG_HOST` | host used in generated VLESS links |
| `XRAY_SERVER_NAME` | `www.google.com` | default Reality SNI |
| `XRAY_FINGERPRINT` | `randomized` | uTLS fingerprint |
| `AMNEZIA_JC/JMIN/JMAX` | see example | junk packet count and size |
| `AMNEZIA_S1/S2` | `64` | Init and Response padding |
| `AMNEZIA_H1-H4` | see example | global packet header values/ranges |
| `AMNEZIA_I1-I5` | see example | global CPS packet expressions |
| `BOT_TOKEN` | empty | token from `@BotFather` |
| `ALLOWED_USERNAMES` | empty | allowed usernames without `@` |

Apply environment changes with:

```bash
docker compose up -d --build --force-recreate
```

Server parameters are persisted in `data/wg-easy/wg0.json`. Existing `J`, `S`,
and server `H` values are not automatically replaced when `.env` changes.
Never remove or edit this file without a backup because it contains keys and
peer records.

### Creating an AmneziaWG peer

Create one peer per device. Reusing one configuration on multiple devices
causes key and internal-address conflicts.

#### Web UI

1. Sign in with `WG_EASY_PASSWORD`.
2. Click **New Client** and enter a descriptive name.
3. Select **System defaults** or one of the 11 masking profiles.
4. Review or edit `H1-H4`, `I1-I5`, and `Init_Packet_Delay`.
5. Create the peer and download the `.conf` file or display its QR code.

**System defaults** fills the form with current server `H/I` values. Selecting
a profile replaces every field with that profile. Manual changes are stored
for the new peer in `wg0.json` and are used for both `.conf` and QR output.

| Profile | Traffic shape | Delay |
|---------|---------------|-------|
| YouTube Consumer - Streaming video | long sessions, QUIC-like start, large buffers | `500` |
| Zoom Meeting - Video conference | STUN-like request and frequent media frames | `150` |
| Discord Voice - VoIP + text | TLS/WebSocket-like start and voice packets | `300` |
| Cloudflare WARP / 1.1.1.1 - DNS-over-TLS | short and frequent resolver sessions | `50` |
| Steam Download - Gaming platform | large packets and high throughput | `200` |
| Gosuslugi / ESIA - Protected REST requests | short TLS/REST-like sequence | `600` |
| Mail.ru / VK Mail - Mail synchronization | background IMAP/SMTP-like traffic | `400` |
| Yandex Weather / News - Widget bursts | short periodic requests | `200` |
| VTB / Sberbank Online - Financial traffic | varied sizes and delayed start | `800` |
| Wildberries / Ozon - E-commerce | mixed images, prices, and reviews | `350` |
| GitHub / Habr - Developer traffic | Git, APIs, and long sessions | `500` |

Field syntax:

```ini
H1 = 1010101010
I1 = <b 0x160303>
I2 = <b 0x160303><r 64>
Init_Packet_Delay = 500
```

- `H1-H4` accept an integer or a `MIN-MAX` range.
- `<b 0x...>` inserts static bytes.
- `<r N>` inserts `N` random bytes.
- Multiple expressions may be concatenated in one `I` field.
- `Init_Packet_Delay` must be a non-negative integer.
- An empty delay omits the directive.

The client must support every directive present in the configuration. These
profiles only shape initial packet characteristics; they do not guarantee
availability or bypassing restrictions on a particular network.

#### Telegram bot

1. Send `/start`.
2. Select **Create Peer**.
3. Enter a unique device name.
4. Download the generated `.conf`.

The bot currently uses global server `H/I` values. Per-peer profile selection
is available in the web UI.

The `.conf` and QR code contain the private key. Do not publish them. Delete
and recreate the peer immediately after a leak.

### Telegram and VLESS management

Create a bot with [@BotFather](https://t.me/BotFather), put its token in
`BOT_TOKEN`, set `ALLOWED_USERNAMES`, and restart:

```bash
docker compose up -d --build vpn-bot
docker compose logs -f vpn-bot
```

VLESS commands:

| Command | Action |
|---------|--------|
| `/vless_create [name]` | create a VLESS Reality client |
| `/vless_list` | list existing links |
| `/vless_delete` | select and delete a client |

The bot sends a standard `vless://` link and a separate Xray/NekoBox JSON with
recommended Mux settings.

### Client applications

- **Windows**: [VeilBox](https://www.veilbox.site/) or
  [AmneziaWG for Windows](https://github.com/amnezia-vpn/amneziawg-windows-client/releases).
- **macOS**: VeilBox on Apple Silicon or
  [AmneziaWG from the App Store](https://apps.apple.com/us/app/amneziawg/id6478942365).
- **iPhone/iPad**: import the file or scan the QR code in AmneziaWG.
- **Android**: [WG Tunnel](https://wgtunnel.com/download/), using
  VPN/Userspace mode for AmneziaWG configurations.

Do not enable a full-tunnel override if local printers, NAS devices, or routers
must remain reachable. WG Tunnel automatically selects its AmneziaWG backend
when Amnezia-specific directives are present.

### Xray Reality

Xray Reality is the fallback transport. Clients must support VLESS Reality and
the `xtls-rprx-vision` flow.

New installations use `www.google.com:443` as the default target and SNI. For
existing installations, the bot reads the actual `serverNames` from
`xray-config/config.json`. Choose an accessible TLS target, preferably in the
same ASN as the VPS. Changing target/server names requires updating existing
clients.

Generated links resemble:

```text
vless://UUID@SERVER_IP:8443?encryption=none&type=tcp&security=reality&flow=xtls-rprx-vision&fp=randomized&sni=www.google.com&pbk=PUBLIC_KEY&sid=SHORT_ID&spx=%2F#NAME
```

For each client the bot creates a UUID and short ID, derives the public key
from the existing Reality private key, validates changes with
`xray run -test`, atomically replaces the configuration, and restarts only
`vpn-xray`. Failed validation triggers rollback.

### Update, backup, and maintenance

Back up secrets and runtime data:

```bash
tar -czf vpn-stack-backup.tar.gz .env data xray-config
```

Update:

```bash
cd vpn-stack
git pull --ff-only
docker compose pull --ignore-buildable
docker compose up -d --build
docker image prune -f
```

Useful commands:

| Command | Purpose |
|---------|---------|
| `docker compose ps` | container status |
| `docker compose logs -f` | follow all logs |
| `docker compose restart vpn-bot` | restart the bot |
| `docker compose down` | stop the stack |
| `docker compose up -d` | start the stack |

### Troubleshooting

If a peer imports but does not connect:

- verify the provider firewall and UFW allow `WG_PORT/udp`;
- compare `Endpoint` with the public address and port;
- verify client support for all AmneziaWG directives;
- check server time with `timedatectl status`;
- inspect `docker compose logs -f wg-easy`.

If the tunnel connects but websites fail, reduce `WG_MTU` to `1240`, recreate
`wg-easy`, and download the configuration again. Also verify DNS.

If LAN devices are unavailable, ensure `AllowedIPs` does not contain
`0.0.0.0/0`, disable lockdown or enable **Allow LAN Traffic**, and check that
the VPN subnet does not overlap the home network.

If the Telegram bot does not respond, verify `BOT_TOKEN`, the exact username
in `ALLOWED_USERNAMES`, and `docker compose logs -f vpn-bot`.

---

## 简体中文

本仓库提供一套用于 VPS 的个人 VPN Docker 部署方案。AmneziaWG 是主要
UDP 传输方式，Xray Reality 可作为备用连接。

### 组件

- **AmneziaWG Easy**：AmneziaWG 服务端和 peer Web 管理面板。
- **Xray Reality**：监听 `8443/tcp` 的备用 VLESS Reality 服务。
- **Telegram 机器人**：创建、搜索、重命名、删除和导出 AmneziaWG
  peer，并管理 VLESS Reality 客户端。
- **分流**：公网 IPv4 流量经过 VPN，RFC1918 私有网络保持本地访问。

### 要求和端口

- 具有公网 IPv4 的 VPS。
- Ubuntu 22.04/24.04 或 Debian 12。
- SSH 访问权限和可使用 `sudo` 的用户。
- 建议至少 1 vCPU、1 GB 内存和 10 GB 磁盘。

| 端口 | 协议 | 用途 |
|------|------|------|
| `22` | TCP | SSH；如果使用其他端口请相应修改 |
| `51820` | UDP | AmneziaWG |
| `8443` | TCP | Xray Reality |
| `51821` | TCP | Web 面板；建议仅通过 SSH 隧道访问 |

必须同时在操作系统防火墙和 VPS 提供商的安全组中开放公网端口。
Web 面板使用 HTTP，建议只绑定到 `127.0.0.1`。

### 分步部署

1. 连接服务器并配置 UFW：

```bash
ssh username@SERVER_IP
sudo -i
apt update
apt install -y ufw
ufw allow OpenSSH
ufw allow 51820/udp
ufw allow 8443/tcp
ufw enable
```

2. 克隆并运行安装程序：

```bash
apt install -y git curl
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
./setup.sh
```

脚本会检查 Docker、询问公网地址和密码、可选配置 Telegram 机器人、
创建 `.env`、生成 Reality 配置并启动容器。

3. 检查运行状态：

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
ss -lntup | grep -E ':(8443|51820|51821)\b'
```

4. 通过 SSH 隧道访问面板：

```bash
ssh -L 51821:127.0.0.1:51821 username@SERVER_IP
```

然后打开 `http://127.0.0.1:51821`。

### `.env` 配置

```dotenv
WG_HOST=203.0.113.10
WG_EASY_PASSWORD=replace_with_a_long_random_password
WG_PORT=51820
WG_MTU=1280
WG_PERSISTENT_KEEPALIVE=25
WG_ALLOWED_IPS=

XRAY_PORT=8443
XRAY_PUBLIC_HOST=
XRAY_SERVER_NAME=www.google.com
XRAY_FINGERPRINT=randomized

AMNEZIA_JC=10
AMNEZIA_JMIN=64
AMNEZIA_JMAX=200
AMNEZIA_S1=64
AMNEZIA_S2=64
AMNEZIA_H1=1000-12999
AMNEZIA_H2=13000-24999
AMNEZIA_H3=25000-36999
AMNEZIA_H4=37000-50000
AMNEZIA_I1='<b 0x160301>'
AMNEZIA_I2='<r 3><b 0x0303><r 32>'
AMNEZIA_I3='<b 0x00><r 5>'
AMNEZIA_I4='<r 40>'
AMNEZIA_I5='<b 0xC0000000><r 8><b 0x04><r 100>'

BOT_TOKEN=123456789:replace_with_botfather_token
ALLOWED_USERNAMES=your_telegram_username
```

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `WG_HOST` | 无 | 公网 IPv4 或域名 |
| `WG_EASY_PASSWORD` | 无 | Web 面板密码 |
| `WG_PORT` | `51820` | AmneziaWG UDP 端口 |
| `WG_MTU` | `1280` | 写入客户端配置的 MTU |
| `WG_PERSISTENT_KEEPALIVE` | `25` | 客户端 keepalive 间隔 |
| `WG_ALLOWED_IPS` | 分流路由 | 覆盖客户端路由 |
| `XRAY_PORT` | `8443` | Xray Reality TCP 端口 |
| `XRAY_PUBLIC_HOST` | `WG_HOST` | VLESS 链接使用的主机 |
| `XRAY_SERVER_NAME` | `www.google.com` | 默认 Reality SNI |
| `XRAY_FINGERPRINT` | `randomized` | uTLS fingerprint |
| `AMNEZIA_JC/JMIN/JMAX` | 见示例 | junk 数据包数量和大小 |
| `AMNEZIA_S1/S2` | `64` | Init/Response 填充 |
| `AMNEZIA_H1-H4` | 见示例 | 全局包头值或范围 |
| `AMNEZIA_I1-I5` | 见示例 | 全局 CPS 表达式 |
| `BOT_TOKEN` | 空 | `@BotFather` 生成的令牌 |
| `ALLOWED_USERNAMES` | 空 | 不带 `@` 的允许用户名 |

修改后执行：

```bash
docker compose up -d --build --force-recreate
```

服务端参数保存在 `data/wg-easy/wg0.json`。该文件包含密钥和 peer，
没有备份时不要删除或手工编辑。

### 创建 AmneziaWG peer

每台设备应使用独立 peer，避免密钥和内部地址冲突。

#### Web 面板

1. 使用 `WG_EASY_PASSWORD` 登录。
2. 点击 **New Client** 并输入名称。
3. 选择 **System defaults** 或 11 个预设之一。
4. 检查或修改 `H1-H4`、`I1-I5` 和 `Init_Packet_Delay`。
5. 创建 peer，并下载 `.conf` 或显示二维码。

**System defaults** 会填入当前服务端的 `H/I` 参数。选择预设会替换
所有字段，之后仍可手工修改。最终值保存在该 peer 的 `wg0.json`
记录中，并同时用于配置文件和二维码。

| 预设 | 流量特征 | 延迟 |
|------|----------|------|
| YouTube Consumer - 流媒体视频 | 长会话、类似 QUIC 的开始、大缓冲区 | `500` |
| Zoom Meeting - 视频会议 | 类似 STUN 的请求和频繁媒体帧 | `150` |
| Discord Voice - VoIP + 文本 | 类似 TLS/WebSocket 的开始和语音包 | `300` |
| Cloudflare WARP / 1.1.1.1 - DNS-over-TLS | 短而频繁的解析器会话 | `50` |
| Steam Download - 游戏平台 | 大数据包和高吞吐量 | `200` |
| Госуслуги / ЕСИА - 受保护 REST 请求 | 短 TLS/REST 类序列 | `600` |
| Mail.ru / VK Mail - 邮件同步 | 后台 IMAP/SMTP 类流量 | `400` |
| Yandex Weather / News - 小组件请求 | 短周期突发 | `200` |
| VTB / Sberbank Online - 金融流量 | 不同大小数据包和较大启动延迟 | `800` |
| Wildberries / Ozon - 电商 | 图片、价格和评论的混合流量 | `350` |
| GitHub / Habr - 开发者流量 | Git、API 和长会话 | `500` |

字段格式：

```ini
H1 = 1010101010
I1 = <b 0x160303>
I2 = <b 0x160303><r 64>
Init_Packet_Delay = 500
```

- `H1-H4` 支持整数或 `MIN-MAX` 范围。
- `<b 0x...>` 插入固定字节。
- `<r N>` 插入 `N` 个随机字节。
- 一个 `I` 字段可以连续包含多个表达式。
- `Init_Packet_Delay` 必须是非负整数。
- 延迟留空时不会写入该指令。

客户端必须支持配置中出现的所有指令。这些预设只调整初始数据包
特征，不保证任何特定网络中的可用性或绕过限制。

#### Telegram 机器人

向机器人发送 `/start`，选择 **Create Peer**，输入设备名称并下载
配置。机器人当前使用服务端全局 `H/I`；per-peer 预设由 Web 面板提供。

配置文件和二维码包含私钥。泄露后应立即删除并重新创建 peer。

### Telegram 和 VLESS

通过 [@BotFather](https://t.me/BotFather) 创建机器人，将令牌写入
`BOT_TOKEN`，设置 `ALLOWED_USERNAMES`，然后重启：

```bash
docker compose up -d --build vpn-bot
docker compose logs -f vpn-bot
```

| 命令 | 功能 |
|------|------|
| `/vless_create [name]` | 创建 VLESS Reality 客户端 |
| `/vless_list` | 查看已有链接 |
| `/vless_delete` | 选择并删除客户端 |

机器人会发送标准 `vless://` 链接以及包含推荐 Mux 参数的单独 JSON。

### 客户端

- **Windows**：[VeilBox](https://www.veilbox.site/) 或
  [AmneziaWG Windows](https://github.com/amnezia-vpn/amneziawg-windows-client/releases)。
- **macOS**：Apple Silicon 可使用 VeilBox，也可使用
  [App Store 版 AmneziaWG](https://apps.apple.com/us/app/amneziawg/id6478942365)。
- **iPhone/iPad**：在 AmneziaWG 中导入文件或扫描二维码。
- **Android**：[WG Tunnel](https://wgtunnel.com/download/)，AmneziaWG
  配置应使用 VPN/Userspace 模式。

如果需要访问打印机、NAS 和路由器，不要启用额外的 full-tunnel
覆盖。WG Tunnel 检测到 Amnezia 指令时会自动使用对应后端。

### Xray Reality

Xray Reality 是备用传输。客户端必须支持 VLESS Reality 和
`xtls-rprx-vision` flow。

新安装默认使用 `www.google.com:443` 作为 target 和 SNI。已有安装中，
机器人会读取 `xray-config/config.json` 的实际 `serverNames`。建议选择
可访问且尽量与 VPS 同 ASN 的 TLS 站点。修改 target/server name 后
需要同步更新已有客户端。

```text
vless://UUID@SERVER_IP:8443?encryption=none&type=tcp&security=reality&flow=xtls-rprx-vision&fp=randomized&sni=www.google.com&pbk=PUBLIC_KEY&sid=SHORT_ID&spx=%2F#NAME
```

机器人会为每个客户端创建 UUID 和 short ID，从现有私钥推导公钥，
使用 `xray run -test` 验证配置，原子替换文件并只重启 `vpn-xray`。
验证失败时会自动恢复旧配置。

### 更新、备份和维护

```bash
tar -czf vpn-stack-backup.tar.gz .env data xray-config
cd vpn-stack
git pull --ff-only
docker compose pull --ignore-buildable
docker compose up -d --build
docker image prune -f
```

| 命令 | 用途 |
|------|------|
| `docker compose ps` | 查看容器状态 |
| `docker compose logs -f` | 查看所有日志 |
| `docker compose restart vpn-bot` | 重启机器人 |
| `docker compose down` | 停止服务 |
| `docker compose up -d` | 启动服务 |

### 故障排查

peer 无法连接时：

- 检查提供商防火墙和 UFW 是否允许 `WG_PORT/udp`；
- 检查配置中的 `Endpoint`；
- 确认客户端支持全部 AmneziaWG 指令；
- 使用 `timedatectl status` 检查服务器时间；
- 查看 `docker compose logs -f wg-easy`。

连接成功但网页无法打开时，可将 `WG_MTU` 降到 `1240`，重新创建
`wg-easy` 并重新下载配置，同时检查 DNS。

无法访问局域网时，确认 `AllowedIPs` 不包含 `0.0.0.0/0`，关闭
lockdown 或启用 **Allow LAN Traffic**，并检查 VPN 子网是否与家庭
网络重叠。

Telegram 机器人无响应时，检查 `BOT_TOKEN`、`ALLOWED_USERNAMES`
以及 `docker compose logs -f vpn-bot`。
