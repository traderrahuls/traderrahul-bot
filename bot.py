import logging
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
CHANNEL_ID = "@traderrahul1"
PROP_LINK = "https://bit.ly/m/traderrahul"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# SIGNALS - BTC (Daily) + XAUUSD (Mon-Fri only)
# Scalping: 5M and 15M timeframes only
# =============================================
BTC_SIGNALS = [
    {"pair": "BTC/USDT", "type": "BUY 📈", "entry": "67,150", "tp1": "67,320", "tp2": "67,480", "sl": "66,980", "timeframe": "15M", "confidence": "84%"},
    {"pair": "BTC/USDT", "type": "SELL 📉", "entry": "67,800", "tp1": "67,630", "tp2": "67,450", "sl": "67,970", "timeframe": "5M",  "confidence": "81%"},
    {"pair": "BTC/USDT", "type": "BUY 📈", "entry": "66,900", "tp1": "67,080", "tp2": "67,220", "sl": "66,720", "timeframe": "15M", "confidence": "87%"},
    {"pair": "BTC/USDT", "type": "SELL 📉", "entry": "68,200", "tp1": "68,020", "tp2": "67,850", "sl": "68,390", "timeframe": "5M",  "confidence": "79%"},
    {"pair": "BTC/USDT", "type": "BUY 📈", "entry": "67,400", "tp1": "67,580", "tp2": "67,720", "sl": "67,230", "timeframe": "15M", "confidence": "83%"},
]

XAUUSD_SIGNALS = [
    {"pair": "XAU/USD", "type": "BUY 📈",  "entry": "2,318.50", "tp1": "2,321.00", "tp2": "2,324.50", "sl": "2,315.00", "timeframe": "15M", "confidence": "88%"},
    {"pair": "XAU/USD", "type": "SELL 📉", "entry": "2,325.00", "tp1": "2,322.50", "tp2": "2,319.00", "sl": "2,328.50", "timeframe": "5M",  "confidence": "85%"},
    {"pair": "XAU/USD", "type": "BUY 📈",  "entry": "2,310.00", "tp1": "2,313.00", "tp2": "2,316.50", "sl": "2,306.50", "timeframe": "15M", "confidence": "91%"},
    {"pair": "XAU/USD", "type": "SELL 📉", "entry": "2,330.50", "tp1": "2,327.00", "tp2": "2,323.50", "sl": "2,334.00", "timeframe": "5M",  "confidence": "82%"},
    {"pair": "XAU/USD", "type": "BUY 📈",  "entry": "2,305.75", "tp1": "2,308.50", "tp2": "2,312.00", "sl": "2,302.00", "timeframe": "15M", "confidence": "86%"},
]

# =============================================
# CHECK IF MARKET IS OPEN
# =============================================
def is_xauusd_market_open():
    # XAUUSD closed on Saturday (5) and Sunday (6)
    day = datetime.now().weekday()  # Mon=0, Sun=6
    return day < 5  # Mon-Fri only

def get_available_signals():
    if is_xauusd_market_open():
        return BTC_SIGNALS + XAUUSD_SIGNALS
    else:
        return BTC_SIGNALS

# =============================================
# FORMAT SIGNAL MESSAGE
# =============================================
def format_signal(signal, is_vip=False):
    badge = "👑 *VIP PRO SIGNAL*" if is_vip else "🆓 *FREE SIGNAL*"
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")
    is_buy = "BUY" in signal['type']
    direction = "🟢" if is_buy else "🔴"

    msg = f"""
{badge}
━━━━━━━━━━━━━━━━━━━━
{direction} *{signal['pair']}* — {signal['type']}
⏱ *Scalping {signal['timeframe']}*

💰 *Entry:* `{signal['entry']}`
🎯 *TP1:* `{signal['tp1']}`
🎯 *TP2:* `{signal['tp2']}`
🛑 *Stop Loss:* `{signal['sl']}`

📊 *Accuracy:* {signal['confidence']}
━━━━━━━━━━━━━━━━━━━━
⚠️ _Risk management zaroor karo._
_Ye financial advice nahi hai._

🕐 {time_now}
📢 @traderrahul1
"""
    return msg

