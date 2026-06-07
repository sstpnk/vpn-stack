import html
import logging
import os
from datetime import datetime, timedelta, timezone
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

wg = WGEasyAPI()

ALLOWED_USERNAMES = {
    u.strip().lstrip("@")
    for u in os.environ.get("ALLOWED_USERNAMES", "").split(",")
    if u.strip()
}

WAITING_FOR_NAME = 1
WAITING_FOR_SEARCH = 2
WAITING_FOR_RENAME = 3

PAGE_SIZE = 8

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📋 Peers", "🟢 Active"],
        ["➕ Create Peer", "📥 Get Config"],
        ["🔍 Search", "🗑 Delete Peer"],
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
        InlineKeyboardButton("🟢 Active", callback_data="menu:active"),
    ],
    [
        InlineKeyboardButton("➕ Create Peer", callback_data="menu:create"),
        InlineKeyboardButton("📥 Get Config", callback_data="menu:config"),
    ],
    [
        InlineKeyboardButton("🔍 Search", callback_data="menu:search"),
        InlineKeyboardButton("🗑 Delete Peer", callback_data="menu:delete"),
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
        addr = c.get("ipv4Address") or "N/A"
        lines.append(f"{status} <b>{name}</b>  —  {addr}")
    return "\n".join(lines)


def format_active_peers_text(clients: list) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)
    lines = []
    for c in clients:
        hs = c.get("latestHandshakeAt")
        if not hs:
            continue
        hs_dt = datetime.fromisoformat(hs.replace("Z", "+00:00"))
        if hs_dt < cutoff:
            continue
        ago = int((datetime.now(timezone.utc) - hs_dt).total_seconds())
        name = html.escape(c.get("name", "?"))
        addr = c.get("ipv4Address") or "N/A"
        lines.append(f"🟢 <b>{name}</b>  —  {addr}  <i>({ago}s ago)</i>")
    return "\n".join(lines) if lines else ""


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
async def active_peers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clients = wg.list_clients()
    except Exception as e:
        await update.message.reply_text(f"API error: {e}")
        return

    text = format_active_peers_text(clients)
    await update.message.reply_text(text or "No peers active in the last 3 minutes.", parse_mode="HTML")


@require_access
async def config_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_peer_selection(update, context, "cfg")


@require_access
async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _show_peer_selection(update, context, "del")


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
        client_id = result.get("clientId")
        if client_id:
            config_data, filename = wg.get_client_config(client_id)
            await update.message.reply_document(
                document=BytesIO(config_data),
                filename=filename,
                caption=f"✅ Peer <b>{html.escape(name)}</b> created!" + AMNEZIA_LINKS,
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                f"✅ Peer <b>{html.escape(name)}</b> created!" + AMNEZIA_LINKS,
                parse_mode="HTML",
                disable_web_page_preview=True,
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

        elif action == "active":
            try:
                clients = wg.list_clients()
            except Exception as e:
                await query.message.reply_text(f"API error: {e}")
                return
            text = format_active_peers_text(clients)
            await query.message.reply_text(text or "No peers active in the last 3 minutes.", parse_mode="HTML")

        elif action == "create":
            await query.message.reply_text("Use /create &lt;name&gt; to create a new peer.", parse_mode="HTML")

        elif action == "search":
            await query.message.reply_text("Use /search &lt;name&gt; to find peers.", parse_mode="HTML")

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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    kb_buttons = ["📋 Peers", "🟢 Active", "➕ Create Peer", "📥 Get Config", "🔍 Search", "🗑 Delete Peer"]
    kb_filter = filters.Text(kb_buttons)
    cancel_cb = CallbackQueryHandler(cancel_from_button, pattern="^cancel_conv$")

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["➕ Create Peer"]), create_start),
            CommandHandler("create", create_start),
            MessageHandler(filters.Text(["🔍 Search"]), search_start),
            CommandHandler("search", search_start),
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
    app.add_handler(MessageHandler(filters.Text(["🟢 Active"]), active_peers))
    app.add_handler(MessageHandler(filters.Text(["📥 Get Config"]), config_menu))
    app.add_handler(MessageHandler(filters.Text(["🗑 Delete Peer"]), delete_menu))
    app.add_handler(CallbackQueryHandler(on_callback))

    logger.info("Bot started, allowed users: %s", ALLOWED_USERNAMES)
    app.run_polling()


if __name__ == "__main__":
    main()
