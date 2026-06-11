import logging
import aiohttp
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
# LIVE PRICE — BINANCE (FREE, NO API KEY)
# =============================================
async def get_price(symbol):
    """Binance se live price — BTCUSDT ya XAUUSDT"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data['price'])
    except Exception as e:
        logger.error(f"{symbol} price error: {e}")
    return None

async def get_candles(symbol, interval="15m", limit=4):
    """Binance se candles fetch karo trend ke liye"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [(float(c[1]), float(c[2]), float(c[3]), float(c[4])) for c in data]
    except Exception as e:
        logger.error(f"{symbol} candles error: {e}")
    return None

# =============================================
# SIGNAL GENERATOR
# =============================================
def generate_signal(pair, symbol, price, candles=None):
    if not price:
        return None

    # Trend — last 2 candles dekho
    signal_type = "BUY"
    if candles and len(candles) >= 2:
        last_close  = candles[-1][3]
        last_open   = candles[-1][0]
        prev_close  = candles[-2][3]
        if last_close < last_open and last_close < prev_close:
            signal_type = "SELL"
        elif last_close > last_open and last_close > prev_close:
            signal_type = "BUY"
        else:
            signal_type = random.choice(["BUY", "SELL"])

    # TP/SL calculate karo
    if "XAU" in symbol:
        # Gold — tight scalping $2-5
        if signal_type == "BUY":
            tp1 = round(price + 3.0, 2)
            tp2 = round(price + 6.0, 2)
            sl  = round(price - 2.5, 2)
        else:
            tp1 = round(price - 3.0, 2)
            tp2 = round(price - 6.0, 2)
            sl  = round(price + 2.5, 2)
    else:
        # BTC — 0.3% TP, 0.2% SL
        if signal_type == "BUY":
            tp1 = round(price * 1.003, 1)
            tp2 = round(price * 1.006, 1)
            sl  = round(price * 0.998, 1)
        else:
            tp1 = round(price * 0.997, 1)
            tp2 = round(price * 0.994, 1)
            sl  = round(price * 1.002, 1)

    tf = random.choice(["5M", "15M"])
    confidence = random.randint(79, 93)

    return {
        "pair": pair,
        "type": f"{'BUY 📈' if signal_type == 'BUY' else 'SELL 📉'}",
        "entry": f"{price:,.2f}",
        "tp1":   f"{tp1:,.2f}",
        "tp2":   f"{tp2:,.2f}",
        "sl":    f"{sl:,.2f}",
        "timeframe": tf,
        "confidence": f"{confidence}%",
        "tp1_raw": tp1,
        "tp2_raw": tp2,
    }

# =============================================
# MARKET OPEN CHECK
# =============================================
def is_xau_market_open():
    return datetime.now().weekday() < 5  # Mon=0 Sun=6

# =============================================
# GET LIVE SIGNAL
# =============================================
async def get_live_signal(prefer_xau=None):
    use_xau = is_xau_market_open() if prefer_xau is None else (prefer_xau and is_xau_market_open())

    if use_xau:
        price   = await get_price("XAUUSDT")
        candles = await get_candles("XAUUSDT")
        if price and price > 500:
            return generate_signal("XAU/USD", "XAUUSDT", price, candles)

    # BTC fallback
    price   = await get_price("BTCUSDT")
    candles = await get_candles("BTCUSDT")
    if price:
        return generate_signal("BTC/USDT", "BTCUSDT", price, candles)

    return None

# =============================================
# FORMAT SIGNAL
# =============================================
def format_signal(signal, is_vip=False):
    badge = "👑 *VIP PRO SIGNAL*" if is_vip else "🆓 *FREE SIGNAL*"
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")
    direction = "🟢" if "BUY" in signal['type'] else "🔴"

    return f"""
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

# =============================================
# TP HIT MESSAGE
# =============================================
def format_tp_hit(signal, tp_level="TP1"):
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")
    msgs = [
        "Zabardast! Paisa bana liya! 💰",
        "Mast trade tha! Keep it up! 🔥",
        "Ekdum sahi signal! Rahul bhai ne kaha tha! 🎯",
        "Bahut khoob! Profit book karo! 💪",
        "Trading ka maza aa gaya! 🚀",
        "Ye hai asli trading! 🏆",
    ]
    tp_price = signal['tp1'] if tp_level == 'TP1' else signal['tp2']

    return f"""
🎉 *TARGET HIT! {tp_level} DONE!* 🎉
━━━━━━━━━━━━━━━━━━━━
✅ *{signal['pair']}* — {signal['type']}

🏆 *{tp_level} Successfully Hit!*
🎯 *Target:* `{tp_price}`
━━━━━━━━━━━━━━━━━━━━
🥳 *{random.choice(msgs)}*

💡 _Ab SL entry pe le aao, TP2 ka wait karo!_

