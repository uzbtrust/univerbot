from __future__ import annotations
import logging
from typing import Dict
from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from keyboards.inline import InlineKeyboardMarkup
from keyboards.reply import ReplyKeyboardMarkup
from utils.database import db

logger = logging.getLogger(__name__)


async def verify_bot_admin_status(
    bot: Bot,
    channel_id: int,
    user_id: int,
    call: CallbackQuery,
    state: FSMContext,
    context_storage: Dict[int, int],
    is_premium: bool,
    reply_keyboard: ReplyKeyboardMarkup,
) -> bool:
    if db.channel_exists(channel_id, premium=is_premium):
        await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
        await state.clear()
        if user_id in context_storage:
            del context_storage[user_id]
        return False

    bot_id = (await bot.me()).id

    try:
        member = await bot.get_chat_member(channel_id, bot_id)
        if member.status in ("administrator", "creator"):
            if db.channel_exists(channel_id, premium=is_premium):
                await call.answer("Bu kanal allaqachon qo'shilgan", show_alert=True)
                await state.clear()
                if user_id in context_storage:
                    del context_storage[user_id]
                return False

            db.add_channel(channel_id, user_id, premium=is_premium)

            await call.message.delete()
            await call.message.answer(
                "Kanal qo'shildi!\n\nKanalinggizga bir kunda nechta post tashlamoqchisiz?",
                reply_markup=reply_keyboard
            )
            await state.clear()
            channel_type = "Premium" if is_premium else "Free"
            logger.info(f"{channel_type} channel {channel_id} added for user {user_id}")
            return True
        else:
            await call.answer("Bot hali admin emas. Iltimos botni kanalda admin qiling.", show_alert=True)
            return False
    except Exception as e:
        logger.error(f"Error checking bot admin status: {e}")
        await call.answer("Iltimos botni kanalda admin qiling", show_alert=True)
        return False


__all__ = ["verify_bot_admin_status"]
