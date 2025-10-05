#!/usr/bin/env python3
"""
Python-Telegram-Bot implementation of the unequify command
Removes duplicate files from channels using userbot
"""

import re
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackContext,
    ConversationHandler, MessageHandler, filters as ptb_filters
)
from telegram.constants import ParseMode

from database import db
from config import Config, temp
from plugins.test import CLIENT, start_clone_bot
from translation import Translation
from utils.notifications import NotificationManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_TARGET, WAITING_FOR_CONFIRMATION = range(2)

COMPLETED_BTN = InlineKeyboardMarkup([
    [InlineKeyboardButton('⚡ Support', url='https://t.me/ftmbotzsupportz')],
    [InlineKeyboardButton('📢 Updates', url='https://t.me/ftmbotzofficial')]
])

CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', callback_data='terminate_frwd')]])

async def unequify_start(update: Update, context: CallbackContext) -> int:
    """Start the unequify process"""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    logger.info(f"PTB Unequify command from user {user_id} ({user_name})")

    try:
        # Check if process already running
        temp.CANCEL[user_id] = False
        if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
            await update.message.reply_text(
                "<b>⏳ Process Already Running</b>\n\n"
                "<b>❌ You already have an active unequify process running.</b>\n\n"
                "<b>💡 Please wait until the current process is completed before starting a new one.</b>",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END

        # Check if userbot exists
        _bot = await db.get_bot(user_id)
        if not _bot or _bot.get('is_bot'):
            await update.message.reply_text(
                "<b>🤖 Userbot Required</b>\n\n"
                "<b>❌ The unequify process requires a userbot account, not a regular bot.</b>\n\n"
                "<b>📝 How to fix this:</b>\n"
                "• Use /settings command to add your userbot\n"
                "• Make sure it's a real Telegram user account\n"
                "• Ensure the userbot has admin permissions in the target chat\n\n"
                "<b>💡 Need help? Use /contact to reach admin support.</b>",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END

        # Send start notification
        try:
            notify = NotificationManager(context.bot)
            await notify.notify_user_action(user_id, "Started Unequify Process", "Duplicate message removal")
        except Exception as notify_err:
            logger.error(f"Failed to send unequify start notification: {notify_err}")

        # Store bot info in context
        context.user_data['bot_info'] = _bot

        await update.message.reply_text(
            "<b>🗑️ Unequify - Remove Duplicate Files</b>\n\n"
            "<b>📝 Instructions:</b>\n"
            "1. Forward the last message from your target channel\n"
            "   OR\n"
            "2. Send the last message link from your target channel\n\n"
            "<b>Example link:</b> <code>https://t.me/channelname/12345</code>\n\n"
            "<b>Send /cancel to stop this process</b>",
            parse_mode=ParseMode.HTML
        )

        return WAITING_FOR_TARGET

    except Exception as e:
        logger.error(f"Error in unequify start for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred. Please try again.")
        return ConversationHandler.END

async def receive_target(update: Update, context: CallbackContext) -> int:
    """Receive target channel information"""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id

    # Check for cancel command
    if update.message.text and update.message.text.startswith("/"):
        await update.message.reply_text(
            "<b>❌ Process Cancelled</b>\n\n"
            "<b>The unequify process has been cancelled by your request.</b>\n\n"
            "<b>💡 You can restart the process anytime using /unequify command.</b>",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    chat_id = None
    last_msg_id = None

    # Check if it's a text link
    if update.message.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(update.message.text.replace("?single", ""))
        if match:
            chat_id = match.group(4)
            last_msg_id = int(match.group(5))
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        else:
            await update.message.reply_text(
                "<b>🔗 Invalid Link Format</b>\n\n"
                "<b>❌ The link you provided is not a valid Telegram message link.</b>\n\n"
                "<b>✅ Valid formats:</b>\n"
                "• https://t.me/channelname/123\n"
                "• https://t.me/c/1234567/123\n"
                "• @channelname/123\n\n"
                "<b>💡 Make sure to copy the complete message link from Telegram.</b>",
                parse_mode=ParseMode.HTML
            )
            return WAITING_FOR_TARGET

    # Check if it's a forwarded message
    elif update.message.forward_from_chat and update.message.forward_from_chat.type in ['channel', 'supergroup']:
        last_msg_id = update.message.forward_from_message_id
        chat_id = update.message.forward_from_chat.username or update.message.forward_from_chat.id
    else:
        await update.message.reply_text(
            "<b>📨 Invalid Message</b>\n\n"
            "<b>❌ Please provide either:</b>\n"
            "• Forward the last message from target chat, OR\n"
            "• Send the last message link from target chat\n\n"
            "<b>💡 The message must be from a channel or supergroup.</b>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_FOR_TARGET

    # Store the target info
    context.user_data['chat_id'] = chat_id
    context.user_data['last_msg_id'] = last_msg_id

    await update.message.reply_text(
        "<b>✅ Target Received!</b>\n\n"
        "<b>📋 Channel/Chat ID:</b> <code>{}</code>\n"
        "<b>📨 Last Message ID:</b> <code>{}</code>\n\n"
        "<b>⚠️ This will scan ALL documents in the channel and delete duplicates.</b>\n\n"
        "<b>Are you sure you want to continue?</b>\n\n"
        "Send <b>/yes</b> to start or <b>/no</b> to cancel".format(chat_id, last_msg_id),
        parse_mode=ParseMode.HTML
    )

    return WAITING_FOR_CONFIRMATION

async def receive_confirmation(update: Update, context: CallbackContext) -> int:
    """Receive confirmation and start the process"""
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    user_id = update.effective_user.id

    if not update.message.text:
        return WAITING_FOR_CONFIRMATION

    if update.message.text.lower() == '/no':
        await update.message.reply_text(
            "<b>❌ Process Cancelled</b>\n\n"
            "<b>The unequify process has been cancelled by your request.</b>\n\n"
            "<b>💡 You can restart the process anytime using /unequify command.</b>",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    if update.message.text.lower() != '/yes':
        await update.message.reply_text(
            "<b>Please send /yes to confirm or /no to cancel</b>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_FOR_CONFIRMATION

    # Start the unequify process
    sts = await update.message.reply_text("`Processing...`", parse_mode=ParseMode.MARKDOWN)

    try:
        _bot = context.user_data.get('bot_info')
        chat_id = context.user_data.get('chat_id')
        last_msg_id = context.user_data.get('last_msg_id')

        # Start the clone bot (using Pyrogram)
        CLIENT_instance = CLIENT()
        bot = await start_clone_bot(CLIENT_instance.client(_bot))

        # Test admin access
        try:
            k = await bot.send_message(chat_id, text="testing")
            await k.delete()
        except Exception as e:
            await sts.edit_text(
                f"<b>🔐 Admin Access Required</b>\n\n"
                f"<b>❌ Your userbot @{_bot['username']} needs admin permissions in the target chat.</b>\n\n"
                f"<b>📋 Required permissions:</b>\n"
                f"• Delete messages\n"
                f"• Read message history\n"
                f"• Send messages\n\n"
                f"<b>🔧 Please make your [userbot](t.me/{_bot['username']}) admin with full permissions and try again.</b>",
                parse_mode=ParseMode.HTML
            )
            await bot.stop()
            return ConversationHandler.END

        MESSAGES = []
        DUPLICATE = []
        total = deleted = 0
        temp.lock[user_id] = True

        await sts.edit_text(
            Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"),
            reply_markup=CANCEL_BTN
        )

        # Scan for duplicates
        async for message in bot.search_messages(chat_id=chat_id, filter="document"):
            if temp.CANCEL.get(user_id) == True:
                await sts.edit_text(
                    Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴀɴᴄᴇʟʟᴇᴅ"),
                    reply_markup=COMPLETED_BTN
                )
                await bot.stop()
                temp.lock[user_id] = False
                return ConversationHandler.END

            file = message.document
            if file is None:
                continue

            try:
                file_id = file.file_unique_id
            except Exception:
                try:
                    file_id = file.file_id
                except Exception:
                    continue

            if file_id in MESSAGES:
                DUPLICATE.append(message.id)
            else:
                MESSAGES.append(file_id)

            total += 1

            # Update progress every 10000 messages
            if total % 10000 == 0:
                await sts.edit_text(
                    Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"),
                    reply_markup=CANCEL_BTN
                )

            # Delete duplicates in batches of 100
            if len(DUPLICATE) >= 100:
                await bot.delete_messages(chat_id, DUPLICATE)
                deleted += 100
                await sts.edit_text(
                    Translation.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"),
                    reply_markup=CANCEL_BTN
                )
                DUPLICATE = []

        # Delete remaining duplicates
        if DUPLICATE:
            await bot.delete_messages(chat_id, DUPLICATE)
            deleted += len(DUPLICATE)

        temp.lock[user_id] = False
        await sts.edit_text(
            Translation.DUPLICATE_TEXT.format(total, deleted, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"),
            reply_markup=COMPLETED_BTN
        )

        # Send completion notification
        try:
            notify = NotificationManager(context.bot)
            await notify.notify_user_action(
                user_id,
                "Completed Unequify Process",
                f"Total: {total}, Deleted: {deleted}"
            )
        except Exception as notify_err:
            logger.error(f"Failed to send unequify completion notification: {notify_err}")

        logger.info(f"Unequify completed for user {user_id}: Total={total}, Deleted={deleted}")
        await bot.stop()

    except Exception as e:
        temp.lock[user_id] = False
        error_msg = f"<b>❌ ERROR in Unequify Process</b>\n\n<code>{str(e)}</code>"
        logger.error(f"Unequify error for user {user_id}: {str(e)}", exc_info=True)

        try:
            notify = NotificationManager(context.bot)
            await notify.notify_error(user_id, "Unequify Process Failed", str(e))
        except Exception as notify_err:
            logger.error(f"Failed to send error notification: {notify_err}")

        await sts.edit_text(error_msg, parse_mode=ParseMode.HTML)

        if 'bot' in locals():
            await bot.stop()

    return ConversationHandler.END

async def cancel_unequify(update: Update, context: CallbackContext) -> int:
    """Cancel the unequify process"""
    if update.effective_user:
        user_id = update.effective_user.id
        temp.CANCEL[user_id] = True

    await update.message.reply_text(
        "<b>❌ Process Cancelled</b>\n\n"
        "<b>The unequify process has been cancelled.</b>",
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

def setup_unequify_handler(application: Application):
    """Setup the unequify conversation handler"""

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('unequify', unequify_start)],
        states={
            WAITING_FOR_TARGET: [
                MessageHandler(ptb_filters.TEXT | ptb_filters.FORWARDED, receive_target)
            ],
            WAITING_FOR_CONFIRMATION: [
                MessageHandler(ptb_filters.TEXT, receive_confirmation)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_unequify)],
    )

    application.add_handler(conv_handler)
    logger.info("PTB Unequify handler registered")