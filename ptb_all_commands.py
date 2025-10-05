#!/usr/bin/env python3
"""
PTB (Python-Telegram-Bot) command handlers
Handles specific commands while Pyrogram handles /start, /settings, /forward, /fwd
"""

import asyncio
import logging
import time
import os
import sys
import psutil
import speedtest
import platform
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters as ptb_filters
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest, Forbidden

from database import db
from config import Config
from plugins.timezone import display_joined_date, display_expiry_date, time_until_expiry, get_current_ist_timestamp, display_subscription_date
from translation import Translation
from platform import python_version

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

def get_main_buttons():
    """Get main menu buttons"""
    return [[
        InlineKeyboardButton('📜 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url=Config.SUPPORT_GROUP),
        InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=Config.UPDATE_CHANNEL)
    ],[
        InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial'),
        InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
    ],[
        InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans'),
        InlineKeyboardButton('🙋‍♂️ ʜᴇʟᴘ', callback_data='help')
    ],[
        InlineKeyboardButton('💁‍♂️ ᴀʙᴏᴜᴛ', callback_data='about'),
        InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ⚙️', callback_data='settings#main')
    ],[
        InlineKeyboardButton('💬 Contact Admin', url='https://t.me/ftmdeveloperzbot')
    ]]


async def trial_command(update: Update, context: CallbackContext) -> None:
    """Handle /trial command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    logger.info(f"PTB Trial command from user {user_id}")
    
    await update.message.reply_text(
        "🎁 Use the button below to activate your free trial!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial')
        ]])
    )

async def commands_command(update: Update, context: CallbackContext) -> None:
    """Handle /commands command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    logger.info(f"PTB Commands command from user {user_id}")
    
    is_admin = Config.is_sudo_user(user_id)
    is_premium = await db.is_premium_user(user_id)
    can_trial = await db.can_use_trial(user_id)
    
    commands_text = "<b>📋 Available Commands</b>\n\n"
    commands_text += "<b>🔥 Essential Commands:</b>\n"
    commands_text += "• /start - Start bot and show main menu\n"
    commands_text += "• /help - Get detailed help\n"
    commands_text += "• /forward - Start forwarding\n"
    commands_text += "• /settings - Configure settings\n"
    commands_text += "• /myplan - Check subscription\n"
    commands_text += "• /info - Account information\n\n"
    
    commands_text += "<b>💎 Premium Features:</b>\n"
    commands_text += f"• /trial - Free trial ({'Available' if can_trial else 'Used'})\n"
    commands_text += "• /verify - Verify payment\n"
    commands_text += "• /plan - View plans\n\n"
    
    if is_admin:
        commands_text += "<b>👑 Admin Commands:</b>\n"
        commands_text += "• /users - List users\n"
        commands_text += "• /broadcast - Broadcast message\n"
        commands_text += "• /add_premium - Add premium\n"
        commands_text += "• /remove_premium - Remove premium\n"
        commands_text += "• /pusers - Premium users\n\n"
    
    await update.message.reply_text(
        text=commands_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('🏠 Main Menu', callback_data='back')
        ]])
    )

