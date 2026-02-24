import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_env_int(key: str, default: int = None) -> int:
    value = os.getenv(key)
    if value is None:
        if default is None:
            print(f"❌ ERROR: {key} not configured in .env file")
            sys.exit(1)
        return default
    try:
        return int(value)
    except ValueError:
        print(f"⚠️  Warning: Invalid integer for {key}='{value}', using default {default}")
        return default


def get_env_str(key: str, default: str = None) -> str:
    value = os.getenv(key)
    if value is None:
        if default is None:
            print(f"❌ ERROR: {key} not configured in .env file")
            sys.exit(1)
        return default
    return value


BOT_TOKEN = get_env_str("BOT_TOKEN")


def get_all_super_admins() -> list:
    admins = []
    i = 1
    while True:
        admin_id = os.getenv(f"SUPER_ADMIN{i}")
        if admin_id is None:
            break
        try:
            admin_id_int = int(admin_id)
            if admin_id_int > 0:
                admins.append(admin_id_int)
        except ValueError:
            pass
        i += 1
    return admins


SUPER_ADMINS = get_all_super_admins()

if not SUPER_ADMINS:
    print("❌ ERROR: At least one SUPER_ADMIN must be configured in .env file")
    sys.exit(1)

SUPER_ADMIN1 = SUPER_ADMINS[0] if len(SUPER_ADMINS) > 0 else 0
SUPER_ADMIN2 = SUPER_ADMINS[1] if len(SUPER_ADMINS) > 1 else 0

ADMIN_GROUP_ID = get_env_int("ADMIN_GROUP_ID", 0)

WEEKLY_PRICE = get_env_str("WEEKLY_PRICE", "5000")
DAY15_PRICE = get_env_str("DAY15_PRICE", "10000")
MONTHLY_PRICE = get_env_str("MONTHLY_PRICE", "20000")

CARD_NUMBER = get_env_str("CARD_NUMBER")
CARD_NAME = get_env_str("CARD_NAME")
CARD_SURNAME = get_env_str("CARD_SURNAME")

MAX_CHANNELS_FREE = get_env_int("MAX_CHANNELS_FREE", 1)
MAX_CHANNELS_PREMIUM = get_env_int("MAX_CHANNELS_PREMIUM", 3)
MAX_POSTS_FREE = get_env_int("MAX_POSTS_FREE", 3)
MAX_POSTS_PREMIUM = get_env_int("MAX_POSTS_PREMIUM", 15)

MAX_THEME_WORDS_FREE = get_env_int("MAX_THEME_WORDS_FREE", 10)
MAX_THEME_WORDS_PREMIUM = get_env_int("MAX_THEME_WORDS_PREMIUM", 15)

if MAX_POSTS_FREE < 1 or MAX_POSTS_FREE > 15:
    MAX_POSTS_FREE = 3
if MAX_POSTS_PREMIUM < 1 or MAX_POSTS_PREMIUM > 15:
    MAX_POSTS_PREMIUM = 15

DATABASE_URL = get_env_str("DATABASE_URL")

TIMEZONE = get_env_str("TIMEZONE", "Asia/Tashkent")

GROK_API_KEY = get_env_str("GROK_API_KEY", "")
GROK_BASE_URL = get_env_str("GROK_BASE_URL", "https://api.x.ai/v1")

if not GROK_API_KEY or GROK_API_KEY == "YOUR_GROK_API_KEY_HERE":
    print("⚠️  Warning: GROK_API_KEY not set - AI features will use fallback messages")

GROK_MODEL_PREMIUM = get_env_str("GROK_MODEL_PREMIUM", "grok-4-1-fast-reasoning")
GROK_MODEL_FREE = get_env_str("GROK_MODEL_FREE", "grok-3-mini")
GROK_IMAGE_MODEL = get_env_str("GROK_IMAGE_MODEL", "grok-imagine-image")
GROK_TIMEOUT = get_env_int("GROK_TIMEOUT", 120)
GROK_MAX_TOKENS_FREE = get_env_int("GROK_MAX_TOKENS_FREE", 250)
GROK_MAX_TOKENS_PREMIUM = get_env_int("GROK_MAX_TOKENS_PREMIUM", 400)

# Worker Configuration
SCHEDULER_MIN_WORKERS = get_env_int("SCHEDULER_MIN_WORKERS", 3)
SCHEDULER_MAX_WORKERS = get_env_int("SCHEDULER_MAX_WORKERS", 10)
SCHEDULER_SCALE_THRESHOLD = get_env_int("SCHEDULER_SCALE_THRESHOLD", 5)

# Rate Limiting
GROK_RATE_LIMIT = get_env_int("GROK_RATE_LIMIT", 30)        # req/min
IMAGE_RATE_LIMIT = get_env_int("IMAGE_RATE_LIMIT", 10)       # req/min
TELEGRAM_RATE_LIMIT = get_env_int("TELEGRAM_RATE_LIMIT", 25)  # msg/sec

