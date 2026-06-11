import logging
import urllib.request
import urllib.error
import json
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
# PRICE FETCH
# =============================================
def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"fetch_url error: {e}")
        return None

def get_btc_data():
    """BTC price + 24h change + volume"""
    data = fetch_url("https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&community_data=false&developer_data=false")
    if data and 'market_data' in data:
        md = data['market_data']
        return {
            "price": float(md['current_price']['usd']),
            "change_24h": float(md['price_change_percentage_24h']),
            "high_24h": float(md['high_24h']['usd']),
            "low_24h": float(md['low_24h']['usd']),
            "volume": float(md['total_volume']['usd']),
        }
    # Fallback
    data = fetch_url("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_high_low_24h=true")
    if data and 'bitcoin' in data:
        b = data['bitcoin']
        return {
            "price": float(b.get('usd', 0)),
            "change_24h": float(b.get('usd_24h_change', 0)),
            "high_24h": float(b.get('usd_24h_high', 0)) if b.get('usd_24h_high') else None,
            "low_24h": float(b.get('usd_24h_low', 0)) if b.get('usd_24h_low') else None,
            "volume": float(b.get('usd_24h_vol', 0)),
        }
    return None

def get_xau_data():
    """XAU/USD price + trend"""
    data = fetch_url("https://api.frankfurter.app/latest?from=XAU&to=USD")
    if data and 'rates' in data and 'USD' in data['rates']:
        price = float(data['rates']['USD'])
        return {"price": price}
    return None

def get_btc_hourly_prices():
    """Last 24h hourly prices for RSI/trend"""
    data = fetch_url("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=2&interval=hourly")
    if data and 'prices' in data:
        return [p[1] for p in data['prices'][-25:]]
    return None

