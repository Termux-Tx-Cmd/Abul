# pro_utility_bot.py
import ipaddress
import socket
import httpx
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ====================== CONFIG ======================
BOT_TOKEN = "8364232558:AAHmVVDqkWhBTxCfOTu-LpUBilO83dFpkcI"
# Public channel: use "@YourChannel"; Private channel: use numeric id like -100xxxxxxxxxx
CHANNEL_USERNAME = "@termuxtxcmd"

IP_API_URL = (
    "http://ip-api.com/json/{ip}"
    "?fields=status,message,query,country,countryCode,region,regionName,city,zip,"
    "lat,lon,timezone,isp,org,as,reverse,proxy,hosting"
)
# Admin list (optional; enable later for admin-only stuff)
ADMINS = set()  # e.g. {123456789}
# ====================================================

# ---------- Helpers ----------
def kb_back(tag="main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"back:{tag}")]])

def main_menu():
    rows = [
        [InlineKeyboardButton("🌐 IP / Domain Lookup", callback_data="go:ip")],
        [InlineKeyboardButton("📱 Phone Number Lookup", callback_data="go:phone")],
        [InlineKeyboardButton("🛠 Termux Tools (30+)", callback_data="go:tools")],
        [InlineKeyboardButton("📖 Learn Section", callback_data="go:learn")],
        [InlineKeyboardButton("🙍 Your Info", callback_data="go:me")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="go:settings")],
        [InlineKeyboardButton("📢 Join Channel / Check", callback_data="go:join")]
    ]
    return InlineKeyboardMarkup(rows)

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat = CHANNEL_USERNAME
        member = await context.bot.get_chat_member(chat, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        # If channel misconfigured, fail closed to avoid abuse
        return False

def is_valid_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text.strip())
        return True
    except ValueError:
        return False

# Curated tools (safe, high level guides)
TOOLS = {
    # Networking & Recon
    "nmap": ("pkg install nmap", "Scan hosts/ports. Example: nmap -sV target.com"),
    "whois": ("pkg install whois", "WHOIS records for domains/IPs. Example: whois example.com"),
    "dnsutils (dig)": ("pkg install dnsutils", "DNS lookups. Example: dig A example.com"),
    "dnsmap": ("pkg install dnsmap", "Simple subdomain brute-forcer. Use responsibly."),
    "traceroute": ("pkg install traceroute", "Trace network path to a host."),

    # Web testing (educational)
    "sqlmap": ("pkg install sqlmap", "Automated SQLi testing on authorized targets."),
    "nikto": ("pkg install nikto", "Baseline web server checks."),

    # Auth & wordlists (educational)
    "hydra": ("pkg install hydra", "Login testing tool for your lab systems."),
    "john (JtR)": ("pkg install john", "Hash auditing in lab environments."),
    "crunch": ("pkg install crunch", "Wordlist generator for testing in labs."),

    # Wireless (requires compatible hardware; educational)
    "aircrack-ng": ("pkg install aircrack-ng", "802.11 auditing suite in lawful testbeds."),
    "wifite": ("pkg install wifite", "Wrapper for wireless auditing in labs."),

    # Pentest framework (large)
    "metasploit": ("pkg install unstable-repo && pkg install metasploit", "Exploit dev/testing framework in labs."),

    # System & Dev
    "git": ("pkg install git", "Clone repositories. git clone <url>"),
    "python": ("pkg install python", "Run scripts: python script.py"),
    "pip": ("pip install --upgrade pip", "Python package manager."),
    "nodejs": ("pkg install nodejs", "Run JS apps: node app.js"),
    "openjdk-17": ("pkg install openjdk-17", "Java toolchain on Termux."),
    "golang": ("pkg install golang", "Go toolchain for CLI apps."),

    # Utilities
    "curl": ("pkg install curl", "HTTP/API tester: curl -I https://example.com"),
    "wget": ("pkg install wget", "Download files via HTTP/FTP."),
    "htop": ("pkg install htop", "Interactive process viewer."),
    "nano": ("pkg install nano", "Beginner-friendly editor."),
    "vim": ("pkg install vim", "Advanced modal editor."),
    "zip": ("pkg install zip", "Create zips: zip out.zip file"),
    "unzip": ("pkg install unzip", "Extract zip files."),
    "tar": ("pkg install tar", "Extract archives: tar -xvf file.tar.gz"),
    "openssl": ("pkg install openssl", "Crypto toolkit: checksums, TLS client, etc."),
    "fd (fd-find)": ("pkg install fd", "Fast file search."),
    "ripgrep (rg)": ("pkg install ripgrep", "Fast text search in files."),

    # Networking/Remote
    "openssh (ssh/scp)": ("pkg install openssh", "SSH/SCP client; ssh user@host"),
    "netcat (nc)": ("pkg install netcat", "Simple TCP/UDP read/write & listeners."),
    "iproute2 (ip)": ("pkg install iproute2", "Network info: ip a, ip r"),
    "rsync": ("pkg install rsync", "Efficient file sync/copy."),
    "openvpn": ("pkg install openvpn", "VPN client (needs config)."),

    # Termux special
    "termux-api": ("pkg install termux-api", "Access phone features: termux-battery-status"),
    "termux-tools": ("pkg install termux-tools", "Core Termux utilities."),
    "termux-setup-storage": ("termux-setup-storage", "Grant storage access from Android.")
}

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Gate with join prompt
    if not await check_membership(user.id, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{str(CHANNEL_USERNAME).lstrip('@')}")],
            [InlineKeyboardButton("🔍 Check Join", callback_data="go:join")]
        ])
        await update.message.reply_text(
            "⚠️ To use this bot, please join our channel first.",
            reply_markup=kb
        )
        return
    await update.message.reply_text("👋 Welcome! Choose an option:", reply_markup=main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "🆘 *Help*\n\n"
        "/start — open main menu\n"
        "/menu — open main menu\n"
        "/help — this help\n"
        "/me — your info card\n\n"
        "Use the menu buttons to run lookups and browse tools.\n"
        "Always follow local laws and test only on systems you own or have written permission to assess."
    )
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=main_menu())

