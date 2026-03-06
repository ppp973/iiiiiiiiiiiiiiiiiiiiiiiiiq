import os

# Your Telegram API credentials (from my.telegram.org)
API_ID = 21503125
API_HASH = "bab9855c442e9e4e87f413cb5b9dc3f9"
BOT_TOKEN = "8768725493:AAFDhnWucAWD9Tl9djbRtOr6v5bUUOFmCQY"

# Channel ID for logs - YOU MUST CREATE A CHANNEL AND GET ITS ID
# How to get:
# 1. Create a private channel on Telegram
# 2. Add your bot (@sdfvghhghhbnm_bot) as administrator
# 3. Send any message in the channel
# 4. Forward that message to @getidsbot
# 5. Copy the ID (it will be negative, like -100123456789)
# 6. Replace the value below with your channel ID
CHANNEL_ID = -1002393162019  # <-- CHANGE THIS TO YOUR ACTUAL CHANNEL ID

# Don't modify below - this validates that all values are set
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Please check API_ID, API_HASH, and BOT_TOKEN in config.py")

if CHANNEL_ID == -1002393162019:
    print("⚠️ WARNING: You haven't set your CHANNEL_ID yet!")
    print("Please create a channel and add your bot as admin, then get the ID from @getidsbot")
    print("The bot will still work but logs won't be saved to a channel.\n")
