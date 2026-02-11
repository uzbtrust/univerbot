# UniverBot

Telegram kanallar uchun avtomatik post yaratish va joylashtirish boti.

## Imkoniyatlar

- **Avtomatik post yaratish** - Grok AI yordamida berilgan mavzu bo'yicha post generatsiya qilish
- **Jadval bo'yicha joylash** - Belgilangan vaqtda postlarni avtomatik joylash
- **Ko'p kanal qo'llab-quvvatlash** - Bir nechta kanallarni boshqarish
- **Premium obuna** - Kengaytirilgan imkoniyatlar (ko'proq postlar, rasmli postlar)
- **HTML formatlash** - Qalin, kursiv matn qo'llab-quvvatlash

## O'rnatish

1. Reponi klonlash:
```bash
git clone https://github.com/uzbtrust/univerbot.git
cd univerbot
```

2. Virtual muhit yaratish:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

3. Kutubxonalarni o'rnatish:
```bash
pip install -r requirements.txt
```

4. `.env` faylini sozlash:
```
BOT_TOKEN=your_bot_token
GROK_API_KEY=your_grok_api_key
ADMIN_IDS=123456789
```

5. Botni ishga tushirish:
```bash
python main.py
```

## Foydalanish

1. Botga `/start` buyrug'ini yuboring
2. "Kanal qo'shish" tugmasini bosing
3. Kanalingizni tanlang va postlar jadvalini sozlang
4. Bot avtomatik ravishda belgilangan vaqtda post yaratib joylaydi

## Texnologiyalar

- Python 3.10+
- aiogram 3.x
- SQLite
- Grok AI

## Muallif

Abdurakhmonov Dostonbek

---

Made with ❤️ by uzbtrust
