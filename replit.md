# Overview

This is a Telegram Auto-Forward Bot built with Python, Pyrogram, and Python-Telegram-Bot. The bot enables users to automatically forward messages from one Telegram channel/chat to another with advanced filtering, customization options, and premium subscription management. It supports multiple bots per user, duplicate detection, FTM (Forward Tracking Mode), and a comprehensive referral system.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework Architecture
- **Dual-Bot System**: Uses both Pyrogram (for message forwarding) and Python-Telegram-Bot/PTB (for command handling)
  - Pyrogram handles the core forwarding engine and message processing
  - PTB handles all command interactions to resolve command unresponsiveness issues
  - Both frameworks run concurrently via asyncio
- **Plugin-Based Modular Design**: Separate plugin files for different functionalities (commands, settings, premium, referral, etc.)
- **Asynchronous Processing**: Built on asyncio with 50 workers for concurrent request handling
- **Process Management**: Flask web server integrated for deployment monitoring and health checks on port 5000

## Authentication & Access Control
- **Multi-Bot Support**: Users can register multiple Telegram bots or userbots to their account
- **Session Management**: Supports both bot tokens (from @BotFather) and user session strings (from userbot authentication)
- **Owner/Admin System**: Configurable owner IDs and admin IDs with sudo privileges
- **Phone Authentication**: Direct phone number authentication for userbot setup

## Message Forwarding Engine
- **Core Forwarding Logic**: Custom async forwarding with source and target chat validation
- **FTM (Forward Tracking Mode)**: Special mode that adds source link tracking and attribution to forwarded messages
- **Message Type Filtering**: Comprehensive filtering by media type (text, photo, video, document, audio, voice, animation, sticker, poll)
- **Duplicate Detection**: MongoDB-based tracking to prevent forwarding duplicate messages
- **File Filtering**: Size limits and file extension-based filtering
- **Skip/Limit Controls**: Configurable message offset and limit for batch forwarding
- **Caption & Button Customization**: Users can add custom captions and inline buttons to forwarded messages
- **Protected Content**: Option to forward with content protection enabled
- **Keyword Filtering**: Filter messages based on specific keywords

## Premium & Subscription System
- **Three-Tier Plans**:
  - Free Trial: 3-day trial (once per year per user)
  - Plus Plan: 15-day (₹199) or 30-day (₹299) subscriptions
  - Pro Plan: 15-day or 30-day subscriptions with FTM mode access
- **Payment Verification**: UPI-based payment system with screenshot verification via `/verify` command
- **Usage Tracking**: Daily and monthly usage limits enforced for non-premium users
- **Trial Management**: One free trial per year tracked via database
- **Expiry Notifications**: Automated notifications for subscription expirations

## Referral System
- **Referral Code Generation**: Unique referral codes for each user
- **Auto-Rewards System**:
  - 15 completed referrals → Plus Plan 30 days free
  - 30 completed referrals → Pro Plan 15 days free
- **Referred User Benefits**: 1-day Plus plan for users who join via referral link
- **Referral Tracking**: Tracks pending and completed referrals
- **Notification System**: Real-time notifications for referrer and referred users
- **Leaderboard**: Top referrers ranking system

## Force Subscribe System
- **Multi-Channel Force Subscribe**: Requires users to join multiple channels before using the bot
- **Channel Membership Validation**: Checks user membership status across configured channels
- **Dynamic Join Buttons**: Auto-generated buttons for channels user hasn't joined
- **Bypass for Premium/Sudo Users**: Premium and admin users bypass force subscribe

## Data Storage (MongoDB)
- **Database Engine**: MongoDB with Motor async driver for non-blocking operations
- **Collections Structure**:
  - `users`: User profiles, join dates, ban status, referral info, and process tracking data
    - Includes `process_tracking` field with real-time forwarding progress (message IDs, links, counts)
  - `bots`: Bot configurations, tokens, session strings
  - `channels`: Channel/chat configurations for forwarding
  - `notify`: Notification settings
  - `premium_users`: Premium subscription details and expiry dates
  - `payment_verifications`: Payment screenshot verification queue
  - `usage_tracking`: Daily/monthly usage limits
  - `trial_usage`: Free trial tracking
  - `referrals`: Referral system data
  - `contact_requests`: User contact requests (deprecated)
  - `chat_requests`: Admin chat sessions (deprecated)
  - `alpha_configs`: FTM Alpha mode configurations (deprecated)
  - `queue_col`: Crash recovery queue for interrupted forwards

## Configuration Management
- **Environment Variables**: All sensitive credentials via environment variables (API_ID, API_HASH, BOT_TOKEN, DATABASE_URI, OWNER_ID, etc.)
- **Per-User Settings**: Individual user configurations stored in database for filters, captions, buttons, forwarding preferences
- **Dynamic Updates**: Runtime configuration changes via inline keyboard interfaces
- **Validation**: Environment variable validation on startup

