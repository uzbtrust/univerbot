from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import WEEKLY_PRICE, DAY15_PRICE, MONTHLY_PRICE

non_premium = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📢 Kanal biriktirish', callback_data='channel')],
    [InlineKeyboardButton(text='⚙️ Kanallarni boshqarish', callback_data='manage_channels')],
    [InlineKeyboardButton(text='⭐ Premium sotib olish', callback_data='premium')]
])

premium = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💎 Kanal biriktirish', callback_data='channel')],
    [InlineKeyboardButton(text='⚙️ Kanallarni boshqarish', callback_data='manage_channels')],
    [InlineKeyboardButton(text='🛠️ Texnik yordam', callback_data='tech_support')]
])

premium_buy = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f'⚡ 1 haftalik - {WEEKLY_PRICE} so\'m', callback_data='weekly')],
    [InlineKeyboardButton(text=f'🔥 15 kunlik - {DAY15_PRICE} so\'m', callback_data='day15')],
    [InlineKeyboardButton(text=f'💎 1 oylik - {MONTHLY_PRICE} so\'m', callback_data='monthly')],
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='sub_back')]
])

premium_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='sub_back')]
])

add_bot_to_channel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='➕ Botni kanalga qo\'shish', url='https://t.me/YourBotUsername?startchannel=true')],
    [InlineKeyboardButton(text='✅ Qo\'shdim, davom etish', callback_data='bot_added')]
])

p_add_bot_to_channel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='➕ Botni kanalga qo\'shish', url='https://t.me/YourBotUsername?startchannel=true')],
    [InlineKeyboardButton(text='✅ Qo\'shdim, davom etish', callback_data='p_bot_added')]
])

make_bot_admin_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Tekshirish', callback_data='channel_check'),
     InlineKeyboardButton(text='🔄 Boshqa habar', callback_data='another')]
])

p_make_bot_admin_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Tekshirish', callback_data='p_channel_check'),
     InlineKeyboardButton(text='🔄 Boshqa habar', callback_data='p_another')]
])

make_bot_admin = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Tekshirish', callback_data='channel_check')]
])

p_make_bot_admin = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Tekshirish', callback_data='p_channel_check')]
])

admin_confirm = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Ha', callback_data='admin_yes')],
    [InlineKeyboardButton(text="❌ Yo'q", callback_data='admin_no')]
])

premium_admin_confirm = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Ha', callback_data='p_admin_yes')],
    [InlineKeyboardButton(text="❌ Yo'q", callback_data='p_admin_no')]
])

back_to_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='back')]
])

p_back_to_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='p_back')]
])

cheque_check = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Qabul qilish', callback_data='approve'),
     InlineKeyboardButton(text='❌ Rad etish', callback_data='reject')]
])

admin_panel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📊 Statistika', callback_data='admin_stats')],
    [InlineKeyboardButton(text='📢 Xabar yuborish', callback_data='admin_broadcast')],
    [InlineKeyboardButton(text='⚙️ Bot sozlamalari', callback_data='admin_settings')],
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='back')]
])

superadmin_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📢 Kanal biriktirish', callback_data='channel')],
    [InlineKeyboardButton(text='⚙️ Kanallarni boshqarish', callback_data='manage_channels')],
    [InlineKeyboardButton(text='⭐ Premium sotib olish', callback_data='premium')],
    [InlineKeyboardButton(text='👑 Admin Panel', callback_data='admin_panel')]
])

superadmin_premium_main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💎 Kanal biriktirish', callback_data='channel')],
    [InlineKeyboardButton(text='⚙️ Kanallarni boshqarish', callback_data='manage_channels')],
    [InlineKeyboardButton(text='🛠️ Texnik yordam', callback_data='tech_support')],
    [InlineKeyboardButton(text='👑 Admin Panel', callback_data='admin_panel')]
])

confirm_broadcast = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Tasdiqlash', callback_data='confirm_broadcast')],
    [InlineKeyboardButton(text='❌ Bekor qilish', callback_data='cancel_broadcast')]
])

image_toggle = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🖼️ Ha, rasm qo\'shish', callback_data='image_yes')],
    [InlineKeyboardButton(text='❌ Yo\'q, rasm kerak emas', callback_data='image_no')]
])

premium_image_toggle = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🖼️ Ha, rasm qo\'shish', callback_data='p_image_yes')],
    [InlineKeyboardButton(text='❌ Yo\'q, rasm kerak emas', callback_data='p_image_no')]
])

bot_settings_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💳 To\'lov sozlamalari', callback_data='settings_payment')],
    [InlineKeyboardButton(text='📊 Limitlar', callback_data='settings_limits')],
    [InlineKeyboardButton(text='🖼️ Rasm rejimi', callback_data='settings_image')],
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='admin_panel')]
])

payment_settings_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💳 Karta raqami', callback_data='edit_card_number')],
    [InlineKeyboardButton(text='👤 Karta egasi ismi', callback_data='edit_card_name')],
    [InlineKeyboardButton(text='👤 Karta egasi familiyasi', callback_data='edit_card_surname')],
    [InlineKeyboardButton(text='💰 Haftalik narx', callback_data='edit_weekly_price')],
    [InlineKeyboardButton(text='💰 15 kunlik narx', callback_data='edit_day15_price')],
    [InlineKeyboardButton(text='💰 Oylik narx', callback_data='edit_monthly_price')],
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='admin_settings')]
])

limits_settings_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📝 Free post limiti', callback_data='edit_max_posts_free')],
    [InlineKeyboardButton(text='📝 Premium post limiti', callback_data='edit_max_posts_premium')],
    [InlineKeyboardButton(text='📢 Free kanal limiti', callback_data='edit_max_channels_free')],
    [InlineKeyboardButton(text='📢 Premium kanal limiti', callback_data='edit_max_channels_premium')],
    [InlineKeyboardButton(text='📝 Free mavzu so\'z limiti', callback_data='edit_max_theme_words_free')],
    [InlineKeyboardButton(text='📝 Premium mavzu so\'z limiti', callback_data='edit_max_theme_words_premium')],
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='admin_settings')]
])

back_to_settings = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='◀️ Orqaga', callback_data='admin_settings')]
])
