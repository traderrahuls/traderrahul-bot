import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = "8244372675:AAEzNzglqjT8saJd3L2B-wJYS7kHmmxqu30"
VIP_URL = "https://t.me/rahulyadavs1"
CHANNEL_URL = "https://t.me/traderrahul1"
PROP_URL = "https://bit.ly/m/traderrahul"
XM_URL = "https://www.xmglobal.com/referral?token=6tdxFdG-CQ6aW5d-AKWobQ"
BOT_URL = "https://t.me/traderrahul_1_bot"
CHANNEL = "@traderrahul1"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# =============================================
# WELCOME MESSAGES
# =============================================
WELCOME_MSGS = [
    """\
Arre bhai aa gaye aap!

Yahan pe milega sab kuch jo ek serious trader ko chahiye.
Main Rahul hoon - XAU/USD scalping karta hoon aur results deta hoon.

Neeche se apna kaam shuru karo!""",

    """\
Welcome bhai!

Trading mein paisa tab banta hai jab sahi jagah ho,
sahi platform ho aur sahi signals mile.

Teen cheezein hain mere paas - VIP signals, XM platform aur Prop funding.
Kya chahiye tumhe?""",

    """\
Kya haal hai bhai!

Bahut log trading karte hain par sirf kuch hi kama paate hain.
Farq hota hai - sahi setup aur sahi community ka.

Aao mere saath - main bahut time se XAU trade kar raha hoon.""",

    """\
Bhai perfect time pe aaye ho!

Gold market mein opportunities hain - har din.
Bas chahiye sahi entry, sahi platform aur thoda guidance.

Sab kuch yahan hai - explore karo!""",
]

# =============================================
# XM MESSAGES
# =============================================
XM_MSGS = [
    """\
Bhai seriously XM try karo ek baar!

Maine khud kai platforms use kiye hain - XM sabse smooth hai.
UPI se deposit karo - 2 minute mein account ready.
Spread itna low hai ki seriously difference feel hota hai.

Aur ye weekly $25,000 contest - bhai free mein participate karo!
Real dollar milte hain - har hafte top traders ko.
Maine khud dekha hai log jeet rahe hain.

Koi risk nahi - free registration hai.""",

    """\
Ek cheez puchho - trading mein spread kitna matter karta hai?

BAHUT! Har paise ka fark padta hai scalping mein.
XM pe spread itna tight hai ki aapko lagta hi nahi cost lag rahi.

Aur deposit? UPI se seedha - bank transfer ka jhanjhat nahi.
5 minute mein live trading shuru!

Weekly $25K contest alag se - real prize, real dollar, free entry.""",

    """\
Bhai jo platform use karo woh trusted hona chahiye na?

XM globally regulated hai - lakho traders use karte hain.
Aur Indian traders ke liye UPI deposit - game changer hai ye!

Mere sabse favorite feature - weekly trading contest.
$25,000 prize pool - top traders mein baanta hai.
Register karo FREE mein - kuch nahi jaata.""",

    """\
Ek serious baat karta hoon -

Agar trading platform reliable nahi toh trade kitna bhi perfect ho fark nahi padta.
XM pe execution fast hai, spread low hai, support 24/7 hai.

India mein UPI se deposit - sabse easy option.
Aur weekly $25K contest mein compete karo - real dollar jeeto!

Link neeche hai - FREE join karo.""",

    """\
Yaar XM ka ek aur feature batata hoon -

Demo account bhi milta hai - bina risk ke practice karo.
Jab confident ho tab real account pe switch karo.

Aur real account pe bhi weekly contest FREE hai!
$25,000 prize - har hafte - real cash.

Abhi join karo - koi fee nahi koi risk nahi.""",
]

