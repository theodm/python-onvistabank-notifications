from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
)
from config import get_allowed_user_ids, get_telegram_token
from onvistabank_api.OnVistaApi import OnVistaApiOTPRequiredException
from onvistabank_api.OnVistaLowLevelApi import OnVistaOTPIsWrongException
from datetime import timedelta
from loguru import logger
import random
import asyncio
from onvistabank_api.OnVistaApi import OnVistaApi
from config import get_onvistabank_username, get_onvistabank_password
from typing import Optional
import telegram.ext as tg_ext
from portfolio_message import (
    get_portfolio_message_markdown,
    OTPRequiredException,
    OTPWrongException,
)

# Das API-Objekt für die OnVistaBank-API
# es wird in der portfolio()-Funktion initialisiert und in der reply_with_otp()-Funktion verwendet,
# ist also global.
api = None

# Es wird eine kurze Konversation mit dem Benutzer geführt, für den Fall, dass der Benutzer eine TAN eingeben muss. Im
# Grundfall wird das Portfolio einfach angezeigt, aber wenn der Server eine TAN anfordert, wird diese Konversation
# mit REPLY_WITH_OTP gestartet. Die Konversation wird mit /cancel abgebrochen oder es kommt nach 10 Minuten zu einem
# Timeout.
REPLY_WITH_OTP = 1


# Start der Konversation, wenn der Benutzer /portfolio aufruft. Rückgabewert entscheidet,
# ob die Konversation mit der Eingabe der TAN fortgesetzt oder beendet wird.
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global api
    # Wir lassen nur geladene Gäste rein. ;-)
    if not update.effective_user or not str(update.effective_user.id) in (
        get_allowed_user_ids()
    ):
        logger.info(
            f"User {update.effective_user.id} tried to access the portfolio, but is not allowed. (allowed are {get_allowed_user_ids()}))"
        )
        await update.message.reply_text(
            f"Sorry {update.effective_user.first_name}, I'm not allowed to send you any confidential information."
        )
        return ConversationHandler.END

    api = OnVistaApi(
        "cookies.txt", get_onvistabank_username(), get_onvistabank_password()
    )

    try:
        await update.message.reply_markdown_v2(get_portfolio_message_markdown(api))
    except OTPRequiredException:
        await update.message.reply_text(
            f"Der Server hat ein OTP (One-Time-Passwort) angefordert. Bitte geben Sie es ein:"
        )
        return REPLY_WITH_OTP
    except Exception as e:
        logger.error(f"An unknown error occured: {e}")
        await update.message.reply_text(f"Ein unbekannter Fehler ist aufgetreten: {e}")

    return ConversationHandler.END


# Konversation: Der Benutzer muss nun mit dem OTP antworten, danach wird diese Methode aufgerufen.
async def reply_with_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global api
    # Wir lassen nur geladene Gäste rein. ;-)
    if not update.effective_user or not str(update.effective_user.id) in (
        get_allowed_user_ids()
    ):
        logger.info(
            f"User {update.effective_user.id} tried to access the portfolio, but is not allowed.  (allowed are {get_allowed_user_ids()})"
        )
        await update.message.reply_text(
            f"Sorry {update.effective_user.first_name}, I'm not allowed to send you any confidential information."
        )
        return ConversationHandler.END

    otp = update.message.text
    await update.message.reply_text(f"Login wird mit folgendem OTP versucht: {otp}")

    try:
        await update.message.reply_markdown_v2(get_portfolio_message_markdown(api, otp))
    except OTPRequiredException:
        await update.message.reply_text(
            f"Das eingegebene OTP (One-Time-Passwort) war falsch. Die Konversation kann mit /cancel abgebrochen werden. Bitte OTP eingeben:"
        )
        return REPLY_WITH_OTP
    except OTPWrongException:
        await update.message.reply_text(
            f"Das eingegebene OTP (One-Time-Passwort) war falsch. Die Konversation kann mit /cancel abgebrochen werden. Bitte OTP eingeben:"
        )
        return REPLY_WITH_OTP
    except Exception as e:
        logger.error(f"An unknown error occured: {e}")
        await update.message.reply_text(f"Ein unbekannter Fehler ist aufgetreten: {e}")

    return ConversationHandler.END


# Konversation: Der Benutzer hat mit /cancel abgebrochen.
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Die Konversation wurde vom Benutzer abgebrochen. (Mit /portfolio kann sie erneut gestartet werden.)"
    )
    return ConversationHandler.END


# Konversation: Der Benutzer hat zu lange gebraucht, um das OTP einzugeben.
async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Die Eingabe des OTP (One-Time-Passwort) hat zu lange gedauert. Die Konversation wird abgebrochen. "
    )
    return ConversationHandler.END


# Diese Methode wird alle 30 Tage aufgerufen und verschickt das monatliche Portfolio-Update, sofern der
# Benutzer eingeloggt ist. Dies wird aus den Cookies ermittelt.
async def send_monthly(context: tg_ext.CallbackContext):
    logger.info("Sending monthly portfolio update...")

    try:
        api = OnVistaApi(
            "cookies.txt", get_onvistabank_username(), get_onvistabank_password()
        )

        portfolio_message = get_portfolio_message_markdown(api)

        for user_id in get_allowed_user_ids():
            logger.info(f"Sending portfolio update to user {user_id}...")
            await context.bot.send_message(
                chat_id=user_id, text=portfolio_message, parse_mode="MarkdownV2"
            )
    except OnVistaApiOTPRequiredException:
        logger.info("Sending portfolio update failed, OTP required.")

        for user_id in get_allowed_user_ids():
            await context
    except Exception as e:
        logger.error(f"Sending portfolio update failed: {e}")

        for user_id in get_allowed_user_ids():
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Beim Versenden des monatlichen Portfolio-Updates ist ein Fehler aufgetreten: {e}",
            )


# Hiermit kann das Menü für den Bot in Telegram gesetzt werden.
async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            ("portfolio", "Zeigt alle verknüpften Konten und deren Performance an."),
            ("cancel", "Bricht eine bestehende Konversation ab."),
        ]
    )


app = ApplicationBuilder().token(get_telegram_token()).post_init(post_init).build()

# Siehe hierzu auch die Dokumentation der python-telegram-bot-Bibliothek:
portfolio_with_otp_handler = ConversationHandler(
    entry_points=[CommandHandler("portfolio", portfolio)],
    states={
        REPLY_WITH_OTP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, reply_with_otp)
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, timeout)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    # Maximal 10 Minuten, das ist mehr als genug Zeit, um eine TAN einzugeben.
    conversation_timeout=timedelta(seconds=60 * 10),
)

p = app.job_queue.run_repeating(
    send_monthly, interval=timedelta(days=30), first=timedelta(seconds=10)
)

app.add_handler(portfolio_with_otp_handler)
app.run_polling()
