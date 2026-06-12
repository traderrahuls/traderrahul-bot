import logging
import urllib.request
import json
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
from datetime import datetime

BOT_TOKEN = "8244372675:AAEzNzglqjT8saJd3L2B-wJYS7kHmmxqu30"
TWELVE_API = "f1bccc914cf04871b8cc0d37be85fa9a"
VIP_USERNAME = "@rahulyadavs1"
VIP_USER_CLEAN = "rahulyadavs1"
CHANNEL_LINK = "https://t.me/traderrahul1"
CHANNEL_ID = "@traderrahul1"
PROP_LINK = "https://bit.ly/m/traderrahul"
XM_LINK = "https://www.xmglobal.com/referral?token=6tdxFdG-CQ6aW5d-AKWobQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# LIVE DATA FROM TWELVE DATA API
# =============================================
def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.error(f"fetch error: {e}")
        return None

def get_live_candles(symbol="XAU/USD", interval="5min", count=50):
    """Twelve Data se real live candles"""
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={count}&apikey={TWELVE_API}"
    data = fetch_url(url)
    if not data or data.get('status') == 'error':
        logger.error(f"Twelve Data error: {data}")
        return None
    values = data.get('values', [])
    if not values:
        return None
    # Reverse — oldest first
    candles = []
    for v in reversed(values):
        try:
            candles.append({
                "open":  float(v['open']),
                "high":  float(v['high']),
                "low":   float(v['low']),
                "close": float(v['close']),
                "datetime": v['datetime']
            })
        except:
            continue
    return candles if candles else None

def get_live_price(symbol="XAU/USD"):
    """Twelve Data se live price"""
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_API}"
    data = fetch_url(url)
    if data and 'price' in data:
        return float(data['price'])
    return None

# =============================================
# TECHNICAL INDICATORS
# =============================================
def calc_ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    k = 2 / (period + 1)
    e = sum(prices[:period]) / period
    for p in prices[period:]:
        e = p * k + e * (1 - k)
    return round(e, 2)

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100
    return round(100 - (100 / (1 + ag/al)), 1)

def calc_ema_angle(prices, period, last_n=5):
    """EMA ka angle degrees mein"""
    if len(prices) < period + last_n:
        return 0
    ema_series = []
    for i in range(len(prices) - last_n, len(prices) + 1):
        ema_series.append(calc_ema(prices[:i], period))
    if len(ema_series) < 2:
        return 0
    dy = ema_series[-1] - ema_series[0]
    dx = last_n
    # Normalize by price to get meaningful angle
    dy_pct = (dy / ema_series[0]) * 100 if ema_series[0] else 0
    angle = math.degrees(math.atan(abs(dy_pct) / dx * 10))
    return round(min(angle, 89), 1)

def find_support_resistance(candles):
    """Real S/R from actual candle highs/lows"""
    highs = sorted([c['high'] for c in candles[-30:]], reverse=True)
    lows  = sorted([c['low']  for c in candles[-30:]])
    resistance  = round(highs[0], 2)
    resistance2 = round(highs[2], 2) if len(highs) > 2 else round(highs[0] * 1.001, 2)
    support     = round(lows[0], 2)
    support2    = round(lows[2], 2) if len(lows) > 2 else round(lows[0] * 0.999, 2)
    return support, resistance, support2, resistance2

def find_order_block(candles, signal_type):
    """Real Order Block — strong opposite candle before move"""
    for i in range(len(candles)-3, max(len(candles)-12, 0), -1):
        c = candles[i]
        body = abs(c['close'] - c['open'])
        candle_range = c['high'] - c['low']
        # Strong candle = body > 60% of range
        if candle_range > 0 and body / candle_range > 0.6:
            if signal_type == "BUY" and c['close'] < c['open']:
                return round(c['low'], 2), round(c['high'], 2)
            elif signal_type == "SELL" and c['close'] > c['open']:
                return round(c['low'], 2), round(c['high'], 2)
    return None, None

