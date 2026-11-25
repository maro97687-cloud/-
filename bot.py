import asyncio
import re
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler

TOKEN = "9138968294:AAEzvzo7-NeebbMLAnvBBzQ3DSVlmIdJyXs"
CHANNEL_USERNAME = "@mo_f_u"
CHANNEL_URL = "https://t.me/mo_f_u"
DEV_USERNAME = "@f_v_o12"
DEV_ID = 9067196275

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(context.bot, update.effective_user.id):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📢 اشترك هنا", url=CHANNEL_URL)], [InlineKeyboardButton("✅ تحققت", callback_data="check_sub")]])
        await update.message.reply_text("لازم تشترك في القناة الأول!", reply_markup=kb)
        return
    kb = [
        [KeyboardButton("🟦 حل JavaScript"), KeyboardButton("🟩 حل Python")],
        [KeyboardButton("🟥 حل ثقافة مالية")],
        [KeyboardButton(f"👨‍💻 المطور {DEV_USERNAME}")]
    ]
    await update.message.reply_text("أهلاً بيك 👋\nاختر المادة:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def check_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_subscribed(context.bot, q.from_user.id):
        await q.message.edit_text("✅ تم التحقق! ابعت /start تاني.")
    else:
        await q.answer("لسه مش مشترك ❌", show_alert=True)

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("👨‍💻"):
        await update.message.reply_text(f"المطور: {DEV_USERNAME}\nID: {DEV_ID}")
        return ConversationHandler.END
    mapping = {"🟦 حل JavaScript": "1", "🟩 حل Python": "2", "🟥 حل ثقافة مالية": "3"}
    if text not in mapping: return ConversationHandler.END
    context.user_data["subject"] = mapping[text]
    await update.message.reply_text("ابعتلي ID تسجيل الدخول (مثال: 473635380):", reply_markup=ReplyKeyboardRemove())
    return 1

async def receive_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not re.fullmatch(r"\d+", text):
        await update.message.reply_text("❌ الـ ID لازم يكون أرقام. جرب تاني:")
        return 1
    context.user_data["student_id"] = text
    await update.message.reply_text("تمام ✅\nابعت الباسورد:")
    return 2

async def receive_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    context.user_data["password"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 بدء", callback_data="go")], [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]])
    await update.message.reply_text("✅ تم تسجيل البيانات.\nهل تريد الدخول إلى سجل شركتك يا موظف؟", reply_markup=kb)
    return 3

async def confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "cancel":
        await q.message.edit_text("تم الإلغاء ❌")
        return ConversationHandler.END
    
    status_msg = await q.message.edit_text("⏳ جاري تشغيل الأداة...")
    
    sid = context.user_data.get("student_id")
    pwd = context.user_data.get("password")
    subj = context.user_data.get("subject")

    async def run_and_stream():
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "solver.py", "--id", sid, "--password", pwd, "--subject", subj,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            last_text = ""
            buffer = ""
            last_update_time = asyncio.get_running_loop().time()

            while True:
                line = await process.stdout.readline()
                if not line: break
                
                text_line = line.decode('utf-8', errors='ignore').strip()
                text_line = re.sub(r'\x1b\[[0-9;]*m', '', text_line) # تنظيف ألوان rich
                
                if text_line:
                    buffer += text_line + "\n"
                    if len(buffer) > 4000: buffer = buffer[-3000:] # الحفاظ على آخر جزء فقط
                    
                    now = asyncio.get_running_loop().time()
                    if now - last_update_time > 1.5: # تحديث الشات كل 1.5 ثانية عشان ميعملش بان
                        try:
                            display_text = f"🧭 الخط الزمني:\n\n{buffer[-1500:]}"
                            if display_text != last_text:
                                await status_msg.edit_text(display_text)
                                last_text = display_text
                                last_update_time = now
                        except Exception:
                            pass

            await process.wait()
            
            if "SUCCESS" in buffer or process.returncode == 0:
                await status_msg.edit_text("✅ تم يالشيخ")
            else:
                await status_msg.edit_text(f"⚠️ الأداة واجهت مشكلة:\n{buffer[-1500:]}")
                
        except Exception as e:
            await context.bot.send_message(q.message.chat_id, f"❌ خطأ: {e}")

    asyncio.create_task(run_and_stream())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(🟦 حل JavaScript|🟩 حل Python|🟥 حل ثقافة مالية|👨‍💻)"), choose_subject)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_id)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pass)],
            3: [CallbackQueryHandler(confirm_cb, pattern="^(go|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_cb, pattern="^check_sub$"))
    app.add_handler(conv)
    print("✅ البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
