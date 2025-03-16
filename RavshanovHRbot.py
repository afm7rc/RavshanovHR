import csv
import os
import mysql.connector
from mysql.connector import Error
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, CommandHandler, CallbackContext, ContextTypes, ConversationHandler
from datetime import datetime
from telegram.helpers import escape_markdown
from config import TOKEN, ADMINS, SUPER_ADMIN  # Token, adminlar va super adminni yuklab olamiz
from db import get_user_data, update_user_info, export_users_to_csv, is_admin, fix_blocked_users, mark_active, get_stats, save_user, connect_db, get_all_users

ASK_OPTION, ASK_NAME, ASK_PHONE, RECEIVE_MESSAGE, ASK_MESSAGE, ASK_USER_ID, ASK_REPLY_MESSAGE, WAITING_FOR_ID, WAITING_FOR_MESSAGE, = range(9)

# 📌 `/start` komandasi
async def start(update: Update, context: CallbackContext):
    """Foydalanuvchiga xush kelibsiz xabarini yuborish va ma'lumotlarini bazaga yozish."""
    user = update.effective_user
    user_id = user.id
    username = user.username if user.username else "NoUsername"
    nickname = user.full_name
    fullname = user.full_name

    # 📌 Foydalanuvchini MySQL bazaga saqlash
    save_user(user_id, username, nickname, fullname)
    
    # 📌 Foydalanuvchini "faol" qilib belgilash
    mark_active(user_id)
    
    # 📌 Bloklangan foydalanuvchilarni avtomatik tiklash
    fix_blocked_users()

    # 📌 Agar admin bo‘lsa, maxsus xabar yuboramiz
    if user_id in ADMINS:
        admin_message = (
            "👑 Assalomu alaykum, Admin!\n\n"
            "Siz *RavshanovHRbot*'ning boshqaruv panelidasiz. "
            "Bu yerdan foydalanuvchilarni kuzatish va boshqa jarayonlarni boshqarishingiz mumkin.\n\n"
            "📩 Foydalanuvchilarga javob berish: /reply\n"
            "📨 Bitta foydalanuvchiga xabar yuborish: /send\n"
            "📢 Barcha foydalanuvchilarga xabar yuborish: /sendall\n"
            "📂 Xabarlarni ko‘rish: /show\n"
            "📊 Statistika ko‘rish: /stats\n"
            "📝 Buyruqlar ro‘yxati: /help\n"
        )
        await update.message.reply_text(admin_message)
    else:
        # 📌 Oddiy foydalanuvchilarga xabar
        user_message = (
            "Assalomu alaykum! 🪡\n\n"
            "Men *Asilbek Ravshanov*. Ushbu bot sizga men haqimda ma'lumot berish, "
            "men bilan bog‘lanish hamda savol va takliflar uchun yaratilgan.\n\n"
            "📝 Buyruqlar ro‘yxatini ko‘rish uchun /help ni bosing.\n"
            "📞 Bog‘lanish uchun /contact ni bosing.\n"
            "🤖 Bot: @RavshanovHRbot"
        )
        await update.message.reply_text(user_message, parse_mode="Markdown")

async def social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📢 *Meni ijtimoiy tarmoqlarimni kuzatib boring!* 🗿\n\n"
        "📌 *Telegram:* https://t.me/+EcAOcYLTaFI2ZTgy\n"
        "📌 *Facebook:* https://www.facebook.com/As1lbekRavshanov\n"
        "📌 *X (Twitter):* https://x.com/afm7rc\n\n"
        "Barcha yangiliklarni kuzatib boring! 🔔\n"
        "🤖 Bot: @RavshanovHRbot",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat.id
    escaped_id = f"`{telegram_id}`"  # Monoboshliq qilish
    
    await update.message.reply_text(f"Sizning Telegram ID: {escaped_id}", parse_mode="MarkdownV2")

from telegram import ReplyKeyboardRemove

