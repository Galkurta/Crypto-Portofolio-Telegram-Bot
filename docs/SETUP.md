# Setup Instructions for Crypto Portfolio Telegram Bot

## Prerequisites

- Python 3.7 or newer
- pip (Python package installer)
- Telegram account
- Google Cloud Platform account (for Google Sheets API)

## Setup Steps

1. **Clone Repository**

   ```
   git clone [YOUR_REPOSITORY_URL]
   cd [PROJECT_DIRECTORY_NAME]
   ```

2. **Create and Activate Virtual Environment**

   ```
   python -m venv venv
   source venv/bin/activate  # For Unix or MacOS
   venv\Scripts\activate  # For Windows
   ```

3. **Install Dependencies**

   ```
   pip install -r requirements.txt
   ```

4. **Create Telegram Bot**

   - Open Telegram and search for @BotFather
   - Send the /newbot command and follow the instructions
   - Copy the bot token provided

5. **Setup Google Sheets API**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Sheets API
   - Create credentials (Service Account Key)
   - Download the JSON credentials file

6. **Configure Environment Variables**

   - Create a `.env` file in the project root directory
   - Add the following variables:
     ```
     TELEGRAM_BOT_TOKEN=your_bot_token_here
     AUTHORIZED_USER_ID=your_telegram_user_id
     GOOGLE_SHEETS_CRED_FILE=path/to/your/credentials.json
     GOOGLE_SHEET_ID=your_google_sheet_id
     CACHE_EXPIRY=300
     ```

7. **Prepare Google Sheet**

   - Create a new Google Sheet
   - Share it with the service account email from your Google Cloud credentials
   - Copy the Sheet ID (from the URL)

8. **Run the Bot**
   ```
   python main.py
   ```

## Troubleshooting

- If experiencing issues with Google Sheets authentication, ensure the credentials file is in the correct location and has proper permissions.
- If the bot is not responding, check the logs for any errors that might have occurred.

## Further Assistance

If you encounter any issues during setup, please open an issue in the GitHub repository or contact the project maintainer.
