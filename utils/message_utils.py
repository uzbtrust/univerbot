"""Xabar boshqarish yordamchi funksiyalari.

Kanal registratsiya jarayonida xabarlarni tartibli o'chirish uchun:
- Eski bot promptlari o'chiriladi (yangi prompt kelganda)
- Xato xabarlari o'chirilMAYDI (foydalanuvchi ko'rishi uchun)
- Yakuniy muvaffaqiyat xabarlari o'chirilMAYDI
- Foydalanuvchi kiritgan matnlar o'chiriladi (chat tozalik uchun)
"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

_PROMPT_KEY = "_bot_prompt_id"


async def safe_delete(message) -> bool:
    """Xabarni xavfsiz o'chirish. Muvaffaqiyatsiz bo'lsa log yozadi."""
    try:
        await message.delete()
        return True
    except TelegramBadRequest:
        return False
    except Exception as e:
        logger.debug(f"Xabar o'chirib bo'lmadi: {e}")
        return False


async def delete_prev_prompt(state: FSMContext, source):
    """State da saqlangan oldingi bot prompt xabarini o'chirish.

    Args:
        state: FSMContext
        source: Message yoki CallbackQuery - bot instance olish uchun kerak
    """
    data = await state.get_data()
    prev_id = data.get(_PROMPT_KEY)
    if not prev_id:
        return

    try:
        if isinstance(source, Message):
            await source.bot.delete_message(source.chat.id, prev_id)
        elif isinstance(source, CallbackQuery) and source.message:
            await source.bot.delete_message(source.message.chat.id, prev_id)
    except Exception:
        pass

    await state.update_data(**{_PROMPT_KEY: None})


async def send_prompt(source, state: FSMContext, text: str, **kwargs) -> Message:
    """Yangi prompt yuborish va oldingi promptni o'chirish.

    Keyingi step ga o'tganda bu xabar avtomatik o'chiriladi.

    Args:
        source: Message yoki CallbackQuery
        state: FSMContext
        text: Xabar matni
        **kwargs: message.answer() ga qo'shimcha argumentlar

    Returns:
        Yuborilgan Message
    """
    await delete_prev_prompt(state, source)

    if isinstance(source, CallbackQuery):
        sent = await source.message.answer(text, **kwargs)
    else:
        sent = await source.answer(text, **kwargs)

    await state.update_data(**{_PROMPT_KEY: sent.message_id})
    return sent


async def send_final(source, state: FSMContext, text: str, **kwargs) -> Message:
    """Yakuniy xabar yuborish (o'chirilMAYDI). Oldingi promptni o'chiradi.

    Args:
        source: Message yoki CallbackQuery
        state: FSMContext
        text: Xabar matni
        **kwargs: message.answer() ga qo'shimcha argumentlar

    Returns:
        Yuborilgan Message
    """
    await delete_prev_prompt(state, source)

    if isinstance(source, CallbackQuery):
        return await source.message.answer(text, **kwargs)
    else:
        return await source.answer(text, **kwargs)


async def send_error(source, text: str, **kwargs) -> Message:
    """Xato xabari yuborish (o'chirilMAYDI, track qilinMAYDI).

    Args:
        source: Message yoki CallbackQuery
        text: Xato matni
        **kwargs: message.answer() ga qo'shimcha argumentlar

    Returns:
        Yuborilgan Message
    """
    if isinstance(source, CallbackQuery):
        return await source.message.answer(text, **kwargs)
    else:
        return await source.answer(text, **kwargs)