# /contact komandasi - boshlanish
async def contact(update: Update, context: CallbackContext):
    keyboard = [["📞 Bog‘lanish", "❌ Bekor qilish"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📞 *Bog‘lanish yoki bekor qilishni tanlang:*", 
        reply_markup=reply_markup, parse_mode="Markdown"
    )
    return ASK_OPTION

# Bog‘lanish yoki bekor qilishni tanlash
async def ask_option(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    if text == "❌ Bekor qilish":
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=ReplyKeyboardRemove())  
        return ConversationHandler.END
    
    if text == "📞 Bog‘lanish":
        await update.message.reply_text("👤 *Iltimos, to‘liq ismingizni kiriting:*", 
                                        reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return ASK_NAME  

    await update.message.reply_text("❗ *Iltimos, quyidagi tugmalardan birini tanlang!*", parse_mode="Markdown")
    return ASK_OPTION  

# Ism-familiyani qabul qilish
async def ask_name(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("❗ *Ismingizni kiriting!*", parse_mode="Markdown")
        return ASK_NAME  

    context.user_data["name"] = text  # Ism-familiyani saqlash
    
    # Telefon so‘rash tugmasi
    keyboard = [[KeyboardButton("📱 Telefon nomeringizni yuboring", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📞 *Endi telefon nomeringizni yuboring:*", 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )
    return ASK_PHONE

async def ask_phone(update: Update, context: CallbackContext):
    contact = update.message.contact
    text = update.message.text  

    if contact:
        context.user_data["phone"] = contact.phone_number
    elif text and text.isdigit():  
        context.user_data["phone"] = text
    else:
        await update.message.reply_text("❗ *Iltimos, telefon nomeringizni to'g'ri kiriting yoki tugmadan foydalaning.*",
                                        parse_mode="Markdown")
        return ASK_PHONE  

    user = update.message.from_user
    user_id = user.id
    user_name = context.user_data.get("name", "Ism yo‘q")
    user_phone = context.user_data.get("phone", "Telefon yo‘q")
    user_username = f"@{user.username}" if user.username else "Username yo‘q"

    # ✅ Foydalanuvchi ma'lumotlarini yangilash
    update_user_info(user_id, user_username, user_name, user_phone)
    print(f"✅ {user_id} foydalanuvchi ma'lumotlari yangilandi.")  

    # 🔄 Xabar yozishni so‘rash
    await update.message.reply_text(
        "✍ *Endi xabaringizni yozing:*", 
        reply_markup=ReplyKeyboardRemove(), 
        parse_mode="Markdown"
    )
    return RECEIVE_MESSAGE

async def receive_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_message = update.message.text.strip()
    user_id = user.id

    # Bazadan user malumotlarini olish
    db = connect_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT fullname, phone FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    db.close()

    user_name = user_data["fullname"] if user_data else context.user_data.get("name", "Ism yo‘q")
    user_phone = user_data["phone"] if user_data else context.user_data.get("phone", "Telefon yo‘q")

    # Adminlarga yuboriladigan xabar
    admin_message = (
        "📩 *Yangi xabar!* 📩\n\n"
        f"🆔 *Foydalanuvchi ID:* `{user_id}`\n"
        f"👤 *Foydalanuvchi:* {user_name}\n"
        f"📞 *Telefon:* {user_phone}\n"
        f"💬 *Xabar:* {user_message}\n\n"
        "✉️ *Javob berish uchun /reply komandasidan foydalaning!*\n"
    )

    from config import ADMINS
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_message, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Admin {admin_id} ga xabar yuborishda xatolik: {e}")

    await update.message.reply_text(
        "✅ *Xabaringiz qabul qilindi!*", 
        reply_markup=ReplyKeyboardRemove(), 
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END  

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchiga javob yozish uchun ID so‘raydi."""
    user_id = update.message.from_user.id

    if user_id not in ADMINS:
        await update.message.reply_text("⚠️ Sizga bu amalni bajarishga ruxsat berilmagan!")
        return ConversationHandler.END

    await update.message.reply_text("📩 Iltimos, foydalanuvchi ID'sini kiriting:")
    return ASK_USER_ID

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining Telegram ID sini olish va inline tugmalar orqali tasdiqlash."""
    user_id = update.message.text.strip()

    if not user_id.isdigit():
        await update.message.reply_text("⚠️ Xatolik: ID faqat raqamlardan iborat bo‘lishi kerak! Iltimos, qayta kiriting:")
        return ASK_USER_ID

    user_id = int(user_id)
    context.user_data["user_id"] = user_id

    # Endi foydalanuvchi ma'lumotlarini olishni olib tashladik, faqat xabar yuborish so'raladi
    await update.message.reply_text("✍️ Endi yuboriladigan xabarni yozing:")
    return ASK_REPLY_MESSAGE

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin xabarini foydalanuvchiga jo‘natish."""
    user_id = context.user_data.get("user_id")
    message_text = update.message.text

    if not user_id:
        await update.message.reply_text("⚠️ Xatolik: Avval foydalanuvchi ID sini kiriting! /reply ni qaytadan ishga tushiring.")
        return ConversationHandler.END

    try:
        # Admin javobi qo‘shish
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = (
            f"📩 *Admin javobi*\n"
            f"🕒 *Vaqt:* `{now}`\n"
            "💬 *Xabar:*\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"{message_text}"
        )

        # Foydalanuvchiga xabar yuborish
        await context.bot.send_message(chat_id=user_id, text=formatted_message, parse_mode="Markdown")
        await update.message.reply_text(f"✅ Xabar foydalanuvchiga (`{user_id}`) yuborildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}\nXabar yuborishda xatolik yuz berdi.")

    return ConversationHandler.END

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *Yordam bo‘limi*\n\n"
        "Quyidagi buyruqlardan foydalanishingiz mumkin:\n\n"
        "🔹 */start* – Botni ishga tushirish\n"
        "🔹 */social* – Ijtimoiy tarmoqlarim\n"
        "🔹 */myid* – Telegram ID'ni bilish\n"
        "🔹 */contact* – Aloqaga chiqish\n"
        "🔹 */help* – Yordam bo‘limi\n"
        "🔹 */about* – Bot haqida ma'lumot",
        parse_mode="Markdown"
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *RavshanovHRbot* haqida:\n\n"
        "Bu bot sizga men haqimda ma'lumot berish va bog‘lanish imkoniyatini yaratish uchun ishlab chiqilgan.\n\n"
        "Qo‘shimcha ma'lumotlar uchun: /help",
        parse_mode="Markdown"
    )

# Fayl nomlari
files = ["usersdata.csv", "usersmessagedata.csv"]

# Fayllar mavjudligini tekshirish, yo'q bo'lsa yaratish
for file in files:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            f.write("user_id,username,fullname,phone\n")  # Sarlavha qo'shish
        print(f"✅ {file} fayli yaratildi.")

# 📌 /show komandasi - Adminga fayllarni yuborish
async def show_files(update: Update, context: CallbackContext):
    if update.message.chat_id not in ADMINS:
        await update.message.reply_text("⛔ Sizda bu komandaning ishlashiga ruxsat yo‘q!")
        return
    
    # 📌 CSV faylni yangilash
    export_users_to_csv()
    
    files = ["usersdata.csv"]
    
    for file in files:
        if os.path.exists(file):
            with open(file, "rb") as f:
                for admin_id in ADMINS:
                    try:
                        await context.bot.send_document(chat_id=admin_id, document=f, filename=file, caption=f"📂 {file} fayli")
                    except Exception as e:
                        print(f"⚠️ Xatolik: Admin {admin_id} ga {file} fayli yuborilmadi! Sabab: {e}")
        else:
            await update.message.reply_text(f"❗ {file} topilmadi!")

# 📌 /stats komandasini ishlovchi funksiya
async def stats(update: Update, context: CallbackContext):
    users_count, active_users, admins_count = get_stats()

    stats_message = (
        f"📊 *Statistika*\n\n"
        f"👥 Foydalanuvchilar soni: {users_count}\n"
        f"✅ Faol foydalanuvchilar: {active_users}\n"
        f"🛡 Adminlar soni: {admins_count}"
    )

    await update.message.reply_text(stats_message)

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchiga ID orqali xabar yuborishi."""
    user_id = update.message.from_user.id
    if user_id not in ADMINS and user_id != SUPER_ADMIN:  # Admin yoki Super Admin bo‘lishi kerak
        await update.message.reply_text("❌ Sizga bu funksiyadan foydalanish ruxsat etilmagan.")
        return ConversationHandler.END
    
    await update.message.reply_text("📩 Iltimos, xabar yuboriladigan foydalanuvchi ID sini kiriting yoki bekor qilish uchun /cancel ni bosing.")
    return WAITING_FOR_ID

async def receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi ID sini qabul qilish."""
    user_id = update.message.text.strip()
    if not user_id.isdigit():
        await update.message.reply_text("❗ Iltimos, faqat raqamlardan iborat ID kiriting!")
        return WAITING_FOR_ID
    
    user_id = int(user_id)
    context.user_data['target_user_id'] = user_id
    await update.message.reply_text("✍ Endi yuboriladigan xabar matnini kiriting yoki bekor qilish uchun /cancel ni bosing.")
    return WAITING_FOR_MESSAGE

async def send_message_to_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchiga yuboriladigan xabarni qabul qilish va jo‘natish."""
    message_text = update.message.text
    target_user_id = context.user_data.get('target_user_id')
    
    if not target_user_id:
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, jarayonni qaytadan boshlang.")
        return ConversationHandler.END
    
    try:
        await context.bot.send_message(chat_id=target_user_id, text=message_text)
        await update.message.reply_text(f"✅ Xabar {target_user_id} ga yuborildi.")
    except Exception:
        # Xatolik yuz bermasa, hech qanday xabar yuborilmaydi
        pass
    
    return ConversationHandler.END

async def send_message_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin barcha foydalanuvchilarga xabar yuborishi."""
    user_id = update.message.from_user.id

    if not is_admin(user_id):  # Adminligini tekshiramiz
        await update.message.reply_text("❌ Sizga bu funksiyadan foydalanish ruxsat etilmagan.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📩 Iltimos, yuboriladigan xabar matnini kiriting yoki bekor qilish uchun /cancel yuboring."
    )
    return WAITING_FOR_MESSAGE  # Yangi xabarni kutish holatiga o'tish

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin yubormoqchi bo‘lgan xabarni qabul qilish va barcha foydalanuvchilarga jo‘natish."""
    message_text = update.message.text

    # Foydalanuvchi ID va boshqa ma'lumotlar bo'lmasligi kerak
    if message_text.startswith("/contact"):
        await update.message.reply_text("⚠️ Xatolik: Siz faqat xabar matnini yuborishingiz kerak.")
        return ConversationHandler.END

    users = get_all_users()  # Barcha user_id larni bazadan olish
    if not users:
        await update.message.reply_text("⚠️ Bazada foydalanuvchilar topilmadi.")
        return ConversationHandler.END

    sent_count = 0
    failed_count = 0

    # Adminning e'lonini xabar matniga qo'shamiz
    admin_announcement = "📢 *E'lon*: Bu xabar admin tomonidan yuborildi. Iltimos, har qanday savollarni admin bilan bog'lanib hal qiling."

    for user in users:
        chat_id = user[0]  # Agar bazada (user_id,) shaklida saqlansa
        try:
            # Faqat xabar matnini yuborishdan oldin adminning e'lonini qo'shish
            formatted_message = f"{admin_announcement}\n\n{message_text}"
            await context.bot.send_message(chat_id=chat_id, text=formatted_message, parse_mode="Markdown")
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"❌ Xatolik {chat_id}: {e}")  # Xatolikni log qilamiz

    await update.message.reply_text(
        f"✅ Xabar {sent_count} foydalanuvchiga yuborildi.\n"
        f"❌ {failed_count} foydalanuvchiga yuborib bo‘lmadi."
    )
    return ConversationHandler.END  # Suhbatni yakunlash

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jarayonni bekor qilish."""
    await update.message.reply_text("❌ Xabar yuborish jarayoni bekor qilindi.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    contact_handler = ConversationHandler(
        entry_points=[CommandHandler("contact", contact)],
        states={
            ASK_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_option)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_PHONE: [
                MessageHandler(filters.CONTACT, ask_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)
            ],
            RECEIVE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],  # Bekor qilish komandasi
    )

    # Admin foydalanuvchiga javob berishi uchun ConversationHandler
    reply_handler = ConversationHandler(
        entry_points=[CommandHandler("reply", reply)],
        states={
            ASK_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_id)],
            ASK_REPLY_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # /send komandasi uchun ConversationHandler
    send_handler = ConversationHandler(
        entry_points=[CommandHandler("send", send_message)],
        states={
            WAITING_FOR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_id)],
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    send_message_handler = ConversationHandler(
        entry_points=[CommandHandler("sendall", send_message_to_all)],
        states={
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Asosiy handlerlarni qo‘shish
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("social", social))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("show", show_files))
    app.add_handler(CommandHandler("myid", get_id))
    app.add_handler(CommandHandler("stats", stats))  # 📊 Statistika qo'shildi
    app.add_handler(contact_handler)
    app.add_handler(send_handler)
    app.add_handler(reply_handler)
    app.add_handler(send_message_handler) 

    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    main()