async def verify_command(update: Update, context: CallbackContext) -> None:
    """Handle /verify command - Process payment verification"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    logger.info(f"PTB Verify command from user {user_id}")
    
    # Parse command arguments
    plan_type = 'pro'
    duration = 30
    
    if context.args and len(context.args) >= 2:
        plan_type = context.args[0].lower()
        try:
            duration = int(context.args[1])
        except:
            duration = 30
    
    # Check if replying to a photo
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Please reply to your payment screenshot with /verify command.</b>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/verify pro 30</code> (for Pro 30 days)\n"
            "• <code>/verify plus 15</code> (for Plus 15 days)\n"
            "• <code>/verify</code> (defaults to Pro 30 days)\n\n"
            "<b>Steps:</b>\n"
            "1. Send your payment screenshot\n"
            "2. Reply to that screenshot with the verify command",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get the screenshot
    photo = update.message.reply_to_message.photo[-1]  # Get largest photo
    screenshot_file_id = photo.file_id
    
    # Validate plan and get amount
    if plan_type not in ['plus', 'pro']:
        await update.message.reply_text("❌ Invalid plan type. Use 'plus' or 'pro'", parse_mode=ParseMode.HTML)
        return
    
    if duration not in [15, 30]:
        await update.message.reply_text("❌ Invalid duration. Use 15 or 30 days", parse_mode=ParseMode.HTML)
        return
    
    amount = Config.PLAN_PRICING[plan_type][f'{duration}_days']
    
    try:
        # Submit payment verification
        verification_id = await db.submit_payment_verification(
            user_id, screenshot_file_id, plan_type, duration, amount
        )
        
        await update.message.reply_text(
            "<b>✅ Payment Screenshot Submitted!</b>\n\n"
            f"<b>Plan:</b> {plan_type.upper()}\n"
            f"<b>Duration:</b> {duration} days\n"
            f"<b>Amount:</b> ₹{amount}\n\n"
            "<b>Your payment verification has been submitted to admins for review.</b>\n\n"
            "<b>⏳ Please wait for admin approval.</b>\n"
            "<b>💬 You will be notified once your payment is verified.</b>\n\n"
            f"<b>Verification ID:</b> <code>{verification_id}</code>",
            parse_mode=ParseMode.HTML
        )
        
        # Notify sudo users
        from plugins.timezone import get_current_ist_timestamp
        sudo_users = Config.OWNER_ID + Config.ADMIN_ID
        
        for sudo_id in sudo_users:
            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                buttons = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{verification_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{verification_id}")
                    ]
                ]
                
                # Download and send photo
                file = await context.bot.get_file(screenshot_file_id)
                await context.bot.send_photo(
                    sudo_id,
                    photo=screenshot_file_id,
                    caption=f"<b>💰 New Payment Verification</b>\n\n"
                            f"<b>User:</b> {user_name} (<code>{user_id}</code>)\n"
                            f"<b>Plan:</b> {plan_type.upper()}\n"
                            f"<b>Duration:</b> {duration} days\n"
                            f"<b>Amount:</b> ₹{amount}\n"
                            f"<b>Payment Method:</b> {Config.UPI_ID}\n"
                            f"<b>Submitted:</b> {get_current_ist_timestamp()}\n"
                            f"<b>Verification ID:</b> <code>{verification_id}</code>",
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to notify sudo user {sudo_id}: {e}")
                
    except Exception as e:
        await update.message.reply_text(
            f"<b>❌ Error submitting verification:</b>\n<code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )
        logger.error(f"Error in verify command: {e}", exc_info=True)

async def add_premium_command(update: Update, context: CallbackContext) -> None:
    """Handle /add_premium command - admin only"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Usage:</b> <code>/add_premium [user_id] [plan_type] [days]</code>\n"
            "<b>Example:</b> <code>/add_premium 123456789 pro 30</code>\n\n"
            "<b>Plan Types:</b>\n"
            "• <b>plus</b> - Unlimited forwarding only\n"
            "• <b>pro</b> - Unlimited forwarding + FTM mode + Priority support\n\n"
            "<b>Default: 30 days if days not specified.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        plan_type = context.args[1].lower()
        days = int(context.args[2]) if len(context.args) > 2 else 30
        
        # Validate plan type
        if plan_type not in ['plus', 'pro']:
            await update.message.reply_text(
                "❌ Invalid plan type! Please use 'plus' or 'pro'.\n\n"
                "<b>Plan Types:</b>\n"
                "• <b>plus</b> - Unlimited forwarding only\n"
                "• <b>pro</b> - Unlimited forwarding + FTM mode + Priority support",
                parse_mode=ParseMode.HTML
            )
            return
        
        if days <= 0:
            await update.message.reply_text("❌ Days must be greater than 0!")
            return
        
        # Add premium subscription
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(days=days)
        await db.add_premium_user(target_user_id, plan_type, days)
        
        # Get user info
        try:
            target_user = await context.bot.get_chat(target_user_id)
            user_info = f"{target_user.first_name}"
            if target_user.username:
                user_info += f" (@{target_user.username})"
        except:
            user_info = f"User ID: {target_user_id}"
        
        from plugins.timezone import display_expiry_date
        await update.message.reply_text(
            f"<b>✅ Premium Added Successfully!</b>\n\n"
            f"<b>User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Plan Type:</b> {plan_type.upper()}\n"
            f"<b>Duration:</b> {days} days\n"
            f"<b>Expires:</b> {display_expiry_date(expires_at)}",
            parse_mode=ParseMode.HTML
        )
        
        # Notify the user
        try:
            features_text = "• Unlimited forwarding processes\n"
            if plan_type == 'pro':
                features_text += "• FTM mode enabled\n• Priority support\n"
            
            await context.bot.send_message(
                target_user_id,
                f"<b>🎉 Premium Access Granted!</b>\n\n"
                f"<b>✅ You have been granted {plan_type.upper()} plan for {days} days!</b>\n"
                f"<b>💎 Granted by: {update.effective_user.first_name}</b>\n\n"
                f"<b>{plan_type.upper()} Plan Benefits:</b>\n"
                f"{features_text}\n"
                f"<b>Expires:</b> {display_expiry_date(expires_at)}\n"
                "<b>Use /myplan to check your subscription details.</b>",
                parse_mode=ParseMode.HTML
            )
        except:
            await update.message.reply_text("⚠️ Could not notify the user about premium access.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or days! Please provide valid numeric values.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding premium: {str(e)}")
        logger.error(f"Error in add_premium: {e}", exc_info=True)

