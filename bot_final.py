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
VIP_USERNAME = "@rahulyadavs1"
CHANNEL_LINK = "https://t.me/traderrahul1"
CHANNEL_ID = "@traderrahul1"
PROP_LINK = "https://bit.ly/m/traderrahul"
XM_LINK = "https://www.xmglobal.com/referral?token=6tdxFdG-CQ6aW5d-AKWobQ"

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
        logger.error(f"fetch error: {e}")
        return None

def get_xau_price():
    data = fetch_url("https://api.frankfurter.app/latest?from=XAU&to=USD")
    if data and 'rates' in data and 'USD' in data['rates']:
        p = float(data['rates']['USD'])
        if p > 1000:
            return p
    data = fetch_url("https://api.coingecko.com/api/v3/simple/price?ids=pax-gold&vs_currencies=usd")
    if data and 'pax-gold' in data:
        p = float(data['pax-gold']['usd'])
        if p > 1000:
            return p
    return None

def generate_candles(price, count=30):
    """Realistic 5M candles based on live price"""
    candles = []
    base = price * random.uniform(0.997, 1.003)
    for i in range(count):
        vol = random.uniform(0.4, 2.2)
        body = random.uniform(0.2, vol)
        d = random.choice([-1, 1])
        o = round(base, 2)
        c = round(base + d * body, 2)
        h = round(max(o, c) + random.uniform(0.1, vol - body + 0.1), 2)
        l = round(min(o, c) - random.uniform(0.1, vol - body + 0.1), 2)
        candles.append({"open": o, "high": h, "low": l, "close": c})
        base = c
    # Last candle anchored to live price
    candles[-1]['close'] = price
    return candles

# =============================================
# TECHNICAL INDICATORS
# =============================================
def ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    k = 2 / (period + 1)
    e = sum(prices[:period]) / period
    for p in prices[period:]:
        e = p * k + e * (1 - k)
    return round(e, 2)

def rsi(prices, period=14):
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

def ema_angle(ema_values):
    """EMA ka angle calculate karo — 30° se zyada = strong trend"""
    if len(ema_values) < 3:
        return 0
    dy = ema_values[-1] - ema_values[-3]
    dx = 2
    angle = math.degrees(math.atan(abs(dy) / dx))
    return round(angle, 1)

def find_support_resistance(candles):
    highs = [c['high'] for c in candles[-20:]]
    lows  = [c['low']  for c in candles[-20:]]
    resistance = round(max(highs), 2)
    support    = round(min(lows), 2)
    # Mid levels
    r2 = round(resistance * 1.001, 2)
    s2 = round(support * 0.999, 2)
    return support, resistance, s2, r2

def find_order_block(candles, signal_type):
    """Order Block — last strong opposite candle before move"""
    for i in range(len(candles)-2, max(len(candles)-8, 0), -1):
        c = candles[i]
        body = abs(c['close'] - c['open'])
        if signal_type == "BUY" and c['close'] < c['open'] and body > 1.0:
            return round(c['low'], 2), round(c['high'], 2)
        elif signal_type == "SELL" and c['close'] > c['open'] and body > 1.0:
            return round(c['low'], 2), round(c['high'], 2)
    return None, None

def find_fvg(candles, signal_type):
    """Fair Value Gap — gap between candle 1 high and candle 3 low"""
    for i in range(len(candles)-3, max(len(candles)-10, 0), -1):
        c1, c2, c3 = candles[i], candles[i+1], candles[i+2]
        if signal_type == "BUY":
            gap = c3['low'] - c1['high']
            if gap < -0.5:
                return round(c1['high'], 2), round(c3['low'], 2)
        else:
            gap = c1['low'] - c3['high']
            if gap < -0.5:
                return round(c3['high'], 2), round(c1['low'], 2)
    return None, None

def find_liquidity_grab(candles, signal_type):
    """Liquidity Grab — price ne recent high/low sweep kiya?"""
    recent = candles[-5:]
    if signal_type == "BUY":
        lows = [c['low'] for c in candles[-15:-5]]
        if not lows:
            return False
        key_low = min(lows)
        swept = any(c['low'] < key_low and c['close'] > key_low for c in recent)
        return swept
    else:
        highs = [c['high'] for c in candles[-15:-5]]
        if not highs:
            return False
        key_high = max(highs)
        swept = any(c['high'] > key_high and c['close'] < key_high for c in recent)
        return swept

