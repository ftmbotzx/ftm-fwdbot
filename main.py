import os
import asyncio
import threading
from flask import Flask
from bot import Bot
from ptb_all_commands import setup_ptb_application
from ptb_commands import setup_ptb_application as setup_ptb_commands

# Create Flask app for Render/uptime monitoring
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "✅ Fᴛᴍ Dᴇᴠᴇʟᴏᴘᴇʀᴢ bot is live with PTB command handlers."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# Run Flask in background
threading.Thread(target=run_flask).start()

async def run_pyrogram_bot():
    """Run the Pyrogram bot for forwarding only (no command plugins)"""
    print("Starting Pyrogram bot for forwarding functionality...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            app = Bot()
            await app.start()
            print("Pyrogram bot started successfully (forwarding only)!")
            await asyncio.Event().wait()
            break
        except Exception as e:
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                print(f"Database locked, retrying in {(attempt + 1) * 2} seconds...")
                await asyncio.sleep((attempt + 1) * 2)
                continue
            else:
                print(f"Failed to start Pyrogram bot: {e}")
                raise

async def run_ptb_bot():
    """Run PTB for all command handling"""
    print("Starting Python-Telegram-Bot for ALL command handling...")
    try:
        # Setup main application with start, help, myplan, speedtest, system
        application = setup_ptb_application()
        
        # Setup commands application with info, users, reset, resetall, broadcast
        commands_app = setup_ptb_commands()
        
        # Merge handlers from commands_app into main application
        for handler in commands_app.handlers[0]:
            application.add_handler(handler)
        
        # Setup unequify handler
        from ptb_unequify import setup_unequify_handler
        setup_unequify_handler(application)
        
        await application.initialize()
        await application.start()
        
        await application.updater.start_polling(
            allowed_updates=["message", "callback_query"], 
            drop_pending_updates=True
        )
        
        print("PTB bot started successfully - handling all commands!")
        
        try:
            await asyncio.Event().wait()
        finally:
            print("Stopping PTB bot...")
            try:
                await application.updater.stop()
            except:
                pass
            try:
                await application.stop()
            except:
                pass
            try:
                await application.shutdown()
            except:
                pass
            
    except Exception as e:
        print(f"Error in PTB bot: {e}")
        return False

async def main():
    """Run both Pyrogram (forwarding) and PTB (commands) bots concurrently"""
    try:
        print("Starting Pyrogram (forwarding) and PTB (commands) bots...")
        
        pyrogram_task = asyncio.create_task(run_pyrogram_bot())
        
        await asyncio.sleep(2)
        
        try:
            ptb_task = asyncio.create_task(run_ptb_bot())
            await asyncio.gather(pyrogram_task, ptb_task)
        except Exception as ptb_error:
            print(f"PTB failed to start: {ptb_error}")
            print("Continuing with Pyrogram only...")
            await pyrogram_task
        
    except Exception as e:
        print(f"Error running bots: {e}")
        print("Falling back to Pyrogram only...")
        await run_pyrogram_bot()

# Safe async run
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"[!] RuntimeError: {e}")
        print("Trying alternative startup method...")
        
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Create tasks for both bots
        try:
            pyrogram_task = loop.create_task(run_pyrogram_bot())
            ptb_task = loop.create_task(run_ptb_bot())
            
            print("Starting both bots with alternative method...")
            loop.run_forever()
            
        except Exception as fallback_error:
            print(f"Fallback failed: {fallback_error}")
            print("Starting only Pyrogram bot...")
            loop.create_task(run_pyrogram_bot())
            loop.run_forever()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