async def remove_premium_command(update: Update, context: CallbackContext) -> None:
    """Handle /remove_premium command - admin only"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Usage:</b> <code>/remove_premium [user_id]</code>\n"
            "<b>Example:</b> <code>/remove_premium 123456789</code>\n\n"
            "<b>This will remove premium access from the user.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Check if user has premium
        if not await db.is_premium_user(target_user_id):
            await update.message.reply_text("❌ User doesn't have premium access!")
            return
        
        # Remove premium subscription
        await db.remove_premium_user(target_user_id)
        
        # Get user info
        try:
            target_user = await context.bot.get_chat(target_user_id)
            user_info = f"{target_user.first_name}"
            if target_user.username:
                user_info += f" (@{target_user.username})"
        except:
            user_info = f"User ID: {target_user_id}"
        
        await update.message.reply_text(
            f"<b>✅ Premium Removed Successfully!</b>\n\n"
            f"<b>User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Removed by:</b> {update.effective_user.first_name}",
            parse_mode=ParseMode.HTML
        )
        
        # Notify the user
        try:
            await context.bot.send_message(
                target_user_id,
                f"<b>❌ Premium Access Removed</b>\n\n"
                f"<b>Your premium access has been removed by an admin.</b>\n"
                f"<b>Removed by:</b> {update.effective_user.first_name}\n\n"
                "<b>You are now on the free plan with monthly limits.</b>\n"
                "<b>💎 To get premium again, use /plan to see available plans</b>",
                parse_mode=ParseMode.HTML
            )
        except:
            await update.message.reply_text("⚠️ Could not notify the user about premium removal.")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Please provide a valid numeric user ID.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error removing premium: {str(e)}")
        logger.error(f"Error in remove_premium: {e}", exc_info=True)

async def pusers_command(update: Update, context: CallbackContext) -> None:
    """Handle /pusers command with pagination and details - admin only"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    
    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
    
    try:
        premium_users = await db.get_all_premium_users()
        
        if not premium_users:
            await update.message.reply_text("📋 No premium users found.")
            return
        
        # Get page number from command args
        page = 1
        if context.args and len(context.args) > 0:
            try:
                page = int(context.args[0])
            except:
                page = 1
        
        # Pagination settings
        users_per_page = 10
        total_pages = (len(premium_users) + users_per_page - 1) // users_per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * users_per_page
        end_idx = min(start_idx + users_per_page, len(premium_users))
        
        from plugins.timezone import display_expiry_date
        
        text = f"<b>💎 Premium Users ({len(premium_users)})</b>\n"
        text += f"<b>📄 Page {page} of {total_pages}</b>\n"
        text += f"{'='*40}\n\n"
        
        for i, user in enumerate(premium_users[start_idx:end_idx], start_idx + 1):
            user_id_info = user.get('user_id')
            plan_type = user.get('plan_type', 'unknown').upper()
            subscribed = user.get('subscribed_at')
            expires = user.get('expires_at')
            amount = user.get('amount_paid', 0)
            
            # Get user info
            try:
                user_chat = await context.bot.get_chat(user_id_info)
                name = user_chat.first_name
                if user_chat.username:
                    name += f" (@{user_chat.username})"
            except:
                name = "Unknown User"
            
            text += f"<b>{i}.</b> {name}\n"
            text += f"   <b>ID:</b> <code>{user_id_info}</code>\n"
            text += f"   <b>Plan:</b> {plan_type}\n"
            
            if subscribed:
                from datetime import datetime
                if isinstance(subscribed, datetime):
                    text += f"   <b>Subscribed:</b> {subscribed.strftime('%Y-%m-%d')}\n"
            
            if expires:
                from datetime import datetime
                if isinstance(expires, datetime):
                    days_left = (expires - datetime.utcnow()).days
                    text += f"   <b>Expires:</b> {display_expiry_date(expires)}\n"
                    text += f"   <b>Days Left:</b> {days_left} days\n"
            
            if amount and amount != "sudo_lifetime_subscription":
                text += f"   <b>Paid:</b> ₹{amount}\n"
            elif amount == "sudo_lifetime_subscription":
                text += f"   <b>Type:</b> Lifetime Sudo\n"
            
            text += "\n"
        
        # Navigation buttons
        text += f"{'='*40}\n"
        
        buttons = []
        nav_row = []
        
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"pusers_page_{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="pusers_current"))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"pusers_page_{page+1}"))
        
        if nav_row:
            buttons.append(nav_row)
        
        buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"pusers_refresh_{page}")])
        
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in pusers: {e}", exc_info=True)
        await update.message.reply_text("❌ Error fetching premium users")