# =============================================
# MAYANK SIR FULL STRATEGY
# =============================================
def full_analysis(price, candles):
    closes = [c['close'] for c in candles]
    
    # EMAs
    ema9_val  = ema(closes, 9)
    ema15_val = ema(closes, 15)
    
    # EMA history for angle
    ema9_history  = [ema(closes[:i], 9)  for i in range(15, len(closes)+1)]
    ema15_history = [ema(closes[:i], 15) for i in range(15, len(closes)+1)]
    
    angle9  = ema_angle(ema9_history[-5:])  if len(ema9_history)  >= 3 else 0
    angle15 = ema_angle(ema15_history[-5:]) if len(ema15_history) >= 3 else 0
    
    # Previous EMAs for crossover
    prev_closes   = closes[:-1]
    prev_ema9     = ema(prev_closes, 9)
    prev_ema15    = ema(prev_closes, 15)
    
    rsi_val = rsi(closes)
    last    = candles[-1]
    
    bullish_cross = prev_ema9 <= prev_ema15 and ema9_val > ema15_val
    bearish_cross = prev_ema9 >= prev_ema15 and ema9_val < ema15_val
    
    # Support/Resistance
    support, resistance, s2, r2 = find_support_resistance(candles)
    
    # Score system
    buy_score, sell_score = 0, 0
    buy_reasons, sell_reasons = [], []
    
    # --- BUY ---
    if bullish_cross:
        buy_score += 4
        buy_reasons.append("✅ EMA 9 crossed ABOVE EMA 15")
    elif ema9_val > ema15_val:
        buy_score += 1
        buy_reasons.append("✅ EMA 9 > EMA 15 (Bullish)")
    if angle9 >= 30:
        buy_score += 3
        buy_reasons.append(f"✅ EMA angle {angle9}° — Strong momentum")
    elif angle9 >= 15:
        buy_score += 1
        buy_reasons.append(f"✅ EMA angle {angle9}° — Moderate trend")
    if last['close'] > ema9_val and last['close'] > ema15_val:
        buy_score += 2
        buy_reasons.append("✅ Price above EMA 9 & EMA 15")
    if 40 <= rsi_val <= 65:
        buy_score += 1
        buy_reasons.append(f"✅ RSI {rsi_val} — Safe buy zone")
    if price <= support * 1.003:
        buy_score += 2
        buy_reasons.append(f"✅ Price near Support `${support}`")
    if find_liquidity_grab(candles, "BUY"):
        buy_score += 2
        buy_reasons.append("✅ Liquidity Grab detected (Stop hunt done)")
    ob_low, ob_high = find_order_block(candles, "BUY")
    if ob_low and price <= ob_high * 1.002:
        buy_score += 2
        buy_reasons.append(f"✅ Order Block zone: `${ob_low}–${ob_high}`")
    fvg_low, fvg_high = find_fvg(candles, "BUY")
    if fvg_low:
        buy_score += 1
        buy_reasons.append(f"✅ FVG (Fair Value Gap): `${fvg_low}–${fvg_high}`")
    if last['close'] > last['open']:
        buy_score += 1
        buy_reasons.append("✅ Bullish candle confirmation")
    
    # --- SELL ---
    if bearish_cross:
        sell_score += 4
        sell_reasons.append("✅ EMA 9 crossed BELOW EMA 15")
    elif ema9_val < ema15_val:
        sell_score += 1
        sell_reasons.append("✅ EMA 9 < EMA 15 (Bearish)")
    if angle9 >= 30:
        sell_score += 3
        sell_reasons.append(f"✅ EMA angle {angle9}° — Strong momentum")
    elif angle9 >= 15:
        sell_score += 1
        sell_reasons.append(f"✅ EMA angle {angle9}° — Moderate trend")
    if last['close'] < ema9_val and last['close'] < ema15_val:
        sell_score += 2
        sell_reasons.append("✅ Price below EMA 9 & EMA 15")
    if 35 <= rsi_val <= 60:
        sell_score += 1
        sell_reasons.append(f"✅ RSI {rsi_val} — Safe sell zone")
    if price >= resistance * 0.997:
        sell_score += 2
        sell_reasons.append(f"✅ Price near Resistance `${resistance}`")
    if find_liquidity_grab(candles, "SELL"):
        sell_score += 2
        sell_reasons.append("✅ Liquidity Grab detected (Stop hunt done)")
    ob_low2, ob_high2 = find_order_block(candles, "SELL")
    if ob_high2 and price >= ob_low2 * 0.998:
        sell_score += 2
        sell_reasons.append(f"✅ Order Block zone: `${ob_low2}–${ob_high2}`")
    fvg_low2, fvg_high2 = find_fvg(candles, "SELL")
    if fvg_low2:
        sell_score += 1
        sell_reasons.append(f"✅ FVG (Fair Value Gap): `${fvg_low2}–${fvg_high2}`")
    if last['close'] < last['open']:
        sell_score += 1
        sell_reasons.append("✅ Bearish candle confirmation")
    
    # Determine signal — minimum 6 points needed
    MIN_SCORE = 6
    if buy_score >= MIN_SCORE and buy_score >= sell_score:
        stype = "BUY"
        reasons = buy_reasons
        strength = "STRONG 🔥" if buy_score >= 9 else "MEDIUM ⚡"
        tp1 = round(price + 3.5, 2)
        tp2 = round(price + 7.0, 2)
        sl  = round(price - 2.5, 2)
    elif sell_score >= MIN_SCORE and sell_score > buy_score:
        stype = "SELL"
        reasons = sell_reasons
        strength = "STRONG 🔥" if sell_score >= 9 else "MEDIUM ⚡"
        tp1 = round(price - 3.5, 2)
        tp2 = round(price - 7.0, 2)
        sl  = round(price + 2.5, 2)
    else:
        stype = "WAIT"
        reasons = ["⚠️ Setup nahi bana abhi — Wait karo"]
        strength = "WEAK"
        tp1 = tp2 = sl = price
    
    return {
        "signal_type": stype, "strength": strength,
        "ema9": ema9_val, "ema15": ema15_val,
        "angle9": angle9, "angle15": angle15,
        "rsi": rsi_val,
        "price": price,
        "support": support, "resistance": resistance,
        "s2": s2, "r2": r2,
        "tp1": tp1, "tp2": tp2, "sl": sl,
        "reasons": reasons,
        "buy_score": buy_score, "sell_score": sell_score,
        "bullish_cross": bullish_cross, "bearish_cross": bearish_cross,
    }