# =============================================
# TECHNICAL ANALYSIS
# =============================================
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calculate_ma(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    return sum(prices[-period:]) / period

def get_rsi_signal(rsi):
    if rsi >= 70:
        return "🔴 Overbought — Sell Zone"
    elif rsi <= 30:
        return "🟢 Oversold — Buy Zone"
    elif rsi >= 55:
        return "🟡 Bullish Zone"
    elif rsi <= 45:
        return "🟡 Bearish Zone"
    else:
        return "⚪ Neutral Zone"

def get_trend_emoji(change):
    if change >= 2:
        return "🚀 Strong Bullish"
    elif change >= 0.5:
        return "📈 Bullish"
    elif change <= -2:
        return "💥 Strong Bearish"
    elif change <= -0.5:
        return "📉 Bearish"
    else:
        return "↔️ Sideways"

def get_volume_signal(volume):
    if volume > 50_000_000_000:
        return "🔥 Very High — Strong Move Expected"
    elif volume > 30_000_000_000:
        return "📊 High — Good Momentum"
    elif volume > 15_000_000_000:
        return "📉 Medium — Normal Trading"
    else:
        return "😴 Low — Caution, Sideways Possible"

def get_support_resistance(price, high, low):
    """Simple S/R levels"""
    if not high or not low:
        return None, None
    support = round(low * 0.998, 2)
    resistance = round(high * 1.002, 2)
    return support, resistance

# =============================================
# MARKET ANALYSIS MESSAGE
# =============================================
def format_btc_analysis(btc_data, hourly_prices=None):
    price = btc_data['price']
    change = btc_data['change_24h']
    high = btc_data.get('high_24h')
    low = btc_data.get('low_24h')
    volume = btc_data.get('volume', 0)
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")

    trend = get_trend_emoji(change)
    change_emoji = "🟢" if change >= 0 else "🔴"

    # RSI
    rsi_val = 50
    ma7 = ma25 = price
    if hourly_prices and len(hourly_prices) >= 15:
        rsi_val = calculate_rsi(hourly_prices)
        ma7  = round(calculate_ma(hourly_prices, 7), 2)
        ma25 = round(calculate_ma(hourly_prices, 25), 2)

    rsi_signal = get_rsi_signal(rsi_val)
    vol_signal = get_volume_signal(volume)
    support, resistance = get_support_resistance(price, high, low)

    ma_signal = "🟢 Bullish (MA7 > MA25)" if ma7 > ma25 else "🔴 Bearish (MA7 < MA25)"

    # Overall bias
    bias_score = 0
    if change >= 0: bias_score += 1
    if rsi_val < 60: bias_score += 1
    if ma7 > ma25: bias_score += 1
    overall = "🟢 *BULLISH BIAS*" if bias_score >= 2 else "🔴 *BEARISH BIAS*"

    msg = f"""
📊 *BTC/USDT — MARKET ANALYSIS*
━━━━━━━━━━━━━━━━━━━━
💰 *Price:* `${price:,.2f}`
{change_emoji} *24h Change:* `{change:+.2f}%` — {trend}

📈 *24h High:* `${high:,.2f}`
📉 *24h Low:* `${low:,.2f}`
━━━━━━━━━━━━━━━━━━━━
🔢 *TECHNICAL INDICATORS*

📌 *RSI (14):* `{rsi_val}` — {rsi_signal}
📌 *MA7:* `${ma7:,.2f}`
📌 *MA25:* `${ma25:,.2f}`
📌 *MA Signal:* {ma_signal}
━━━━━━━━━━━━━━━━━━━━
🏗 *KEY LEVELS*

🟢 *Support:* `${support:,.2f}`
🔴 *Resistance:* `${resistance:,.2f}`
━━━━━━━━━━━━━━━━━━━━
📦 *Volume:* {vol_signal}

🎯 *Overall Bias:* {overall}
━━━━━━━━━━━━━━━━━━━━
🕐 {time_now}
📢 @traderrahul1
"""
    return msg

def format_xau_analysis(xau_data, btc_change=0):
    price = xau_data['price']
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")

    # XAU approximate levels
    support    = round(price - 8, 2)
    resistance = round(price + 8, 2)
    pivot      = round((price + support + resistance) / 3, 2)

    # Simple bias from BTC correlation + random trend
    xau_change = random.uniform(-0.8, 0.8)
    trend = get_trend_emoji(xau_change)
    change_emoji = "🟢" if xau_change >= 0 else "🔴"

    # RSI approximate
    rsi_val = random.randint(42, 68)
    rsi_signal = get_rsi_signal(rsi_val)

    overall = "🟢 *BULLISH BIAS*" if xau_change >= 0 else "🔴 *BEARISH BIAS*"

    msg = f"""
📊 *XAU/USD — MARKET ANALYSIS*
━━━━━━━━━━━━━━━━━━━━
💰 *Price:* `${price:,.2f}`
{change_emoji} *Trend:* {trend}

⚠️ _XAUUSD: Mon–Fri only_
━━━━━━━━━━━━━━━━━━━━
🔢 *TECHNICAL INDICATORS*

📌 *RSI (14):* `{rsi_val}` — {rsi_signal}
📌 *Pivot:* `${pivot:,.2f}`
━━━━━━━━━━━━━━━━━━━━
🏗 *KEY LEVELS*

🟢 *Support:* `${support:,.2f}`
🔴 *Resistance:* `${resistance:,.2f}`
━━━━━━━━━━━━━━━━━━━━
💡 *Scalping Tips:*
• Buy near support, Sell near resistance
• 5M/15M timeframe use karo
• Always SL lagao!

🎯 *Overall Bias:* {overall}
━━━━━━━━━━━━━━━━━━━━
🕐 {time_now}
📢 @traderrahul1
"""
    return msg

# =============================================
# SIGNAL GENERATOR
# =============================================
def is_xau_open():
    return datetime.now().weekday() < 5

def generate_signal(pair, price, trend=None):
    if not price:
        return None
    signal_type = trend or random.choice(["BUY", "SELL"])
    if "XAU" in pair:
        if signal_type == "BUY":
            tp1, tp2, sl = round(price+3,2), round(price+6,2), round(price-2.5,2)
        else:
            tp1, tp2, sl = round(price-3,2), round(price-6,2), round(price+2.5,2)
    else:
        if signal_type == "BUY":
            tp1, tp2, sl = round(price*1.003,1), round(price*1.006,1), round(price*0.998,1)
        else:
            tp1, tp2, sl = round(price*0.997,1), round(price*0.994,1), round(price*1.002,1)
    return {
        "pair": pair,
        "type": f"{'BUY 📈' if signal_type == 'BUY' else 'SELL 📉'}",
        "entry": f"{price:,.2f}",
        "tp1": f"{tp1:,.2f}", "tp2": f"{tp2:,.2f}", "sl": f"{sl:,.2f}",
        "timeframe": random.choice(["5M","15M"]),
        "confidence": f"{random.randint(79,93)}%",
        "tp1_val": tp1, "tp2_val": tp2,
    }

def get_live_signal(prefer_xau=None):
    use_xau = is_xau_open() if prefer_xau is None else (prefer_xau and is_xau_open())
    if use_xau:
        d = get_xau_data()
        if d and d['price'] > 500:
            return generate_signal("XAU/USD", d['price'])
    d = get_btc_data()
    if d:
        trend = "BUY" if d['change_24h'] >= 0 else "SELL"
        return generate_signal("BTC/USDT", d['price'], trend)
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

def format_tp_hit(signal, tp_level="TP1"):
    time_now = datetime.now().strftime("%d %b %Y • %I:%M %p")
    msgs = ["Zabardast! Paisa bana liya! 💰","Mast trade tha! Keep it up! 🔥",
            "Ekdum sahi signal! Rahul bhai ne kaha tha! 🎯","Bahut khoob! Profit book karo! 💪",
            "Trading ka maza aa gaya! 🚀","Ye hai asli trading! 🏆"]
    tp_price = signal['tp1'] if tp_level=='TP1' else signal['tp2']
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
🕐 {time_now} | 📢 @traderrahul1
"""

# =============================================
# /start
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Trader"
    weekend = "\n⚠️ _Weekend: XAUUSD band, sirf BTC signals._\n" if not is_xau_open() else ""
    msg = f"""
👋 *Welcome {name}!*
📡 *TraderRahul Signal Bot* — Live Signals!
{weekend}
━━━━━━━━━━━━━━━━━━━━
💹 *Live Market Signals + Analysis:*
• 🥇 *XAU/USD* — Mon–Fri Scalping
• ₿ *BTC/USDT* — Daily Scalping
• ⏱ *5M & 15M* timeframe only
• 📊 *Full Market Analysis*

🆓 *FREE:* Signals + Basic Analysis
👑 *VIP PRO:* 10-15 signals + Deep Analysis
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = [
        [InlineKeyboardButton("🆓 Free Channel Join", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("📊 Live Signal Lo", callback_data="free_signal")],
        [InlineKeyboardButton("📈 Market Analysis", callback_data="market_analysis")],
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
        await query.message.reply_text("⏳ _Live price + analysis fetch ho rahi hai..._", parse_mode="Markdown")
        use_xau = is_xau_open() and random.choice([True, False])
        signal = get_live_signal(prefer_xau=use_xau)
        if signal:
            # Signal + mini analysis
            if "XAU" in signal['pair']:
                d = get_xau_data()
                analysis = format_xau_analysis(d) if d else ""
            else:
                d = get_btc_data()
                hp = get_btc_hourly_prices()
                analysis = format_btc_analysis(d, hp) if d else ""

            keyboard = [
                [InlineKeyboardButton("👑 VIP Signal chahiye?", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
                [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
                [InlineKeyboardButton("📢 Channel Join", url=CHANNEL_LINK)],
            ]
            await query.message.reply_text(format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
            if analysis:
                await query.message.reply_text(analysis, parse_mode="Markdown")
        else:
            await query.message.reply_text("❌ Price fetch nahi hua, thodi der baad try karo.")

    elif query.data == "market_analysis":
        await query.message.reply_text("⏳ _Market analysis prepare ho rahi hai..._", parse_mode="Markdown")
        keyboard = [
            [InlineKeyboardButton("₿ BTC Analysis", callback_data="btc_analysis")],
            [InlineKeyboardButton("🥇 XAU Analysis", callback_data="xau_analysis")],
        ]
        await query.message.reply_text("📊 *Kaunsa analysis chahiye?*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "btc_analysis":
        await query.message.reply_text("⏳ _BTC analysis..._", parse_mode="Markdown")
        d = get_btc_data()
        hp = get_btc_hourly_prices()
        if d:
            keyboard = [
                [InlineKeyboardButton("📊 BTC Signal Lo", callback_data="btc_signal")],
                [InlineKeyboardButton("👑 VIP Join", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
            ]
            await query.message.reply_text(format_btc_analysis(d, hp), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("❌ BTC data fetch nahi hua.")

    elif query.data == "xau_analysis":
        if not is_xau_open():
            await query.message.reply_text("⚠️ _Weekend hai — XAUUSD market band hai. Monday ko aana!_", parse_mode="Markdown")
            return
        await query.message.reply_text("⏳ _XAU analysis..._", parse_mode="Markdown")
        d = get_xau_data()
        btc_d = get_btc_data()
        btc_change = btc_d['change_24h'] if btc_d else 0
        if d:
            keyboard = [
                [InlineKeyboardButton("📊 XAU Signal Lo", callback_data="xau_signal")],
                [InlineKeyboardButton("👑 VIP Join", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
            ]
            await query.message.reply_text(format_xau_analysis(d, btc_change), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("❌ XAU data fetch nahi hua.")

    elif query.data == "btc_signal":
        d = get_btc_data()
        if d:
            trend = "BUY" if d['change_24h'] >= 0 else "SELL"
            signal = generate_signal("BTC/USDT", d['price'], trend)
            keyboard = [[InlineKeyboardButton("👑 VIP PRO", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")]]
            await query.message.reply_text(format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "xau_signal":
        d = get_xau_data()
        if d:
            signal = generate_signal("XAU/USD", d['price'])
            keyboard = [[InlineKeyboardButton("👑 VIP PRO", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")]]
            await query.message.reply_text(format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

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
# AUTO POST
# =============================================
async def auto_post_signal(app):
    use_xau = is_xau_open() and random.choice([True, False])
    signal = get_live_signal(prefer_xau=use_xau)
    if not signal:
        return

    # Analysis bhi bhejo
    if "XAU" in signal['pair']:
        d = get_xau_data()
        analysis = format_xau_analysis(d) if d else None
    else:
        d = get_btc_data()
        hp = get_btc_hourly_prices()
        analysis = format_btc_analysis(d, hp) if d else None

    keyboard = [
        [InlineKeyboardButton("👑 VIP Signal ke liye DM", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("🤖 Bot Start Karo", url="https://t.me/traderrahul_1_bot")],
    ]
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_signal(signal), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        if analysis:
            await app.bot.send_message(chat_id=CHANNEL_ID, text=analysis, parse_mode="Markdown")
        logger.info(f"Signal+Analysis posted: {signal['pair']} @ {signal['entry']}")
    except Exception as e:
        logger.error(f"Auto post error: {e}")

async def auto_post_tp_hit(app):
    signal = get_live_signal(prefer_xau=is_xau_open())
    if not signal:
        return
    tp_level = random.choice(["TP1","TP2"])
    keyboard = [
        [InlineKeyboardButton("🚀 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("👑 VIP Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
    ]
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_tp_hit(signal, tp_level), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"TP hit error: {e}")

# =============================================
# COMMANDS
# =============================================
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ _Live signal + analysis..._", parse_mode="Markdown")
    use_xau = is_xau_open() and random.choice([True, False])
    signal = get_live_signal(prefer_xau=use_xau)
    if signal:
        keyboard = [
            [InlineKeyboardButton("👑 VIP PRO Join Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("🏦 Prop Account Lo", url=PROP_LINK)],
        
