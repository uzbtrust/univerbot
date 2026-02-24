"""Ramazon referral tizimi — mart 19 gacha vaqtinchalik."""

import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import CallbackQuery, FSInputFile
from aiogram import Bot

from utils.database import db
from keyboards.inline import build_ramadan_gift_kb, referral_back
from config import (
    REFERRAL_TIER1_COUNT, REFERRAL_TIER1_DAYS,
    REFERRAL_TIER2_COUNT, REFERRAL_TIER2_DAYS,
    REFERRAL_TIER3_COUNT, REFERRAL_TIER3_DAYS,
)

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")

IMAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "image.jpg")

TIERS = [
    (REFERRAL_TIER3_COUNT, REFERRAL_TIER3_DAYS, "1 oy"),
    (REFERRAL_TIER2_COUNT, REFERRAL_TIER2_DAYS, "2 hafta"),
    (REFERRAL_TIER1_COUNT, REFERRAL_TIER1_DAYS, "1 hafta"),
]


def _get_current_tier(activated_count: int) -> tuple | None:
    """Faol referrallar soniga qarab hozirgi tier qaytaradi: (count, days, label) yoki None."""
    for count, days, label in TIERS:
        if activated_count >= count:
            return (count, days, label)
    return None


def _get_next_tier(activated_count: int) -> tuple | None:
    """Keyingi tier qaytaradi: (count, days, label) yoki None."""
    for count, days, label in reversed(TIERS):
        if activated_count < count:
            return (count, days, label)
    return None


