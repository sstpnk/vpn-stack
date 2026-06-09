# VPN Stack: AmneziaWG + Xray Reality + Telegram Bot

Готовая Docker-сборка для развёртывания личного VPN на VPS. Основной
протокол — AmneziaWG с обфускацией UDP-трафика; Xray Reality можно
использовать как резервный вариант.

## Что входит в стек

- **AmneziaWG Easy** — VPN-сервер и веб-интерфейс управления peer-ами.
- **Xray Reality** — резервный VLESS Reality-сервер на TCP-порту 443.
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
| `443` | TCP | Xray Reality |
| `51821` | TCP | веб-интерфейс; рекомендуется только локальный доступ через SSH |

Публичные порты `22/tcp`, `51820/udp` и `443/tcp` нужно разрешить и в firewall
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
ufw allow 443/tcp
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
ss -lntup | grep -E ':(443|51820|51821)\b'
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
XRAY_PORT=443
XRAY_PUBLIC_HOST=
XRAY_SERVER_NAME=zoom.us
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
| `XRAY_PORT` | `443` | внешний TCP-порт Xray Reality |
| `XRAY_PUBLIC_HOST` | `WG_HOST` | адрес, используемый в VLESS-ссылках |
| `XRAY_SERVER_NAME` | `zoom.us` | предпочтительный Reality SNI, если он разрешён серверным конфигом |
| `XRAY_FINGERPRINT` | `randomized` | uTLS fingerprint в клиентских VLESS-профилях |
| `AMNEZIA_JC` | `10` | количество мусорных пакетов перед handshake |
| `AMNEZIA_JMIN` | `64` | минимальный размер мусорного пакета в байтах |
| `AMNEZIA_JMAX` | `200` | максимальный размер мусорного пакета в байтах |
| `AMNEZIA_S1`, `AMNEZIA_S2` | `64`, `64` | padding пакетов Init и Response |
| `AMNEZIA_H1`...`AMNEZIA_H4` | см. пример | непересекающиеся диапазоны заголовков пакетов |
| `AMNEZIA_I1`...`AMNEZIA_I5` | см. пример | CPS-пакеты с байтами и случайными фрагментами |
| `BOT_TOKEN` | пусто | токен, полученный у `@BotFather` |
| `ALLOWED_USERNAMES` | пусто | Telegram username без `@`; несколько имён через запятую |

Локальный fork AmneziaWG Easy получает все эти значения из `.env` через
`docker-compose.yml` и добавляет их непосредственно при генерации `.conf`.
Поэтому веб-интерфейс, QR-код и Telegram-бот возвращают одинаковую
конфигурацию с `J*`, `S*`, `H*`, `I1`–`I5`, `MTU` и split `AllowedIPs`.
Скачиваемый файл содержит комментарии, поясняющие назначение параметров.
Директива `Init_Packet_Delay` не добавляется: официальные AmneziaWG tools и
клиенты её не поддерживают.

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
3. Создайте клиента и скачайте `.conf` или покажите QR-код.

Конфиг из веб-интерфейса, QR-код и файл из Telegram-бота генерируются одним
кодом и содержат одинаковые параметры обфускации, MTU и маршруты.

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
- Убедитесь, что серверные и клиентские параметры `Jc/Jmin/Jmax/S1/S2/H1-H4`
  совпадают.
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

Новая установка использует `zoom.us:443` как Reality target и разрешает SNI
`zoom.us` и `www.zoom.us`. Для уже существующей установки бот читает
фактический `serverNames` из `xray-config/config.json` и использует разрешённое
значение в ссылке. Это не ломает ранее созданные подключения при обновлении
бота.

`zoom.us` является настраиваемым default, а не универсально лучшим target.
Официальная рекомендация Xray — выбирать доступный TLS-сайт по возможности в
том же ASN, что и VPS. Не меняйте `target/serverNames` у работающего сервера без
плана обновления существующих клиентов.

Пример генерируемой ссылки:

```text
vless://UUID@SERVER_IP:443?encryption=none&type=tcp&security=reality&flow=xtls-rprx-vision&fp=randomized&sni=zoom.us&pbk=PUBLIC_KEY&sid=SHORT_ID&spx=%2FSHORT_ID#NAME
```

Для каждого подключения бот:

- создаёт отдельный UUID с flow `xtls-rprx-vision`;
- создаёт отдельный 8-символьный hex `shortId`;
- вычисляет public key из существующего Reality private key, не меняя пару;
- формирует ссылку с согласованным SNI;
- создаёт отдельный `spiderX` в формате `/<shortId>`;
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