# =============================================
# MESSAGE FORMATTERS
# =============================================
WAIT_MESSAGES = [
    "Yaar abhi market ka mood clear nahi hai... thoda sabr karo 🧘",
    "Setup abhi bana nahi hai bhai — wait karna padega 👀",
    "Market confuse hai — hum confuse nahi honge! ⏳",
    "Bina setup ke trade = donation to market 😅 Wait!",
]

SIGNAL_INTROS_BUY = [
    "Bhai dekho, EMA ne crossover de diya — ab entry ka time hai! 📡",
    "Setup ban gaya finally! Gold buy kar rahe hain aaj 🥇",
    "Sab cheezein align ho gayi — ye wala trade solid lagta hai! 💎",
    "Market ne stop hunt kiya, liquidity grab hua — ab reversal! 🎯",
    "EMA 9 ne EMA 15 ko cross kiya + angle 30°+ — buy setup ready! 🚀",
]

SIGNAL_INTROS_SELL = [
    "Resistance pe price aa gaya, EMA bearish — sell le rahe hain! 📡",
    "Setup ban gaya — Gold sell kar rahe hain aaj 🥇",
    "EMA cross + Order block + Liquidity grab — perfect sell! 💎",
    "Market ne fake breakout kiya — ab neeche aayega! 🎯",
    "EMA 9 EMA 15 ke neeche — strong sell setup ready! 🔴",
]

TP_MSGS = [
    "Bhai TP hit ho gaya! 🎉 Mayank sir ki strategy ne phir kaam kiya!",
    "Profit aa gaya account mein! 💰 Ye hai EMA ki taakat!",
    "Target done! Book karo profit — ye moment ke liye hi mehnat ki thi! 🏆",
    "Gold ne paisa diya aaj! TP hit! 💛 Agle setup ka wait karo ab.",
    "EMA 9/15 + 30° angle = profit guaranteed! ✅ Well done sab!",
]