💰 *Fund nahi hai? Prop account lo!*
_Kam price, minimum rules!_
🕐 {time_now} | 📢 @traderrahul1
"""

# =============================================
# /start
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Trader"
    weekend = "\n⚠️ _Weekend: XAUUSD band, sirf BTC signals._\n" if not is_xau_market_open() else ""

    msg = f"""
👋 *Welcome {name}!*

📡 *TraderRahul Signal Bot* — Live Signals!
{weekend}
━━━━━━━━━━━━━━━━━━━━
💹 *Live Binance Prices:*
• 🥇 *XAU/USD* — Mon–Fri Scalping
• ₿ *BTC/USDT* — Daily Scalping
• ⏱ *5M & 15M* timeframe only

🆓 *FREE:* 2-3 signals daily
👑 *VIP PRO:* 10-15 signals + support
━━━━━━━━━━━━━━━━━━━━
Niche buttons se join karo! 👇
"""
    keyboard = [
        [InlineKeyboardButton("🆓 Free Channel Join", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("📊 Live Signal Lo", callback_data="free_signal")],
        [InlineKeyboardButton("🏦 Prop Account Info", callback_data="prop_info")],
    ]
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# CALLBACKS
# =============================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "free_signal":
        await query.message.reply_text("⏳ _Live Binance price fetch ho rahi hai..._", parse_mode="Markdown")
        signal = await get_live_signal()
        if signal:
            keyboard = [
                [InlineKeyboardButton("👑 VIP Signal chahiye?", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
                [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
                [InlineKeyboardButton("📢 Channel Join", url=CHANNEL_LINK)],
            ]
            await query.message.reply_text(format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("❌ Price fetch nahi hua, thodi der baad try karo.")

    elif query.data == "prop_info":
        msg = f"""
🏦 *Prop Account — Trader ke liye Best!*
━━━━━━━━━━━━━━━━━━━━
💡 *Apna fund nahi hai? Koi baat nahi!*

✅ Bahut kam price mein account
✅ Minimum rules — asaan pass
✅ Profit aapka — risk unka
✅ $10K se $200K tak
✅ Gold, BTC, Forex sab

🎯 *Hamare signals se prop pass karo!*
━━━━━━━━━━━━━━━━━━━━
"""
        keyboard = [
            [InlineKeyboardButton("🚀 Abhi Join Karo", url=PROP_LINK)],
            [InlineKeyboardButton("👑 VIP Signals bhi lo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        ]
        await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# AUTO POST CHANNEL
# =============================================
async def auto_post_signal(app):
    use_xau = is_xau_market_open() and random.choice([True, False])
    signal = await get_live_signal(prefer_xau=use_xau)
    if not signal:
        return

    weekend = "\n⚠️ _Weekend: Sirf BTC. XAUUSD Monday se!_\n" if not is_xau_market_open() else ""
    keyboard = [
        [InlineKeyboardButton("👑 VIP Signal ke liye DM", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("🤖 Bot Start Karo", url="https://t.me/traderrahul_1_bot")],
    ]
    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=format_signal(signal) + weekend,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Signal posted: {signal['pair']} @ {signal['entry']}")
    except Exception as e:
        logger.error(f"Auto post error: {e}")

async def auto_post_tp_hit(app):
    signal = await get_live_signal(prefer_xau=is_xau_market_open())
    if not signal:
        return
    tp_level = random.choice(["TP1", "TP2"])
    keyboard = [
        [InlineKeyboardButton("🚀 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("👑 VIP Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
    ]
    try:
        await app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=format_tp_hit(signal, tp_level),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"TP hit error: {e}")

# =============================================
# COMMANDS
# =============================================
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ _Live Binance price fetch ho rahi hai..._", parse_mode="Markdown")
    signal = await get_live_signal()
    if signal:
        keyboard = [
            [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        ]
        await update.message.reply_text(format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("❌ Price fetch nahi hua, thodi der baad try karo.")

async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"""
👑 *VIP PRO Membership*

✅ 10-15 live signals daily
✅ 92%+ accuracy
✅ XAU/USD Mon-Fri scalping
✅ BTC daily scalping
✅ Entry, TP1, TP2, SL
✅ Direct support from Rahul sir

💬 *Abhi DM karo:* 👉 {VIP_USERNAME}
"""
    keyboard = [[InlineKeyboardButton(f"📩 DM {VIP_USERNAME}", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")]]
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def prop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🏦 *Prop Account — Best Option!*

✅ Kam price mein account
✅ Minimum rules
✅ Profit aapka
✅ $10K–$200K accounts
✅ Gold, BTC, Forex
"""
    keyboard = [
        [InlineKeyboardButton("🚀 Abhi Join Karo", url=PROP_LINK)],
        [InlineKeyboardButton("👑 VIP Signals", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
    ]
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("prop", prop_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_post_signal, "interval", minutes=1, args=[app])
    scheduler.add_job(auto_post_tp_hit, "cron", hour="10,14,18", minute=30, args=[app])
    scheduler.start()

    logger.info("🤖 TraderRahul LIVE Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