async def plan_command(update: Update, context: CallbackContext) -> None:
    """Handle /plan command"""
    if not update.effective_user or not update.message:
        return
    
    await update.message.reply_text(
        "💎 View our premium plans!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans')
        ]])
    )


async def referral_command(update: Update, context: CallbackContext) -> None:
    """Handle /referral command"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    referral_stats = await db.get_referral_stats(user_id)
    user_data = await db.get_user(user_id)
    
    referral_code = user_data.get('referral_code', 'None')
    total_referrals = referral_stats.get('total_referrals', 0)
    
    text = (
        f"<b>🔗 Your Referral Dashboard</b>\n\n"
        f"<b>Your Code:</b> <code>{referral_code}</code>\n"
        f"<b>Total Referrals:</b> {total_referrals}\n\n"
        f"<b>Share your referral link to earn rewards!</b>"
    )
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('🔄 Refresh', callback_data='refresh_referral')
        ]])
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle /help command"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"PTB Help command from user {user_id}")

    try:
        is_admin = Config.is_sudo_user(user_id)

        buttons = [[
            InlineKeyboardButton('🛠️ How To Use Me 🛠️', callback_data='how_to_use')
        ],[
            InlineKeyboardButton('⚙️ Settings ⚙️', callback_data='settings#main'),
            InlineKeyboardButton('📊 Stats 📊', callback_data='status')
        ],[
            InlineKeyboardButton('💬 Contact Admin', url='https://t.me/ftmdeveloperzbot')
        ]]

        if is_admin:
            buttons.append([InlineKeyboardButton('👨‍💻 Admin Commands 👨‍💻', callback_data='admin_commands')])

        buttons.append([InlineKeyboardButton('🔙 Back', callback_data='back')])

        await update.message.reply_text(
            text=Translation.HELP_TXT,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"Error in help command: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def info_command(update: Update, context: CallbackContext) -> None:
    """Handle /info command"""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_id = user.id

    logger.info(f"PTB Info command from user {user_id}")

    try:
        premium_info = await db.get_premium_user_details(user_id)
        daily_usage = await db.get_daily_usage(user_id)
        monthly_usage = await db.get_monthly_usage(user_id)
        user_data = await db.get_user(user_id)

        join_date = user_data.get('joined_date', datetime.utcnow()) if user_data else datetime.utcnow()
        join_date_str = display_joined_date(join_date)

        info_text = f"<b>👤 Your Account Information</b>\n\n"
        info_text += f"<b>📋 Basic Details:</b>\n"
        info_text += f"• <b>Name:</b> {user.first_name}"
        if user.last_name:
            info_text += f" {user.last_name}"
        info_text += f"\n• <b>Username:</b> @{user.username}" if user.username else "\n• <b>Username:</b> Not set"
        info_text += f"\n• <b>User ID:</b> <code>{user_id}</code>"
        info_text += f"\n• <b>Joined:</b> {join_date_str}\n\n"

        if premium_info:
            plan_type = premium_info.get('plan_type', 'unknown').upper()
            expires_at = premium_info.get('expires_at', 'Unknown')
            if isinstance(expires_at, datetime):
                expires_at_str = display_expiry_date(expires_at)
                time_remaining = time_until_expiry(expires_at)
            else:
                expires_at_str = str(expires_at)
                time_remaining = "Unknown"

            info_text += f"<b>💎 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> {plan_type} Plan ✅\n"
            info_text += f"• <b>Expires:</b> {expires_at_str}\n"
            info_text += f"• <b>Time Left:</b> {time_remaining}\n\n"
        else:
            info_text += f"<b>🆓 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> Free User\n"
            info_text += f"• <b>Limit:</b> 1 process per month\n\n"

        info_text += f"<b>📊 Usage Statistics:</b>\n"
        info_text += f"• <b>This Month:</b> {monthly_usage.get('processes', 0)} processes\n"
        info_text += f"• <b>Today:</b> {daily_usage.get('processes', 0)} processes\n"

        limit = await db.get_forwarding_limit(user_id)
        if limit == -1:
            info_text += f"• <b>Limit:</b> Unlimited processes ♾️\n\n"
        else:
            remaining = max(0, limit - monthly_usage.get('processes', 0))
            info_text += f"• <b>Monthly Limit:</b> {limit} processes\n"
            info_text += f"• <b>Remaining:</b> {remaining} processes\n\n"

        info_text += f"<b>Use /myplan for subscription details and upgrade options.</b>"

        keyboard = [
            [InlineKeyboardButton('💎 My Plan', callback_data='my_plan')],
            [InlineKeyboardButton('⚙️ Settings', callback_data='settings#main')],
            [InlineKeyboardButton('💬 Contact Admin', url='https://t.me/ftmdeveloperzbot')],
            [InlineKeyboardButton('🔙 Main Menu', callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in PTB info command for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while fetching your information. Please try again.")

async def myplan_command(update: Update, context: CallbackContext) -> None:
    """Handle /myplan command"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"PTB MyPlan command from user {user_id}")

    try:
        premium_info = await db.get_premium_user_details(user_id)

        if premium_info:
            plan_type = premium_info.get('plan_type', 'unknown').upper()
            expires_at = premium_info.get('expires_at')
            subscribed_at = premium_info.get('subscribed_at')
            amount_paid = premium_info.get('amount_paid', 0)

            plan_text = f"<b>💎 Your Subscription Details</b>\n\n"
            plan_text += f"<b>📦 Plan Type:</b> {plan_type} Plan\n"

            if subscribed_at:
                plan_text += f"<b>📅 Subscribed On:</b> {display_subscription_date(subscribed_at)}\n"

            if isinstance(expires_at, datetime):
                plan_text += f"<b>⏰ Expires On:</b> {display_expiry_date(expires_at)}\n"
                plan_text += f"<b>⏳ Time Left:</b> {time_until_expiry(expires_at)}\n"

            if amount_paid and amount_paid != "sudo_lifetime_subscription":
                plan_text += f"<b>💰 Amount Paid:</b> ₹{amount_paid}\n"
            elif amount_paid == "sudo_lifetime_subscription":
                plan_text += f"<b>👑 Special:</b> Lifetime Sudo Access\n"

            plan_text += f"\n<b>✨ Your Benefits:</b>\n"

            features = await db.get_user_plan_features(user_id)
            if features.get('unlimited_forwarding'):
                plan_text += "• ♾️ Unlimited forwarding processes\n"
            if features.get('ftm_mode'):
                plan_text += "• 🔥 FTM mode enabled\n"
            if features.get('priority_support'):
                plan_text += "• 🛡️ Priority support\n"

            buttons = [[
                InlineKeyboardButton('💎 Upgrade Plan', callback_data='premium_plans')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data='back')
            ]]
        else:
            plan_text = f"<b>🆓 Free Plan</b>\n\n"
            plan_text += f"<b>Current Limits:</b>\n"
            plan_text += f"• 1 process per month\n"
            plan_text += f"• Basic features only\n"
            plan_text += f"• No FTM mode\n\n"
            plan_text += f"<b>💎 Upgrade to get:</b>\n"
            plan_text += f"• Unlimited processes\n"
            plan_text += f"• FTM mode (Pro plan)\n"
            plan_text += f"• Priority support\n\n"
            plan_text += f"<b>🎁 Try /trial for 3-day free trial!</b>"

            buttons = [[
                InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial'),
                InlineKeyboardButton('💎 View Plans', callback_data='premium_plans')
            ],[
                InlineKeyboardButton('🔙 Back', callback_data='back')
            ]]

        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            text=plan_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in myplan command: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def users_command(update: Update, context: CallbackContext) -> None:
    """Handle /users command - admin only"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"PTB Users command from admin {user_id}")

    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command!")
        return

    try:
        all_users = await db.get_all_users()

        if not all_users:
            await update.message.reply_text("📋 No registered users found.")
            return

        total_users = len(all_users)
        premium_count = 0
        free_count = 0

        for user_info in all_users:
            user_id_info = user_info.get('id')
            premium_info = await db.get_premium_user_details(user_id_info)
            if premium_info:
                premium_count += 1
            else:
                free_count += 1

        users_text = f"<b>👥 User Statistics</b>\n\n"
        users_text += f"<b>📊 Overview:</b>\n"
        users_text += f"• Total Users: {total_users:,}\n"
        users_text += f"• 💎 Premium: {premium_count}\n"
        users_text += f"• 🆓 Free: {free_count}\n\n"
        users_text += f"<i>Use buttons below for detailed user information</i>"

        buttons = [[
            InlineKeyboardButton('📊 Detailed Stats', callback_data='users_detailed'),
            InlineKeyboardButton('🔄 Refresh', callback_data='users_refresh')
        ],[
            InlineKeyboardButton('🔙 Back', callback_data='admin_commands')
        ]]

        await update.message.reply_text(
            text=users_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in users command: {e}", exc_info=True)
        await update.message.reply_text("❌ An error occurred while fetching user data.")

async def speedtest_command(update: Update, context: CallbackContext) -> None:
    """Handle /speedtest command - admin only"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"PTB Speedtest command from user {user_id}")

    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ This command is only available for administrators.")
        return

    status_msg = await update.message.reply_text("🔄 <b>Running Network Speed Test...</b>\n⏳ Please wait, this may take a moment.", parse_mode=ParseMode.HTML)

    try:
        st = speedtest.Speedtest()
        await status_msg.edit_text("🔄 <b>Finding best server...</b>\n⏳ Please wait.", parse_mode=ParseMode.HTML)

        st.get_best_server()
        await status_msg.edit_text("🔄 <b>Testing download speed...</b>\n⏳ Please wait.", parse_mode=ParseMode.HTML)

        download_speed = st.download()
        await status_msg.edit_text("🔄 <b>Testing upload speed...</b>\n⏳ Please wait.", parse_mode=ParseMode.HTML)

        upload_speed = st.upload()
        ping = st.results.ping
        server = st.get_best_server()

        download_mbps = download_speed / 1024 / 1024
        upload_mbps = upload_speed / 1024 / 1024

        speed_text = f"""<b>🌐 Bot Server Network Speed Test</b>

<b>📡 Server Connection Info:</b>
├ <b>ISP:</b> <code>{server.get('sponsor', 'Unknown')}</code>
├ <b>Server Location:</b> <code>{server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}</code>
├ <b>Distance:</b> <code>{server.get('d', 0):.1f} km</code>

<b>🚀 Bot Server Speed Results:</b>
├ <b>📥 Download:</b> <code>{download_mbps:.2f} Mbps</code>
├ <b>📤 Upload:</b> <code>{upload_mbps:.2f} Mbps</code>
├ <b>📶 Ping:</b> <code>{ping:.1f} ms</code>

<b>📊 Test Information:</b>
├ <b>Test Date:</b> <code>{st.results.timestamp}</code>
└ <b>Note:</b> <code>Shows bot server network, not your location</code>"""

        await status_msg.edit_text(speed_text, parse_mode=ParseMode.HTML)
        logger.info(f"Speedtest completed for user {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>Speed Test Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg, parse_mode=ParseMode.HTML)
        logger.error(f"Speedtest error for user {user_id}: {e}", exc_info=True)

async def system_command(update: Update, context: CallbackContext) -> None:
    """Handle /system command - admin only"""
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"PTB System info command from user {user_id}")

    if not Config.is_sudo_user(user_id):
        await update.message.reply_text("❌ This command is only available for administrators.")
        return

    status_msg = await update.message.reply_text("🔄 <b>Gathering system information...</b>", parse_mode=ParseMode.HTML)

    try:
        uname = platform.uname()
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()

        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024**3)
        memory_used = memory.used / (1024**3)
        memory_percent = memory.percent

        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)
        disk_used = disk.used / (1024**3)
        disk_percent = (disk.used / disk.total) * 100

        boot_time = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(boot_time)
        uptime_str = str(uptime).split('.')[0]

        python_ver = python_version()

        system_text = f"""<b>🖥️ Bot Server System Information</b>

<b>💻 Server System Details:</b>
├ <b>OS:</b> <code>{uname.system} {uname.release}</code>
├ <b>Architecture:</b> <code>{uname.machine}</code>
├ <b>Hostname:</b> <code>{uname.node}</code>

<b>🔧 Server Hardware Info:</b>
├ <b>CPU Cores:</b> <code>{cpu_count} cores</code>
├ <b>CPU Usage:</b> <code>{cpu_percent}%</code>
├ <b>CPU Frequency:</b> <code>{cpu_freq.current:.0f} MHz</code>

<b>💾 Memory Info:</b>
├ <b>Total RAM:</b> <code>{memory_total:.2f} GB</code>
├ <b>Used RAM:</b> <code>{memory_used:.2f} GB</code>
├ <b>RAM Usage:</b> <code>{memory_percent}%</code>

<b>💿 Disk Info:</b>
├ <b>Total Disk:</b> <code>{disk_total:.2f} GB</code>
├ <b>Used Disk:</b> <code>{disk_used:.2f} GB</code>
├ <b>Disk Usage:</b> <code>{disk_percent:.1f}%</code>

<b>⏰ Uptime:</b> <code>{uptime_str}</code>
<b>🐍 Python:</b> <code>{python_ver}</code>"""

        await status_msg.edit_text(system_text, parse_mode=ParseMode.HTML)
        logger.info(f"System info sent to user {user_id}")

    except Exception as e:
        error_msg = f"❌ <b>System Info Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg, parse_mode=ParseMode.HTML)
        logger.error(f"System info error for user {user_id}: {e}", exc_info=True)

