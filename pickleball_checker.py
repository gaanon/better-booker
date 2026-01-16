import asyncio
import os
import sys
import argparse
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

USER = os.getenv("BETTER_USER")
PASS = os.getenv("BETTER_PASS")
LOCATION = os.getenv("BETTER_LOCATION", "barnet-copthall-leisure-centre")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = f"https://bookings.better.org.uk/location/{LOCATION}"

async def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                print(f"Telegram API Error: {response.status_code} - {response.text}")
            response.raise_for_status()
            print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")

async def login(page):
    if not USER or not PASS:
        print("Credentials not found. Skipping login (slots are still viewable).")
        return False
    
    print(f"Logging in as {USER}...")
    try:
        # Navigate to a page that has the login button
        await page.goto(f"{BASE_URL}/sports-hall-activities")
        
        # Handle Cookie Banner (OneTrust)
        try:
            accept_btn = await page.wait_for_selector(
                "#accept-recommended-btn-handler, #onetrust-accept-btn-handler", 
                timeout=5000
            )
            if accept_btn:
                print("Accepting cookies...")
                await accept_btn.click()
                await page.wait_for_selector("#onetrust-consent-sdk", state="hidden", timeout=5000)
        except:
            pass

        # Click the header login button
        login_btn = await page.wait_for_selector("button[data-testid='login']", timeout=10000)
        await login_btn.click()
        
        # Wait for the modal fields
        print("Waiting for login modal...")
        await page.wait_for_selector("#username", timeout=10000)
        await page.fill("#username", USER)
        await page.fill("#password", PASS)
        
        # Click the modal submit button
        print("Submitting login form...")
        login_submit = await page.wait_for_selector("button[data-testid='log-in']", timeout=5000)
        await login_submit.dispatch_event("click")
        
        # Wait for success signals
        try:
            await page.wait_for_selector("text='Log out', text='My account', [class*='ErrorMessage'], [class*='Alert']", timeout=20000)
        except:
            pass

        if await page.is_visible("text='Log out'") or await page.is_visible("text='My account'"):
            print("Login successful.")
            return True
        else:
            error_elems = await page.query_selector_all("[class*='SharedLoginComponent__Error'], .error, [role='alert']")
            for err in error_elems:
                text = await err.inner_text()
                if text.strip():
                    print(f"Login error from website: {text.strip()}")
            raise Exception("Login failed to reach authorized state.")

    except Exception as e:
        print(f"Login failed: {e}")
        await page.screenshot(path="login_error.png")
        print("Reference login_error.png for details.")
        return False

async def get_slots(page, activity_type, date_str):
    url = f"{BASE_URL}/{activity_type}/{date_str}/by-time"
    # print(f"Checking {activity_type} for {date_str}...") # Reduced noise
    
    await page.goto(url)
    
    no_results = await page.query_selector("text='No results were found at this centre'")
    if no_results:
        return []

    try:
        await page.wait_for_selector("[class*='ClassCardComponent__Wrap']", timeout=10000)
    except:
        return []

    slots = []
    wrappers = await page.query_selector_all("[class*='ClassCardComponent__Wrap']")
    
    for wrapper in wrappers:
        time_elem = await wrapper.query_selector("h3, div:first-child")
        time_text = await time_elem.inner_text() if time_elem else "Unknown Time"
        
        space_elem = await wrapper.query_selector("[class*='ContextualComponent__BookWrap']")
        if space_elem:
            space_text = await space_elem.inner_text()
            if "available" in space_text.lower():
                slots.append({
                    "time": time_text.split('\n')[0].strip(),
                    "spaces": space_text.replace("\nBook", "").strip(),
                    "type": activity_type
                })
                
    return slots

def is_filtered(time_str, filter_time, is_weekend):
    if is_weekend:
        return False
    if not filter_time:
        return False
    
    try:
        slot_time = datetime.strptime(time_str.split(' - ')[0], "%H:%M").time()
        filter_limit = datetime.strptime(filter_time, "%H:%M").time()
        return slot_time < filter_limit
    except:
        return False

async def main():
    parser = argparse.ArgumentParser(description="Pickleball Slot Checker")
    parser.add_argument("--date", help="Specific date to check (YYYY-MM-DD)")
    parser.add_argument("--range", action="store_true", help="Check 6-day range starting today")
    parser.add_argument("--after", default="17:30", help="Filter slots after this time (weekdays only, HH:MM)")
    parser.add_argument("--all", action="store_true", help="Show all slots, ignore time filter")
    parser.add_argument("--telegram", action="store_true", help="Send results to Telegram")
    args = parser.parse_args()

    # Determine dates to check
    dates_to_check = []
    if args.range:
        today = datetime.now()
        dates_to_check = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    elif args.date:
        dates_to_check = [args.date]
    else:
        dates_to_check = [datetime.now().strftime("%Y-%m-%d")]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Login is not needed for checking slots, preserved for future booking automation
        # await login(page)

        telegram_report = ""
        for date_str in dates_to_check:
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            is_weekend = dt_obj.weekday() >= 5
            day_name = dt_obj.strftime("%A")
            
            print(f"\n--- {day_name} {date_str} ---")
            
            slots_60 = await get_slots(page, "pickleball-60mins", date_str)
            slots_40 = await get_slots(page, "pickleball-40mins", date_str)
            all_slots = slots_60 + slots_40

            # Filter slots
            visible_slots = []
            filtered_count = 0
            
            for s in all_slots:
                if args.all or not is_filtered(s['time'], args.after, is_weekend):
                    visible_slots.append(s)
                else:
                    filtered_count += 1

            if not all_slots:
                print("No free slots found.")
            elif not visible_slots:
                print(f"No slots found after {args.after} ({filtered_count} earlier slots hidden).")
            else:
                for slot in visible_slots:
                    print(f"[{slot['type'].replace('pickleball-', '')}] {slot['time']} - {slot['spaces']}")
                if filtered_count > 0:
                    print(f"({filtered_count} earlier slots hidden on this weekday. Use --all to see them.)")
            
            if args.telegram and visible_slots:
                telegram_report += f"\n<b>{day_name} {date_str}</b>\n"
                for slot in visible_slots:
                    telegram_report += f"• [{slot['type'].replace('pickleball-', '')}] {slot['time']} - {slot['spaces']}\n"

        if args.telegram:
            if telegram_report:
                await send_telegram_message(f"🏸 <b>Pickleball Slots Found:</b>\n{telegram_report}")
            else:
                print("No slots to send to Telegram.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