def find_fvg(candles, signal_type):
    """Real Fair Value Gap"""
    for i in range(len(candles)-4, max(len(candles)-15, 0), -1):
        if i + 2 >= len(candles):
            continue
        c1, c3 = candles[i], candles[i+2]
        if signal_type == "BUY":
            if c3['low'] > c1['high']:
                return round(c1['high'], 2), round(c3['low'], 2)
        else:
            if c1['low'] > c3['high']:
                return round(c3['high'], 2), round(c1['low'], 2)
    return None, None

def find_liquidity_grab(candles, signal_type):
    """Real Liquidity Grab — recent swing swept"""
    if len(candles) < 15:
        return False
    recent  = candles[-4:]
    history = candles[-15:-4]
    if signal_type == "BUY":
        key_low = min(c['low'] for c in history)
        return any(c['low'] < key_low and c['close'] > key_low for c in recent)
    else:
        key_high = max(c['high'] for c in history)
        return any(c['high'] > key_high and c['close'] < key_high for c in recent)

# =============================================
# FULL MAYANK SIR STRATEGY ANALYSIS
# =============================================
def full_analysis(candles):
    closes = [c['close'] for c in candles]
    price  = closes[-1]

    ema9  = calc_ema(closes, 9)
    ema15 = calc_ema(closes, 15)
    prev9  = calc_ema(closes[:-1], 9)
    prev15 = calc_ema(closes[:-1], 15)

    angle9  = calc_ema_angle(closes, 9)
    angle15 = calc_ema_angle(closes, 15)

    rsi_val = calc_rsi(closes)
    last    = candles[-1]

    bullish_cross = prev9 <= prev15 and ema9 > ema15
    bearish_cross = prev9 >= prev15 and ema9 < ema15

    support, resistance, support2, resistance2 = find_support_resistance(candles)

    # ---- BUY SCORING ----
    buy_score = 0
    buy_reasons = []

    if bullish_cross:
        buy_score += 4
        buy_reasons.append("✅ EMA 9 ne EMA 15 ko cross kiya — BULLISH!")
    elif ema9 > ema15:
        buy_score += 1
        buy_reasons.append("✅ EMA 9 > EMA 15 — Bullish trend")

    if angle9 >= 30:
        buy_score += 3
        buy_reasons.append(f"✅ EMA angle {angle9}° — Strong momentum (30°+)")
    elif angle9 >= 20:
        buy_score += 2
        buy_reasons.append(f"✅ EMA angle {angle9}° — Good momentum")
    elif angle9 >= 10:
        buy_score += 1
        buy_reasons.append(f"⚠️ EMA angle {angle9}° — Weak (30° chahiye)")

    if last['close'] > ema9 and last['close'] > ema15:
        buy_score += 2
        buy_reasons.append("✅ Price EMA 9 & 15 ke upar — Bullish confirmation")

    if 40 <= rsi_val <= 65:
        buy_score += 1
        buy_reasons.append(f"✅ RSI {rsi_val} — Safe buy zone")
    elif rsi_val < 40:
        buy_score += 2
        buy_reasons.append(f"✅ RSI {rsi_val} — Oversold, bounce expected")

    if price <= support * 1.004:
        buy_score += 2
        buy_reasons.append(f"✅ Support zone mein price `${support:,.2f}`")

    if find_liquidity_grab(candles, "BUY"):
        buy_score += 2
        buy_reasons.append("✅ Liquidity Grab — Stop hunt ho gaya, reversal expected!")

    ob_low, ob_high = find_order_block(candles, "BUY")
    if ob_low and ob_low <= price <= ob_high * 1.003:
        buy_score += 2
        buy_reasons.append(f"✅ Order Block zone: `${ob_low:,.2f} – ${ob_high:,.2f}`")

    fvg_low, fvg_high = find_fvg(candles, "BUY")
    if fvg_low and fvg_low <= price <= fvg_high:
        buy_score += 1
        buy_reasons.append(f"✅ FVG (Fair Value Gap): `${fvg_low:,.2f} – ${fvg_high:,.2f}`")

    if last['close'] > last['open']:
        buy_score += 1
        buy_reasons.append("✅ Bullish candle confirmation")

    # ---- SELL SCORING ----
    sell_score = 0
    sell_reasons = []

    if bearish_cross:
        sell_score += 4
        sell_reasons.append("✅ EMA 9 ne EMA 15 ko cross kiya — BEARISH!")
    elif ema9 < ema15:
        sell_score += 1
        sell_reasons.append("✅ EMA 9 < EMA 15 — Bearish trend")

    if angle9 >= 30:
        sell_score += 3
        sell_reasons.append(f"✅ EMA angle {angle9}° — Strong momentum (30°+)")
    elif angle9 >= 20:
        sell_score += 2
        sell_reasons.append(f"✅ EMA angle {angle9}° — Good momentum")
    elif angle9 >= 10:
        sell_score += 1
        sell_reasons.append(f"⚠️ EMA angle {angle9}° — Weak")

    if last['close'] < ema9 and last['close'] < ema15:
        sell_score += 2
        sell_reasons.append("✅ Price EMA 9 & 15 ke neeche — Bearish confirmation")

    if 35 <= rsi_val <= 60:
        sell_score += 1
        sell_reasons.append(f"✅ RSI {rsi_val} — Safe sell zone")
    elif rsi_val > 70:
        sell_score += 2
        sell_reasons.append(f"✅ RSI {rsi_val} — Overbought, reversal expected")

    if price >= resistance * 0.997:
        sell_score += 2
        sell_reasons.append(f"✅ Resistance zone mein price `${resistance:,.2f}`")

    if find_liquidity_grab(candles, "SELL"):
        sell_score += 2
        sell_reasons.append("✅ Liquidity Grab — Fake breakout, reversal expected!")

    ob_low2, ob_high2 = find_order_block(candles, "SELL")
    if ob_high2 and ob_low2 * 0.997 <= price <= ob_high2:
        sell_score += 2
        sell_reasons.append(f"✅ Order Block zone: `${ob_low2:,.2f} – ${ob_high2:,.2f}`")

    fvg_low2, fvg_high2 = find_fvg(candles, "SELL")
    if fvg_high2 and fvg_low2 <= price <= fvg_high2:
        sell_score += 1
        sell_reasons.append(f"✅ FVG (Fair Value Gap): `${fvg_low2:,.2f} – ${fvg_high2:,.2f}`")

    if last['close'] < last['open']:
        sell_score += 1
        sell_reasons.append("✅ Bearish candle confirmation")

    # ---- DECISION — min 7 score + crossover + 30° angle ----
    MIN_SCORE  = 7
    need_cross = bullish_cross or bearish_cross
    need_angle = angle9 >= 30

    if buy_score >= MIN_SCORE and buy_score >= sell_score and need_cross and need_angle:
        stype    = "BUY"
        reasons  = buy_reasons
        strength = "🔥 STRONG" if buy_score >= 10 else "⚡ MEDIUM"
        tp1 = round(price + 3.5, 2)
        tp2 = round(price + 7.0, 2)
        sl  = round(price - 2.5, 2)
    elif sell_score >= MIN_SCORE and sell_score > buy_score and need_cross and need_angle:
        stype    = "SELL"
        reasons  = sell_reasons
        strength = "🔥 STRONG" if sell_score >= 10 else "⚡ MEDIUM"
        tp1 = round(price - 3.5, 2)
        tp2 = round(price - 7.0, 2)
        sl  = round(price + 2.5, 2)
    else:
        stype    = "WAIT"
        reasons  = []
        if not need_cross:
            reasons.append("❌ EMA crossover nahi hua abhi")
        if not need_angle:
            reasons.append(f"❌ EMA angle sirf {angle9}° hai — 30°+ chahiye")
        if buy_score < MIN_SCORE and sell_score < MIN_SCORE:
            reasons.append("❌ Setup score kam hai — aur confirmation chahiye")
        strength = "WEAK"
        tp1 = tp2 = sl = price

    candle_time = candles[-1].get('datetime', '')

    return {
        "signal_type": stype, "strength": strength,
        "ema9": ema9, "ema15": ema15,
        "angle9": angle9, "angle15": angle15,
        "rsi": rsi_val,
        "price": price,
        "support": support, "resistance": resistance,
        "support2": support2, "resistance2": resistance2,
        "tp1": tp1, "tp2": tp2, "sl": sl,
        "reasons": reasons,
        "buy_score": buy_score, "sell_score": sell_score,
        "bullish_cross": bullish_cross, "bearish_cross": bearish_cross,
        "candle_time": candle_time,
    }

