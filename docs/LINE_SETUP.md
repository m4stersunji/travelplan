# LINE Messaging API Setup

## Step 1: Create a LINE Developers Account
1. Go to https://developers.line.biz/
2. Log in with your LINE account
3. Create a new Provider (e.g., "Flight Tracker")

## Step 2: Create a Messaging API Channel
1. Under your provider, click "Create a Messaging API channel"
2. Fill in: Channel name = "Flight Price Tracker", Description, Category = "Utility"
3. Agree to terms and create

## Step 3: Get Your Channel Access Token
1. Go to the "Messaging API" tab
2. Under "Channel access token", click "Issue"
3. Copy the long-lived token

## Step 4: Get Your User ID
1. Go to the "Basic settings" tab
2. Copy "Your user ID" (starts with U...)

## Step 5: Configure .env
```
LINE_CHANNEL_ACCESS_TOKEN=<paste your token>
LINE_USER_ID=<paste your user ID>
```

## Step 6: Add the Bot as Friend
1. In the "Messaging API" tab, find the QR code
2. Scan it with LINE to add the bot as a friend
3. The bot can now send you push messages

## Step 7: Test
```bash
cd /home/m4stersun/travelplan
python3 -c "
from src.notifier import send_line_notification
result = send_line_notification('🧪 Test message from Flight Tracker!')
print('Success!' if result else 'Failed — check your .env')
"
```
