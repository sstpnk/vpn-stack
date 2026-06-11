# VPN Stack: AmneziaWG + Xray Reality + Telegram Bot

[Русский](#русский) | [English](#english) | [简体中文](#简体中文)

## Русский

Готовый Docker-стек для личного VPN на VPS:

- **AmneziaWG Easy**: AmneziaWG-сервер и веб-панель управления peer-ами.
- **Xray Reality**: резервный VLESS Reality-сервер.
- **Telegram-бот**: создание, поиск, переименование и удаление клиентов, выдача конфигураций.
- **Split tunneling**: публичный IPv4-трафик идёт через VPN, локальные сети остаются доступными напрямую.

### Требования

- Ubuntu 22.04/24.04 или Debian 12.
- Публичный IPv4, SSH и пользователь с `sudo`.
- Рекомендуемый минимум: 1 vCPU, 1 ГБ RAM, 10 ГБ диска.
- Открытые порты: `51820/udp` для AmneziaWG и `8443/tcp` для Xray.

Веб-панель использует `51821/tcp`. Не публикуйте её без необходимости: безопаснее привязать порт к `127.0.0.1` и открывать через SSH-туннель.

### Установка

```bash
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
sudo ./setup.sh
```

Скрипт установит Docker при необходимости, создаст `.env`, подготовит Xray Reality и запустит контейнеры.

Проверка:

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
```

Доступ к локально опубликованной панели:

```bash
ssh -L 51821:127.0.0.1:51821 user@SERVER_IP
```

Откройте `http://127.0.0.1:51821`.

### Основные переменные `.env`

| Переменная | Назначение |
|---|---|
| `WG_HOST` | публичный IP или DNS-имя сервера |
| `WG_PORT` | UDP-порт AmneziaWG, обычно `51820` |
| `PASSWORD` | пароль веб-панели |
| `WG_DEFAULT_DNS` | DNS в клиентских конфигурациях |
| `WG_ALLOWED_IPS` | маршруты клиента |
| `WG_MTU` | MTU клиента |
| `AMNEZIA_JC`, `AMNEZIA_JMIN`, `AMNEZIA_JMAX` | параметры junk-пакетов |
| `AMNEZIA_S1`, `AMNEZIA_S2` | размеры дополнения handshake |
| `AMNEZIA_H1`...`AMNEZIA_H4` | глобальные значения заголовков |
| `AMNEZIA_I1`...`AMNEZIA_I5` | глобальные CPS-пакеты |
| `BOT_TOKEN` | токен Telegram-бота |
| `BOT_ALLOWED_USER` | разрешённый Telegram username |

После изменения серверных параметров пересоздайте клиентские конфигурации и перезапустите стек:

```bash
docker compose up -d --build
```

Не редактируйте `data/wireguard/wg0.json` вручную без резервной копии: файл содержит ключи и peer-ы.

### Создание peer в веб-панели

В окне **New Client** укажите имя и выберите:

- **Server defaults**: глобальные `H1-H4` и `I1-I5`.
- Один из 11 готовых шаблонов.
- Готовый шаблон с ручной корректировкой полей.
- Полностью пользовательскую комбинацию `H1-H4`, `I1-I5` и `Init_Packet_Delay`.

Значения сохраняются отдельно для peer-а в `wg0.json` и используются в скачиваемом `.conf` и QR-коде. Пустые поля наследуют глобальные значения сервера.

Доступные шаблоны:

| Шаблон | Профиль |
|---|---|
| YouTube Consumer | потоковое видео и крупные буферы |
| Zoom Meeting | STUN и частые аудио/видео-фреймы |
| Discord Voice | VoIP, WebSocket и небольшие сообщения |
| Cloudflare WARP / 1.1.1.1 | короткие DNS-over-TLS-подобные сессии |
| Steam Download | крупные пакеты и высокая пропускная способность |
| Gosuslugi / ESIA | короткие REST-подобные запросы |
| Mail.ru / VK Mail | фоновая почтовая синхронизация |
| Yandex Weather / News | короткие периодические всплески |
| VTB / Sberbank Online | пакеты разного размера и увеличенная задержка старта |
| Wildberries / Ozon | смешанный e-commerce-профиль |
| GitHub / Habr | API, Git и длинные сессии |

`I1-I5` принимают последовательности вида `<b 0x160303><r 64>`. `Init_Packet_Delay` должен быть целым неотрицательным числом. Используемый клиент AmneziaWG должен поддерживать эту директиву; иначе удалите её из конфигурации или выберите параметры сервера.

Шаблоны лишь формируют профиль пакетов. Они не гарантируют доступность сервиса или обход ограничений в конкретной сети.

### Telegram-бот

После запуска отправьте боту `/start`. Бот умеет управлять AmneziaWG peer-ами и VLESS Reality-клиентами. Доступ ограничивается переменной `BOT_ALLOWED_USER`.

Для каждого устройства создавайте отдельный peer. При утечке конфигурации удалите соответствующий peer и создайте новый.

### Обновление

```bash
git pull
docker compose up -d --build
docker image prune -f
```

Перед обновлением сохраните резервную копию:

```bash
tar -czf vpn-stack-backup.tar.gz .env data xray-config
```

### Диагностика

```bash
docker compose ps
docker compose logs --tail=200 wg-easy
docker compose logs --tail=200 vpn-bot
docker compose logs --tail=200 xray
sudo ss -lntup
```

Если peer не подключается, проверьте UDP-порт, endpoint, время на сервере, поддержку параметров клиентом и отсутствие пересечений значений `H1-H4`.

---

## English

A Docker-based personal VPN stack for a VPS:

- **AmneziaWG Easy**: AmneziaWG server with a web administration panel.
- **Xray Reality**: fallback VLESS Reality server.
- **Telegram bot**: client creation, search, rename, deletion, and configuration delivery.
- **Split tunneling**: public IPv4 traffic uses the VPN while private networks remain local.

### Requirements

- Ubuntu 22.04/24.04 or Debian 12.
- Public IPv4, SSH access, and a user with `sudo`.
- Recommended minimum: 1 vCPU, 1 GB RAM, 10 GB disk.
- Open `51820/udp` for AmneziaWG and `8443/tcp` for Xray.

The web panel listens on `51821/tcp`. Prefer binding it to `127.0.0.1` and accessing it through an SSH tunnel.

### Installation

```bash
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
sudo ./setup.sh
```

The setup script installs Docker when needed, creates `.env`, prepares Xray Reality, and starts the containers.

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
```

For a locally bound web panel:

```bash
ssh -L 51821:127.0.0.1:51821 user@SERVER_IP
```

Then open `http://127.0.0.1:51821`.

### Main `.env` variables

| Variable | Purpose |
|---|---|
| `WG_HOST` | public server IP or hostname |
| `WG_PORT` | AmneziaWG UDP port, normally `51820` |
| `PASSWORD` | web panel password |
| `WG_DEFAULT_DNS` | DNS written to client configurations |
| `WG_ALLOWED_IPS` | client routes |
| `WG_MTU` | client MTU |
| `AMNEZIA_JC`, `AMNEZIA_JMIN`, `AMNEZIA_JMAX` | junk packet settings |
| `AMNEZIA_S1`, `AMNEZIA_S2` | handshake padding |
| `AMNEZIA_H1`...`AMNEZIA_H4` | global header values |
| `AMNEZIA_I1`...`AMNEZIA_I5` | global CPS packets |
| `BOT_TOKEN` | Telegram bot token |
| `BOT_ALLOWED_USER` | allowed Telegram username |

After changing server parameters, rebuild the stack and regenerate client configurations:

```bash
docker compose up -d --build
```

Do not edit `data/wireguard/wg0.json` without a backup. It contains private keys and peer records.

### Creating a peer in the web panel

In **New Client**, enter a name and choose:

- **Server defaults**.
- One of the 11 built-in traffic profiles.
- A preset followed by manual field changes.
- A fully custom `H1-H4`, `I1-I5`, and `Init_Packet_Delay` combination.

Per-peer values are stored in `wg0.json` and used for downloaded configurations and QR codes. Empty fields inherit global server values.

Available profiles: YouTube Consumer, Zoom Meeting, Discord Voice, Cloudflare WARP / 1.1.1.1, Steam Download, Gosuslugi / ESIA, Mail.ru / VK Mail, Yandex Weather / News, VTB / Sberbank Online, Wildberries / Ozon, and GitHub / Habr.

`I1-I5` use expressions such as `<b 0x160303><r 64>`. `Init_Packet_Delay` must be a non-negative integer. The client application must support this directive; otherwise remove it or use server defaults.

Profiles only shape packet characteristics. They do not guarantee service availability or restriction bypassing on any specific network.

### Telegram bot

Send `/start` after deployment. Access is restricted by `BOT_ALLOWED_USER`. Create a separate peer for every device and revoke a peer immediately if its configuration is exposed.

### Update and backup

```bash
tar -czf vpn-stack-backup.tar.gz .env data xray-config
git pull
docker compose up -d --build
docker image prune -f
```

### Troubleshooting

```bash
docker compose ps
docker compose logs --tail=200 wg-easy
docker compose logs --tail=200 vpn-bot
docker compose logs --tail=200 xray
sudo ss -lntup
```

For connection failures, verify the UDP firewall rule, endpoint, server clock, client feature support, and non-overlapping `H1-H4` values.

---

## 简体中文

这是一个用于 VPS 的个人 VPN Docker 套件：

- **AmneziaWG Easy**：AmneziaWG 服务端和 Web 管理面板。
- **Xray Reality**：备用 VLESS Reality 服务。
- **Telegram 机器人**：创建、搜索、重命名、删除客户端并发送配置。
- **分流**：公网 IPv4 流量经过 VPN，局域网流量保持本地访问。

### 系统要求

- Ubuntu 22.04/24.04 或 Debian 12。
- 公网 IPv4、SSH 访问权限和可使用 `sudo` 的用户。
- 建议至少 1 vCPU、1 GB 内存和 10 GB 磁盘。
- 开放 `51820/udp`（AmneziaWG）和 `8443/tcp`（Xray）。

Web 面板使用 `51821/tcp`。建议只绑定到 `127.0.0.1`，并通过 SSH 隧道访问。

### 安装

```bash
git clone https://github.com/sstpnk/vpn-stack.git
cd vpn-stack
chmod +x setup.sh
sudo ./setup.sh
```

安装脚本会按需安装 Docker、创建 `.env`、生成 Xray Reality 配置并启动容器。

```bash
docker compose ps
docker compose logs --tail=100 wg-easy
docker compose logs --tail=100 vpn-bot
docker compose logs --tail=100 xray
```

访问仅绑定本机的管理面板：

```bash
ssh -L 51821:127.0.0.1:51821 user@SERVER_IP
```

然后打开 `http://127.0.0.1:51821`。

### 主要 `.env` 变量

| 变量 | 用途 |
|---|---|
| `WG_HOST` | 服务器公网 IP 或域名 |
| `WG_PORT` | AmneziaWG UDP 端口，通常为 `51820` |
| `PASSWORD` | Web 面板密码 |
| `WG_DEFAULT_DNS` | 客户端配置中的 DNS |
| `WG_ALLOWED_IPS` | 客户端路由 |
| `WG_MTU` | 客户端 MTU |
| `AMNEZIA_JC`, `AMNEZIA_JMIN`, `AMNEZIA_JMAX` | junk 数据包参数 |
| `AMNEZIA_S1`, `AMNEZIA_S2` | 握手填充参数 |
| `AMNEZIA_H1`...`AMNEZIA_H4` | 全局包头值 |
| `AMNEZIA_I1`...`AMNEZIA_I5` | 全局 CPS 数据包 |
| `BOT_TOKEN` | Telegram 机器人令牌 |
| `BOT_ALLOWED_USER` | 允许使用机器人的 Telegram 用户名 |

修改服务端参数后，需要重新构建并重新生成客户端配置：

```bash
docker compose up -d --build
```

不要在没有备份的情况下手工编辑 `data/wireguard/wg0.json`，其中包含私钥和 peer 数据。

### 在 Web 面板中创建 peer

在 **New Client** 窗口输入名称，并选择：

- **Server defaults**：使用服务端全局参数。
- 11 个内置流量预设之一。
- 选择预设后手工修改字段。
- 完全自定义 `H1-H4`、`I1-I5` 和 `Init_Packet_Delay`。

每个 peer 的参数会保存在 `wg0.json` 中，并用于下载的配置文件和二维码。空字段继承服务端全局值。

内置预设包括：YouTube Consumer、Zoom Meeting、Discord Voice、Cloudflare WARP / 1.1.1.1、Steam Download、Gosuslugi / ESIA、Mail.ru / VK Mail、Yandex Weather / News、VTB / Sberbank Online、Wildberries / Ozon、GitHub / Habr。

`I1-I5` 使用类似 `<b 0x160303><r 64>` 的表达式。`Init_Packet_Delay` 必须是非负整数。客户端必须支持该指令，否则请删除它或使用服务端默认参数。

这些预设只调整数据包特征，不能保证任何特定网络中的服务可用性或绕过限制。

### Telegram 机器人

部署后向机器人发送 `/start`。访问权限由 `BOT_ALLOWED_USER` 限制。每台设备应使用独立 peer；配置泄露后应立即删除对应 peer。

### 更新和备份

```bash
tar -czf vpn-stack-backup.tar.gz .env data xray-config
git pull
docker compose up -d --build
docker image prune -f
```

### 故障排查

```bash
docker compose ps
docker compose logs --tail=200 wg-easy
docker compose logs --tail=200 vpn-bot
docker compose logs --tail=200 xray
sudo ss -lntup
```

如果 peer 无法连接，请检查 UDP 防火墙、endpoint、服务器时间、客户端功能支持，以及 `H1-H4` 是否互相重叠。

## Project layout

```text
.
├── awg-easy/       # AmneziaWG server and web UI
├── bot/            # Telegram bot
├── data/           # persistent runtime data
├── xray-config/    # Xray Reality templates
├── docker-compose.yml
└── setup.sh
```

## License

See [awg-easy/LICENSE](awg-easy/LICENSE) and the licenses of the included upstream components.