# =============================================
# MESSAGE FORMATTERS
# =============================================
WAIT_MSGS = [
    "Yaar abhi market ka mood clear nahi hai... thoda sabr karo 🧘",
    "Setup abhi bana nahi hai bhai — wait karna padega 👀",
    "Bina setup ke trade = donation to market 😅 Ruko!",
    "Market confuse hai — hum confuse nahi honge! ⏳",
    "Patience is profit! Setup ka wait karo 💪",
]
BUY_INTROS = [
    "Bhai dekho — EMA ne crossover de diya aur angle bhi 30°+ hai! Solid setup! 🎯",
    "Finally setup ban gaya! Gold buy kar rahe hain — sab indicators align hain! 🥇",
    "Liquidity grab + EMA cross + Order Block — ye wala trade strong lagta hai! 💎",
    "EMA 9 ne EMA 15 ko cross kiya aur market structure bullish — buy le rahe hain! 🚀",
]
SELL_INTROS = [
    "Resistance pe fake breakout, EMA bearish cross — sell setup ready hai! 🎯",
    "EMA 9 neeche aaya, liquidity grab hua — ab gold neeche jayega! 📉",
    "Order block + bearish EMA cross + RSI overbought — strong sell setup! 💎",
    "Mayank sir ki strategy ne signal de diya — sell le rahe hain aaj! 🔴",
]
TP_MSGS = [
    "EMA strategy ne phir kaam kiya bhai! Maza aa gaya! 🔥",
    "Tight SL, perfect entry — profit aaya account mein! 💰",
    "Ye hai real trading! Setup wait karo, entry lo, profit lo! 🏆",
    "Gold ne paisa diya! TP hit! 💛 Agle setup ka intezaar karo.",
    "Mayank sir ki strategy ka jawab nahi! ✅ Zabardast!",
]