GROK_PROMPT_FREE = get_env_str(
    "GROK_PROMPT_FREE",
    """Telegram post yoz. Mavzu: {user_words}
BUGUN: {today}

QOIDALAR:
- 40-60 so'z
- Oddiy, tushunarli til
- 1-2 emoji
- Faqat post matni, boshqa hech narsa
- Yangilik/Sport so'ralsa FAQAT bugungi yoki oxirgi kunlardagi voqealarni yoz
- HTML formatlash: <b>qalin</b>, <i>kursiv</i> ishlatasan

MAVZU TURIGA QARAB:
• Yangilik/Sport/Texnologiya → BUGUNGI sana va eng so'nggi real faktlar
• Motivatsiya/Iqtibos → mashhur shaxs ismi va iqtibosi (HAR SAFAR BOSHQA iqtibos va BOSHQA shaxs!)
• Ta'lim/Maslahat → aniq, foydali ma'lumot
• Boshqa → qiziqarli fakt yoki maslahat

MUHIM: Har safar YANGI va TAKRORLANMAYDIGAN kontent yoz! Oldingi postlardagi iqtibos, fakt yoki ma'lumotni qaytarma."""
)

GROK_PROMPT_PREMIUM = get_env_str(
    "GROK_PROMPT_PREMIUM",
    """Professional Telegram kontent menejeri sifatida premium sifatli post yarat.

MAVZU: {user_words}
BUGUN: {today}

MUHIM: Yangilik, sport, voqealar haqida yozganda FAQAT bugungi ({today}) yoki so'nggi kunlardagi real ma'lumotlarni ishlatasan!

TALABLAR:
1. Hajmi: 60-100 so'z
2. Struktura: Hook (diqqatni tortuvchi ochilish) → Asosiy kontent → CTA yoki xulosa
3. Til: Professional, lekin sodda va jozibali
4. Emoji: 2-3 ta strategik joylashtirilgan
5. HTML formatlash: <b>qalin sarlavha</b>, <i>kursiv</i> ishlatasan. Markdown emas, faqat HTML teglar!

KONTENT SIFATI:
• Yangiliklar → BUGUNGI sana, manba, aniq raqamlar
• Sport → So'nggi o'yinlar, o'yinchi ismlari, natijalar, statistika
• Texnologiya → Kompaniya nomlari, versiyalar, xususiyatlar
• Motivatsiya → Mashhur shaxs, original iqtibos, kontekst
• Biznes/Moliya → Raqamlar, foizlar, real misollar
• Ta'lim → Qadamlar, amaliy maslahatlar

MUHIM: Har safar MUTLAQO YANGI va TAKRORLANMAYDIGAN kontent yoz! Oldingi postlardagi iqtibos, fakt, raqam yoki ma'lumotni QAYTARMA. Agar iqtibos so'ralsa - har safar BOSHQA shaxs yoki shu shaxsning BOSHQA iqtibosini ishlat.

Faqat tayyor post matnini ber, hech qanday izoh yoki savol qo'shma."""
)

GROK_IMAGE_PROMPT = get_env_str(
    "GROK_IMAGE_PROMPT",
    """Create a visually striking image for this Telegram post:

"{post_content}"

STYLE REQUIREMENTS:
- Modern, clean, minimalist design
- Vibrant but harmonious color palette
- Professional quality, suitable for social media
- NO text, letters, words, or watermarks in the image
- High contrast, eye-catching composition
- Relevant visual metaphors matching the post mood

OUTPUT: Single cohesive image, 1:1 aspect ratio, photorealistic or high-quality illustration style."""
)

# Referral thresholds (Ramazon)
REFERRAL_TIER1_COUNT = get_env_int("REFERRAL_TIER1_COUNT", 5)
REFERRAL_TIER1_DAYS = get_env_int("REFERRAL_TIER1_DAYS", 7)
REFERRAL_TIER2_COUNT = get_env_int("REFERRAL_TIER2_COUNT", 10)
REFERRAL_TIER2_DAYS = get_env_int("REFERRAL_TIER2_DAYS", 14)
REFERRAL_TIER3_COUNT = get_env_int("REFERRAL_TIER3_COUNT", 18)
REFERRAL_TIER3_DAYS = get_env_int("REFERRAL_TIER3_DAYS", 30)

IMAGE_MODE = get_env_str("IMAGE_MODE", "OFF").upper() == "ON"