# =============================================
# TP HIT CONGRATULATIONS MESSAGE
# =============================================
def format_tp_hit(signal, tp_level="TP1"):
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")
    congrats_msgs = [
        "Zabardast! Paisa bana liya! 💰",
        "Mast trade tha! Keep it up! 🔥",
        "Ekdum sahi signal! 🎯",
        "Bahut khoob! Profit book karo! 💪",
        "Trading ka maza aa gaya! 🚀",
    ]
    congrats = random.choice(congrats_msgs)

    msg = f"""
🎉 *TARGET HIT! {tp_level} DONE!* 🎉
━━━━━━━━━━━━━━━━━━━━
✅ *{signal['pair']}* — {signal['type']}

🏆 *{tp_level} Successfully Hit!*
🎯 *Target:* `{signal['tp1'] if tp_level == 'TP1' else signal['tp2']}`

━━━━━━━━━━━━━━━━━━━━
🥳 *{congrats}*

💡 _Ab SL ko entry pe le aao aur TP2 ka wait karo!_

💰 *Fund nahi hai trading ke liye?*
_Prop account lo — bahut kam price mein,_
_minimum rules ke saath!_
👇 *Join karo:*
━━━━━━━━━━━━━━━━━━━━
🕐 {time_now}
📢 @traderrahul1
"""
    return msg

