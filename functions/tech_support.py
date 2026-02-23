import re
import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram import Bot

from states import TechnicalSupport
from keyboards.inline import p_back_to_main
from utils.database import db
from config import ADMIN_GROUP_ID

logger = logging.getLogger(__name__)

# Suhbat mapping: user_id <-> group_msg_id
# {user_id: group_msg_id} va {group_msg_id: user_id}
_user_to_group = {}
_group_to_user = {}


def _save_mapping(user_id: int, group_msg_id: int):
    """User va guruh xabar ID lari orasidagi bog'lanishni saqlash."""
    _user_to_group[user_id] = group_msg_id
    _group_to_user[group_msg_id] = user_id


def _find_user_from_reply(message: Message) -> int | None:
    """Guruhda reply qilingan xabardan user_id topish."""
    replied = message.reply_to_message
    if not replied:
        return None

    # 1. Matn yoki caption dan User ID ajratish
    text = replied.text or replied.caption or ""
    match = re.search(r"User ID:?\s*(?:<code>)?(\d+)(?:</code>)?", text)
    if match:
        return int(match.group(1))

    # 2. Mapping dan qidiruv
    return _group_to_user.get(replied.message_id)


async def request_support(call: CallbackQuery, state: FSMContext):
    try:
        user_id = call.from_user.id

        if not await db.is_premium_user(user_id):
            await call.answer(
                "Texnik yordam faqat premium foydalanuvchilar uchun mavjud!",
                show_alert=True
            )
            return

        await call.message.delete()
        await call.message.answer(
            "<b>TEXNIK YORDAM</b>\n\n"
            "Assalomu alaykum!\n\n"
            "Sizning xabaringiz to'g'ridan-to'g'ri admin guruhiga yuboriladi.\n"
            "Iltimos muammoyingizni batafsil yozing:\n\n"
            "<i>Masalan:</i>\n"
            "- Post yuklanmayapti\n"
            "- Vaqt noto'g'ri ishlayapti\n"
            "- Kanal qo'sha olmayapman\n\n"
            "Admin javob berishi odatda 10-30 daqiqa ichida.",
            reply_markup=p_back_to_main,
            parse_mode='HTML'
        )
        await state.set_state(TechnicalSupport.WAITING_MESSAGE)

    except Exception as e:
        logger.error(f"Error in request_support: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = message.from_user.id
        user_name = message.from_user.full_name
        username = message.from_user.username or "Yo'q"

        if not await db.is_premium_user(user_id):
            await message.answer(
                "Texnik yordam faqat premium foydalanuvchilar uchun mavjud!",
                reply_markup=p_back_to_main
            )
            await state.clear()
            return

        if not message.text:
            await message.answer(
                "Iltimos muammoyingizni matn shaklida yozing.\n"
                "Rasm yoki stiker yuborish mumkin emas.",
                reply_markup=p_back_to_main
            )
            return

        admin_message = (
            f"<b>TEXNIK YORDAM SO'ROVI</b>\n\n"
            f"Foydalanuvchi: {user_name}\n"
            f"User ID: <code>{user_id}</code>\n"
            f"Username: @{username}\n"
            f"Status: Premium\n\n"
            f"<b>Muammo:</b>\n"
            f"{message.text}\n\n"
            f"Vaqt: {message.date.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Agar suhbat davom etayotgan bo'lsa — reply qilib yuborish
        reply_to = _user_to_group.get(user_id)

        sent = await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=admin_message,
            parse_mode='HTML',
            reply_to_message_id=reply_to
        )

        _save_mapping(user_id, sent.message_id)

        await message.answer(
            "<b>Xabar yuborildi!</b>\n\n"
            "Sizning muammoyingiz admin guruhiga yuborildi.\n"
            "Tez orada javob olasiz.\n\n"
            "Sabr qilganingiz uchun rahmat!",
            reply_markup=p_back_to_main,
            parse_mode='HTML'
        )

        await state.set_state(TechnicalSupport.WAITING_REPLY)
        logger.info(f"Support request from premium user {user_id} sent to admin")

    except Exception as e:
        logger.error(f"Error in process_support_message: {e}", exc_info=True)
        await message.answer(
            "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.",
            reply_markup=p_back_to_main
        )
        await state.clear()


async def handle_group_reply(message: Message, bot: Bot, storage):
    """Guruhda admin bot xabariga reply qilganda — userga yuborish."""
    try:
        user_id = _find_user_from_reply(message)
        if not user_id:
            return

        admin_name = message.from_user.full_name

        await bot.send_message(
            chat_id=user_id,
            text=f"<b>Admin javobi ({admin_name}):</b>\n\n"
                 f"{message.text}\n\n"
                 f"<i>Javob yozishingiz mumkin.</i>",
            parse_mode='HTML'
        )

        _save_mapping(user_id, message.message_id)

        # User FSM state ni WAITING_REPLY ga o'rnatish (boshqa chat uchun)
        key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        ctx = FSMContext(storage=storage, key=key)
        await ctx.set_state(TechnicalSupport.WAITING_REPLY)

        logger.info(f"Admin reply forwarded to user {user_id}")

    except Exception as e:
        logger.error(f"Error in handle_group_reply: {e}", exc_info=True)


async def process_support_reply(message: Message, state: FSMContext, bot: Bot):
    """User admin javobiga reply qilganda — guruhga yuborish."""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.full_name

        if not message.text:
            await message.answer(
                "Iltimos matn shaklida yozing.",
                reply_markup=p_back_to_main
            )
            return

        reply_text = (
            f"<b>Foydalanuvchi javobi</b>\n\n"
            f"Foydalanuvchi: {user_name}\n"
            f"User ID: <code>{user_id}</code>\n\n"
            f"{message.text}"
        )

        reply_to = _user_to_group.get(user_id)

        sent = await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=reply_text,
            parse_mode='HTML',
            reply_to_message_id=reply_to
        )

        _save_mapping(user_id, sent.message_id)

        await message.answer(
            "Javobingiz yuborildi! Admin tez orada javob beradi.",
            reply_markup=p_back_to_main
        )

        await state.set_state(TechnicalSupport.WAITING_REPLY)
        logger.info(f"User {user_id} reply forwarded to admin group")

    except Exception as e:
        logger.error(f"Error in process_support_reply: {e}", exc_info=True)
        await message.answer(
            "Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            reply_markup=p_back_to_main
        )
        await state.clear()
