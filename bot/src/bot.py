import html
import json
import logging
import os
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from wgapi import WGEasyAPI
from xray_manager import XrayManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

wg = WGEasyAPI()
xray = XrayManager()

ALLOWED_USERNAMES = {
    u.strip().lstrip("@")
    for u in os.environ.get("ALLOWED_USERNAMES", "").split(",")
    if u.strip()
}

WAITING_FOR_NAME = 1
WAITING_FOR_SEARCH = 2
WAITING_FOR_RENAME = 3
WAITING_FOR_VLESS_NAME = 4

PAGE_SIZE = 8

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📋 Peers"],
        ["➕ Create Peer", "📥 Get Config"],
        ["🔍 Search", "🗑 Delete Peer"],
        ["➕ VLESS", "🔗 VLESS Links"],
        ["🗑 VLESS"],
    ],
    resize_keyboard=True,
)

CANCEL_CONV_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("❌ Cancel", callback_data="cancel_conv"),
]])

PEER_SELECT_TITLE = {
    "cfg": "Select peer to download config:",
    "del": "Select peer to delete:",
}

INLINE_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📋 Peers", callback_data="menu:list"),
    ],
    [
        InlineKeyboardButton("➕ Create Peer", callback_data="menu:create"),
        InlineKeyboardButton("📥 Get Config", callback_data="menu:config"),
    ],
    [
        InlineKeyboardButton("🔍 Search", callback_data="menu:search"),
        InlineKeyboardButton("🗑 Delete Peer", callback_data="menu:delete"),
    ],
    [
        InlineKeyboardButton("➕ VLESS", callback_data="menu:vless_create"),
        InlineKeyboardButton("🔗 VLESS Links", callback_data="menu:vless_list"),
    ],
    [
        InlineKeyboardButton("🗑 VLESS", callback_data="menu:vless_delete"),
    ],
])