# =============================================
# /start COMMAND
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else "Trader"

    weekend_note = ""
    if not is_xauusd_market_open():
        weekend_note = "\n⚠️ _Aaj Weekend hai — XAUUSD market band hai. Sirf BTC signals milenge._\n"

    welcome_msg = f"""
👋 *Welcome {name}!*

📡 *TraderRahul Signal Bot* mein aapka swagat hai!
{weekend_note}
━━━━━━━━━━━━━━━━━━━━
📊 *Hum dete hain:*
• 🥇 *XAU/USD* — Mon to Fri (Scalping)
• ₿ *BTC/USDT* — Daily (Scalping)
• ⏱ Sirf *5M & 15M* timeframe

🆓 *FREE Members:*
• 2-3 signals daily
• Basic signals + TP hit alerts

👑 *VIP PRO Members:*
• 10-15 signals daily
• 92%+ win rate
• Entry + TP1 + TP2 + SL
• 1-on-1 support
━━━━━━━━━━━━━━━━━━━━

Niche buttons se join karo! 👇
"""

    keyboard = [
        [InlineKeyboardButton("🆓 Free Channel Join", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📊 Free Signal Lo", callback_data="free_signal")],
        [InlineKeyboardButton("🏦 Prop Account Info", callback_data="prop_info")],
    ]

    await update.message.reply_text(
        welcome_msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =============================================
# CALLBACK - Button Press
# =============================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "free_signal":
        signals = get_available_signals()
        signal = random.choice(signals)
        msg = format_signal(signal, is_vip=False)

        # If weekend and only BTC available
        note = ""
        if not is_xauusd_market_open():
            note = "\n⚠️ _Weekend: XAUUSD band hai, sirf BTC signal._\n"

        keyboard = [
            [InlineKeyboardButton("👑 VIP Signal chahiye?", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
            [InlineKeyboardButton("📢 Channel Join", url=CHANNEL_LINK)],
        ]
        await query.message.reply_text(msg + note, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "prop_info":
        prop_msg = f"""
🏦 *Prop Account — Trader ke liye Best Option!*
━━━━━━━━━━━━━━━━━━━━
💡 *Apna fund nahi hai?*
_Koi baat nahi! Prop account se trade karo!_

✅ *Kya milta hai:*
• Bahut kam price mein account
• Minimum rules — asaan pass
• Profit aapka — risk unka
• $10K se $200K tak ka account
• Sab instruments — Gold, BTC, Forex

🎯 *Hamare signals se prop pass karo!*
━━━━━━━━━━━━━━━━━━━━
👇 *Abhi join karo:*
"""
        keyboard = [
            [InlineKeyboardButton("🚀 Prop Account Join Karo", url=PROP_LINK)],
            [InlineKeyboardButton("👑 VIP Signals bhi lo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        ]
        await query.message.reply_text(prop_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "vip_info":
        vip_msg = f"""
👑 *VIP PRO Membership*

✅ 10-15 premium signals daily
✅ 92%+ accuracy
✅ XAU/USD + BTC scalping
✅ Entry, TP1, TP2 levels
✅ Stop Loss with every signal
✅ Direct support from Rahul sir

💬 *Abhi DM karo:*
👉 {VIP_USERNAME}
"""
        keyboard = [
            [InlineKeyboardButton(f"📩 DM {VIP_USERNAME}", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        ]
        await query.message.reply_text(vip_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# AUTO POST TO CHANNEL (Scheduler)
# =============================================
async def auto_post_signal(app):
    signals = get_available_signals()
    signal = random.choice(signals)
    msg = format_signal(signal, is_vip=False)

    weekend_note = ""
    if not is_xauusd_market_open():
        weekend_note = "\n⚠️ _Weekend: Sirf BTC signals. XAUUSD Monday se!_\n"

    keyboard = [
        [InlineKeyboardButton("👑 VIP Signal ke liye DM", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("🤖 Bot Start Karo", url="https://t.me/traderrahul_1_bot")],
    ]

    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg + weekend_note,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Signal posted: {signal['pair']}")
    except Exception as e:
        logger.error(f"Channel post error: {e}")

# =============================================
# AUTO POST TP HIT MESSAGE
# =============================================
async def auto_post_tp_hit(app):
    signals = get_available_signals()
    signal = random.choice(signals)
    tp_level = random.choice(["TP1", "TP2"])
    msg = format_tp_hit(signal, tp_level)

    keyboard = [
        [InlineKeyboardButton("🚀 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("👑 VIP Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
    ]

    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"TP Hit posted: {signal['pair']} {tp_level}")
    except Exception as e:
        logger.error(f"TP hit post error: {e}")

# =============================================
# /signal COMMAND
# =============================================
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signals = get_available_signals()
    signal = random.choice(signals)
    msg = format_signal(signal, is_vip=False)

    note = ""
    if not is_xauusd_market_open():
        note = "\n⚠️ _Weekend: XAUUSD band hai, sirf BTC signal._\n"

    keyboard = [
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("📢 Channel Join", url=CHANNEL_LINK)],
    ]
    await update.message.reply_text(msg + note, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# /vip COMMAND
# =============================================
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vip_msg = f"""
👑 *VIP PRO Membership*

✅ 10-15 premium signals daily
✅ 92%+ accuracy
✅ XAU/USD Mon-Fri scalping
✅ BTC daily scalping
✅ Entry, TP1, TP2, SL levels
✅ Direct support from Rahul sir

💬 *Abhi DM karo:*
👉 {VIP_USERNAME}
"""
    keyboard = [
        [InlineKeyboardButton(f"📩 DM {VIP_USERNAME}", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
    ]
    await update.message.reply_text(vip_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# /prop COMMAND
# =============================================
async def prop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prop_msg = f"""
🏦 *Prop Account — Trader ke liye Best Option!*
━━━━━━━━━━━━━━━━━━━━
💡 *Apna fund nahi hai? Koi baat nahi!*

✅ Bahut kam price mein account
✅ Minimum rules — asaan pass
✅ Profit aapka — risk unka
✅ $10K se $200K tak ka account
✅ Gold, BTC, Forex sab milega

🎯 *Hamare signals se prop pass karo!*
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = [
        [InlineKeyboardButton("🚀 Abhi Join Karo", url=PROP_LINK)],
        [InlineKeyboardButton("👑 VIP Signals bhi lo", url=f"https://t.me/{VIP_USERNAME.replace('@', '')}")],
    ]
    await update.message.reply_text(prop_msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("prop", prop_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Scheduler
    scheduler = AsyncIOScheduler()

    # Auto signal - har 3 ghante (Mon-Fri 5M/15M scalping time pe)
    scheduler.add_job(auto_post_signal, "interval", minutes=1, args=[app])

    # TP Hit message - din mein 3 baar
    scheduler.add_job(auto_post_tp_hit, "cron", hour="10,14,18", minute=30, args=[app])

    scheduler.start()

    logger.info("🤖 TraderRahul Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