async def handle_non_command_messages(update: Update, context: CallbackContext) -> None:
    """Forward non-command text messages to Pyrogram's waiting system"""
    if not update.effective_user or not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    message_text = update.message.text

    # Import waiting_messages from plugins.test
    try:
        from plugins.test import waiting_messages

        # Check if this user is waiting for input in Pyrogram
        if user_id in waiting_messages:
            future = waiting_messages[user_id]
            if not future.done():
                # Create a message-like object that Pyrogram expects
                class MessageProxy:
                    def __init__(self, text):
                        self.text = text
                        self.from_user = update.effective_user

                    async def delete(self):
                        try:
                            await update.message.delete()
                        except:
                            pass

                # Set the result with the message proxy
                try:
                    future.set_result(MessageProxy(message_text))
                    logger.info(f"PTB forwarded message from waiting user {user_id} to Pyrogram: {message_text[:50]}...")
                    # Delete from waiting_messages
                    if user_id in waiting_messages:
                        del waiting_messages[user_id]
                except Exception as e:
                    logger.error(f"Error forwarding message to Pyrogram for user {user_id}: {e}")
            return
    except Exception as e:
        logger.error(f"Error checking waiting_messages: {e}")

def setup_ptb_application():
    """Setup PTB application with all handlers"""
    from config import Config
    from ptb_callbacks import setup_callback_handlers

    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Register command handlers (info, users, reset, resetall, broadcast handled by ptb_commands.py)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myplan", myplan_command))
    application.add_handler(CommandHandler("speedtest", speedtest_command))
    application.add_handler(CommandHandler("system", system_command))

    # Register pass-through handlers for Pyrogram commands (prevents PTB from blocking them)
    application.add_handler(CommandHandler("trial", trial_command))
    application.add_handler(CommandHandler("commands", commands_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("add_premium", add_premium_command))
    application.add_handler(CommandHandler("remove_premium", remove_premium_command))
    application.add_handler(CommandHandler("pusers", pusers_command))
    application.add_handler(CommandHandler("plan", plan_command))
    application.add_handler(CommandHandler("referral", referral_command))

    # Register callback query handlers
    setup_callback_handlers(application)

    # Register command handlers that PTB should handle
    # Commands handled by PTB: /help, /myplan, /speedtest, /system
    # Commands NOT handled by PTB (Pyrogram handles these):
    # /start, /settings, /forward, /fwd
    # /trial, /commands, /verify, /add_premium, /remove_premium, /pusers, /plan, /referral

    # Add message handler for non-command messages (to forward to Pyrogram waiting system)
    # This must be added AFTER all command handlers so it catches only non-command messages
    application.add_handler(MessageHandler(
        ptb_filters.TEXT & ~ptb_filters.COMMAND,
        handle_non_command_messages
    ))

    logger.info("PTB Application configured with callback handlers")
    logger.info("PTB user commands: /help, /myplan, /trial, /commands, /verify, /plan, /referral")
    logger.info("PTB admin commands: /info, /users, /reset, /resetall, /broadcast, /add_premium, /remove_premium, /pusers")
    logger.info("Pyrogram handles: /start, /settings, /forward, /fwd and all forwarding operations")
    logger.info("Message handler added to forward non-command messages to Pyrogram")

    return application