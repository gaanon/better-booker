# Better.org.uk Pickleball Slot Checker 🏸

A Python-based automation script that scrapes the [Better.org.uk](https://www.better.org.uk/) booking system to find available Pickleball slots (40min and 60min) across multiple dates and notifies you via Telegram.

## Features

- **7-Day Automatic Range**: Checks from today through the next 6 days in one command.
- **Smart Filtering**: Optionally filter weekday slots by time (e.g., only after 5:30 PM).
- **Telegram Integration**: Sends found slots directly to your phone with bold, clean formatting.
- **Robust Scraping**: Handles cookie banners and dynamic loading using Playwright.
- **Headless Mode**: Runs in the background without opening a browser window.

## Prerequisites

- Python 3.8+
- [Playwright](https://playwright.dev/python/docs/intro)

## Installation

1. **Clone the repository** (or navigate to the folder).
2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # Or install manually
   pip install playwright python-dotenv httpx
   playwright install chromium
   ```

## Configuration

Create a `.env` file in the root directory:

```env
# Location (from url: bookings.better.org.uk/location/xyz)
BETTER_LOCATION=barnet-copthall-leisure-centre

# Credentials (Only needed for future booking automation)
BETTER_USER=your_customer_id
BETTER_PASS=your_password

# Telegram Notifications (Optional)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

Run the script using the following flags:

### 1. Check current 7-day range
```bash
python3 pickleball_checker.py --range
```

### 2. Check a specific date
```bash
python3 pickleball_checker.py --date 2026-01-20
```

### 3. Filter weekday slots (e.g., after 6:00 PM)
```bash
python3 pickleball_checker.py --range --after 18:00
```

### 4. Send to Telegram
```bash
python3 pickleball_checker.py --range --telegram
```

### 5. Run the Telegram Bot (On-Demand Trigger)
This script stays running and listens for your commands in Telegram.
```bash
python3 telegram_bot.py
```
- Send `/check` to your bot to trigger a 7-day search instantly.
- Send `/weekends` to only see Saturday/Sunday slots for the next 7 days.
- Send `/help` to see the command list.

## How to get Telegram Credentials
1.  Message [@BotFather](https://t.me/botfather) to create a bot and get your `TELEGRAM_TOKEN`.
2.  Message [@userinfobot](https://t.me/userinfobot) to get your `TELEGRAM_CHAT_ID`.
3.  **Important**: You must message your bot and click **/start** before it can send you notifications.

## Project Structure
- `pickleball_checker.py`: The main scraping and logic script.
- `.env`: Secret configuration (not in git).
- `.gitignore`: Excludes environment files and cache.
- `walkthrough.md`: Detailed development history and technical overview.