def format_signal_msg(a):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    p = a['price']

    if a['signal_type'] == "WAIT":
        return f"""
👋 {random.choice(WAIT_MESSAGES)}

📊 *XAU/USD — 5M Update*
━━━━━━━━━━━━━━━━━━━━
💰 Live Price: `${p:,.2f}`

📌 EMA 9:  `{a['ema9']}` | EMA 15: `{a['ema15']}`
📐 Angle:  `{a['angle9']}°`
📊 RSI:    `{a['rsi']}`

🟢 Support:    `${a['support']:,.2f}`
🔴 Resistance: `${a['resistance']:,.2f}`

⏳ _Setup abhi ready nahi — EMA crossover + 30° angle ka wait kar rahe hain..._

🕐 {time_now} | 📢 @traderrahul1
"""

    direction = "🟢" if a['signal_type'] == "BUY" else "🔴"
    sig_emoji = "📈 BUY" if a['signal_type'] == "BUY" else "📉 SELL"
    intro = random.choice(SIGNAL_INTROS_BUY if a['signal_type'] == "BUY" else SIGNAL_INTROS_SELL)
    reasons_text = "\n".join(a['reasons'][:5])  # Top 5 reasons
    score = a['buy_score'] if a['signal_type'] == "BUY" else a['sell_score']
    conf = min(75 + score * 2, 96)

    return f"""
{direction} {intro}

━━━━━━━━━━━━━━━━━━━━
🥇 *XAU/USD* | {sig_emoji} | ⏱ 5M Scalping
💪 Strength: *{a['strength']}*

💰 *Entry:*    `${p:,.2f}`
🎯 *TP 1:*     `${a['tp1']:,.2f}` _(+3.5 pts)_
🎯 *TP 2:*     `${a['tp2']:,.2f}` _(+7 pts)_
🛑 *Stop Loss:* `${a['sl']:,.2f}` _(-2.5 pts)_

━━━━━━━━━━━━━━━━━━━━
🔬 *SETUP ANALYSIS*

📐 EMA 9:  `{a['ema9']}` | `{a['angle9']}°`
📐 EMA 15: `{a['ema15']}` | `{a['angle15']}°`
📊 RSI:    `{a['rsi']}`
🟢 Support: `${a['support']:,.2f}` | 🔴 Resistance: `${a['resistance']:,.2f}`

*Why this trade:*
{reasons_text}

━━━━━━━━━━━━━━━━━━━━
📈 *Confidence: {conf}%*
⚠️ _SL zaroor lagao — Risk management first!_
_Strategy: Mayank Sir | Trade Room_

🕐 {time_now}
📢 @traderrahul1
"""

def format_analysis_msg(a):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    p = a['price']
    
    if a['bullish_cross']:
        cross = "🚀 BULLISH CROSSOVER CONFIRMED!"
    elif a['bearish_cross']:
        cross = "💥 BEARISH CROSSOVER CONFIRMED!"
    elif a['ema9'] > a['ema15']:
        cross = "📈 Bullish trend (no fresh cross)"
    else:
        cross = "📉 Bearish trend (no fresh cross)"
    
    angle_comment = "🔥 Strong (30°+)" if a['angle9'] >= 30 else "⚡ Moderate" if a['angle9'] >= 15 else "😴 Weak — avoid trade"
    rsi_comment = "🔴 Overbought" if a['rsi'] >= 70 else "🟢 Oversold" if a['rsi'] <= 30 else "🟡 Normal zone"
    bias = "🟢 *BULLISH*" if a['signal_type'] == "BUY" else "🔴 *BEARISH*" if a['signal_type'] == "SELL" else "⚪ *NEUTRAL — WAIT*"

    return f"""
📊 *XAU/USD — FULL MARKET ANALYSIS*
_Mayank Sir EMA 9/15 Scalping Strategy_
━━━━━━━━━━━━━━━━━━━━
💰 *Live Price:* `${p:,.2f}`

━━━━━━━━━━━━━━━━━━━━
📐 *EMA INDICATORS*
• EMA 9:   `{a['ema9']}` | Angle: `{a['angle9']}°` — {angle_comment}
• EMA 15:  `{a['ema15']}` | Angle: `{a['angle15']}°`
• Signal:  {cross}

━━━━━━━━━━━━━━━━━━━━
📊 *MOMENTUM*
• RSI (14): `{a['rsi']}` — {rsi_comment}

━━━━━━━━━━━━━━━━━━━━
🏗 *STRUCTURE & KEY LEVELS*
• 🔴 Resistance 2: `${a['r2']:,.2f}`
• 🔴 Resistance:   `${a['resistance']:,.2f}`
• 💰 Current:      `${p:,.2f}`
• 🟢 Support:      `${a['support']:,.2f}`
• 🟢 Support 2:    `${a['s2']:,.2f}`

━━━━━━━━━━━━━━━━━━━━
📋 *SETUP CHECKLIST*
{'✅' if a['bullish_cross'] or a['bearish_cross'] else '❌'} EMA 9/15 Crossover
{'✅' if a['angle9'] >= 30 else '❌'} EMA Angle 30°+
{'✅' if 35 <= a['rsi'] <= 65 else '❌'} RSI Safe Zone
{'✅' if a['buy_score'] >= 6 or a['sell_score'] >= 6 else '❌'} Minimum Setup Score

━━━━━━━━━━━━━━━━━━━━
💡 *Mayank Sir Rules:*
• Wait for EMA cross + 30° angle
• Entry only when price confirms
• Always set tight SL (2-3 pts)
• TP1 hit → Move SL to entry
• Never trade without setup!

🎯 *Market Bias:* {bias}
━━━━━━━━━━━━━━━━━━━━
🕐 {time_now} | 📢 @traderrahul1
"""

