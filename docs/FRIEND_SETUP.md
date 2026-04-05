# How to Use This for Your Own Trip

No coding needed! Just fork, configure, and go.

## Step 1: Fork the Repo

Click "Fork" on GitHub to copy this repo to your account.

## Step 2: Set Up LINE Bot

1. Go to https://developers.line.biz/
2. Create a Provider → Create a Messaging API channel
3. Get your **Channel Access Token** (Messaging API tab → Issue)
4. Get your **User ID** (Basic settings tab)
5. Add the bot as friend (scan QR code)

## Step 3: Set Up Google Sheets

1. Go to https://console.cloud.google.com/
2. Create a project → Enable Google Sheets API
3. Create a Service Account → Download JSON key
4. Create a new Google Sheet → Share it with the service account email (Editor)
5. Copy the Sheet ID from the URL

## Step 4: Configure Your Trip

Edit `src/config.py` in your forked repo:

```python
# Change these to your trip
SEARCH_ROUTES = [
    {"origin": "Bangkok", "destination": "Tokyo", "date": "2026-10-18", "label": "BKK-TYO-Oct18", "route_code": "BKK-TYO"},
    {"origin": "Tokyo", "destination": "Bangkok", "date": "2026-10-25", "label": "TYO-BKK-Oct25", "route_code": "TYO-BKK"},
]

# Your valid trip combos
VALID_COMBOS = [
    ("2026-10-18", "2026-10-25"),  # 18 Oct → 25 Oct (7 nights)
]

# Add any new airlines to the baggage list if needed
# Add any new airports to AIRPORT_SHORT if needed
```

## Step 5: Add GitHub Secrets

In your forked repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `LINE_CHANNEL_ACCESS_TOKEN` | Your LINE bot token |
| `LINE_USER_ID` | Your LINE user ID (starts with U...) |
| `GOOGLE_SHEET_ID` | Your Google Sheet ID |
| `GOOGLE_CREDENTIALS_JSON` | Paste the ENTIRE contents of your Google credentials JSON file |

## Step 6: Enable GitHub Actions

1. Go to the "Actions" tab in your forked repo
2. Click "I understand my workflows, go ahead and enable them"
3. The tracker will run every 4 hours automatically

## Step 7: Test It

1. Go to Actions tab → "Flight Price Tracker" → "Run workflow" → Click the green button
2. Wait 3-5 minutes
3. Check your LINE and Google Sheet

## Tips

- **Change schedule:** Edit `.github/workflows/flight-tracker.yml`, change the cron line
- **Stop tracking:** Disable the workflow in Actions tab, or set `SCRAPER_EXPIRY_DATE` in config
- **Add more dates:** Add more entries to `SEARCH_ROUTES` and `VALID_COMBOS`
- **Different airports:** Use city names (e.g., "Tokyo", "Osaka") to search all airports in that city

## Scoring

The system scores flights 0-20:
- **Price Score (0-10):** Cheapest = 10
- **Time Score (0-10):**
  - Outbound: mid-day departure (10:00-14:00) = 10
  - Return: arrive home ~18:00 = 10

Edit `_calc_time_score()` in `src/scraper.py` to change preferred times.

## Cost

Everything is free:
- GitHub Actions: 2000 min/month free
- LINE Messaging API: 200 messages/month free
- Google Sheets API: free
- No server needed
