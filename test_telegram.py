import asyncio

from trading_bot_backend.app.services.notifications import send_telegram_message


async def main():
    print("Testing Telegram notification...")
    test_msg = "<b>Test Notification</b>\n\nLe bot est pret a envoyer des alertes sur Telegram."
    await send_telegram_message(test_msg)
    print("Request sent. Verify the configured Telegram chat.")


if __name__ == "__main__":
    asyncio.run(main())