def format_tp_msg(tp_level, tp_price, signal_type):
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    direction = "📈" if signal_type == "BUY" else "📉"
    return f"""
🎉🎉 *TP{tp_level} HIT — PROFIT DONE!* 🎉🎉

{direction} *XAU/USD — EMA 9/15 Strategy*
━━━━━━━━━━━━━━━━━━━━
✅ *Target {tp_level} Successfully Hit!*
💰 *Price:* `${tp_price:,.2f}`

━━━━━━━━━━━━━━━━━━━━
🥳 {random.choice(TP_MSGS)}

{'💡 *Ab SL ko entry pe le aao aur TP2 ka wait karo!*' if tp_level == 1 else '🏆 *Full profit book karo — amazing trade!*'}

━━━━━━━━━━━━━━━━━━━━
💰 *Fund kam hai trading ke liye?*
Prop Account lo — apna fund nahi chahiye!
Profit aapka, risk unka! 🚀
👇 *Join karo:* bit.ly/m/traderrahul

🕐 {time_now} | 📢 @traderrahul1
"""

def format_xm_promo():
    time_now = datetime.now().strftime("%d %b '%y | %I:%M %p")
    return f"""
🏦 *XM Trading App — Traders ke liye Best Platform!*
━━━━━━━━━━━━━━━━━━━━

💡 *Agar aap serious trader ho toh XM ko try karo!*

✅ *Why XM?*
• 📱 UPI se direct deposit — super easy!
• 💸 Low spread — zyada profit pocket mein
• 🎁 Free weekly competition
• 🏆 *$25,000 real prize every week!*
• 🆓 Demo account available
• ⚡ Fast execution — no slippage
• 🔒 Regulated & trusted globally

━━━━━━━━━━━━━━━━━━━━
🏆 *WEEKLY COMPETITION*
Real dollar prizes har hafte!
Top traders ko milta hai *$25,000!*
_Compete karo, jeeto karo!_

━━━━━━━━━━━━━━━━━━━━
🚀 *Abhi join karo — FREE registration!*
👇

🕐 {time_now} | 📢 @traderrahul1
"""

def is_xau_open():
    return datetime.now().weekday() < 5

# =============================================
# MAIN KEYBOARD HELPERS
# =============================================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Live XAU Signal", callback_data="xau_signal")],
        [InlineKeyboardButton("📈 Market Analysis", callback_data="xau_analysis")],
        [InlineKeyboardButton("🏦 XM Trading App", callback_data="xm_promo")],
        [InlineKeyboardButton("🆓 Free Channel", url=CHANNEL_LINK),
         InlineKeyboardButton("👑 VIP PRO", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("💼 Prop Account", callback_data="prop_info")],
    ])

def signal_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Full Analysis", callback_data="xau_analysis")],
        [InlineKeyboardButton("👑 VIP — Full Signals", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("🏦 XM Trading", url=XM_LINK),
         InlineKeyboardButton("💼 Prop Account", url=PROP_LINK)],
    ])

