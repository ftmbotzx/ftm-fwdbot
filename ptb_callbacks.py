#!/usr/bin/env python3
"""
PTB Callback Query Handlers
Handles all inline keyboard button callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest

from database import db
from config import Config
from translation import Translation
from plugins.timezone import display_expiry_date, time_until_expiry, get_current_ist_timestamp, display_subscription_date

logger = logging.getLogger(__name__)

async def back_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'back' callback - return to main menu"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    main_buttons = [[
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
    
    text = Translation.START_TXT.format(user.mention_html())
    
    try:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(main_buttons)
        )
    except BadRequest:
        pass

async def help_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'help' callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
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
    
    try:
        await query.edit_message_text(
            text=Translation.HELP_TXT,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass

async def about_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'about' callback"""
    query = update.callback_query
    await query.answer()
    
    about_text = Translation.ABOUT_TXT
    buttons = [[InlineKeyboardButton('🔙 Back', callback_data='back')]]
    
    try:
        await query.edit_message_text(
            text=about_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass

async def how_to_use_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'how_to_use' callback"""
    query = update.callback_query
    await query.answer()
    
    how_to_text = Translation.HOW_TO_USE_TXT
    buttons = [[InlineKeyboardButton('🔙 Back to Help', callback_data='help')]]
    
    try:
        await query.edit_message_text(
            text=how_to_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass

async def status_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'status' callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        total_users, total_bots = await db.total_users_bots_count()
        premium_count = await db.count_premium_users()
        daily_usage = await db.get_daily_usage(user_id)
        monthly_usage = await db.get_monthly_usage(user_id)
        
        status_text = f"""<b>📊 Bot Status</b>

<b>👥 Total Users:</b> {total_users:,}
<b>🤖 Total Bots:</b> {total_bots:,}
<b>💎 Premium Users:</b> {premium_count}

<b>📈 Your Usage:</b>
• Today: {daily_usage.get('processes', 0)} processes
• This Month: {monthly_usage.get('processes', 0)} processes"""
        
        buttons = [[InlineKeyboardButton('🔙 Back', callback_data='help')]]
        
        await query.edit_message_text(
            text=status_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass
    except Exception as e:
        logger.error(f"Error in status callback: {e}", exc_info=True)

async def my_plan_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'my_plan' callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
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
            
            if expires_at:
                plan_text += f"<b>⏰ Expires On:</b> {display_expiry_date(expires_at)}\n"
                plan_text += f"<b>⏳ Time Left:</b> {time_until_expiry(expires_at)}\n"
            
            if amount_paid and amount_paid != "sudo_lifetime_subscription":
                plan_text += f"<b>💰 Amount Paid:</b> ₹{amount_paid}\n"
            
            plan_text += f"\n<b>✨ Your Benefits:</b>\n"
            plan_text += "• ♾️ Unlimited forwarding processes\n"
            
            if plan_type == "PRO":
                plan_text += "• 🔥 FTM mode enabled\n"
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
        
        await query.edit_message_text(
            text=plan_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass
    except Exception as e:
        logger.error(f"Error in my_plan callback: {e}", exc_info=True)

async def premium_plans_callback(update: Update, context: CallbackContext) -> None:
    """Handle 'premium_plans' callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    try:
        current_plan = "FREE"
        plan_details = await db.get_premium_user_details(user_id)
        
        if plan_details:
            current_plan = plan_details.get('plan_type', 'FREE').upper()
        
        plans_text = (
            "💎 <b>Premium Plans</b>\n\n"
            f"👤 <b>Your Current Plan:</b> {current_plan}\n\n"
            "📋 <b>Available Plans:</b>\n\n"
            "🆓 <b>FREE PLAN</b>\n"
            "• 1 forwarding process per month\n"
            "• Basic features only\n"
            "• No FTM mode\n\n"
            
            "✨ <b>PLUS PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• All basic features\n"
            "• No FTM mode\n"
            "• 15 days: ₹199\n"
            "• 30 days: ₹299\n\n"
            
            "🏆 <b>PRO PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• FTM mode enabled\n"
            "• Priority support\n"
            "• All premium features\n"
            "• 15 days: ₹299\n"
            "• 30 days: ₹549\n\n"
            
            f"💳 <b>Payment:</b> UPI - {Config.UPI_ID}\n"
            "📸 <b>After payment, send screenshot with /verify</b>"
        )
        
        plans_buttons = [
            [
                InlineKeyboardButton("✨ Plus 15 Days (₹199)", callback_data="buy_plus_15"),
                InlineKeyboardButton("✨ Plus 30 Days (₹299)", callback_data="buy_plus_30")
            ],
            [
                InlineKeyboardButton("🏆 Pro 15 Days (₹299)", callback_data="buy_pro_15"),
                InlineKeyboardButton("🏆 Pro 30 Days (₹549)", callback_data="buy_pro_30")
            ],
            [
                InlineKeyboardButton("📊 My Plan Details", callback_data="my_plan"),
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
        
        await query.edit_message_text(
            text=plans_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(plans_buttons)
        )
    except BadRequest:
        pass
    except Exception as e:
        logger.error(f"Error in premium_plans callback: {e}", exc_info=True)

async def buy_plan_callback(update: Update, context: CallbackContext) -> None:
    """Handle buy_plus_X and buy_pro_X callbacks"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    plan_type = data_parts[1]  # plus or pro
    duration = int(data_parts[2])  # 15 or 30
    
    amount = Config.PLAN_PRICING[plan_type][f'{duration}_days']
    
    purchase_text = (
        f"💳 <b>Purchase {plan_type.upper()} Plan</b>\n\n"
        f"📦 <b>Plan:</b> {plan_type.upper()}\n"
        f"⏰ <b>Duration:</b> {duration} days\n"
        f"💰 <b>Amount:</b> ₹{amount}\n\n"
        f"<b>💵 Payment Instructions:</b>\n"
        f"1. Send ₹{amount} to UPI: <code>{Config.UPI_ID}</code>\n"
        f"2. Take a screenshot of the payment\n"
        f"3. Send the screenshot to this bot\n"
        f"4. Reply to the screenshot with: <code>/verify {plan_type} {duration}</code>\n\n"
        f"<b>⚠️ Important:</b>\n"
        f"• Pay exact amount: ₹{amount}\n"
        f"• Include payment reference in screenshot\n"
        f"• Verification usually takes 5-10 minutes"
    )
    
    buttons = [
        [
            InlineKeyboardButton("📋 Copy UPI ID", callback_data="copy_upi"),
            InlineKeyboardButton("💬 Contact Admin", url='https://t.me/ftmdeveloperzbot')
        ],
        [
            InlineKeyboardButton("🔙 Back to Plans", callback_data="premium_plans")
        ]
    ]
    
    try:
        await query.edit_message_text(
            text=purchase_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass

async def copy_upi_callback(update: Update, context: CallbackContext) -> None:
    """Handle copy_upi callback"""
    query = update.callback_query
    await query.answer(
        f"✅ UPI ID copied!\n{Config.UPI_ID}",
        show_alert=True
    )

async def get_free_trial_callback(update: Update, context: CallbackContext) -> None:
    """Handle get_free_trial callback"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        can_trial = await db.can_use_trial(user_id)
        
        if not can_trial:
            await query.answer("❌ You have already used your free trial this year!", show_alert=True)
            return
        
        is_premium = await db.is_premium_user(user_id)
        if is_premium:
            await query.answer("✅ You already have premium access!", show_alert=True)
            return
        
        trial_text = (
            "<b>🎁 Get 3-Day Free Trial</b>\n\n"
            "<b>Trial Benefits:</b>\n"
            "• Unlimited forwarding for 3 days\n"
            "• All Plus plan features\n"
            "• Test before buying\n\n"
            "<b>⚠️ Trial Rules:</b>\n"
            "• One trial per year per user\n"
            "• Activates immediately\n"
            "• Cannot be extended\n\n"
            "<b>Ready to activate your free trial?</b>"
        )
        
        buttons = [[
            InlineKeyboardButton('✅ Activate Trial', callback_data='confirm_trial'),
            InlineKeyboardButton('❌ Cancel', callback_data='back')
        ]]
        
        await query.edit_message_text(
            text=trial_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest:
        pass
    except Exception as e:
        logger.error(f"Error in get_free_trial callback: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

async def confirm_trial_callback(update: Update, context: CallbackContext) -> None:
    """Handle confirm_trial callback"""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        can_trial = await db.can_use_trial(user_id)
        
        if not can_trial:
            await query.answer("❌ You have already used your free trial!", show_alert=True)
            return
        
        success, result = await db.grant_trial(user_id)
        
        if success:
            expires_date = display_expiry_date(result)
            success_text = (
                f"<b>🎉 3-Day Trial Activated!</b>\n\n"
                f"<b>✅ You now have unlimited forwarding for 3 days!</b>\n\n"
                f"<b>Trial Benefits:</b>\n"
                f"• Unlimited forwarding processes\n"
                f"• All Plus plan features\n"
                f"• No FTM mode\n\n"
                f"<b>⏰ Expires:</b> {expires_date}\n\n"
                f"<b>💎 Upgrade to Pro for FTM mode and more!</b>"
            )
            
            buttons = [[
                InlineKeyboardButton('💎 View Premium Plans', callback_data='premium_plans'),
                InlineKeyboardButton('🏠 Main Menu', callback_data='back')
            ]]
            
            await query.edit_message_text(
                text=success_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.answer("✅ Trial activated successfully!", show_alert=True)
        else:
            await query.answer("❌ Failed to activate trial. Please contact admin.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in confirm_trial callback: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

async def pusers_pagination_callback(update: Update, context: CallbackContext) -> None:
    """Handle pusers pagination callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        await query.answer("❌ You don't have permission!", show_alert=True)
        return
    
    try:
        callback_data = query.data
        
        if callback_data == "pusers_current":
            await query.answer("You are on this page", show_alert=False)
            return
        
        if callback_data.startswith("pusers_page_"):
            page = int(callback_data.split("_")[-1])
        elif callback_data.startswith("pusers_refresh_"):
            page = int(callback_data.split("_")[-1])
        else:
            await query.answer("Invalid action")
            return
        
        await query.answer()
        
        # Get premium users
        premium_users = await db.get_all_premium_users()
        
        if not premium_users:
            await query.edit_message_text("📋 No premium users found.")
            return
        
        # Pagination
        users_per_page = 10
        total_pages = (len(premium_users) + users_per_page - 1) // users_per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * users_per_page
        end_idx = min(start_idx + users_per_page, len(premium_users))
        
        text = f"<b>💎 Premium Users ({len(premium_users)})</b>\n"
        text += f"<b>📄 Page {page} of {total_pages}</b>\n"
        text += f"{'='*40}\n\n"
        
        for i, user in enumerate(premium_users[start_idx:end_idx], start_idx + 1):
            user_id_info = user.get('user_id')
            plan_type = user.get('plan_type', 'unknown').upper()
            expires = user.get('expires_at')
            amount = user.get('amount_paid', 0)
            
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
        
        text += f"{'='*40}\n"
        
        # Navigation buttons
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
        
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Error in pusers pagination: {e}", exc_info=True)
        await query.answer("❌ Error loading page", show_alert=True)

async def admin_commands_callback(update: Update, context: CallbackContext) -> None:
    """Handle admin_commands callback"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        await query.answer("❌ You don't have permission!", show_alert=True)
        return
    
    await query.answer()
    
    admin_buttons = [[
        InlineKeyboardButton('📊 System Info', callback_data='admin_system'),
        InlineKeyboardButton('⚡ Speed Test', callback_data='admin_speedtest')
    ],[
        InlineKeyboardButton('🔙 Back to Help', callback_data='help')
    ]]
    
    admin_text = (
        "<b>🔧 Admin Commands Panel</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• <code>/users</code> - List all users\n"
        "• <code>/speedtest</code> - Test network speed\n"
        "• <code>/system</code> - System information\n\n"
        "<i>Use buttons below for quick actions</i>"
    )
    
    try:
        await query.edit_message_text(
            text=admin_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_buttons)
        )
    except BadRequest:
        pass

def setup_callback_handlers(application):
    """Register all callback query handlers"""
    
    # Main navigation callbacks
    application.add_handler(CallbackQueryHandler(back_callback, pattern=r'^back$'))
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r'^help$'))
    application.add_handler(CallbackQueryHandler(about_callback, pattern=r'^about$'))
    application.add_handler(CallbackQueryHandler(how_to_use_callback, pattern=r'^how_to_use$'))
    application.add_handler(CallbackQueryHandler(status_callback, pattern=r'^status$'))
    
    # Plan and premium callbacks
    application.add_handler(CallbackQueryHandler(my_plan_callback, pattern=r'^my_plan$'))
    application.add_handler(CallbackQueryHandler(premium_plans_callback, pattern=r'^premium_plans$'))
    application.add_handler(CallbackQueryHandler(premium_plans_callback, pattern=r'^premium#'))
    application.add_handler(CallbackQueryHandler(buy_plan_callback, pattern=r'^buy_(plus|pro)_(15|30)$'))
    application.add_handler(CallbackQueryHandler(copy_upi_callback, pattern=r'^copy_upi$'))
    
    # Trial callbacks
    application.add_handler(CallbackQueryHandler(get_free_trial_callback, pattern=r'^get_free_trial$'))
    application.add_handler(CallbackQueryHandler(confirm_trial_callback, pattern=r'^confirm_trial$'))
    
    # Admin callbacks
    application.add_handler(CallbackQueryHandler(admin_commands_callback, pattern=r'^admin_commands$'))
    application.add_handler(CallbackQueryHandler(pusers_pagination_callback, pattern=r'^pusers_(page|refresh|current)'))
    
    # NOTE: settings# callbacks are handled by Pyrogram in plugins/settings.py
    # Do NOT add PTB handler for settings# to avoid conflicts
    
    logger.info("All PTB callback handlers registered")