async def me_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    info = (
        f"🙍 *Your Info*\n\n"
        f"ID: `{u.id}`\n"
        f"Name: {u.full_name}\n"
        f"Username: @{u.username if u.username else '—'}\n"
        f"Language: {u.language_code or '—'}\n"
    )
    await update.message.reply_text(info, parse_mode="Markdown", reply_markup=main_menu())

# ---------- Menu / Callbacks ----------
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Channel gate
    if not await check_membership(user_id, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{str(CHANNEL_USERNAME).lstrip('@')}")],
            [InlineKeyboardButton("🔍 Check Join Again", callback_data="go:join")]
        ])
        await query.edit_message_text(
            "⚠️ You must join our channel to use this bot.",
            reply_markup=kb
        )
        return

    action, _, arg = query.data.partition(":")
    if action == "go":
        dest = arg
        if dest == "join":
            # Re-check join
            if await check_membership(user_id, context):
                await query.edit_message_text(
                    "✅ Thanks for joining! Use the menu below.",
                    reply_markup=main_menu()
                )
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{str(CHANNEL_USERNAME).lstrip('@')}")],
                    [InlineKeyboardButton("🔍 Check Join Again", callback_data="go:join")]
                ])
                await query.edit_message_text("❌ Not joined yet. Please join and check again.", reply_markup=kb)
        elif dest == "ip":
            await query.edit_message_text(
                "🌐 *IP / Domain Lookup*\n\n"
                "Send me an **IP** (e.g., `8.8.8.8`) or a **domain** (e.g., `example.com`).",
                parse_mode="Markdown",
                reply_markup=kb_back("main")
            )
        elif dest == "phone":
            await query.edit_message_text(
                "📱 *Phone Number Lookup*\n\n"
                "Send a number in **international format** (e.g., `+88017XXXXXXX`).",
                parse_mode="Markdown",
                reply_markup=kb_back("main")
            )
        elif dest == "tools":
            # build 2-column grid of tool buttons
            buttons = []
            row = []
            for i, name in enumerate(TOOLS.keys(), start=1):
                row.append(InlineKeyboardButton(name, callback_data=f"tool:{name}"))
                if len(row) == 2:
                    buttons.append(row); row = []
            if row: buttons.append(row)
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
            await query.edit_message_text("🛠 *Termux Tools (tap to view guide)*", parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))
        elif dest == "learn":
            await query.edit_message_text(
                "📖 *Learn Section*\n\n"
                "• Linux basics:\n"
                "  - List files: `ls -la`\n"
                "  - Change dir: `cd folder`\n"
                "  - Show path: `pwd`\n"
                "  - Copy/move: `cp`, `mv`\n"
                "  - Permissions: `chmod`, `chown`\n\n"
                "• Termux tips:\n"
                "  - Update pkgs: `pkg update && pkg upgrade`\n"
                "  - Storage: `termux-setup-storage`\n"
                "  - Shell rc: `~/.bashrc` or `~/.zshrc`\n\n"
                "• Python snippet:\n"
                "  ```python\n"
                "  print('Hello from Termux!')\n"
                "  ```\n\n"
                "Practice safely and legally ✅",
                parse_mode="Markdown",
                reply_markup=kb_back("main")
            )
        elif dest == "me":
            u = query.from_user
            info = (
                f"🙍 *Your Info*\n\n"
                f"ID: `{u.id}`\n"
                f"Name: {u.full_name}\n"
                f"Username: @{u.username if u.username else '—'}\n"
                f"Language: {u.language_code or '—'}\n"
            )
            await query.edit_message_text(info, parse_mode="Markdown", reply_markup=kb_back("main"))
        elif dest == "settings":
            await query.edit_message_text(
                "⚙️ *Settings*\n\n"
                "Coming soon:\n"
                "• Language\n"
                "• Privacy toggles\n"
                "• Admin panel (owner-only)\n",
                parse_mode="Markdown",
                reply_markup=kb_back("main")
            )

    elif action == "tool":
        name = arg
        if name in TOOLS:
            install, guide = TOOLS[name]
            text = (
                f"🛠 *{name}*\n\n"
                f"Install:\n`{install}`\n\n"
                f"Guide:\n{guide}\n\n"
                "Use only on systems you own or have written permission to test."
            )
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back("tools"))

    elif action == "back":
        dest = arg or "main"
        if dest == "main":
            await query.edit_message_text("🏠 Main Menu:", reply_markup=main_menu())
        elif dest == "tools":
            # rebuild tools grid
            buttons = []
            row = []
            for i, name in enumerate(TOOLS.keys(), start=1):
                row.append(InlineKeyboardButton(name, callback_data=f"tool:{name}"))
                if len(row) == 2:
                    buttons.append(row); row = []
            if row: buttons.append(row)
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
            await query.edit_message_text("🛠 *Termux Tools (tap to view guide)*", parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))

