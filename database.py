import json
import logging
import traceback
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager
import gspread
from config import GOOGLE_SHEETS_CRED_FILE, GOOGLE_SHEET_ID

logger = logging.getLogger(__name__)

def get_creds():
    try:
        creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CRED_FILE)
        scoped = creds.with_scopes([
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        return scoped
    except Exception as e:
        logger.error(f"Error loading credentials: {str(e)}")
        raise

agcm = AsyncioGspreadClientManager(get_creds)

async def get_sheet():
    try:
        agc = await agcm.authorize()
        sheet = await agc.open_by_key(GOOGLE_SHEET_ID)
        return await sheet.worksheet("Portfolio")
    except gspread.exceptions.APIError as e:
        if e.response.status_code == 403:
            logger.error("Permission denied when accessing Google Sheet. Please check your credentials and sheet permissions.")
        else:
            logger.error(f"API Error when accessing Google Sheet: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error when accessing Google Sheet: {str(e)}")
        raise

async def get_profiles():
    try:
        sheet = await get_sheet()
        cell = await sheet.cell(1, 1)
        cell_value = cell.value if cell else '{}'
        return json.loads(cell_value)
    except Exception as e:
        logger.error(f"Error getting profiles: {str(e)}")
        return {}

async def update_profiles(profiles):
    try:
        sheet = await get_sheet()
        await sheet.update_cell(1, 1, json.dumps(profiles))
        logger.info("Profiles updated successfully")
    except Exception as e:
        logger.error(f"Error updating profiles: {str(e)}")
        raise

async def get_portfolio(profile_name):
    try:
        sheet = await get_sheet()
        profiles = await get_profiles()
        if profile_name not in profiles:
            return {}
        cell_address = profiles[profile_name]
        cell = await sheet.cell(*cell_address)
        cell_value = cell.value if cell else '{}'
        return json.loads(cell_value)
    except Exception as e:
        logger.error(f"Error getting portfolio for profile {profile_name}: {str(e)}")
        return {}

async def update_portfolio(profile_name, portfolio):
    try:
        sheet = await get_sheet()
        profiles = await get_profiles()
        if profile_name not in profiles:
            raise ValueError(f"Profile {profile_name} does not exist")
        cell_address = profiles[profile_name]
        await sheet.update_cell(*cell_address, json.dumps(portfolio))
        logger.info(f"Portfolio for profile {profile_name} updated successfully")
    except Exception as e:
        logger.error(f"Error updating portfolio for profile {profile_name}: {str(e)}")
        raise

async def create_profile(profile_name):
    try:
        profiles = await get_profiles()
        if profile_name in profiles:
            raise ValueError(f"Profile {profile_name} already exists")
        sheet = await get_sheet()
        next_row = len(profiles) * 2 + 3  # Assuming we use odd rows for profiles
        profiles[profile_name] = [next_row, 2]  # Column 2 for portfolio data
        await update_profiles(profiles)
        await sheet.update_cell(next_row, 2, '{}')  # Initialize empty portfolio
        logger.info(f"Profile {profile_name} created successfully")
    except Exception as e:
        logger.error(f"Error creating profile {profile_name}: {str(e)}")
        raise

async def delete_profile(profile_name):
    try:
        profiles = await get_profiles()
        if profile_name not in profiles:
            raise ValueError(f"Profile {profile_name} does not exist")
        del profiles[profile_name]
        await update_profiles(profiles)
        logger.info(f"Profile {profile_name} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting profile {profile_name}: {str(e)}")
        raise