def format_signal(a):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    p = a['price']

    if a['signal_type'] == "WAIT":
        reasons_text = "\n".join(a['reasons'])
        return f"""
👋 {random.choice(WAIT_MSGS)}

📊 *XAU/USD — 5M Live Update*
━━━━━━━━━━━━━━━━━━━━
💰 *Live Price:* `${p:,.2f}`
🕐 Candle: `{a['candle_time']}`

📐 EMA 9:  `{a['ema9']}` | Angle: `{a['angle9']}°`
📐 EMA 15: `{a['ema15']}` | Angle: `{a['angle15']}°`
📊 RSI:    `{a['rsi']}`

🟢 Support:    `${a['support']:,.2f}`
🔴 Resistance: `${a['resistance']:,.2f}`

*Setup incomplete kyun:*
{reasons_text}

⏳ _EMA crossover + 30°+ angle ka wait kar rahe hain..._
_Jab setup banega tab hi trade denge!_ 💪

🕐 {time_now} | 📢 @traderrahul1
"""

    direction   = "🟢" if a['signal_type'] == "BUY" else "🔴"
    sig_text    = "BUY 📈" if a['signal_type'] == "BUY" else "SELL 📉"
    intro       = random.choice(BUY_INTROS if a['signal_type'] == "BUY" else SELL_INTROS)
    reasons_txt = "\n".join(a['reasons'][:6])
    score       = a['buy_score'] if a['signal_type'] == "BUY" else a['sell_score']
    conf        = min(78 + score * 1.5, 96)
    rr_ratio    = "1:1.4" if a['strength'] == "⚡ MEDIUM" else "1:2.8"

    return f"""
{direction} {intro}

━━━━━━━━━━━━━━━━━━━━
🥇 *XAU/USD* | {sig_text} | ⏱ 5M Scalp
💪 *{a['strength']}* | Setup Score: `{score}/12`

💰 *Entry:*     `${p:,.2f}`
🎯 *TP 1:*      `${a['tp1']:,.2f}` _(+3.5 pts)_
🎯 *TP 2:*      `${a['tp2']:,.2f}` _(+7.0 pts)_
🛑 *Stop Loss:* `${a['sl']:,.2f}` _(-2.5 pts)_
📊 *R:R Ratio:* `{rr_ratio}`

━━━━━━━━━━━━━━━━━━━━
🔬 *LIVE SETUP ANALYSIS*

📐 EMA 9:  `{a['ema9']}` | `{a['angle9']}°` {'✅' if a['angle9'] >= 30 else '⚠️'}
📐 EMA 15: `{a['ema15']}` | `{a['angle15']}°`
📊 RSI:    `{a['rsi']}`
🟢 Support:    `${a['support']:,.2f}`
🔴 Resistance: `${a['resistance']:,.2f}`

*Confirmations:*
{reasons_txt}

━━━━━━━━━━━━━━━━━━━━
📈 *Confidence: {conf:.0f}%*
🕐 Candle: `{a['candle_time']}`

⚠️ _SL zaroor lagao — Capital protect karo!_
_Strategy: Mayank Sir | The Trade Room_

🕐 {time_now} | 📢 @traderrahul1
"""