# =============================================
# PROP MESSAGES
# =============================================
PROP_MSGS = [
    """\
Bhai ek common problem hai traders mein -

"Paisa nahi hai trading ke liye"

Aur honestly - ye problem SOLVE ho sakti hai.
Prop trading isi liye exist karta hai.

Tum trading karo - unka paisa use karo.
Profit mein tera hissa - loss mein tera kuch nahi.
Account bahut kam mein milta hai - aur rules bhi simple hain.""",

    """\
Soch ke dekho ek second -

Agar kisi ne tumhe $50,000 diya trade karne ke liye,
aur bola - profit mein 80% tera hai,
loss mein tera kuch nahi...

Yahi hota hai prop trading mein!
Sirf ek chota sa evaluation pass karna hota hai.
Hamare signals use karo - easily pass ho jaoge.""",

    """\
Prop account ke bare mein seriously socho -

Normal trading mein apna capital risk hota hai.
Prop mein? Sirf evaluation fee - ek baar.
Uske baad company ka paisa, tera profit!

$10K se $200K tak ke accounts available hain.
Gold, Forex, Crypto - sab trade kar sakte ho.
Aur hamare EMA signals se evaluation pass karna easy hai.""",

    """\
Bhai ye wala concept samajh lo -

Duniya mein successful traders wahi hain jo apna capital protect karte hain.
Prop trading mein - evaluation pass karo - company ka fund use karo.

Risk aapka minimum - reward aapka maximum.
Ek baar try karne layak toh hai bilkul.

Link hai neeche - details dekho.""",

    """\
Real baat karta hoon -

Capital ki kami ki wajah se bahut log trading nahi kar paate.
Par ab ye excuse khatam ho sakta hai.

Prop firms qualified traders ko fund deti hain.
Hamare signals se evaluation rules follow karna easy ho jaata hai.

Low drawdown, consistent profit - bas yahi chahiye unhe.
Join karo - details dekho - apna decision lo.""",
]

# =============================================
# VIP MESSAGES
# =============================================
VIP_MSGS = [
    """\
Seedha baat karta hoon VIP ke bare mein -

Main daily XAU/USD track karta hoon.
Jab setup banta hai - signal deta hoon.
Entry, TP1, TP2, Stop Loss - sab clear.

Free channel pe limited signals aate hain.
VIP mein - full signals, full analysis, direct support.

Join karna ho toh admin se baat karo.""",

    """\
VIP group mein kya milta hai? Honestly batata hoon -

Sirf signals nahi - poora context milta hai.
Kyun entry li, kahan SL hai, kab book karna hai.

Ye samajhne se apni trading improve hoti hai.
Ek signal se seekhte ho - agle khud le sakte ho.

Interested ho toh admin se connect karo.""",

    """\
Bhai ek cheez clearly samjhao -

Free channel pe jo signal aata hai - woh general hota hai.
VIP mein - personalized, timely, with full reasoning.

Difference feel hota hai clearly.
Results bhi different hote hain.

Admin se baat karo - VIP ke plans puchho.""",

    """\
Trading community ka ek faida aur hota hai -

Akele trade karte ho toh doubt aata hai.
Group mein hote ho toh clarity rehti hai.

VIP mein sirf signals nahi - ek community hai.
Log share karte hain - seekhte hain - saath badhte hain.

Admin se join karne ke liye baat karo.""",

    """\
VIP lene se pehle ye puchh sakte ho mujhse -

Kitne signals aate hain? Daily accuracy? Support kaisa hai?
Ye sab admin se seedha pooch sakte ho.

Transparent hoon main - koi hidden claims nahi.
Jo hai woh batata hoon.

Admin ka link neeche hai - connect karo.""",
]

# =============================================
# CHANNEL MESSAGES
# =============================================
CHANNEL_MSGS = [
    """\
Bhai free channel pe ho?

Wahan daily market updates aate hain.
General analysis, important levels, occasional signals.

Join karo - kuch nahi jaata - sab free hai.""",

    """\
Ek kaam karo abhi -

Free channel join karo mere saath.
Market updates, analysis, tips - daily aate hain.

Baad mein VIP sochna - pehle free mein dekho kaam kaise karta hai.""",
]

# =============================================
# KEYBOARDS
# =============================================
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("VIP Signals Join Karo", callback_data="vip")],
        [InlineKeyboardButton("XM Trading Platform", callback_data="xm")],
        [InlineKeyboardButton("Prop Funded Account", callback_data="prop")],
        [InlineKeyboardButton("Free Channel Join", url=CHANNEL_URL)],
    ])