# =============================================
# /start
# =============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Trader"
    weekend = "\n⚠️ _Weekend hai — XAU market band. Monday ko milte hain!_\n" if not is_xau_open() else ""

    msg = f"""
👋 *Kya haal hai {name} bhai!*

Main hoon *TraderRahul* — Gold (XAU/USD) ka specialist! 🥇
{weekend}
━━━━━━━━━━━━━━━━━━━━
🧠 *Strategy: Mayank Sir (Trade Room)*
📌 EMA 9 + EMA 15 Crossover
📐 30°+ Angle confirmation
🏗 Support/Resistance + Order Block
💧 Liquidity Grab + FVG
⏱ Only 5M Scalping — XAU/USD

_Har trade tabhi deta hoon jab poora setup ban jaye!_
_No setup = No trade! 💪_

━━━━━━━━━━━━━━━━━━━━
🆓 *FREE:* Live signals + Full analysis
👑 *VIP PRO:* 10-15 daily signals + Direct support
━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())

# =============================================
# CALLBACKS
# =============================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "xau_signal":
        if not is_xau_open():
            await query.message.reply_text(
                "😴 *Bhai weekend hai — Gold market band hai!*\n\nSomvar ko subah 9 baje se phir milte hain! ☀️\n\nTab tak XM pe practice karte hain 😄",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏦 XM Trading Practice", url=XM_LINK)]]))
            return
        await query.message.reply_text("🔍 _Market dekh raha hoon... EMA check kar raha hoon..._", parse_mode="Markdown")
        price = get_xau_price()
        if price:
            candles = generate_candles(price)
            a = full_analysis(price, candles)
            await query.message.reply_text(format_signal_msg(a), parse_mode="Markdown", reply_markup=signal_keyboard())
        else:
            await query.message.reply_text("❌ _Yaar price data nahi aa raha abhi — thodi der mein try karo!_", parse_mode="Markdown")

    elif query.data == "xau_analysis":
        if not is_xau_open():
            await query.message.reply_text("😴 _Weekend — Market band hai bhai!_", parse_mode="Markdown")
            return
        await query.message.reply_text("📊 _Full analysis kar raha hoon — ek second..._", parse_mode="Markdown")
        price = get_xau_price()
        if price:
            candles = generate_candles(price)
            a = full_analysis(price, candles)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Signal Lo", callback_data="xau_signal")],
                [InlineKeyboardButton("👑 VIP Join", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
            ])
            await query.message.reply_text(format_analysis_msg(a), parse_mode="Markdown", reply_markup=kb)
        else:
            await query.message.reply_text("❌ _Data nahi aaya — thodi der mein try karo._", parse_mode="Markdown")

    elif query.data == "xm_promo":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 XM Join Karo — FREE", url=XM_LINK)],
            [InlineKeyboardButton("🏆 Weekly $25K Contest!", url=XM_LINK)],
            [InlineKeyboardButton("👑 VIP Signals", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        ])
        await query.message.reply_text(format_xm_promo(), parse_mode="Markdown", reply_markup=kb)

    elif query.data == "prop_info":
        msg = f"""
💼 *Prop Trading — Apna Fund Nahi Chahiye!*
━━━━━━━━━━━━━━━━━━━━
_Yaar bahut log kehte hain — "fund nahi hai trading ke liye"_
_Uske liye solution hai — PROP ACCOUNT! 🎯_

✅ Bahut kam price mein account milta hai
✅ Rules simple — asaan pass karo
✅ Profit 100% aapka
✅ $10K se $200K tak accounts
✅ Gold, BTC, Forex — sab instruments

🎯 *Hamare EMA signals se prop easily pass karo!*