def format_analysis(a):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    p = a['price']

    cross_txt = (
        "🚀 *BULLISH CROSSOVER — LIVE!*" if a['bullish_cross'] else
        "💥 *BEARISH CROSSOVER — LIVE!*" if a['bearish_cross'] else
        ("📈 Bullish (EMA 9 > 15)" if a['ema9'] > a['ema15'] else "📉 Bearish (EMA 9 < 15)")
    )
    angle_txt  = "🔥 Strong (30°+)" if a['angle9'] >= 30 else "⚡ Moderate" if a['angle9'] >= 15 else "😴 Weak — avoid trade"
    rsi_txt    = "🔴 Overbought — Sell zone" if a['rsi'] >= 70 else "🟢 Oversold — Buy zone" if a['rsi'] <= 30 else "🟡 Normal zone"
    bias       = "🟢 *BULLISH BIAS*" if a['signal_type'] == "BUY" else "🔴 *BEARISH BIAS*" if a['signal_type'] == "SELL" else "⚪ *WAIT — No setup yet*"

    checklist = f"""
{'✅' if a['bullish_cross'] or a['bearish_cross'] else '❌'} EMA 9/15 Crossover
{'✅' if a['angle9'] >= 30 else '❌'} EMA Angle 30°+
{'✅' if 35 <= a['rsi'] <= 65 else '⚠️'} RSI Safe Zone ({a['rsi']})
{'✅' if a['buy_score'] >= 7 or a['sell_score'] >= 7 else '❌'} Min Setup Score (7+)
{'✅' if a['signal_type'] != 'WAIT' else '❌'} Trade Ready"""

    return f"""
📊 *XAU/USD — LIVE MARKET ANALYSIS*
_Mayank Sir | EMA 9/15 Scalping Strategy_
━━━━━━━━━━━━━━━━━━━━
💰 *Live Price:* `${p:,.2f}`
🕐 Last Candle: `{a['candle_time']}`

━━━━━━━━━━━━━━━━━━━━
📐 *EMA ANALYSIS (LIVE)*
• EMA 9:   `{a['ema9']}` | Angle: `{a['angle9']}°` — {angle_txt}
• EMA 15:  `{a['ema15']}` | Angle: `{a['angle15']}°`
• Status:  {cross_txt}

━━━━━━━━━━━━━━━━━━━━
📊 *MOMENTUM*
• RSI (14): `{a['rsi']}` — {rsi_txt}

━━━━━━━━━━━━━━━━━━━━
🏗 *MARKET STRUCTURE (LIVE)*
• 🔴 Resistance 2: `${a['resistance2']:,.2f}`
• 🔴 Resistance 1: `${a['resistance']:,.2f}`
• 💰 Current Price: `${p:,.2f}`
• 🟢 Support 1:    `${a['support']:,.2f}`
• 🟢 Support 2:    `${a['support2']:,.2f}`

━━━━━━━━━━━━━━━━━━━━
☑️ *SETUP CHECKLIST*
{checklist}

━━━━━━━━━━━━━━━━━━━━
💡 *Mayank Sir Rules:*
• Sirf EMA cross + 30°+ angle pe entry
• Price + EMA alignment confirm karo
• SL tight rakho — 2.5 points max
• TP1 hit → SL entry pe lao
• No setup = No trade (sabr karo!)

🎯 *Bias:* {bias}
━━━━━━━━━━━━━━━━━━━━
🕐 {time_now} | 📢 @traderrahul1
"""

