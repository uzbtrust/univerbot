import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram.types import Message, CallbackQuery

from utils.database import db
from keyboards.inline import non_premium, premium, superadmin_main, superadmin_premium_main
from config import STICKERS, MESSAGES, WEEKLY_PRICE, DAY15_PRICE, MONTHLY_PRICE

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")


async def _get_premium_info_text(user_id: int) -> str:
    """Premium foydalanuvchi uchun obuna ma'lumotlari."""
    info = await db.get_user_premium_info(user_id)
    if not info:
        return ""

    is_sub, p_type, start_date, end_date, _ = info
    if not is_sub:
        return ""

    lines = []
    type_names = {
        "weekly": "Haftalik", "15days": "15 kunlik", "monthly": "Oylik",
        "referral": "Referral", "unknown": ""
    }
    type_label = type_names.get(p_type, p_type or "")
    if type_label:
        lines.append(f"⭐ Premium: {type_label}")

    if end_date:
        try:
            end_dt = datetime.fromisoformat(str(end_date))
            lines.append(f"📅 Tugash: {end_dt.strftime('%Y-%m-%d')}")
        except (ValueError, TypeError):
            pass

    if lines:
        return "\n".join(lines) + "\n\n"
    return ""


async def greating(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        message = event.message
        user = event.from_user
        try:
            await event.message.delete()
        except:
            pass
        referral_arg = None
    else:
        message = event
        user = event.from_user
        # Deep link: /start ref_123456
        args = event.text.split(maxsplit=1)
        referral_arg = args[1] if len(args) > 1 and args[1].startswith("ref_") else None

    user_id = user.id
    full_name = user.full_name

    try:
        if await db.is_superadmin(user_id):
            is_prem = await db.is_premium_user(user_id)
            premium_info = await _get_premium_info_text(user_id) if is_prem else ""

            if is_prem:
                await message.answer(
                    f'SUPERADMIN PANEL\n\n'
                    f'Assalomu alaykum, {full_name}!\n\n'
                    f'{premium_info}'
                    f'Sizda barcha admin va premium huquqlar mavjud.',
                    reply_markup=superadmin_premium_main,
                    parse_mode='HTML'
                )
            else:
                await message.answer(
                    f'SUPERADMIN PANEL\n\n'
                    f'Assalomu alaykum, {full_name}!',
                    reply_markup=superadmin_main,
                    parse_mode='HTML'
                )
            logger.info(f"Superadmin {user_id} accessed the bot")
            return

        if not await db.user_exists(user_id):
            await db.add_user(user_id, subscription=False)

            # Referral deep link tekshirish
            if referral_arg:
                try:
                    referrer_id = int(referral_arg.replace("ref_", ""))
                    if referrer_id != user_id and await db.user_exists(referrer_id):
                        await db.add_referral(referrer_id, user_id)
                        from functions.referral import notify_referrer_joined
                        await notify_referrer_joined(referrer_id, full_name, event.bot)
                        logger.info(f"Referral: {user_id} invited by {referrer_id}")
                except (ValueError, TypeError):
                    pass

            welcome_text = (
                f"<b>Xush kelibsiz!</b>\n\n"
                f"Assalomu alaykum, {full_name}!\n\n"
                f"Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
                f"<b>Botimiz imkoniyatlari:</b>\n"
                f"- Avtomatik postlar yaratish\n"
                f"- Kanallarni boshqarish\n"
                f"- Vaqt rejalashtirish\n\n"
                f"<i>Premium obuna bilan ko'proq imkoniyatlar!</i>"
            )

            await message.answer(
                welcome_text,
                reply_markup=non_premium,
                parse_mode='HTML'
            )
            logger.info(f"New user registered: {user_id}")
        else:
            if await db.is_premium_user(user_id):
                premium_info = await _get_premium_info_text(user_id)
                welcome_msg = MESSAGES["welcome_premium"].format(name=full_name)
                if premium_info:
                    welcome_msg += f"\n{premium_info}"
                await message.answer(
                    welcome_msg,
                    reply_markup=premium,
                    parse_mode='HTML'
                )
            else:
                welcome_msg = MESSAGES["welcome_free"].format(name=full_name)
                await message.answer(
                    welcome_msg,
                    reply_markup=non_premium,
                    parse_mode='HTML'
                )
    except Exception as e:
        logger.error(f"Error in greating handler: {e}", exc_info=True)
        await message.answer("Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
