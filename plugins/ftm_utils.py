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
    """Add FTM Delta mode information to caption with formatted footer"""
    # FTM Delta formatted footer (moved to bottom for classy look)
    ftm_footer = f"\n\n🔥 <b>FTM Delta Mode</b> 🔥\n📤 <b>Source:</b> <a href='{source_link}'>Original Message</a>"
    
    if target_link:
        ftm_footer += f"\n📥 <b>Target:</b> <a href='{target_link}'>Forwarded Message</a>"
    
    if original_caption:
        # Add footer after original caption
        return original_caption + ftm_footer
    else:
        return ftm_footer.strip()

def create_ftm_button(source_link):
    """Create FTM mode button with source link - disabled as per user request"""
    return None

def combine_buttons(ftm_button, existing_buttons=None):
    """Combine FTM button with existing buttons - disabled"""
    return existing_buttons

def apply_watermark(caption, prefix=None, suffix=None):
    """Apply prefix and suffix watermarks to caption with proper formatting"""
    # Start with original caption or empty string
    result = caption if caption else ""
    
    # Add prefix if provided (with newline after it)
    if prefix:
        result = prefix + "\n" + result
    
    # Add suffix if provided (at the bottom)
    if suffix:
        # Add newline before suffix if there's content
        if result:
            result = result + "\n" + suffix
        else:
            result = suffix
    
    # Return None if result is empty, otherwise return the watermarked text
    return result if result.strip() else None

def apply_watermark_before_ftm(caption, prefix=None, suffix=None):
    """Apply watermarks with suffix BEFORE FTM footer (for FTM Delta mode)"""
    # Start with original caption or empty string
    result = caption if caption else ""
    
    # Add prefix if provided (with newline after it)
    if prefix:
        result = prefix + "\n" + result
    
    # Add suffix if provided (will be added before FTM footer)
    if suffix:
        # Add newline before suffix if there's content
        if result:
            result = result + "\n" + suffix
        else:
            result = suffix
    
    # Return result (FTM footer will be added after this)
    return result if result else ""