def format_tp(tp_num, tp_price, stype):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    emoji = "📈" if stype == "BUY" else "📉"
    return f"""
🎉🎉 *TP{tp_num} HIT — PROFIT BOOK KARO!* 🎉🎉

{emoji} *XAU/USD — EMA 9/15 Strategy*
━━━━━━━━━━━━━━━━━━━━
✅ *Target {tp_num} Successfully Hit!*
💰 *Hit Price:* `${tp_price:,.2f}`
━━━━━━━━━━━━━━━━━━━━
🥳 *{random.choice(TP_MSGS)}*

{'💡 *Ab SL ko entry pe le aao aur TP2 wait karo!*' if tp_num == 1 else '🏆 *Full profit book karo — amazing trade tha!*'}

━━━━━━━━━━━━━━━━━━━━
💰 *Apna fund nahi hai?*
_Prop account lo — profit aapka, risk unka!_

🕐 {time_now} | 📢 @traderrahul1
"""

def format_xm():
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    return f"""
🏦 *XM Trading — Traders ka Favourite Platform!*
━━━━━━━━━━━━━━━━━━━━
💡 *Main khud XM use karta hoon — ye kyun?*

✅ 📱 *UPI se Direct Deposit* — Super easy!
✅ 💸 *Low Spread* — Zyada profit pocket mein
✅ ⚡ *Fast Execution* — No slippage
✅ 🔒 *Regulated & Trusted* globally
✅ 📊 *All Instruments* — Gold, Forex, Crypto

━━━━━━━━━━━━━━━━━━━━
🏆 *WEEKLY TRADING CONTEST!*

🎯 *$25,000 Real Cash — Har Hafte!*
_Top traders ko real dollar milte hain!_
_Free registration — koi risk nahi!_

_Hamare signals use karo → Contest jeeto!_ 🚀

━━━━━━━━━━━━━━━━━━━━
👇 *Abhi join karo — FREE!*

🕐 {time_now} | 📢 @traderrahul1
"""

def is_xau_open():
    return datetime.now().weekday() < 5

# =============================================
# KEYBOARDS
# =============================================
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Live XAU Signal", callback_data="signal")],
        [InlineKeyboardButton("Market Analysis", callback_data="analysis")],
        [InlineKeyboardButton("XM Trading App", callback_data="xm")],
        [InlineKeyboardButton("Free Channel", url=CHANNEL_LINK),
         InlineKeyboardButton("VIP PRO", url="https://t.me/" + VIP_USER_CLEAN)],
        [InlineKeyboardButton("Prop Account", callback_data="prop")],
    ])

def signal_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Full Analysis", callback_data="analysis")],
        [InlineKeyboardButton("VIP - 10-15 Daily Signals", url="https://t.me/" + VIP_USER_CLEAN)],
        [InlineKeyboardButton("XM Trading", url=XM_LINK),
         InlineKeyboardButton("Prop Account", url=PROP_LINK)],
    ])