LOG_LEVEL = get_env_str("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    LOG_LEVEL = "INFO"

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

STICKERS = {
    "welcome": "CAACAgIAAxkBAAEMxhJnO7pHAAGqCmW5AAHlhM0IzQrGKU8AAjcBAAJWnb0KHVfiXFqh8Xc2BA",
    "premium_welcome": "CAACAgIAAxkBAAEMxhRnO7pYpyLc3PcvQGBbAAGSpZa6dwACOAEAAladvQofKXrT7pPPNjYE",
    "success": "CAACAgIAAxkBAAEMxhZnO7pcLRx2qMJAAczQNPqhKpswAAI5AQACVp29Cn9X0w4AAWxnczYE",
    "premium_success": "CAACAgIAAxkBAAEMxhhnO7pgAAFMcMLu8fQsJUaD9EpL4gACOgEAAladvQpveNz3A_GGPjYE",
    "error": "CAACAgIAAxkBAAEMxhpnO7pkd1q_T4SWxNlrcWLAAZ5-AAI7AQACVp29CqFN9uAAAShVAzYE",
    "thinking": "CAACAgIAAxkBAAEMxhxnO7poN_9XCo0eAAGZ4AaBwj8QAAFWAAI8AQACVp29CqRO5zqTD5f6NgQ",
    "premium_feature": "CAACAgIAAxkBAAEMxh5nO7ps-YbJf0rQAAHxfLsJdMSmAAI9AQACVp29CgABlS7WVwVWNjYE",
    "payment": "CAACAgIAAxkBAAEMxiBnO7pwAAEWTaUAAd-6pRxO8Z3WcQACPgEAAladvQr5_K2hJ_8vUTYE",
    "channel": "CAACAgIAAxkBAAEMxiJnO7p0bAqw8QW_1lvpP1JW1PoAAj8BAAJWnb0Kgg0hV3pSgj82BA",
    "admin": "CAACAgIAAxkBAAEMxiRnO7p4Dk-Q7cKk6pBGnwGpAAFKAAJAAQACVp29CouDr_SoqgZTNgQ",
}

EMOJI = {
    "premium": "⭐💎✨🌟🎯🚀💰🏆🎁👑",
    "success": "✅✓☑️✔️",
    "error": "❌⛔❗⚠️",
    "time": "⏰🕐🕑🕒🕓🕔🕕",
    "channel": "📢📣📡📻",
    "post": "📝✍️📄📃",
    "stats": "📊📈📉💹",
    "money": "💰💵💸💴💶💷",
    "loading": "⏳⌛",
}

MESSAGES = {
    "welcome_premium": """
╔═══════════════════════╗
║   ⭐ PREMIUM PANEL ⭐   ║
╚═══════════════════════╝

Assalomu alaykum, {name}! 👑

Siz premium foydalanuvchi sifatida quyidagi imkoniyatlarga egasiz:

✨ Kuniga 15 tagacha post
💎 3 ta kanal biriktirish
🎨 AI orqali rasm yaratish
🤖 Grok AI Premium bilan matn
🛡️ Tezkor texnik yordam (24/7)

Quyidagi tugmalardan birini tanlang:
""",

    "welcome_free": """
👋 Assalomu alaykum, {name}!

Botimizga xush kelibsiz!

Siz quyidagi imkoniyatlardan foydalanishingiz mumkin:

📢 1 ta kanal biriktirish
📝 Kuniga 3 tagacha post
⏰ Avtomatik postlar

💡 Ko'proq imkoniyatlar uchun Premium obunani sotib oling!
""",

    "premium_features": """
⭐ PREMIUM OBUNA IMKONIYATLARI ⭐

✅ Kuniga 15 tagacha avtomatik post
✅ 3 ta kanal biriktirish
✅ AI yordamida rasm yaratish
✅ Grok AI Premium bilan matn yaratish
✅ Tezkor texnik yordam (24/7)

💰 Narxlar:
• 1 haftalik - {weekly} so'm
• 15 kunlik - {day15} so'm
• 1 oylik - {monthly} so'm

🎯 Premium obuna bilan kanalingizni yangi bosqichga olib chiqing!
""",

    "channel_added": """
✅ KANAL MUVAFFAQIYATLI QO'SHILDI!

Tabriklaymiz! Kanalingiz tizimga qo'shildi. 🎉

Endi siz:
📝 Post vaqtlarini belgilashingiz
🎯 Mavzularni kiritishingiz
⏰ Avtomatik postlardan foydalanishingiz mumkin

Keyingi qadamga o'tamiz...
""",

    "payment_instruction": """
💳 TO'LOV MA'LUMOTLARI

Premium obunani faollashtirish uchun:

1️⃣ Quyidagi karta raqamiga {price} so'm o'tkazing
2️⃣ To'lov chekini bu yerga yuboring
3️⃣ Admin tasdiqlashini kuting

💳 Karta: `{card_number}`
👤 Egasi: {card_name} {card_surname}

⏳ Tasdiqlash odatda 5-10 daqiqa ichida amalga oshiriladi.
""",

    "time_edit_restricted": """
⏰ VAQTNI O'ZGARTIRISH CHEKLANGAN

Hurmatli foydalanuvchi!

Vaqtni o'zgartirish faqat 24 soatda bir marta mumkin.

⏳ Keyingi o'zgartirish: {hours} soatdan keyin
📅 Oxirgi o'zgartirish: {last_edit}

💡 Bu cheklov tizimni barqaror ishlashi uchun qo'yilgan.
""",

    "post_scheduled": """
✅ POSTLAR MUVAFFAQIYATLI SOZLANDI!

{count} ta post belgilangan vaqtlarda avtomatik nashr qilinadi:

{schedule}

🎯 Postlar belgilangan vaqtda kanalingizga avtomatik yuboriladi!
💡 Postlar ro'yxatini "Kanallarni boshqarish" orqali ko'rishingiz mumkin.
""",
}