## User Interface
- **Command System**:
  - `/start` - Main menu and welcome message
  - `/trial` - Get 3-day free premium trial
  - `/forward` or `/fwd` - Start forwarding process
  - `/settings` - Configure bot settings
  - `/myplan` - Check subscription status
  - `/verify` - Verify premium payment
  - `/referral` - Referral system dashboard
  - `/unequify` - Remove duplicate messages
  - `/reset` - Reset user configurations
  - Admin commands: `/users`, `/broadcast`, `/speedtest`, `/system`, `/resetall`
- **Inline Keyboards**: Rich interactive menus with callback query handling
- **Progress Tracking**: Real-time status updates during forwarding operations with ASCII art progress display
  - Visual progress bar using ◉ symbols (0-11 circles for 0-100%)
  - Displays: total messages, fetched, forwarded, duplicates, deleted/filtered, skipped, status, progress %, speed (msgs/min), ETA (estimated time)
  - Speed shows messages forwarded per minute
  - ETA shows estimated time remaining to completion
  - Updates every 10 messages for optimal performance
- **Timezone Display**: All timestamps shown in IST (Indian Standard Time)

## Administrative Features
- **Broadcast System**: Mass messaging to all users with delivery tracking
- **User Management**: Ban/unban users, view total user count
- **System Monitoring**: CPU, memory, disk usage tracking via `/system` command
- **Speed Testing**: Network speed tests via `/speedtest` command
- **Reset Functionality**: Admin can reset individual or all user configurations

## Notification System
- **Log Channel Integration**: All important events logged to configured channel
- **User Action Tracking**: Notifications for user actions (start, forward, trial, premium purchase)
- **Referral Notifications**: Automated notifications for referral milestones
- **Error Handling**: Graceful handling of FloodWait, ChatWriteForbidden, UserIsBlocked errors

## Crash Recovery & Process Tracking
- **Queue System**: Interrupted forwarding tasks stored in database queue
- **State Persistence**: Forwarding state (fetched, filtered, duplicates) tracked and recoverable
- **Lock Mechanism**: Prevents multiple concurrent forwarding tasks per user
- **Process Tracking**: Real-time tracking of each user's ongoing forwarding process with detailed progress data
  - Stores: last forwarded message ID, last fetched message ID, message links, target channel link, total/processed counts
  - Updates every 10 messages during forwarding for minimal database overhead
  - Automatic cleanup on process completion, error, or cancellation
- **Restart Recovery**: After bot restart, users with interrupted processes receive:
  - Progress notification with visual progress bar showing completion percentage
  - Links to last processed message and target channel (when available)
  - Detailed status information (source/target chats, processed/total messages)
- **Log Channel Notifications**: All process recovery events logged to admin log channel with:
  - User information and process details
  - Progress statistics and links
  - Summary of all users notified after restart

# External Dependencies

## Third-Party Services
- **Telegram Bot API**: Core messaging platform via Pyrogram and Python-Telegram-Bot libraries
- **Telegram MTProto**: Direct protocol access via Pyrogram for userbot functionality
- **MongoDB Atlas**: Cloud database for persistent data storage (connection via `DATABASE_URI`)
- **Flask**: Lightweight web server for uptime monitoring on Render/Railway deployments

## API & Authentication
- **Telegram API Credentials**: 
  - `API_ID` and `API_HASH` from my.telegram.org or @UseTGSBot
  - `BOT_TOKEN` from @BotFather
- **UPI Payment Gateway**: Manual UPI payment verification (`UPI_ID` configuration)

## Python Libraries
- **pyrofork**: Telegram MTProto framework (Pyrogram fork)
- **python-telegram-bot**: PTB library for command handling
- **motor**: Async MongoDB driver
- **pymongo**: MongoDB Python driver
- **TgCrypto/cryptg**: Encryption for Telegram protocols
- **Dnspython**: DNS toolkit for MongoDB connection
- **telethon**: Alternative Telegram client library
- **opencv-python-headless**: Image processing utilities
- **psutil**: System and process utilities for monitoring
- **speedtest-cli**: Network speed testing
- **python-decouple**: Environment variable management

## Deployment Platforms
- **Render/Railway/Heroku**: Container-based deployment (port 5000 for health checks)
- **Docker**: Containerized deployment support via `app.json` configuration

## Database Schema Dependencies
- MongoDB collections expect specific field structures (user_id, plan_type, expiry_date, referral_code, etc.)
- Timezone handling assumes UTC storage with IST display conversion
- Premium plan pricing structure hardcoded in `Config.PLAN_PRICING`