async def show_ramadan_gift(call: CallbackQuery):
    """Ramazon sovg'asi tugmasi — rasm + referral tushuntirish."""
    try:
        user_id = call.from_user.id
        bot_info = await call.bot.get_me()
        bot_username = bot_info.username

        activated = await db.get_referral_count(user_id, activated_only=True)
        total = await db.get_referral_count(user_id, activated_only=False)

        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        caption = (
            "<b>🎁 RAMAZON SOVG'ASI</b>\n\n"
            "Do'stlaringizni taklif qiling va <b>bepul Premium</b> oling!\n\n"
            "<b>Mukofotlar:</b>\n"
            f"🥉 {REFERRAL_TIER1_COUNT} ta do'st = <b>{REFERRAL_TIER1_DAYS} kun</b> Premium\n"
            f"🥈 {REFERRAL_TIER2_COUNT} ta do'st = <b>{REFERRAL_TIER2_DAYS} kun</b> Premium\n"
            f"🥇 {REFERRAL_TIER3_COUNT} ta do'st = <b>{REFERRAL_TIER3_DAYS} kun</b> Premium\n\n"
            "<b>Shart:</b> Do'stingiz kanal biriktirib, kamida 1 ta post qo'shishi kerak.\n\n"
            f"📊 Taklif qilganlaringiz: <b>{total}</b> | Faol: <b>{activated}</b>\n\n"
            f"👇 <b>Sizning havolangiz:</b>\n"
            f"{ref_link}"
        )

        keyboard = build_ramadan_gift_kb(bot_username, user_id)

        try:
            await call.message.delete()
        except Exception:
            pass

        if os.path.exists(IMAGE_PATH):
            photo = FSInputFile(IMAGE_PATH)
            await call.message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await call.message.answer(
                caption,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error in show_ramadan_gift: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def show_referral_stats(call: CallbackQuery):
    """Shaxsiy referral statistika + top 25 leaderboard."""
    try:
        user_id = call.from_user.id

        activated = await db.get_referral_count(user_id, activated_only=True)
        total = await db.get_referral_count(user_id, activated_only=False)

        current_tier = _get_current_tier(activated)
        next_tier = _get_next_tier(activated)

        text = (
            "<b>📊 REFERRAL STATISTIKANGIZ</b>\n\n"
            f"👥 Jami taklif qilganlar: <b>{total}</b>\n"
            f"✅ Faollashganlar: <b>{activated}</b>\n"
        )

        if current_tier:
            text += f"\n🏆 Hozirgi mukofot: <b>{current_tier[2]} Premium</b>\n"
        else:
            text += f"\n🏆 Hozirgi mukofot: <i>hali yetilmagan</i>\n"

        if next_tier:
            remaining = next_tier[0] - activated
            text += f"🎯 Keyingi bosqich: <b>{next_tier[2]}</b> ({remaining} ta qoldi)\n"
        else:
            text += "🎉 Siz eng yuqori bosqichga yetdingiz!\n"

        # Top 25 leaderboard
        top = await db.get_top_referrers(limit=25)
        if top:
            text += "\n<b>🏅 TOP 25 LEADERBOARD</b>\n\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, (ref_id, count) in enumerate(top):
                medal = medals[i] if i < 3 else f"  {i + 1}."
                marker = " ← siz" if ref_id == user_id else ""
                text += f"{medal} <code>{ref_id}</code> — {count} ta{marker}\n"

        try:
            await call.message.delete()
        except Exception:
            pass

        await call.message.answer(
            text,
            reply_markup=referral_back,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in show_referral_stats: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


async def check_and_award_premium(referrer_id: int, bot: Bot):
    """Referral thresholdni tekshirish va premium berish/uzaytirish.

    Muddat ALMASHTIRILADI, qo'shilmaydi:
    - Premium yo'q: start_date o'zgarmaydi, end_date = start_date + tier_days
    - Premium bor: end_date = referral_base_date + tier_days
    """
    try:
        activated = await db.get_referral_count(referrer_id, activated_only=True)
        tier = _get_current_tier(activated)

        if not tier:
            return

        tier_count, tier_days, tier_label = tier
        now = datetime.now(TZ)

        info = await db.get_user_premium_info(referrer_id)
        if not info:
            return

        is_premium, premium_type, start_date, end_date, referral_base_date = info

        if is_premium and premium_type and premium_type != "referral":
            # Sotib olingan premium bor — uzaytirish
            if not referral_base_date:
                # Birinchi marta referral mukofot — asl end_date ni saqlash
                if end_date:
                    try:
                        base = datetime.fromisoformat(str(end_date))
                        if base.tzinfo is None:
                            base = base.replace(tzinfo=TZ)
                    except (ValueError, TypeError):
                        base = now
                else:
                    base = now
                await db.set_referral_base_date(referrer_id, base.isoformat())
            else:
                try:
                    base = datetime.fromisoformat(str(referral_base_date))
                    if base.tzinfo is None:
                        base = base.replace(tzinfo=TZ)
                except (ValueError, TypeError):
                    base = now

            new_end = base + timedelta(days=tier_days)
            await db.execute_query(
                "UPDATE users SET end_date = ? WHERE id = ?",
                (new_end.isoformat(), referrer_id)
            )

            await bot.send_message(
                chat_id=referrer_id,
                text=f"🎉 <b>Tabriklaymiz!</b>\n\n"
                     f"Siz {activated} ta do'st taklif qildingiz!\n"
                     f"Premium obunangiz <b>{tier_label}</b> ga uzaytirildi.\n"
                     f"Yangi tugash sanasi: <b>{new_end.strftime('%Y-%m-%d')}</b>",
                parse_mode='HTML'
            )
        else:
            # Premium yo'q yoki referral premium — yangi/yangilash
            if not referral_base_date:
                base = now
                await db.set_referral_base_date(referrer_id, base.isoformat())
                new_start = now
            else:
                try:
                    base = datetime.fromisoformat(str(referral_base_date))
                    if base.tzinfo is None:
                        base = base.replace(tzinfo=TZ)
                except (ValueError, TypeError):
                    base = now
                # start_date o'zgarmaydi
                if start_date:
                    try:
                        new_start = datetime.fromisoformat(str(start_date))
                        if new_start.tzinfo is None:
                            new_start = new_start.replace(tzinfo=TZ)
                    except (ValueError, TypeError):
                        new_start = base
                else:
                    new_start = base

            new_end = base + timedelta(days=tier_days)

            await db.update_user_subscription(referrer_id, subscription=True, premium_type="referral")
            await db.execute_query(
                "UPDATE users SET start_date = ?, end_date = ? WHERE id = ?",
                (new_start.isoformat(), new_end.isoformat(), referrer_id)
            )

            # Cache yangilash
            if referrer_id in db._premium_cache:
                del db._premium_cache[referrer_id]

            if not is_premium:
                msg = (
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Siz {activated} ta do'st taklif qildingiz!\n"
                    f"Sizga <b>{tier_label}</b> Premium berildi!\n"
                    f"Tugash sanasi: <b>{new_end.strftime('%Y-%m-%d')}</b>\n\n"
                    f"Endi siz premium imkoniyatlardan foydalanishingiz mumkin!"
                )
            else:
                msg = (
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Siz {activated} ta do'st taklif qildingiz!\n"
                    f"Premium obunangiz <b>{tier_label}</b> ga yangilandi.\n"
                    f"Tugash sanasi: <b>{new_end.strftime('%Y-%m-%d')}</b>"
                )

            await bot.send_message(
                chat_id=referrer_id,
                text=msg,
                parse_mode='HTML'
            )

        logger.info(f"Referral award: user={referrer_id}, tier={tier_label}, activated={activated}")

    except Exception as e:
        logger.error(f"Error in check_and_award_premium: {e}", exc_info=True)


async def notify_referrer_joined(referrer_id: int, new_user_name: str, bot: Bot):
    """Do'st botga qo'shilganda referrerga xabar."""
    try:
        await bot.send_message(
            chat_id=referrer_id,
            text=f"👤 <b>{new_user_name}</b> sizning havolangiz orqali botga qo'shildi!\n\n"
                 f"Mukofot olish uchun u kanal biriktirib, kamida 1 ta post qo'shishi kerak.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Failed to notify referrer {referrer_id}: {e}")


async def notify_referrer_activated(referrer_id: int, new_user_name: str, bot: Bot):
    """Do'st faollashganda (kanal + post) referrerga xabar."""
    try:
        activated = await db.get_referral_count(referrer_id, activated_only=True)
        next_tier = _get_next_tier(activated)

        text = (
            f"✅ <b>{new_user_name}</b> kanal biriktirib post qo'shdi!\n\n"
            f"Sizning faol referrallaringiz: <b>{activated}</b>\n"
        )

        if next_tier:
            remaining = next_tier[0] - activated
            text += f"🎯 Keyingi mukofotgacha: <b>{remaining}</b> ta qoldi ({next_tier[2]})"
        else:
            text += "🎉 Siz eng yuqori bosqichga yetdingiz!"

        await bot.send_message(
            chat_id=referrer_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.warning(f"Failed to notify referrer activated {referrer_id}: {e}")


async def show_admin_referral_stats(call: CallbackQuery):
    """Admin panel — referral statistikasi."""
    try:
        user_id = call.from_user.id
        if not await db.is_superadmin(user_id):
            await call.answer("Sizda ruxsat yo'q!", show_alert=True)
            return

        stats = await db.get_referral_stats()
        top = await db.get_top_referrers(limit=25)

        text = (
            "<b>🔗 REFERRAL STATISTIKA</b>\n\n"
            f"👥 Jami taklif qilinganlar: <b>{stats['total_referrals']}</b>\n"
            f"✅ Faollashganlar: <b>{stats['activated_referrals']}</b>\n"
            f"🧑 Ishtirokchilar soni: <b>{stats['total_participants']}</b>\n"
        )

        # Tier bo'yicha hisoblash
        if top:
            tier1 = sum(1 for _, c in top if c >= REFERRAL_TIER1_COUNT and c < REFERRAL_TIER2_COUNT)
            tier2 = sum(1 for _, c in top if c >= REFERRAL_TIER2_COUNT and c < REFERRAL_TIER3_COUNT)
            tier3 = sum(1 for _, c in top if c >= REFERRAL_TIER3_COUNT)

            text += (
                f"\n<b>Mukofot olganlar:</b>\n"
                f"🥉 {REFERRAL_TIER1_DAYS} kun: {tier1} ta\n"
                f"🥈 {REFERRAL_TIER2_DAYS} kun: {tier2} ta\n"
                f"🥇 {REFERRAL_TIER3_DAYS} kun: {tier3} ta\n"
            )

            text += "\n<b>🏅 TOP 25</b>\n\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, (ref_id, count) in enumerate(top):
                medal = medals[i] if i < 3 else f"  {i + 1}."
                text += f"{medal} <code>{ref_id}</code> — {count} ta\n"

        try:
            await call.message.delete()
        except Exception:
            pass

        from keyboards.inline import admin_panel as admin_panel_kb
        await call.message.answer(
            text,
            reply_markup=admin_panel_kb,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in show_admin_referral_stats: {e}", exc_info=True)
        await call.answer("Xatolik yuz berdi", show_alert=True)


