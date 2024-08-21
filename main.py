import asyncio
import logging
from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN
from handlers import setup_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

async def main() -> None:
    try:
        logger.info("Starting bot...")
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        logger.info("Application built")

        setup_handlers(application)
        logger.info("Handlers set up")

        await application.initialize()
        logger.info("Application initialized")
        
        await application.start()
        logger.info("Application started")
        
        logger.info("Starting polling...")
        await application.updater.start_polling()
        logger.info("Polling started")
        
        # Buat event untuk menjaga bot tetap berjalan
        stop_signal = asyncio.Event()
        
        # Tunggu sampai stop_signal diset (yang tidak akan terjadi dalam kode ini)
        await stop_signal.wait()
        
    except Exception as e:
        logger.exception(f"Error running bot: {e}")
    finally:
        # Hanya akan dieksekusi jika ada exception atau stop_signal diset
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")