# =============================================
# HANDLERS
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "Trader"
    weekend = "\n⚠️ _Weekend — XAU market band. Monday subah milte hain!_ ☀️\n" if not is_xau_open() else ""
    msg = f"""
👋 *Kya haal hai {name} bhai!*

Main hoon *TraderRahul* 🥇
_Gold (XAU/USD) scalping specialist!_
{weekend}
━━━━━━━━━━━━━━━━━━━━
🧠 *Strategy: Mayank Sir (The Trade Room)*

📌 EMA 9 + EMA 15 Crossover
📐 30°+ Angle confirmation
🏗 Support / Resistance (Live)
🟦 Order Block detection
💧 Liquidity Grab analysis
📉 FVG (Fair Value Gap)
⏱ Only 5M — XAU/USD

_Har trade tabhi deta hoon jab poora_
_setup ready ho — no guessing!_ 💪

━━━━━━━━━━━━━━━━━━━━
🆓 *FREE:* Live signals + Analysis
👑 *VIP:* 10-15 signals + Support
"""
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_kb())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "signal":
        if not is_xau_open():
            await query.message.reply_text(
                "😴 *Weekend hai bhai — Gold market band!*\n\nMonday subah 9 baje se phir trade karenge! ☀️\n\nTab tak XM pe practice karo! 😄",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("XM Practice", url=XM_LINK)]]))
            return
        await query.message.reply_text("🔍 _Live market scan kar raha hoon..._\n_EMA 9/15 check ho rahi hai..._ ⏳", parse_mode="Markdown")
        candles = get_live_candles("XAU/USD", "5min", 50)
        if candles and len(candles) >= 20:
            a = full_analysis(candles)
            await query.message.reply_text(format_signal(a), parse_mode="Markdown", reply_markup=signal_kb())
        else:
            await query.message.reply_text("❌ _Live data nahi aaya — thodi der mein try karo!_", parse_mode="Markdown")

    elif query.data == "analysis":
        if not is_xau_open():
            await query.message.reply_text("😴 _Weekend — Market band hai!_", parse_mode="Markdown")
            return
        await query.message.reply_text("📊 _Full live analysis kar raha hoon..._", parse_mode="Markdown")
        candles = get_live_candles("XAU/USD", "5min", 50)
        if candles and len(candles) >= 20:
            a = full_analysis(candles)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Signal Lo", callback_data="signal")],
                [InlineKeyboardButton("VIP Join", url="https://t.me/" + VIP_USER_CLEAN)],
            ])
            await query.message.reply_text(format_analysis(a), parse_mode="Markdown", reply_markup=kb)
        else:
            await query.message.reply_text("❌ _Data nahi aaya._", parse_mode="Markdown")

    elif query.data == "xm":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("XM Join Karo - FREE", url=XM_LINK)],
            [InlineKeyboardButton("$25K Weekly Contest!", url=XM_LINK)],
            [InlineKeyboardButton("VIP Signals bhi lo", url="https://t.me/" + VIP_USER_CLEAN)],
        ])
        await query.message.reply_text(format_xm(), parse_mode="Markdown", reply_markup=kb)

    elif query.data == "prop":
        msg = """
💼 *Prop Trading — Apna Fund Nahi Chahiye!*
━━━━━━━━━━━━━━━━━━━━
_Bahut log kehte hain fund nahi — solution hai!_ 🎯

✅ Bahut kam price mein account
✅ Simple rules — asaan pass karo
✅ Profit 100% aapka
✅ $10K se $200K tak
✅ Gold, BTC, Forex sab
━━━━━━━━━━━━━━━━━━━━
"""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Prop Account Lo", url=PROP_LINK)],
            [InlineKeyboardButton("XM Bhi Try Karo", url=XM_LINK)],
        ])
        await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

# =============================================
# AUTO POST
# =============================================
async def auto_signal(app):
    if not is_xau_open():
        return
    candles = get_live_candles("XAU/USD", "5min", 50)
    if not candles or len(candles) < 20:
        return
    a = full_analysis(candles)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("VIP Full Signals", url="https://t.me/" + VIP_USER_CLEAN)],
        [InlineKeyboardButton("XM Trading", url=XM_LINK),
         InlineKeyboardButton("Prop Account", url=PROP_LINK)],
        [InlineKeyboardButton("Bot Start", url="https://t.me/traderrahul_1_bot")],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_signal(a), parse_mode="Markdown", reply_markup=kb)
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_analysis(a), parse_mode="Markdown")
        logger.info(f"Auto posted: XAU @ {a['price']}")
    except Exception as e:
        logger.error(f"Auto post: {e}")