AMNEZIA_LINKS = (
    "\n\n📱 <b>Install a WireGuard client — two options:</b>\n\n"
    "<b>AmneziaWG</b>\n"
    '  <a href="https://apps.apple.com/us/app/amneziawg/id6478942365">iOS &amp; macOS</a> · '
    '<a href="https://play.google.com/store/apps/details?id=org.amnezia.awg">Android</a> · '
    '<a href="https://github.com/amnezia-vpn/amneziawg-windows-client/releases">Windows</a> · '
    '<a href="https://github.com/amnezia-vpn/amneziawg-linux-kernel-module">Linux</a>\n\n'
    "<b>WG Tunnel</b> (split tunneling)\n"
    '  <a href="https://play.google.com/store/apps/details?id=com.zaneschepke.wireguardautotunnel">Android</a> · '
    '<a href="https://wgtunnel.com/download?platform=windows">Windows</a> · '
    '<a href="https://wgtunnel.com/download?platform=linux">Linux</a>'
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_allowed(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.username in ALLOWED_USERNAMES


def require_access(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_allowed(update):
            await update.effective_message.reply_text("Access denied.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


def filter_clients(clients: list, query: str) -> list:
    if not query:
        return clients
    q = query.lower()
    return [c for c in clients if q in c.get("name", "").lower()]


def peers_keyboard(clients: list, action: str, page: int = 0) -> InlineKeyboardMarkup:
    """Paginated inline keyboard for a peer list. action: 'cfg' or 'del'."""
    total = len(clients)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    rows = []
    for c in clients[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]:
        name = c.get("name", str(c["id"]))
        if action == "cfg":
            rows.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"cfg:{c['id']}")])
        else:
            rows.append([InlineKeyboardButton(
                f"🗑 {name}",
                callback_data=f"del:{c['id']}:{name[:40]}",
            )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"pg:{action}:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"pg:{action}:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def format_peers_text(clients: list) -> str:
    lines = []
    for c in clients:
        status = "🟢" if c.get("enabled") else "🔴"
        name = html.escape(c.get("name", "?"))
        addr = c.get("ipv4Address") or c.get("address") or "N/A"
        hs = c.get("latestHandshakeAt")
        if hs:
            hs_dt = datetime.fromisoformat(hs.replace("Z", "+00:00"))
            ago = int((datetime.now(timezone.utc) - hs_dt).total_seconds())
            handshake = f"{ago}s ago"
        else:
            handshake = "never"
        rx = c.get("transferRx") or 0
        tx = c.get("transferTx") or 0
        rx_str = f"{rx/1024/1024:.1f} MB" if rx > 1024*1024 else f"{rx/1024:.1f} KB"
        tx_str = f"{tx/1024/1024:.1f} MB" if tx > 1024*1024 else f"{tx/1024:.1f} KB"
        lines.append(
            f"{status} <b>{name}</b>  —  {addr}  <i>({handshake})</i>\n"
            f"⬇️ {rx_str}  ⬆️ {tx_str}"
        )
    return "\n\n".join(lines)


async def _show_peer_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    try:
        clients = wg.list_clients()
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")
        return
    if not clients:
        await update.message.reply_text("No peers found.")
        return
    context.user_data[f"{action}_filter"] = ""
    await update.message.reply_text(
        PEER_SELECT_TITLE[action],
        reply_markup=peers_keyboard(clients, action),
    )


# ── Commands ──────────────────────────────────────────────────────────────────

@require_access
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("WireGuard Manager", reply_markup=MAIN_KEYBOARD)


@require_access
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("WireGuard Manager", reply_markup=INLINE_MENU)


@require_access
async def list_peers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = wg.list_clients()
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")
        return

    if not clients:
        await update.message.reply_text("No peers found.")
        return
    await update.message.reply_text(format_peers_text(clients), parse_mode="HTML")


@require_access
async def config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_peer_selection(update, context, "cfg")


@require_access
async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_peer_selection(update, context, "del")


# ── VLESS management ──────────────────────────────────────────────────────────

def vless_delete_keyboard(clients: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            f"🗑 {client['name']}",
            callback_data=f"vldel:{client['id']}",
        )]
        for client in clients
    ]
    rows.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


async def send_vless_connection(
    message,
    connection: dict,
    created: bool = False,
    include_client_config: bool = False,
):
    title = (
        f"✅ VLESS <b>{html.escape(connection['name'])}</b> created"
        if created
        else f"🔗 <b>{html.escape(connection['name'])}</b>"
    )
    await message.reply_text(
        f"{title}\n\n<code>{html.escape(connection['link'])}</code>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    if include_client_config:
        config_data = json.dumps(
            connection["client_config"],
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        await message.reply_document(
            document=BytesIO(config_data),
            filename=f"vless-{connection['id'][:8]}-xray.json",
            caption="Xray/NekoBox client JSON with recommended Mux settings.",
        )


@require_access
async def vless_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            connection = xray.create_client(" ".join(context.args))
            await send_vless_connection(
                update.message,
                connection,
                created=True,
                include_client_config=True,
            )
        except Exception as e:
            logger.exception("Failed to create VLESS connection")
            await update.message.reply_text(f"Xray error: {e}")
        return ConversationHandler.END

    await update.message.reply_text("Enter VLESS connection name:", reply_markup=CANCEL_CONV_KB)
    return WAITING_FOR_VLESS_NAME


@require_access
async def vless_create_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        connection = xray.create_client(update.message.text)
        await send_vless_connection(
            update.message,
            connection,
            created=True,
            include_client_config=True,
        )
    except Exception as e:
        logger.exception("Failed to create VLESS connection")
        await update.message.reply_text(f"Xray error: {e}")
    return ConversationHandler.END


@require_access
async def vless_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = xray.list_clients()
        if not clients:
            await update.message.reply_text("No VLESS connections found.")
            return
        for client in clients:
            await send_vless_connection(update.message, client)
    except Exception as e:
        logger.exception("Failed to list VLESS connections")
        await update.message.reply_text(f"Xray error: {e}")


@require_access
async def vless_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = xray.list_clients()
        if not clients:
            await update.message.reply_text("No VLESS connections found.")
            return
        await update.message.reply_text(
            "Select VLESS connection to delete:",
            reply_markup=vless_delete_keyboard(clients),
        )
    except Exception as e:
        logger.exception("Failed to list VLESS connections for deletion")
        await update.message.reply_text(f"Xray error: {e}")


# ── Create peer conversation ──────────────────────────────────────────────────

@require_access
async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter peer name:", reply_markup=CANCEL_CONV_KB)
    return WAITING_FOR_NAME


@require_access
async def create_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Name cannot be empty. Enter peer name:")
        return WAITING_FOR_NAME

    try:
        result = wg.create_client(name)
        client_id = result.get("id") or result.get("clientId")
        if not client_id:
            raise RuntimeError("Peer was created, but its ID was not returned")

        config_data, filename = wg.get_client_config(client_id)
        await update.message.reply_document(
            document=BytesIO(config_data),
            filename=filename,
            caption=f"✅ Peer <b>{html.escape(name)}</b> created!",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")

    return ConversationHandler.END


# ── Search conversation ───────────────────────────────────────────────────────

@require_access
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await _do_search(update, " ".join(context.args))
        return ConversationHandler.END
    await update.message.reply_text("Enter search term:")
    return WAITING_FOR_SEARCH


@require_access
async def search_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_search(update, update.message.text.strip())
    return ConversationHandler.END


async def _do_search(update: Update, term: str):
    if not term:
        await update.message.reply_text("Search term cannot be empty.")
        return
    try:
        clients = wg.list_clients()
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")
        return

    matching = filter_clients(clients, term)
    if not matching:
        await update.message.reply_text(f"No peers matching <b>{html.escape(term)}</b>.", parse_mode="HTML")
        return

    keyboard = []
    for c in matching:
        name = c.get("name", str(c["id"]))
        keyboard.append([
            InlineKeyboardButton(f"📄 {name}", callback_data=f"cfg:{c['id']}"),
            InlineKeyboardButton("✏️", callback_data=f"ren:{c['id']}:{name[:40]}"),
            InlineKeyboardButton("🗑", callback_data=f"del:{c['id']}:{name[:40]}"),
        ])
    keyboard.append([InlineKeyboardButton("Close", callback_data="cancel")])

    await update.message.reply_text(
        f"Found <b>{len(matching)}</b> peer(s) matching <b>{html.escape(term)}</b>:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def cancel_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Cancelled.")
    return ConversationHandler.END


# ── Rename peer conversation ──────────────────────────────────────────────────

async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_allowed(update):
        await query.edit_message_text("Access denied.")
        return ConversationHandler.END

    parts = query.data.split(":", 2)
    context.user_data["rename_id"] = parts[1]
    context.user_data["rename_old"] = parts[2] if len(parts) > 2 else parts[1]

    await query.message.reply_text(
        f"Enter new name for <b>{html.escape(context.user_data['rename_old'])}</b>:",
        parse_mode="HTML",
        reply_markup=CANCEL_CONV_KB,
    )
    return WAITING_FOR_RENAME


@require_access
async def rename_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text.strip()
    if not new_name:
        await update.message.reply_text("Name cannot be empty. Enter new name:")
        return WAITING_FOR_RENAME

    client_id = context.user_data.get("rename_id")
    old_name = context.user_data.get("rename_old", client_id)
    try:
        wg.rename_client(client_id, new_name)
        await update.message.reply_text(
            f"✅ <b>{html.escape(old_name)}</b> → <b>{html.escape(new_name)}</b>",
            parse_mode="HTML",
        )
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")

    return ConversationHandler.END


# ── Callback handler ──────────────────────────────────────────────────────────

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("Access denied.")
        return

    data = query.data

    if data == "noop":
        return

    if data == "cancel":
        await query.edit_message_text("Cancelled.")
        return

    # ── Inline menu ──
    if data.startswith("menu:"):
        action = data[5:]

        if action == "list":
            try:
                clients = wg.list_clients()
            except Exception as e:
                await query.message.reply_text(f"API error: {e}")
                return
            text = format_peers_text(clients) if clients else "No peers found."
            await query.message.reply_text(text, parse_mode="HTML")

        elif action == "create":
            await query.message.reply_text("Use /create &lt;name&gt; to create a new peer.", parse_mode="HTML")

        elif action == "search":
            await query.message.reply_text("Use /search &lt;name&gt; to find peers.", parse_mode="HTML")

        elif action == "vless_create":
            await query.message.reply_text(
                "Use /vless_create &lt;name&gt; or the ➕ VLESS keyboard button.",
                parse_mode="HTML",
            )

        elif action == "vless_list":
            try:
                clients = xray.list_clients()
                if not clients:
                    await query.message.reply_text("No VLESS connections found.")
                    return
                await query.edit_message_text(f"Found {len(clients)} VLESS connection(s).")
                for client in clients:
                    await send_vless_connection(query.message, client)
            except Exception as e:
                logger.exception("Failed to list VLESS connections")
                await query.edit_message_text(f"Xray error: {e}")

        elif action == "vless_delete":
            try:
                clients = xray.list_clients()
                if not clients:
                    await query.edit_message_text("No VLESS connections found.")
                    return
                await query.edit_message_text(
                    "Select VLESS connection to delete:",
                    reply_markup=vless_delete_keyboard(clients),
                )
            except Exception as e:
                logger.exception("Failed to list VLESS connections for deletion")
                await query.edit_message_text(f"Xray error: {e}")

        elif action in ("config", "delete"):
            try:
                clients = wg.list_clients()
            except Exception as e:
                await query.message.reply_text(f"API error: {e}")
                return
            if not clients:
                await query.message.reply_text("No peers found.")
                return
            act = "cfg" if action == "config" else "del"
            context.user_data[f"{act}_filter"] = ""
            await query.edit_message_text(PEER_SELECT_TITLE[act], reply_markup=peers_keyboard(clients, act))
        return

    # ── Pagination ──
    if data.startswith("pg:"):
        _, act, page_str = data.split(":")
        page = int(page_str)
        try:
            clients = wg.list_clients()
        except Exception as e:
            await query.edit_message_text(f"API error: {e}")
            return
        q = context.user_data.get(f"{act}_filter", "")
        filtered = filter_clients(clients, q)
        if not filtered:
            await query.edit_message_text("No peers found.")
            return
        title = PEER_SELECT_TITLE[act]
        if q:
            title += f"\n🔍 <i>{html.escape(q)}</i>"
        await query.edit_message_text(
            title,
            reply_markup=peers_keyboard(filtered, act, page),
            parse_mode="HTML",
        )
        return

    # ── Config download ──
    if data.startswith("cfg:"):
        client_id = data[4:]
        try:
            config_data, filename = wg.get_client_config(client_id)
            await query.edit_message_text("Here is your config:")
            await query.message.reply_document(
                document=BytesIO(config_data),
                filename=filename,
                caption=AMNEZIA_LINKS,
                parse_mode="HTML",
            )
        except Exception as e:
            await query.edit_message_text(f"API error: {e}")
        return

    # ── Delete ──
    if data.startswith("del:"):
        parts = data.split(":", 2)
        client_id = parts[1]
        name = parts[2] if len(parts) > 2 else client_id
        await query.edit_message_text(
            f"Delete peer <b>{html.escape(name)}</b>?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Yes, delete", callback_data=f"delconfirm:{client_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            ]]),
            parse_mode="HTML",
        )
        return

    if data.startswith("delconfirm:"):
        client_id = data[11:]
        try:
            wg.delete_client(client_id)
            await query.edit_message_text("✅ Peer deleted.")
        except Exception as e:
            await query.edit_message_text(f"API error: {e}")
        return

    # ── VLESS delete ──
    if data.startswith("vldel:"):
        client_id = data[6:]
        try:
            client = next(
                item for item in xray.list_clients()
                if item["id"] == client_id
            )
        except StopIteration:
            await query.edit_message_text("VLESS connection not found.")
            return
        except Exception as e:
            logger.exception("Failed to load VLESS connection")
            await query.edit_message_text(f"Xray error: {e}")
            return

        await query.edit_message_text(
            f"Delete VLESS connection <b>{html.escape(client['name'])}</b>?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "✅ Yes, delete",
                    callback_data=f"vldelconfirm:{client_id}",
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
            ]]),
            parse_mode="HTML",
        )
        return

    if data.startswith("vldelconfirm:"):
        client_id = data[13:]
        try:
            deleted = xray.delete_client(client_id)
            await query.edit_message_text(
                f"✅ VLESS connection <b>{html.escape(deleted['name'])}</b> deleted.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.exception("Failed to delete VLESS connection")
            await query.edit_message_text(f"Xray error: {e}")
        return


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    kb_buttons = [
        "📋 Peers",
        "➕ Create Peer",
        "📥 Get Config",
        "🔍 Search",
        "🗑 Delete Peer",
        "➕ VLESS",
        "🔗 VLESS Links",
        "🗑 VLESS",
    ]
    kb_filter = filters.Text(kb_buttons)
    cancel_cb = CallbackQueryHandler(cancel_from_button, pattern="^cancel_conv$")

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["➕ Create Peer"]), create_start),
            CommandHandler("create", create_start),
            MessageHandler(filters.Text(["🔍 Search"]), search_start),
            CommandHandler("search", search_start),
            MessageHandler(filters.Text(["➕ VLESS"]), vless_create_start),
            CommandHandler("vless_create", vless_create_start),
            CallbackQueryHandler(rename_start, pattern="^ren:"),
        ],
        states={
            WAITING_FOR_NAME: [
                MessageHandler(kb_filter, cancel_conv),
                cancel_cb,
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_receive_name),
            ],
            WAITING_FOR_SEARCH: [
                MessageHandler(kb_filter, cancel_conv),
                cancel_cb,
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_receive),
            ],
            WAITING_FOR_RENAME: [
                MessageHandler(kb_filter, cancel_conv),
                cancel_cb,
                MessageHandler(filters.TEXT & ~filters.COMMAND, rename_receive),
            ],
            WAITING_FOR_VLESS_NAME: [
                MessageHandler(kb_filter, cancel_conv),
                cancel_cb,
                MessageHandler(filters.TEXT & ~filters.COMMAND, vless_create_receive_name),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conv),
            MessageHandler(kb_filter, cancel_conv),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Text(["📋 Peers"]), list_peers))
    app.add_handler(MessageHandler(filters.Text(["📥 Get Config"]), config_menu))
    app.add_handler(MessageHandler(filters.Text(["🗑 Delete Peer"]), delete_menu))
    app.add_handler(MessageHandler(filters.Text(["🔗 VLESS Links"]), vless_list))
    app.add_handler(CommandHandler("vless_list", vless_list))
    app.add_handler(MessageHandler(filters.Text(["🗑 VLESS"]), vless_delete_menu))
    app.add_handler(CommandHandler("vless_delete", vless_delete_menu))
    app.add_handler(CallbackQueryHandler(on_callback))

    logger.info("Bot started, allowed users: %s", ALLOWED_USERNAMES)
    app.run_polling()


if __name__ == "__main__":
    main()
