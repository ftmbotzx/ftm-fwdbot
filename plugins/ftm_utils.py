import re
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def create_source_link(chat_id, message_id):
    """Create a source message link"""
    if str(chat_id).startswith('-100'):
        # Channel/Supergroup
        channel_id = str(chat_id)[4:]  # Remove -100 prefix
        return f"https://t.me/c/{channel_id}/{message_id}"
    else:
        # Private chat or bot
        return f"https://t.me/{chat_id}/{message_id}"

def create_target_link(chat_id, message_id):
    """Create a target message link"""
    if str(chat_id).startswith('-100'):
        # Channel/Supergroup
        channel_id = str(chat_id)[4:]  # Remove -100 prefix
        return f"https://t.me/c/{channel_id}/{message_id}"
    else:
        # Private chat or bot
        return f"https://t.me/{chat_id}/{message_id}"

def add_ftm_caption(original_caption, source_link, target_link=None):
    """Add FTM Delta mode information to caption with formatted header"""
    # FTM Delta formatted header
    ftm_header = f"🔥 <b>FTM Delta Mode</b> 🔥\n📤 <b>Source:</b> <a href='{source_link}'>Original Message</a>"
    
    if target_link:
        ftm_header += f"\n📥 <b>Target:</b> <a href='{target_link}'>Forwarded Message</a>"
    
    ftm_header += "\n\n"
    
    if original_caption:
        # Add header before original caption
        return ftm_header + original_caption
    else:
        return ftm_header.strip()

def create_ftm_button(source_link):
    """Create FTM mode button with source link - disabled as per user request"""
    return None

def combine_buttons(ftm_button, existing_buttons=None):
    """Combine FTM button with existing buttons - disabled"""
    return existing_buttons