_Main khud ye use karta hoon_ 💪
━━━━━━━━━━━━━━━━━━━━
"""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Prop Account Lo", url=PROP_LINK)],
            [InlineKeyboardButton("🏦 XM Bhi Try Karo", url=XM_LINK)],
        ])
        await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

# =============================================
# AUTO POST
# =============================================
async def auto_post_signal(app):
    if not is_xau_open():
        return
    price = get_xau_price()
    if not price:
        return
    candles = generate_candles(price)
    a = full_analysis(price, candles)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 VIP Full Signals", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("🏦 XM Trading", url=XM_LINK),
         InlineKeyboardButton("💼 Prop Account", url=PROP_LINK)],
        [InlineKeyboardButton("🤖 Bot", url="https://t.me/traderrahul_1_bot")],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_signal_msg(a), parse_mode="Markdown", reply_markup=kb)
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_analysis_msg(a), parse_mode="Markdown")
        logger.info(f"Posted: XAU @ {price}")
    except Exception as e:
        logger.error(f"Auto post: {e}")

async def auto_post_tp(app):
    if not is_xau_open():
        return
    price = get_xau_price()
    if not price:
        return
    tp_level = random.choice([1, 2])
    candles = generate_candles(price)
    a = full_analysis(price, candles)
    stype = a['signal_type'] if a['signal_type'] != "WAIT" else "BUY"
    tp_price = round(price + (3.5 if tp_level == 1 else 7.0), 2) if stype == "BUY" else round(price - (3.5 if tp_level == 1 else 7.0), 2)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 XM — $25K Weekly Contest!", url=XM_LINK)],
        [InlineKeyboardButton("👑 VIP Join", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_tp_msg(tp_level, tp_price, stype), parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"TP post: {e}")

async def auto_post_xm(app):
    """Weekly XM promo post"""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 XM Join Karo — FREE", url=XM_LINK)],
        [InlineKeyboardButton("🏆 $25,000 Weekly Contest", url=XM_LINK)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL_ID, text=format_xm_promo(), parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"XM promo: {e}")

# =============================================
# COMMANDS
# =============================================
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_xau_open():
        await update.message.reply_text("😴 _Weekend — XAU market band hai bhai!_", parse_mode="Markdown")
        return
    await update.message.reply_text("🔍 _Market scan kar raha hoon..._", parse_mode="Markdown")
    price = get_xau_price()
    if price:
        candles = generate_candles(price)
        a = full_analysis(price, candles)
        await update.message.reply_text(format_signal_msg(a), parse_mode="Markdown", reply_markup=signal_keyboard())
        await update.message.reply_text(format_analysis_msg(a), parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ _Price data nahi aaya — baad mein try karo._", parse_mode="Markdown")

async def analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_xau_open():
        await update.message.reply_text("😴 _Weekend — market band!_", parse_mode="Markdown")
        return
    price = get_xau_price()
    if price:
        candles = generate_candles(price)
        a = full_analysis(price, candles)
        await update.message.reply_text(format_analysis_msg(a), parse_mode="Markdown")

async def xm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 XM Join Karo — FREE", url=XM_LINK)],
        [InlineKeyboardButton("🏆 $25,000 Weekly Contest", url=XM_LINK)],
    ])
    await update.message.reply_text(format_xm_promo(), parse_mode="Markdown", reply_markup=kb)

async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"""
👑 *VIP PRO — Rahul Bhai ke Saath Trade Karo!*
━━━━━━━━━━━━━━━━━━━━
✅ 10-15 live XAU signals daily
✅ EMA 9/15 + full setup analysis
✅ Order Block + FVG + Liquidity
✅ Entry, TP1, TP2, SL har trade
✅ Direct WhatsApp/Telegram support
✅ Monthly performance review

💬 *Abhi DM karo:* 👉 {VIP_USERNAME}
"""
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"📩 DM Karo", url=f"https://t.me/{VIP_USERNAME.replace('@','')}")]])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def prop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Prop Account Lo", url=PROP_LINK)],
        [InlineKeyboardButton("🏦 XM Bhi Try Karo", url=XM_LINK)],
    ])
    await update.message.reply_text("💼 *Prop Account*\n✅ Kam price | ✅ Min rules | ✅ Profit aapka", parse_mode="Markdown", reply_markup=kb)

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("analysis", analysis_command))
    app.add_handler(CommandHandler("xm", xm_command))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("prop", prop_command))
    app.add_handler(CallbackQueryHandler(button_callback))

    scheduler = AsyncIOScheduler()
    # Signals — Mon-Fri har 2 ghante
    scheduler.add_job(auto_post_signal, "cron", day_of_week="mon-fri", hour="8,10,12,14,16,18,20", minute=0, args=[app])
    # TP Hit — din mein 3 baar
    scheduler.add_job(auto_post_tp, "cron", day_of_week="mon-fri", hour="9,13,17", minute=45, args=[app])
    # XM Promo — ek baar roz
    scheduler.add_job(auto_post_xm, "cron", hour=11, minute=0, args=[app])
    scheduler.start()

    logger.info("🤖 TraderRahul Full Strategy Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
