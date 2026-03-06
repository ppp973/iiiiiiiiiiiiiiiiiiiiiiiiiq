import os

# Your Telegram API credentials (from my.telegram.org)
API_ID = 21503125
API_HASH = "bab9855c442e9e4e87f413cb5b9dc3f9"
BOT_TOKEN = "8768725493:AAFDhnWucAWD9Tl9djbRtOr6v5bUUOFmCQY"

# Channel ID for logs - YOUR ACTUAL CHANNEL ID
# Channel: Your private channel
CHANNEL_ID = -1003724248856  # ✅ Your correct channel ID

# Don't modify below - this validates that all values are set
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Please check API_ID, API_HASH, and BOT_TOKEN in config.py")

if CHANNEL_ID == -1003724248856:
    print("✅ Channel ID configured correctly!")
