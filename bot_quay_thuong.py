from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, filters
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import os
import datetime
import random
import asyncio

TOKEN = "7918568253:AAEoeInDbhyN3c4cKUkVdnT8fziAZoBBKzw"
ADMIN_ID = 5815156606  # <-- Đây là Telegram ID của bạn

INTRO_FILE = "intro_message.txt"
participants = set()
intro_sent = False
intro_message_id = None
group_id = None

scheduler = BackgroundScheduler()
scheduler.start()

def only_admin(func):
    async def wrapper(update: Update, context: CallbackContext):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ Bạn không có quyền sử dụng bot này.")
            return
        return await func(update, context)
    return wrapper

@only_admin
async def set_intro(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❌ Dùng đúng cú pháp: /setintro [nội dung]")
        return
    intro_text = " ".join(context.args)
    with open(INTRO_FILE, "w", encoding="utf-8") as f:
        f.write(intro_text)
    await update.message.reply_text("✅ Đã lưu nội dung giới thiệu!")

@only_admin
async def send_intro(update: Update, context: CallbackContext):
    global intro_sent, intro_message_id, group_id

    if intro_sent:
        await update.message.reply_text("⚠️ Thông báo giới thiệu đã được gửi rồi!")
        return

    if os.path.exists(INTRO_FILE):
        with open(INTRO_FILE, "r", encoding="utf-8") as f:
            intro_text = f.read()
    else:
        intro_text = "🎯 Chào mừng! Hãy nhấn Tham Gia để bắt đầu."

    full_intro = f"{intro_text}\n\n👥 Đã có {len(participants)} người tham gia"
    keyboard = [[InlineKeyboardButton("✅ Tham Gia", callback_data="thamgia")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent_message = await update.message.reply_text(full_intro, reply_markup=reply_markup)

    intro_sent = True
    intro_message_id = sent_message.message_id
    group_id = update.message.chat_id

async def button_click(update: Update, context: CallbackContext):
    global intro_message_id

    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "thamgia":
        if user.id not in participants:
            participants.add(user.id)
            await query.message.reply_text(f"✅ {user.first_name} đã tham gia!")
            await update_intro_message(context)

@only_admin
async def set_time(update: Update, context: CallbackContext):
    global group_id
    if len(context.args) < 2:
        await update.message.reply_text("❌ Cú pháp đúng: /settime YYYY-MM-DD HH:MM")
        return

    date_str = context.args[0]
    time_str = context.args[1]
    try:
        target_datetime = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("❌ Sai định dạng! Ví dụ: /settime 2025-05-01 20:00")
        return

    group_id = update.message.chat_id
    scheduler.add_job(quay_thuong, DateTrigger(run_date=target_datetime), args=[context])

    await update.message.reply_text(f"✅ Đã hẹn giờ quay thưởng lúc {target_datetime.strftime('%Y-%m-%d %H:%M')}!")

async def quay_thuong(context: CallbackContext):
    await context.bot.send_message(
        chat_id=group_id,
        text="🎲 Chương trình quay thưởng may mắn chính thức bắt đầu!\n\n🔒 Trong thời gian quay thưởng, group sẽ tạm cấm chat!"
    )

    await context.bot.set_chat_permissions(
        chat_id=group_id,
        permissions=ChatPermissions(can_send_messages=False)
    )

    if not participants:
        await context.bot.send_message(chat_id=group_id, text="⚠️ Không có ai tham gia, không thể quay thưởng!")
        return

    winners_count = 10
    winner_list = list(participants) if len(participants) <= winners_count else random.sample(list(participants), winners_count)

    result_text = "🏆 Danh sách người chiến thắng:\n\n"
    for idx, user_id in enumerate(winner_list, 1):
        try:
            user = await context.bot.get_chat_member(group_id, user_id)
            display_name = f"@{user.user.username}" if user.user.username else user.user.first_name
            result_text += f"{idx}. <a href='tg://user?id={user_id}'>{display_name}</a>\n"
        except Exception as e:
            result_text += f"{idx}. (Không xác định)\n"

    await context.bot.send_message(
        chat_id=group_id,
        text=result_text,
        parse_mode='HTML'
    )

async def update_intro_message(context: CallbackContext):
    if intro_message_id and group_id:
        try:
            if os.path.exists(INTRO_FILE):
                with open(INTRO_FILE, "r", encoding="utf-8") as f:
                    intro_text = f.read()
            else:
                intro_text = "🎯 Chào mừng! Hãy nhấn Tham Gia để bắt đầu."

            full_intro = f"{intro_text}\n\n👥 Đã có {len(participants)} người tham gia"
            await context.bot.edit_message_text(
                chat_id=group_id,
                message_id=intro_message_id,
                text=full_intro,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Tham Gia", callback_data="thamgia")]
                ])
            )
        except Exception as e:
            print(f"⚠️ Lỗi update intro: {e}")

@only_admin
async def unlock_group(update: Update, context: CallbackContext):
    await context.bot.set_chat_permissions(
        chat_id=update.message.chat_id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text("🔓 Group đã được mở chat lại!")

@only_admin
async def participant_count(update: Update, context: CallbackContext):
    await update.message.reply_text(f"👥 Hiện có {len(participants)} người đã tham gia.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("setintro", set_intro, filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("sendintro", send_intro, filters.ChatType.GROUPS))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(CommandHandler("settime", set_time, filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unlock", unlock_group, filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("participants", participant_count, filters.ChatType.PRIVATE))

    scheduler.add_job(lambda: asyncio.run(update_intro_message(app.bot)), 'interval', hours=1)

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
