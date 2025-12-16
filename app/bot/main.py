import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import config
from app.bot.handlers import common, registration, onboarding, interview, expert, structured_input

async def main():
    logging.basicConfig(level=logging.INFO)
    
    if not config.BOT_TOKEN:
        logging.error("BOT_TOKEN is not set")
        return

    # Check LLM client initialization
    logging.info("Checking LLM model initialization...")
    from app.core.llm_client import llm_client
    if llm_client.model is None:
        logging.warning(f"⚠️ LLM model not initialized: {llm_client._init_error}")
        logging.warning("Bot will start but interview features may not work properly.")
    else:
        provider_info = f"{llm_client.provider.upper()}" if llm_client.provider else "Unknown"
        logging.info(f"✅ LLM model ready: {llm_client.model_name} ({provider_info})")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Include routers
    dp.include_router(common.router)
    dp.include_router(registration.router)
    dp.include_router(structured_input.router)  # Collection flow handler
    dp.include_router(onboarding.router)
    dp.include_router(interview.router)
    dp.include_router(expert.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
