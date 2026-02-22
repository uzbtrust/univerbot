"""Statistika grafik yaratish (matplotlib)."""

import io
import logging

import matplotlib
matplotlib.use('Agg')  # GUI siz backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_stats_chart(stats_data: list) -> bytes | None:
    """Kunlik statistikadan grafik yaratish.

    Args:
        stats_data: [(date, total_users, premium_users, total_channels, total_posts, posts_with_image), ...]

    Returns:
        PNG rasm bytes yoki None (xatolikda)
    """
    if not stats_data:
        return None

    try:
        # Eng eski → eng yangi tartibda
        stats_data = list(reversed(stats_data))

        dates = [datetime.strptime(row[0], "%Y-%m-%d") for row in stats_data]
        users = [row[1] for row in stats_data]
        premium = [row[2] for row in stats_data]
        channels = [row[3] for row in stats_data]
        posts = [row[4] for row in stats_data]
        img_posts = [row[5] for row in stats_data]

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("Bot Statistikasi", fontsize=16, fontweight='bold')

        # ---- 1. Foydalanuvchilar ----
        ax1 = axes[0][0]
        ax1.plot(dates, users, 'b-o', linewidth=2, markersize=4, label='Jami')
        ax1.plot(dates, premium, 'g-o', linewidth=2, markersize=4, label='Premium')
        ax1.fill_between(dates, premium, alpha=0.2, color='green')
        ax1.fill_between(dates, premium, users, alpha=0.15, color='blue')
        ax1.set_title("Foydalanuvchilar", fontweight='bold')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        # ---- 2. Kanallar ----
        ax2 = axes[0][1]
        ax2.bar(dates, channels, color='orange', alpha=0.8, width=0.6)
        ax2.set_title("Kanallar soni", fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        # ---- 3. Postlar ----
        ax3 = axes[1][0]
        posts_no_img = [p - ip for p, ip in zip(posts, img_posts)]
        ax3.bar(dates, posts_no_img, color='#7B68EE', alpha=0.8, label='Matnli', width=0.6)
        ax3.bar(dates, img_posts, bottom=posts_no_img, color='#FF6B6B', alpha=0.8, label='Rasmli', width=0.6)
        ax3.set_title("Postlar soni", fontweight='bold')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3, axis='y')

        # ---- 4. Premium / Free nisbati ----
        ax4 = axes[1][1]
        if users[-1] > 0:
            free_last = users[-1] - premium[-1]
            sizes = [premium[-1], free_last]
            labels = [f"Premium ({premium[-1]})", f"Free ({free_last})"]
            colors = ['#FFD700', '#87CEEB']
            explode = (0.05, 0)
            ax4.pie(sizes, labels=labels, colors=colors, explode=explode,
                    autopct='%1.1f%%', startangle=90, textprops={'fontsize': 9})
        ax4.set_title("Bugungi nisbat", fontweight='bold')

        # Sana formatini chiroyli qilish
        for ax in [axes[0][0], axes[0][1], axes[1][0]]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.tick_params(axis='x', rotation=45, labelsize=8)

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        logger.error(f"Chart yaratishda xatolik: {e}", exc_info=True)
        plt.close('all')
        return None