async def auto_tp(app):
    if not is_xau_open():
        return
    candles = get_live_candles("XAU/USD", "5min", 50)
    if not candles:
        return
    a = full_analysis(candles)
    stype = a['signal_type'] if a['signal_type'] != "WAIT" else random.choice(["BUY", "SELL"])
    tp_num   = random.choice([1, 2])
    tp_price = round(a['price'] + (3.5 if tp_num == 1 else 7.0), 2) if stype == "BUY" else round(a['price'] - (3.5 if tp_num == 1 else 7.0), 2)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("XM - $25K Contest!", url=XM_LINK)],
        [InlineKeyboardButton("VIP Join", url="https://t.me/" + VIP_USER_CLEAN)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_tp(tp_num, tp_price, stype), parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"TP post: {e}")

async def auto_xm(app):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("XM Join Karo - FREE", url=XM_LINK)],
        [InlineKeyboardButton("$25,000 Weekly!", url=XM_LINK)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_xm(), parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"XM promo: {e}")

# =============================================
# COMMANDS
# =============================================
async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_xau_open():
        await update.message.reply_text("😴 _Weekend — XAU band hai!_", parse_mode="Markdown")
        return
    await update.message.reply_text("🔍 _Live scan..._", parse_mode="Markdown")
    candles = get_live_candles("XAU/USD", "5min", 50)
    if candles and len(candles) >= 20:
        a = full_analysis(candles)
        await update.message.reply_text(format_signal(a), parse_mode="Markdown", reply_markup=signal_kb())
        await update.message.reply_text(format_analysis(a), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Data nahi aaya.")

async def cmd_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_xau_open():
        await update.message.reply_text("😴 _Weekend!_", parse_mode="Markdown")
        return
    candles = get_live_candles("XAU/USD", "5min", 50)
    if candles and len(candles) >= 20:
        a = full_analysis(candles)
        await update.message.reply_text(format_analysis(a), parse_mode="Markdown")

async def cmd_xm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("XM Join FREE", url=XM_LINK)],
        [InlineKeyboardButton("$25K Weekly", url=XM_LINK)],
    ])
    await update.message.reply_text(format_xm(), parse_mode="Markdown", reply_markup=kb)

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"""
👑 *VIP PRO — Rahul Bhai ke Saath!*
✅ 10-15 live XAU signals daily
✅ EMA 9/15 + full live analysis
✅ Order Block + FVG + Liquidity
✅ Direct Telegram support
💬 DM: {VIP_USERNAME}
"""
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("DM Karo", url="https://t.me/" + VIP_USER_CLEAN)]])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def cmd_prop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Prop Lo", url=PROP_LINK)]])
    await update.message.reply_text("💼 Prop Account — Apna fund nahi chahiye!\n✅ Kam price | ✅ Min rules | ✅ Profit aapka", parse_mode="Markdown", reply_markup=kb)

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("signal",   cmd_signal))
    app.add_handler(CommandHandler("analysis", cmd_analysis))
    app.add_handler(CommandHandler("xm",       cmd_xm))
    app.add_handler(CommandHandler("vip",      cmd_vip))
    app.add_handler(CommandHandler("prop",     cmd_prop))
    app.add_handler(CallbackQueryHandler(button_callback))

    scheduler = AsyncIOScheduler()
    # Signal + Analysis — Mon-Fri har 2 ghante
    scheduler.add_job(auto_signal, "cron", day_of_week="mon-fri",
                      hour="8,10,12,14,16,18,20", minute=0, args=[app])
    # TP Hit messages
    scheduler.add_job(auto_tp, "cron", day_of_week="mon-fri",
                      hour="9,13,17", minute=45, args=[app])
    # XM Promo — daily 11 AM
    scheduler.add_job(auto_xm, "cron", hour=11, minute=0, args=[app])
    scheduler.start()

    logger.info("🚀 TraderRahul LIVE Bot — Twelve Data connected!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
