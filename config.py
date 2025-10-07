from os import environ 
import sys

class Config:
    # Required environment variables - no defaults for security
    API_ID = environ.get("API_ID") or "28776072"
    API_HASH = environ.get("API_HASH") or "b3a786dce1f4e7d56674b7cadfde3c9d"
    BOT_TOKEN = environ.get("BOT_TOKEN") or "7789900726:AAHRsAcO0VHV2d8HT7tnv4Yl2sbn84CjRDU" 
    BOT_SESSION = environ.get("BOT_SESSION") or "forward-bot" 
    DATABASE_URI = environ.get("DATABASE") or "mongodb+srv://ftm:ftm@cluster0.9a4gw2t.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    DATABASE_NAME = environ.get("DATABASE_NAME") or "forward-bot"
    OWNER_ID_STR = environ.get("OWNER_ID") or "7744665378"
    
    # Validate required environment variables
    @classmethod
    def validate_env(cls):
        """Validate that all required environment variables are set"""
        required_vars = []
        missing_vars = []
        
        for var in required_vars:
            if not environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please set these environment variables before running the bot.")
            sys.exit(1)
    
    # Initialize configuration after validation
    OWNER_ID = [int(id) for id in OWNER_ID_STR.split()] if OWNER_ID_STR else []
    ADMIN_ID = [int(id) for id in (environ.get("ADMIN_ID") or "7810783444").split() if id.strip()]
    LOG_CHANNEL_ID = int(environ.get("LOG_CHANNEL_ID") or "-1003003594014")
    SUPPORT_GROUP = "https://t.me/ftmbotzx_support"
    UPDATE_CHANNEL = "https://t.me/ftmbotzx"
    ADMIN_CONTACT_URL = environ.get("ADMIN_CONTACT_URL", "https://t.me/ftmdeveloperzbot")
    # Multi Force Subscribe - space separated channel IDs
    MULTI_FSUB_STR = environ.get("MULTI_FSUB", "-1002282331890 -1002087228619 -1003040147375")
    MULTI_FSUB = MULTI_FSUB_STR.split() if MULTI_FSUB_STR else []
    MULTI_FSUB = [int(x) for x in MULTI_FSUB if x.strip().lstrip('-').isdigit()]
    
    # UPI ID for payments
    UPI_ID = environ.get("UPI_ID", "gehlotv697@okaxis")
    CHANNEL_ID=MULTI_FSUB_STR
    MESSAGE_DELAY = float(environ.get("MESSAGE_DELAY", "1.3"))
    # Three-tier pricing structure
    PLAN_PRICING = {
        'plus': {
            '15_days': 109,
            '30_days': 199
        },
        'pro': {
            '15_days': 159,
            '30_days': 299
        }
    }
    
    # Plan features
    PLAN_FEATURES = {
        'free': {
            'forwarding_limit': 1,  # per month
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': False
        },
        'plus': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': True
        },
        'pro': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': True,  # FTM Delta mode
            'priority_support': True,
            'unlimited_forwarding': True
        }
    }
    
    @staticmethod
    def is_sudo_user(user_id):
        """Check if user is sudo (owner or admin)"""
        return int(user_id) in Config.OWNER_ID or int(user_id) in Config.ADMIN_ID

class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    CURRENT_PROCESSES = {}  # Track ongoing processes per user
    
