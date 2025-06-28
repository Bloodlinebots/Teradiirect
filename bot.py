import os
import logging
import asyncio
import aiohttp

from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ------------ Logging Setup ------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------ Config from .env ------------
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

LINK_FILE = "links.txt"
DONE_FILE = "done.txt"

# ------------ Direct Link via Your API ------------
async def get_direct_link(terabox_url: str) -> str:
    try:
        if "/s/" not in terabox_url:
            logger.warning(f"Invalid Terabox link: {terabox_url}")
            return None

        file_id = terabox_url.split("/s/")[-1].split("?")[0]
        api_url = f"https://icy-brook12.arjunavai273.workers.dev/?id={file_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    logger.warning(f"API failed for {file_id}: {resp.status}")
                    return None
    except Exception as e:
        logger.error(f"API error for {terabox_url}: {e}")
        return None

# ------------ Background Processing Task ------------
async def process_links(bot: Bot):
    while True:
        if not os.path.exists(LINK_FILE):
            await asyncio.sleep(10)
            continue

        with open(LINK_FILE, "r") as f:
            links = [line.strip() for line in f if line.strip()]

        done_links = set()
        if os.path.exists(DONE_FILE):
            with open(DONE_FILE, "r") as df:
                done_links = set(line.strip() for line in df if line.strip())

        for link in links:
            if link in done_links:
                continue

            logger.info(f"Processing: {link}")
            direct_link = await get_direct_link(link)
            if not direct_link:
                logger.warning(f"Skipping invalid link: {link}")
                continue

            try:
                await bot.send_video(chat_id=ADMIN_ID, video=direct_link, caption="📥 From Terabox")
                with open(DONE_FILE, "a") as df:
                    df.write(link + "\n")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Send failed: {e}")
                await asyncio.sleep(5)

        await asyncio.sleep(60)

# ------------ /upload Command Handler ------------
async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    document = update.message.document
    if not document or not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please upload a valid `.txt` file.")
        return

    file = await document.get_file()
    await file.download_to_drive(LINK_FILE)
    await update.message.reply_text("✅ File uploaded. Processing started...")

# ------------ Start Bot ------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("upload", upload_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_handler))

    asyncio.create_task(process_links(app.bot))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
