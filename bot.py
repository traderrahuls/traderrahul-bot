import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
from datetime import datetime

# =============================================
# BOT CONFIG
# =============================================
BOT_TOKEN = "8244372675:AAEzNzglqjT8saJd3L2B-wJYS7kHmmxqu30"
VIP_USERNAME = "@rahulyadavs1"
CHANNEL_LINK = "https://t.me/traderrahul1"
CHANNEL_ID = "@traderrahul1"  # Channel username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# SAMPLE FREE SIGNALS
# =============================================
FREE_SIGNALS = [
    {
        "pair": "BTC/USDT",
        "type": "BUY 📈",
        "entry": "67,200",
        "tp": "68,500",
        "sl": "66,400",
        "timeframe": "4H",
        "confidence": "85%"
    },
    {
        "pair": "ETH/USDT",
        "type": "SELL 📉",
        "entry": "3,540",
        "tp": "3,420",
        "sl": "3,610",
        "timeframe": "1H",
        "confidence": "78%"
    },
    {
        "pair": "SOL/USDT",
        "type": "BUY 📈",
        "entry": "172.4",
        "tp": "181.0",
        "sl": "167.5",
        "timeframe": "15M",
        "confidence": "82%"
    },
    {
        "pair": "XRP/USDT",
        "type": "BUY 📈",
        "entry": "0.6120",
        "tp": "0.6480",
        "sl": "0.5950",
        "timeframe": "1H",
        "confidence": "79%"
    },
]

# =============================================
# /start COMMAND
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else "Trader"

    welcome_msg = f"""
👋 *Welcome {name}!*

📡 *TraderRahul Signal Bot* mein aapka swagat hai!

━━━━━━━━━━━━━━━━━━━━
🆓 *FREE Members ko milta hai:*
• 2-3 signals daily
• Basic crypto signals
• Market updates

👑 *VIP PRO Members ko milta hai:*
• 10-15 signals daily
• 92%+ win rate
• Entry + TP1 + TP2 + TP3
• Stop Loss alerts
• 1-on-1 support
• Futures & Spot dono
━━━━━━━━━━━━━━━━━━━━

Niche buttons se join karo! 👇
"""

    keyboard = [
        [
            InlineKeyboardButton("🆓 Free Channel Join", url=CHANNEL_LINK),
        ],
        [
            InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}"),
        ],
        [
            InlineKeyboardButton("📊 Free Signal Lo", callback_data="free_signal"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_msg,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# =============================================
# FREE SIGNAL COMMAND
# =============================================
async def free_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signal = random.choice(FREE_SIGNALS)
    await send_signal_message(update.message.chat_id, signal, context, is_vip=False)

# =============================================
# CALLBACK - Button Press
# =============================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "free_signal":
        signal = random.choice(FREE_SIGNALS)
        msg = format_signal(signal, is_vip=False)

        keyboard = [
            [InlineKeyboardButton("👑 VIP Signal chahiye?", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("📢 Channel Join Karo", url=CHANNEL_LINK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

    elif query.data == "vip_info":
        vip_msg = f"""
👑 *VIP PRO Membership*

✅ 10-15 premium signals daily
✅ 92%+ accuracy
✅ Entry, TP1, TP2, TP3 levels
✅ Stop Loss with every signal
✅ Futures + Spot both
✅ Portfolio management tips
✅ Direct support from Rahul sir

💬 *DM karo aur join karo:*
👉 {VIP_USERNAME}
"""
        keyboard = [
            [InlineKeyboardButton(f"📩 DM {VIP_USERNAME}", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        ]
        await query.message.reply_text(vip_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# FORMAT SIGNAL MESSAGE
# =============================================
def format_signal(signal, is_vip=False):
    badge = "👑 *VIP PRO SIGNAL*" if is_vip else "🆓 *FREE SIGNAL*"
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")

    msg = f"""
{badge}
━━━━━━━━━━━━━━━━━━━━
📌 *Pair:* `{signal['pair']}`
🔔 *Type:* {signal['type']}
⏱ *Timeframe:* {signal['timeframe']}

💰 *Entry:* `{signal['entry']}`
🎯 *Target (TP):* `{signal['tp']}`
🛑 *Stop Loss:* `{signal['sl']}`

📊 *Confidence:* {signal['confidence']}
━━━━━━━━━━━━━━━━━━━━
⚠️ _Risk management zaroor karo. Ye financial advice nahi hai._

🕐 {time_now}
📢 @traderrahul1
"""
    return msg

# =============================================
# SEND SIGNAL TO CHAT
# =============================================
async def send_signal_message(chat_id, signal, context, is_vip=False):
    msg = format_signal(signal, is_vip)
    keyboard = [
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📢 Channel", url=CHANNEL_LINK)],
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =============================================
# AUTO POST TO CHANNEL (Scheduler)
# =============================================
async def auto_post_signal(context: ContextTypes.DEFAULT_TYPE):
    signal = random.choice(FREE_SIGNALS)
    msg = format_signal(signal, is_vip=False)

    keyboard = [
        [InlineKeyboardButton("👑 VIP Signal ke liye DM", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🤖 Bot Start Karo", url="https://t.me/traderrahul_1_bot")],
    ]

    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Signal posted to channel: {signal['pair']}")
    except Exception as e:
        logger.error(f"Channel post error: {e}")

# =============================================
# /signal COMMAND
# =============================================
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signal = random.choice(FREE_SIGNALS)
    msg = format_signal(signal, is_vip=False)

    keyboard = [
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📢 Channel Join", url=CHANNEL_LINK)],
    ]
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# /vip COMMAND
# =============================================
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vip_msg = f"""
👑 *VIP PRO Membership*

✅ 10-15 premium signals daily
✅ 92%+ accuracy
✅ Entry, TP1, TP2, TP3 levels
✅ Stop Loss with every signal
✅ Futures + Spot both
✅ Direct support from Rahul sir

💬 *Abhi DM karo:*
👉 {VIP_USERNAME}
"""
    keyboard = [
        [InlineKeyboardButton(f"📩 DM {VIP_USERNAME}", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
    ]
    await update.message.reply_text(vip_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("freesignal", free_signal_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Scheduler - auto post every 4 hours
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_post_signal,
        "interval",
        hours=4,
        args=[app]
    )
    scheduler.start()

    logger.info("🤖 TraderRahul Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
