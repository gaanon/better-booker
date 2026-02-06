import asyncio
import os
import httpx
from dotenv import load_dotenv
from pickleball_checker import run_check, send_telegram_message

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=35)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching updates: {e}")
            return None

async def main():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing in .env. Please check TELEGRAM_TOKEN and TELEGRAM_CHAT_ID.")
        return

    print("Bot is listening for commands...")
    offset = None
    
    while True:
        updates = await get_updates(offset)
        if updates and updates.get("ok"):
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "").lower().strip()
                chat_id = str(message.get("chat", {}).get("id"))

                # Only respond to the authorized user
                if chat_id != TELEGRAM_CHAT_ID:
                    print(f"Ignored message from unauthorized chat: {chat_id}")
                    continue

                if text in ["/check", "check", "pickleball"]:
                    print(f"Received trigger from Telegram: {text}")
                    await send_telegram_message("🔍 Checking for pickleball slots, please wait...")
                    
                    try:
                        # Use default: 7-day range
                        report = await run_check(use_range=True, send_to_telegram=False)
                        await send_telegram_message(report)
                    except Exception as e:
                        print(f"Error during check: {e}")
                        await send_telegram_message(f"❌ An error occurred: {e}")
                
                elif text in ["/weekends", "weekends"]:
                    print(f"Received trigger from Telegram: {text}")
                    await send_telegram_message("🔍 Checking for weekend pickleball slots, please wait...")
                    
                    try:
                        # Use 7-day range, but only weekends
                        report = await run_check(use_range=True, weekends_only=True, send_to_telegram=False)
                        await send_telegram_message(report)
                    except Exception as e:
                        print(f"Error during check: {e}")
                        await send_telegram_message(f"❌ An error occurred: {e}")
                
                elif text in ["/help", "/start", "help"]:
                    await send_telegram_message("🏸 Pickleball Bot Command List:\n- Send /check to see available slots for the next 7 days.\n- Send /weekends to only see Saturday/Sunday slots.\n- Send /help to see this message.")

        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
