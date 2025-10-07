import asyncio
import logging 
import os
import logging.config
from datetime import datetime
from database import db 
from config import Config  
from pyrogram import Client, __version__

# Validate environment variables before starting
Config.validate_env()
from pyrogram.raw.all import layer 
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram import utils as pyroutils 

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Adjust Pyrogram chat ID ranges to solve peer ID issue
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

class Bot(Client): 
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins=dict(root="plugins"),
            workers=50,
            bot_token=Config.BOT_TOKEN
        )
        self.log = logging
        self.log_channel_id = getattr(Config, 'LOG_CHANNEL_ID', -1003003594014)  # Default to the mentioned channel
        self.notification_manager = None  # Will be initialized after start

    async def start(self):
        await super().start()
        me = await self.get_me()
        logging.info(f"{me.first_name} with for pyrogram v{__version__} (Layer {layer}) started on @{me.username}.")
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)
        
        # Initialize notification manager
        from utils.notifications import NotificationManager
        self.notification_manager = NotificationManager(self)
        
        
        
        text = "**๏[-ิ_•ิ]๏ bot restarted !**"
        logging.info(text)
        success = failed = 0
        
        # Send restart message to all users (not just forwarding users)
        all_users = await db.get_all_users()
        for user in all_users:
           chat_id = user['id']
           try:
              await self.send_message(chat_id, text)
              success += 1
           except FloodWait as e:
              await asyncio.sleep(e.value + 1)
              try:
                 await self.send_message(chat_id, text)
                 success += 1
              except Exception:
                 failed += 1
           except Exception:
              failed += 1 
        
        # Also send to owner
        for owner_id in Config.OWNER_ID:
           try:
              await self.send_message(owner_id, text)
           except Exception:
              pass
        
        # Clear all forwarding sessions
        await db.rmve_frwd(all=True)
        if (success + failed) != 0:
           logging.info(f"Restart message status - "
                 f"success: {success}, "
                 f"failed: {failed}")
        
        # Grant lifetime Pro subscriptions to all sudo users if not already given
        await self.grant_sudo_lifetime_subscriptions()
        
        # Notify users about their ongoing processes after restart
        await self.notify_process_recovery()
        
        # Send startup notification to log channel after restart messages are sent
        try:
            startup_msg = f"""<b>🚀 Bot Started Successfully!</b>

<b>Bot Name:</b> {me.first_name}
<b>Username:</b> @{me.username}
<b>Bot ID:</b> <code>{me.id}</code>
<b>Pyrogram Version:</b> v{__version__}
<b>Layer:</b> {layer}

<b>Restart Stats:</b>
• Success: {success} users notified
• Failed: {failed} users failed
• Total Users: {success + failed}

<b>Status:</b> ✅ Online and Ready"""
            
            await self.notification_manager.send_log_notification(startup_msg)
            logging.info("Startup notification sent to log channel")
        except Exception as e:
            logging.error(f"Failed to send startup notification: {e}")
        
        # Start background cleanup task for chat requests
        try:
            from utils.cleanup import periodic_cleanup
            asyncio.create_task(periodic_cleanup())
            logging.info("Background cleanup task started")
        except Exception as e:
            logging.error(f"Failed to start cleanup task: {e}")

    async def grant_sudo_lifetime_subscriptions(self):
        """Grant lifetime Pro subscriptions to all sudo users if not already given"""
        try:
            # Get all sudo users (owners + admins)
            sudo_users = Config.OWNER_ID + Config.ADMIN_ID
            granted_count = 0
            
            for sudo_user_id in sudo_users:
                try:
                    # Check if user already has an active premium subscription
                    existing_premium = await db.get_premium_user_details(sudo_user_id)
                    
                    if existing_premium and existing_premium.get('is_active', False):
                        # Check if it's already a lifetime subscription
                        if existing_premium.get('amount_paid') == 'sudo_lifetime_subscription':
                            logging.info(f"Sudo user {sudo_user_id} already has lifetime subscription, skipping")
                            continue
                        else:
                            # User has some other subscription, remove it first
                            await db.remove_premium_user(sudo_user_id)
                            logging.info(f"Removed existing subscription for sudo user {sudo_user_id}")
                    
                    # Grant lifetime Pro subscription (999 years)
                    await db.add_premium_user(
                        user_id=sudo_user_id,
                        plan_type="pro",
                        duration_days=365250,  # 999+ years (lifetime)
                        amount_paid="sudo_lifetime_subscription"
                    )
                    
                    granted_count += 1
                    logging.info(f"✅ Granted lifetime Pro subscription to sudo user {sudo_user_id}")
                    
                    # Send notification to the sudo user
                    try:
                        await self.send_message(
                            sudo_user_id,
                            "<b>🎉 Lifetime Pro Access Granted!</b>\n\n"
                            "<b>✅ You have been automatically granted lifetime Pro access as a sudo user!</b>\n\n"
                            "<b>🏆 Pro Plan Benefits:</b>\n"
                            "• ♾️ Unlimited forwarding processes\n"
                            "• 🔥 FTM mode with source tracking\n"
                            "• 🛡️ Priority support\n"
                            "• ⚡ Enhanced performance\n"
                            "• 📈 All premium features unlocked\n\n"
                            "<b>⏰ Duration:</b> Lifetime (999+ years)\n"
                            "<b>🔑 Access Level:</b> Sudo User\n\n"
                            "<b>Use /myplan to check your subscription details.</b>"
                        )
                    except Exception as notify_error:
                        logging.error(f"Failed to notify sudo user {sudo_user_id}: {notify_error}")
                        
                except Exception as user_error:
                    logging.error(f"Failed to grant subscription to sudo user {sudo_user_id}: {user_error}")
                    
            if granted_count > 0:
                logging.info(f"✅ Granted lifetime Pro subscriptions to {granted_count} sudo users")
                
                # Send notification to log channel
                try:
                    await self.notification_manager.send_log_notification(
                        f"<b>🏆 Sudo Lifetime Subscriptions Granted!</b>\n\n"
                        f"<b>Count:</b> {granted_count} users\n"
                        f"<b>Plan:</b> Pro (Lifetime)\n"
                        f"<b>Access Level:</b> Sudo Users\n"
                        f"<b>Duration:</b> 999+ years\n\n"
                        f"<b>✅ All sudo users now have lifetime Pro access!</b>"
                    )
                except Exception as log_error:
                    logging.error(f"Failed to send sudo subscription log: {log_error}")
            else:
                logging.info("ℹ️ No new sudo lifetime subscriptions needed - all already have access")
                
        except Exception as e:
            logging.error(f"Error granting sudo lifetime subscriptions: {e}")

    async def notify_process_recovery(self):
        """Auto-resume interrupted forwarding processes after restart"""
        try:
            # Get users with process tracking data (both ongoing and completed)
            all_users_with_tracking = await db.col.find({
                'process_tracking.last_updated': {'$exists': True}
            }).to_list(length=1000)
            
            users_with_processes = await db.get_users_with_ongoing_processes()
            recovery_count = 0
            
            # First, handle users with ongoing processes (auto-resume)
            for user in users_with_processes:
                user_id = user['id']
                tracking = user.get('process_tracking', {})
                
                if not tracking.get('last_ongoing_process'):
                    continue
                
                try:
                    from_chat = tracking.get('from_chat')
                    to_chat = tracking.get('to_chat')
                    last_fetched_msg_id = tracking.get('last_fetched_msg_id')
                    skip = tracking.get('original_skip', 0)  # Get original skip value
                    total_messages = tracking.get('total_messages', 0)
                    processed_count = tracking.get('processed_count', 0)
                    
                    if not from_chat or not to_chat:
                        logging.warning(f"Missing chat info for user {user_id}, clearing tracking")
                        await db.clear_process_tracking(user_id)
                        continue
                    
                    # Calculate where to resume from
                    # If we have a last_fetched_msg_id, resume from the next message after it
                    # Otherwise, resume from the original skip position
                    resume_from = (last_fetched_msg_id + 1) if last_fetched_msg_id else skip
                    
                    # Calculate already processed
                    already_processed = resume_from - 1
                    
                    # Calculate remaining messages
                    remaining = total_messages - already_processed
                    
                    # Calculate progress percentage
                    progress_percentage = 0
                    if total_messages > 0:
                        progress_percentage = (already_processed / total_messages) * 100
                    
                    progress_bar = self._create_progress_bar(progress_percentage)
                    
                    # Send resuming notification
                    user_msg = f"""<b>🔄 Auto-Resuming Interrupted Process</b>

<b>📊 Progress Status:</b>
{progress_bar}
• <b>Already Processed:</b> {already_processed}/{total_messages} messages ({progress_percentage:.1f}%)
• <b>Original Skip:</b> {skip}
• <b>Resuming from:</b> Message ID {resume_from}
• <b>Remaining:</b> {remaining} messages
• <b>Source Chat:</b> <code>{from_chat}</code>
• <b>Target Chat:</b> <code>{to_chat}</code>

<b>⏳ Resuming forwarding process now...</b>"""
                    
                    await self.send_message(user_id, user_msg)
                    
                    # Auto-resume the forwarding process
                    from plugins.utils import STS
                    from config import temp
                    
                    # Create a unique forward ID for this resumed process
                    forward_id = f"{user_id}-resumed-{int(asyncio.get_event_loop().time())}"
                    
                    # Store the forwarding state with correct skip position
                    sts = STS(forward_id).store(
                        From=from_chat,
                        to=to_chat,
                        skip=resume_from,  # Resume from last fetched position
                        limit=total_messages
                    )
                    
                    # Mark as a resumed process
                    sts.data[forward_id]['resumed'] = True
                    sts.data[forward_id]['original_skip'] = skip
                    sts.data[forward_id]['user_id'] = user_id
                    
                    # Start forwarding in background
                    asyncio.create_task(self._resume_forwarding(user_id, forward_id, sts))
                    
                    recovery_count += 1
                    
                    log_msg = f"""<b>🔄 Auto-Resuming Process</b>

<b>👤 User Information:</b>
├ <b>User ID:</b> <code>{user_id}</code>
├ <b>Name:</b> {user.get('name', 'Unknown')}
└ <b>Status:</b> ✅ Process Resumed

<b>📊 Resume Details:</b>
├ <b>Source Chat:</b> <code>{from_chat}</code>
├ <b>Target Chat:</b> <code>{to_chat}</code>
├ <b>Original Skip:</b> {skip}
├ <b>Resume From:</b> Message ID {resume_from}
├ <b>Already Processed:</b> {processed_count}/{total_messages}
└ <b>Remaining:</b> {remaining} messages

<b>✅ Forwarding process automatically resumed from last position.</b>"""
                    
                    await self.notification_manager.send_log_notification(log_msg)
                    logging.info(f"✅ Auto-resumed process for user {user_id} from message {resume_from}")
                    
                except Exception as user_error:
                    logging.error(f"Failed to resume process for user {user_id}: {user_error}")
                    
                    # Clear tracking on error
                    try:
                        await db.clear_process_tracking(user_id)
                    except Exception as clear_error:
                        logging.error(f"Failed to clear tracking for user {user_id}: {clear_error}")
            
            # Now handle users whose last process was completed before shutdown
            completed_before_shutdown_count = 0
            for user in all_users_with_tracking:
                user_id = user['id']
                tracking = user.get('process_tracking', {})
                
                # Skip users with ongoing processes (already handled above)
                if tracking.get('last_ongoing_process'):
                    continue
                
                # Check if process was completed before shutdown
                if tracking.get('process_completed') or tracking.get('process_cancelled'):
                    try:
                        completion_status = "completed" if tracking.get('process_completed') else "cancelled"
                        from_chat = tracking.get('from_chat')
                        to_chat = tracking.get('to_chat')
                        processed_count = tracking.get('processed_count', 0)
                        total_messages = tracking.get('total_messages', 0)
                        
                        if from_chat and to_chat:
                            status_icon = "✅" if completion_status == "completed" else "❌"
                            user_msg = f"""<b>{status_icon} Process Status After Restart</b>

<b>Good news! Your last forwarding process was already {completion_status} before bot shutdown.</b>

<b>📊 Last Process Details:</b>
• <b>Status:</b> {completion_status.title()}
• <b>Source Chat:</b> <code>{from_chat}</code>
• <b>Target Chat:</b> <code>{to_chat}</code>
• <b>Messages Processed:</b> {processed_count}/{total_messages}

<b>ℹ️ No action needed - you can start a new forwarding process anytime!</b>"""
                            
                            await self.send_message(user_id, user_msg)
                            completed_before_shutdown_count += 1
                            
                            log_msg = f"""<b>📋 Completed Process Notification Sent</b>

<b>👤 User Information:</b>
├ <b>User ID:</b> <code>{user_id}</code>
├ <b>Name:</b> {user.get('name', 'Unknown')}
└ <b>Status:</b> Notified about {completion_status} process

<b>📊 Process Details:</b>
├ <b>Source Chat:</b> <code>{from_chat}</code>
├ <b>Target Chat:</b> <code>{to_chat}</code>
├ <b>Processed:</b> {processed_count}/{total_messages}
└ <b>Status Before Shutdown:</b> {completion_status.title()}

<b>✅ User notified that no active process was running before restart.</b>"""
                            
                            await self.notification_manager.send_log_notification(log_msg)
                    except Exception as user_error:
                        logging.error(f"Failed to notify user {user_id} about completed process: {user_error}")
            
            # Send summary
            if recovery_count > 0 or completed_before_shutdown_count > 0:
                summary_msg = f"""<b>📊 Post-Restart Summary</b>

<b>Processes Resumed:</b> {recovery_count}
<b>Completed Before Shutdown:</b> {completed_before_shutdown_count}

<b>Status:</b> ✅ All users notified about their process status</b>"""
                
                await self.notification_manager.send_log_notification(summary_msg)
                logging.info(f"✅ Recovery completed - {recovery_count} resumed, {completed_before_shutdown_count} already completed")
            else:
                logging.info("ℹ️ No process notifications needed")
                
        except Exception as e:
            logging.error(f"Error in auto-resume: {e}")
    
    async def _resume_forwarding(self, user_id, forward_id, sts):
        """Resume forwarding process in background"""
        try:
            from plugins.regix import pub_
            from config import temp
            
            # Send a completely NEW progress message for the resumed process
            # After restart, we have no reference to old messages
            try:
                new_progress_msg = await self.send_message(
                    user_id,
                    "<code>⏳ Resuming your forwarding process from last position...</code>"
                )
                
                # Validate that message was sent successfully
                if not new_progress_msg or not hasattr(new_progress_msg, 'id'):
                    raise ValueError("Failed to send resume progress message")
                    
                logging.info(f"Resume message sent successfully to user {user_id}, msg_id: {new_progress_msg.id}")
                
            except Exception as send_error:
                logging.error(f"Failed to send resume message to user {user_id}: {send_error}")
                raise
            
            # Create a dummy callback query that will use our NEW message
            class DummyMessage:
                def __init__(self, real_msg):
                    if not real_msg:
                        raise ValueError("DummyMessage requires a valid message object")
                    self.id = real_msg.id
                    self.real_message = real_msg
                    
                async def answer(self, text, show_alert=False):
                    pass
                    
                async def edit(self, text, reply_markup=None):
                    # Edit our NEW message (not any old one)
                    try:
                        if not self.real_message:
                            logging.error("Cannot edit: real_message is None")
                            return
                        await self.real_message.edit_text(text, reply_markup=reply_markup)
                    except Exception as e:
                        logging.error(f"Error editing new resume message: {e}")
                    
                async def delete(self):
                    try:
                        if self.real_message:
                            await self.real_message.delete()
                    except:
                        pass
            
            class DummyCallbackQuery:
                def __init__(self, user_id, forward_id, real_msg):
                    self.from_user = type('obj', (object,), {'id': user_id})()
                    self.data = f"start_public_{forward_id}"
                    self.message = DummyMessage(real_msg)
                    
                async def answer(self, text, show_alert=False):
                    pass
            
            # Pass the REAL new message to the dummy callback
            dummy_callback = DummyCallbackQuery(user_id, forward_id, new_progress_msg)
            
            # Call the forwarding function with our NEW progress message
            # Pass the actual progress message so errors can be displayed
            await pub_(self, dummy_callback, resume_msg=new_progress_msg)
            
        except Exception as e:
            logging.error(f"Error resuming forwarding for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Don't clear tracking data - keep it for historical reference
            try:
                await self.send_message(
                    user_id,
                    f"❌ <b>Failed to resume process:</b> {str(e)}\n\n"
                    f"Please start a new forwarding process."
                )
            except:
                pass
    
    def _create_progress_bar(self, percentage):
        """Create a visual progress bar"""
        filled = int(percentage / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}] {percentage:.1f}%"

    async def stop(self, *args):
        msg = f"@{self.username} stopped. Bye."
        await super().stop()
        logging.info(msg)

if __name__ == "__main__":
    bot = Bot()
    bot.run()
