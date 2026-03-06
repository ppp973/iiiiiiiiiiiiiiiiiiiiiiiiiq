import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID
from handlers.iq_handler import handle_iq_command

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create downloads directory
os.makedirs("downloads", exist_ok=True)

# Initialize bot
app = Client(
    "study_iq_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command(["start"]))
async def start_command(client, message):
    await message.reply_text(
        "**🎓 Study IQ Extractor Bot**\n\n"
        "**Available Commands:**\n"
        "├ /start - Show this message\n"
        "├ /help - Detailed help guide\n"
        "├ /iq - Extract Study IQ courses\n"
        "└ /about - About this bot\n\n"
        "**How to use:**\n"
        "1. Send /iq command\n"
        "2. Send your phone number or saved token\n"
        "3. Select batch ID to download\n\n"
        "**Made with ❤️**"
    )

@app.on_message(filters.command(["help"]))
async def help_command(client, message):
    await message.reply_text(
        "**📚 Detailed Help Guide**\n\n"
        "**🔑 First Time Users:**\n"
        "1. Send /iq command\n"
        "2. Send your phone number (without country code)\n"
        "3. Enter OTP received on phone\n"
        "4. Save the token for future use\n\n"
        "**🔄 Returning Users:**\n"
        "1. Send /iq command\n"
        "2. Send your saved token directly\n"
        "3. Select batch to download\n\n"
        "**📥 Download Multiple Batches:**\n"
        "Send batch IDs separated by &\n"
        "Example: `123&456&789`"
    )

@app.on_message(filters.command(["about"]))
async def about_command(client, message):
    await message.reply_text(
        "**🤖 About This Bot**\n\n"
        "**Name:** Study IQ Extractor\n"
        "**Version:** 2.0\n"
        "**Framework:** Pyrogram\n\n"
        "**Features:**\n"
        "✓ Extract all course videos\n"
        "✓ Download PDF notes\n"
        "✓ Multiple batch support\n"
        "✓ Token save feature\n"
        "✓ Detailed statistics"
    )

@app.on_message(filters.command(["iq"]))
async def iq_command(client, message):
    await handle_iq_command(app, message)

if __name__ == "__main__":
    logger.info("🚀 Study IQ Bot Started!")
    app.run()