def kb_vip():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Admin se Baat Karo", url=VIP_URL)],
        [InlineKeyboardButton("Free Channel Dekho", url=CHANNEL_URL)],
        [InlineKeyboardButton("Wapis Jao", callback_data="start")],
    ])

def kb_xm():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("XM Join Karo FREE", url=XM_URL)],
        [InlineKeyboardButton("Weekly 25K Contest", url=XM_URL)],
        [InlineKeyboardButton("VIP Signals bhi lo", callback_data="vip")],
        [InlineKeyboardButton("Wapis Jao", callback_data="start")],
    ])

def kb_prop():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Prop Account Details", url=PROP_URL)],
        [InlineKeyboardButton("Admin se Poochho", url=VIP_URL)],
        [InlineKeyboardButton("XM Bhi Dekho", callback_data="xm")],
        [InlineKeyboardButton("Wapis Jao", callback_data="start")],
    ])

def kb_channel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Free Channel Join", url=CHANNEL_URL)],
        [InlineKeyboardButton("VIP ke liye Admin", url=VIP_URL)],
    ])

# =============================================
# HANDLERS
# =============================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(WELCOME_MSGS), reply_markup=kb_main())

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "start":
        await q.message.reply_text(random.choice(WELCOME_MSGS), reply_markup=kb_main())

    elif q.data == "vip":
        await q.message.reply_text(random.choice(VIP_MSGS), reply_markup=kb_vip())

    elif q.data == "xm":
        await q.message.reply_text(random.choice(XM_MSGS), reply_markup=kb_xm())

    elif q.data == "prop":
        await q.message.reply_text(random.choice(PROP_MSGS), reply_markup=kb_prop())

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(VIP_MSGS), reply_markup=kb_vip())

async def cmd_xm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(XM_MSGS), reply_markup=kb_xm())

async def cmd_prop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(PROP_MSGS), reply_markup=kb_prop())

# =============================================
# AUTO POSTS TO CHANNEL
# =============================================
async def auto_xm(app):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("XM Join Karo FREE", url=XM_URL)],
        [InlineKeyboardButton("Weekly 25K Contest", url=XM_URL)],
        [InlineKeyboardButton("Bot Start Karo", url=BOT_URL)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL, text=random.choice(XM_MSGS), reply_markup=kb)
        log.info("XM promo posted")
    except Exception as e:
        log.error("auto_xm: " + str(e))

async def auto_prop(app):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Prop Account Details", url=PROP_URL)],
        [InlineKeyboardButton("Admin se Poochho", url=VIP_URL)],
        [InlineKeyboardButton("Bot Start Karo", url=BOT_URL)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL, text=random.choice(PROP_MSGS), reply_markup=kb)
        log.info("Prop promo posted")
    except Exception as e:
        log.error("auto_prop: " + str(e))

async def auto_vip(app):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Admin se Baat Karo", url=VIP_URL)],
        [InlineKeyboardButton("Free Channel Join", url=CHANNEL_URL)],
        [InlineKeyboardButton("Bot Start Karo", url=BOT_URL)],
    ])
    try:
        await app.bot.send_message(chat_id=CHANNEL, text=random.choice(VIP_MSGS), reply_markup=kb)
        log.info("VIP promo posted")
    except Exception as e:
        log.error("auto_vip: " + str(e))

# =============================================
# MAIN
# =============================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("xm", cmd_xm))
    app.add_handler(CommandHandler("prop", cmd_prop))
    app.add_handler(CallbackQueryHandler(cb))

    sched = AsyncIOScheduler()
    # XM promo - din mein 3 baar
    sched.add_job(auto_xm, "cron", hour="9,14,19", minute=0, args=[app])
    # Prop promo - din mein 2 baar
    sched.add_job(auto_prop, "cron", hour="11,17", minute=30, args=[app])
    # VIP promo - din mein 2 baar
    sched.add_job(auto_vip, "cron", hour="10,16", minute=0, args=[app])
    sched.start()

    log.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
