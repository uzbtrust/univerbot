# UniverBot - Telegram Kanal Avtomatlashtirish Boti

Telegram kanallar uchun avtomatik post yaratish va boshqarish boti. AI (Grok) yordamida kontent yaratish va rasm generatsiya qilish imkoniyati mavjud.

## Xususiyatlar

- **Avtomatik postlar** - Belgilangan vaqtda avtomatik post yaratish
- **AI kontent** - Grok AI yordamida matn yaratish
- **Rasm generatsiya** - Premium foydalanuvchilar uchun AI rasm yaratish
- **Premium obuna** - Kengaytirilgan imkoniyatlar
- **Admin panel** - Bot sozlamalarini boshqarish

## O'rnatish

### 1. Repositoriyani klonlash
```bash
git clone https://github.com/uzbtrust/univerbot.git
cd univerbot
```

### 2. Virtual environment yaratish
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Dependencylarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. .env faylini sozlash
```env
# Bot Configuration
BOT_TOKEN=your_bot_token_here

# Admin IDs
SUPER_ADMIN1=your_telegram_id
SUPER_ADMIN2=0

# Payment Prices (in so'm)
WEEKLY_PRICE=5000
DAY15_PRICE=10000
MONTHLY_PRICE=20000

# Payment Card Details
CARD_NUMBER=your_card_number
CARD_NAME=Ism
CARD_SURNAME=Familiya

# Channel and Post Limits
MAX_CHANNELS_FREE=1
MAX_CHANNELS_PREMIUM=2
MAX_POSTS_FREE=3
MAX_POSTS_PREMIUM=15

# Theme Word Limits
MAX_THEME_WORDS_FREE=10
MAX_THEME_WORDS_PREMIUM=15

# Grok API Configuration
GROK_API_KEY=your_grok_api_key
GROK_BASE_URL=https://api.x.ai/v1

# Image Mode (ON/OFF)
IMAGE_MODE=ON

# Timezone
TIMEZONE=Asia/Tashkent
```

### 5. Botni ishga tushirish
```bash
python main.py
```

## Loyiha tuzilishi

```
univerbot/
├── main.py                 # Asosiy bot fayli
├── config.py               # Konfiguratsiya
├── states.py               # FSM holatlar
├── requirements.txt        # Dependencylar
├── .env                    # Muhit o'zgaruvchilari
├── functions/
│   ├── starting.py         # Start komandasi
│   ├── channel.py          # Free kanal funksiyalari
│   ├── premium_channel.py  # Premium kanal funksiyalari
│   ├── premium_sub.py      # Obuna funksiyalari
│   ├── admin_panel.py      # Admin panel
│   ├── channel_management.py # Kanal boshqaruvi
│   ├── my_chann.py         # Kanal tahrirlash
│   └── tech_support.py     # Texnik yordam
├── keyboards/
│   ├── inline.py           # Inline tugmalar
│   └── reply.py            # Reply tugmalar
├── utils/
│   ├── database.py         # Database manager
│   ├── validators.py       # Validatorlar
│   ├── helpers.py          # Yordamchi funksiyalar
│   ├── env_manager.py      # .env boshqaruvi
│   └── security.py         # Xavfsizlik
└── services/
    ├── post_scheduler.py   # Post rejalashtirish
    └── grok_client.py      # Grok AI client
```

## Foydalanish

### Oddiy foydalanuvchi
1. `/start` - Botni ishga tushirish
2. "Kanal biriktirish" - Kanalingizni qo'shish
3. Post vaqti va mavzusini belgilash

### Premium foydalanuvchi
- Kuniga 15 tagacha post
- 2 ta kanal biriktirish
- AI rasm generatsiya
- Texnik yordam

### Admin
- Statistika ko'rish
- Reklama yuborish
- Bot sozlamalarini o'zgartirish
- To'lov ma'lumotlarini tahrirlash

## 24-soatlik cheklov

Post vaqtini o'zgartirish 24 soatlik cheklovga ega:
- Vaqt o'zgartirilgandan so'ng 24 soat kutish kerak
- Mavzuni istalgan payt o'zgartirish mumkin
- Free va premium uchun bir xil

## Texnologiyalar

- **Python 3.10+**
- **aiogram 3.24** - Telegram Bot API
- **SQLite** - Database
- **Grok AI** - Kontent generatsiya
- **httpx** - HTTP client

## Litsenziya

MIT License

---

Developed with ❤️ by uzbtrust