# ---------- Text Intake (IP/Domain/Phone) ----------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_membership(user_id, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{str(CHANNEL_USERNAME).lstrip('@')}")],
            [InlineKeyboardButton("🔍 Check Join", callback_data="go:join")]
        ])
        await update.message.reply_text("⚠️ Join the channel to use the bot.", reply_markup=kb)
        return

    text = (update.message.text or "").strip()

    # Phone number?
    if text.startswith("+") and len(text) > 7:
        await phone_lookup(update, context, text)
        return

    # IP or resolve domain?
    if is_valid_ip(text):
        await ip_lookup(update, context, text, resolved_from=None)
        return
    else:
        # Try domain resolve
        try:
            ip = socket.gethostbyname(text)
            await ip_lookup(update, context, ip, resolved_from=text)
            return
        except Exception:
            # Not an IP/domain → show gentle hint (don’t spam)
            await update.message.reply_text(
                "Tip: send an IP like `8.8.8.8`, a domain like `example.com`, "
                "or a phone number like `+88017XXXXXXX`.",
                parse_mode="Markdown"
            )

# ---------- Feature Impl ----------
async def ip_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE, ip: str, resolved_from: str | None):
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(IP_API_URL.format(ip=ip))
            data = r.json()
        if data.get("status") != "success":
            await update.message.reply_text(f"❌ Lookup failed: {data.get('message','unknown error')}")
            return

        msg = "✅ *IP Lookup Result*\n"
        if resolved_from:
            msg += f"Domain: `{resolved_from}`\n"
        msg += (
            f"IP: `{data['query']}`\n"
            f"Country: {data.get('country','-')} ({data.get('countryCode','-')})\n"
            f"Region/City: {data.get('regionName','-')}, {data.get('city','-')} {data.get('zip','')}\n"
            f"Timezone: {data.get('timezone','-')}\n"
            f"ISP: {data.get('isp','-')}\n"
            f"Org: {data.get('org','-')}\n"
            f"AS: {data.get('as','-')}\n"
            f"Reverse DNS: {data.get('reverse','-')}\n"
            f"Coordinates: {data.get('lat')}, {data.get('lon')}\n"
            f"🌍 [Google Maps](https://www.google.com/maps?q={data.get('lat')},{data.get('lon')})\n"
        )
        if data.get("proxy"):
            msg += "⚠️ Flag: Proxy/VPN suspected\n"
        if data.get("hosting"):
            msg += "🏢 Flag: Hosting/DC IP\n"

        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

async def phone_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE, number_str: str):
    try:
        num = phonenumbers.parse(number_str, None)
        if not phonenumbers.is_valid_number(num):
            await update.message.reply_text("❌ Invalid phone number. Include country code (e.g., +88017XXXXXXX).")
            return
        country = geocoder.description_for_number(num, "en") or "Unknown"
        sim_carrier = carrier.name_for_number(num, "en") or "Unknown"
        tzs = timezone.time_zones_for_number(num)
        tz = ", ".join(tzs) if tzs else "Unknown"
        info = (
            "📱 *Phone Number Info*\n\n"
            f"Number: `{number_str}`\n"
            f"Country/Region: {country}\n"
            f"Carrier: {sim_carrier}\n"
            f"Timezones: {tz}\n"
        )
        await update.message.reply_text(info, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error parsing number:\n`{e}`", parse_mode="Markdown")

# ---------- Bootstrap ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("me", me_cmd))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 Pro Utility Bot is running…")
    app.run_polling()

if __name__ == "__main__":
    main()