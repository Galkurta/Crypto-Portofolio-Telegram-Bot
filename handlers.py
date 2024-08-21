from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config import AUTHORIZED_USER_ID
from database import get_profiles, get_portfolio, update_portfolio, create_profile, delete_profile
from price_fetcher import fetch_prices
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Define states
CHOOSING_PROFILE, ADDING_PROFILE, REMOVING_PROFILE, ADDING_ASSET, REMOVING_ASSET, UPDATING_ASSET = range(6)

def is_authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("Sorry, you don't have permission to use this bot.")
            return
        return await func(update, context)
    return wrapper

@is_authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
        [InlineKeyboardButton("See portfolio", callback_data='view_portfolio')],
        [InlineKeyboardButton("Add an asset", callback_data='add_asset')],
        [InlineKeyboardButton("Delete assets", callback_data='remove_asset')],
        [InlineKeyboardButton("Manage profiles", callback_data='manage_profiles')],
        [InlineKeyboardButton("Relief", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = (
        "Welcome to your personal Crypto Portfolio Bot!\n"
        "Please select the option below:"
    )

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        
async def update_asset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Starting the process of updating the number of assets ...")

    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        keyboard = [[InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
                    [InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select a profile first.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    portfolio = await get_portfolio(active_profile)
    if not portfolio:
        keyboard = [[InlineKeyboardButton("Add an asset", callback_data='add_asset')],
                    [InlineKeyboardButton("Return", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Your Portfolio for Profile '{active_profile}' blank.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(symbol, callback_data=f'update:{symbol}')] for symbol in portfolio.keys()]
    keyboard.append([InlineKeyboardButton("Return", callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Select assets to be updated from the profile '{active_profile}':", reply_markup=reply_markup)
    return UPDATING_ASSET

async def update_asset_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.split(':')[1]
    context.user_data['updating_symbol'] = symbol
    
    await query.edit_message_text(f"Enter a new amount for {symbol}:\n\nType 'cancele' to cancel.")
    return UPDATING_ASSET

async def process_asset_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'cancele':
        await update.message.reply_text("The asset update process is canceled.")
        await start(update, context)
        return ConversationHandler.END

    active_profile = context.user_data.get('active_profile')
    updating_symbol = context.user_data.get('updating_symbol')
    
    if not active_profile or not updating_symbol:
        await update.message.reply_text("There is an error.Please start from the beginning.")
        await start(update, context)
        return ConversationHandler.END
    
    try:
        new_amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("The amount must be in the form of numbers. Please try again.")
        return UPDATING_ASSET
    
    await update.message.reply_text(f"Is updating the amount {updating_symbol}...")
    portfolio = await get_portfolio(active_profile)
    
    if updating_symbol in portfolio:
        portfolio[updating_symbol]['amount'] = new_amount
        await update_portfolio(active_profile, portfolio)
        await update.message.reply_text(f"Amount {updating_symbol} successfully updated to be {new_amount} In the profile portfolio '{active_profile}'.")
    else:
        await update.message.reply_text(f"Asset {updating_symbol} not found in a profile portfolio '{active_profile}'. No changes made.")
    
    del context.user_data['updating_symbol']
    await start(update, context)
    return ConversationHandler.END

async def choose_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Loading profile ...")

    profiles = await get_profiles()
    if not profiles:
        message_text = "You don't have a profile yet.Please create a new profile first."
        await query.edit_message_text(message_text)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(profile, callback_data=f'set_profile:{profile}')] for profile in profiles]
    keyboard.append([InlineKeyboardButton("Back", callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Select Profile:", reply_markup=reply_markup)
    return CHOOSING_PROFILE

async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Set the profile ...")
    
    profile = query.data.split(':')[1]
    context.user_data['active_profile'] = profile
    
    await query.edit_message_text(f"Active profile: {profile}")
    await start(update, context)
    return ConversationHandler.END

async def manage_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Loading the Profile Manage menu ...")

    keyboard = [
        [InlineKeyboardButton("Add Profile", callback_data='add_profile')],
        [InlineKeyboardButton("Delete Profile", callback_data='remove_profile')],
        [InlineKeyboardButton("Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Manage Profile:", reply_markup=reply_markup)

async def add_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Starting the process of adding a profile ...")
    await query.edit_message_text("Enter the new profile name:")
    return ADDING_PROFILE

async def create_new_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_name = update.message.text
    await update.message.reply_text(f"Is making a profile '{profile_name}'...")
    try:
        await create_profile(profile_name)
        await update.message.reply_text(f"Profile {profile_name} successfully create.")
    except ValueError as e:
        await update.message.reply_text(str(e))
    
    await start(update, context)
    return ConversationHandler.END

async def remove_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Contains a profile list to be deleted ...")

    profiles = await get_profiles()
    if not profiles:
        await query.edit_message_text("You don't have a profile to delete.")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(profile, callback_data=f'confirm_remove:{profile}')] for profile in profiles]
    keyboard.append([InlineKeyboardButton("Back", callback_data='manage_profiles')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("Pilih profil untuk dihapus:", reply_markup=reply_markup)
    return REMOVING_PROFILE

async def confirm_remove_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Delete Profile ...")
    
    profile = query.data.split(':')[1]
    try:
        await delete_profile(profile)
        await query.edit_message_text(f"Profile {profile} successfully deleted.")
    except ValueError as e:
        await query.edit_message_text(str(e))
    
    await start(update, context)
    return ConversationHandler.END

async def view_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Loading a portfolio ...")

    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        keyboard = [[InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
                    [InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select a profile first.", reply_markup=reply_markup)
        return
    
    portfolio = await get_portfolio(active_profile)
    
    if not portfolio:
        keyboard = [[InlineKeyboardButton("Add an asset", callback_data='add_asset')],
                    [InlineKeyboardButton("Return", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Your Portfolio for Profile '{active_profile}' empty.", reply_markup=reply_markup)
        return
    
    await query.edit_message_text("Is taking the latest price ...")
    prices = await fetch_prices(portfolio)
    
    portfolio_text = f"Your portfolio (Profile: {active_profile}):\n\n"
    total_value = 0
    
    for symbol, asset_data in portfolio.items():
        price = prices.get(symbol)
        amount = asset_data['amount']
        if price is not None:
            value = price * amount
            total_value += value
            portfolio_text += f"{symbol}: {amount} (${value:.2f})\n"
        else:
            portfolio_text += f"{symbol}: {amount} (Prices are not available)\n"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    portfolio_text += f"\nTotal Portfolio Value: ${total_value:.2f}"
    portfolio_text += f"\n\nLast updated: {current_time}"
    
    keyboard = [
        [InlineKeyboardButton("Update the price", callback_data='update_prices')],
        [InlineKeyboardButton("Update the number of assets", callback_data='update_asset')],
        [InlineKeyboardButton("Back", callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(portfolio_text, reply_markup=reply_markup)

async def add_asset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Starting the process of adding assets ...")

    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        keyboard = [[InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
                    [InlineKeyboardButton("Return", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select a profile first.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    message_text = (
        f"To add assets to profiles '{active_profile}', Send Message with Format:\n"
        "<Symbol> <Amount> <Token address>\n"
        "Example: BTC 0.5 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599\n\n"
        "Type 'cancele' to cancel."
    )
    await query.edit_message_text(message_text)
    return ADDING_ASSET

async def add_asset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'cancele':
        await update.message.reply_text("The asset added process was canceled.")
        await start(update, context)
        return ConversationHandler.END

    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        await update.message.reply_text("Please select a profile first.")
        await start(update, context)
        return ConversationHandler.END
    
    try:
        symbol, amount, token_address = update.message.text.split()
        amount = float(amount)
    except ValueError:
        await update.message.reply_text("Invalid format.Use: <symbol> <total> <token address>")
        return ADDING_ASSET
    
    await update.message.reply_text(f"Is adding assets {symbol.upper()}...")
    portfolio = await get_portfolio(active_profile)
    portfolio[symbol.upper()] = {
        'amount': amount,
        'token_address': token_address
    }
    await update_portfolio(active_profile, portfolio)
    await update.message.reply_text(f"Asset {symbol.upper()} a lot {amount} with the token address {token_address} has been added to the profile portfolio '{active_profile}'.")
    
    await start(update, context)
    return ConversationHandler.END

async def remove_asset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Contains a list of assets to be deleted ...")

    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        keyboard = [[InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
                    [InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select a profile first.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    portfolio = await get_portfolio(active_profile)
    if not portfolio:
        keyboard = [[InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Your Portfolio for Profile '{active_profile}' empty.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(symbol, callback_data=f'remove:{symbol}')] for symbol in portfolio.keys()]
    keyboard.append([InlineKeyboardButton("Back", callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Select Assets to Delete from Profile '{active_profile}':", reply_markup=reply_markup)
    return REMOVING_ASSET

async def remove_asset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Delete assets ...")
    
    active_profile = context.user_data.get('active_profile')
    if not active_profile:
        keyboard = [[InlineKeyboardButton("Select Profile", callback_data='choose_profile')],
                    [InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Please select a profile first.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    portfolio = await get_portfolio(active_profile)
    if not portfolio:
        keyboard = [[InlineKeyboardButton("Add an asset", callback_data='add_asset')],
                    [InlineKeyboardButton("Back", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Your Portfolio for Profile '{active_profile}' empty.", reply_markup=reply_markup)
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton(symbol, callback_data=f'update:{symbol}')] for symbol in portfolio.keys()]
    keyboard.append([InlineKeyboardButton("Back", callback_data='start')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Select assets to be updated from the profile '{active_profile}':", reply_markup=reply_markup)
    return UPDATING_ASSET

async def update_asset_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    symbol = query.data.split(':')[1]
    context.user_data['updating_symbol'] = symbol
    
    await query.edit_message_text(f"Enter a new amount for {symbol}:\n\nType 'cancele' to cancel.")
    return UPDATING_ASSET

async def process_asset_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'cancele':
        await update.message.reply_text("The asset update process is canceled.")
        await start(update, context)
        return ConversationHandler.END

    active_profile = context.user_data.get('active_profile')
    updating_symbol = context.user_data.get('updating_symbol')
    
    if not active_profile or not updating_symbol:
        await update.message.reply_text("There is an error.Please start from the beginning.")
        await start(update, context)
        return ConversationHandler.END
    
    try:
        new_amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("The amount must be in the form of numbers.Please try again.")
        return UPDATING_ASSET
    
    await update.message.reply_text(f"Is updating the amount {updating_symbol}...")
    portfolio = await get_portfolio(active_profile)
    
    if updating_symbol in portfolio:
        portfolio[updating_symbol]['amount'] = new_amount
        await update_portfolio(active_profile, portfolio)
        await update.message.reply_text(f"Amount {updating_symbol} successfully updated to be {new_amount} In the profile portfolio '{active_profile}'.")
    else:
        await update.message.reply_text(f"Asset {updating_symbol} not found in a profile portfolio '{active_profile}'. No changes made.")
    
    del context.user_data['updating_symbol']
    await start(update, context)
    return ConversationHandler.END

async def update_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Update the price ...")
    await view_portfolio(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Showing help ...")

    help_text = (
        "Boat Usage Guide:\n\n"
        "1. Select Profile: Select an active portfolio profile\n"
        "2. See Portfolio: Displays your portfolio assets and values\n"
        "3. Add Assets: add new assets to the portfolio\n"
        "4. Delete Assets: Delete Assets from Portfolios\n"
        "5. Update Number of Assets: Changing the Number of Assets that Already\n"
        "6. Manage Profile: Add or delete profiles\n"
        "7. Help: Display this message\n\n"
        "Use the button on the main menu for easy navigation."
    )
    keyboard = [[InlineKeyboardButton("Back to the main menu", callback_data='start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start':
        await start(update, context)
    elif query.data == 'choose_profile':
        return await choose_profile(update, context)
    elif query.data.startswith('set_profile:'):
        return await set_profile(update, context)
    elif query.data == 'view_portfolio':
        await view_portfolio(update, context)
    elif query.data == 'add_asset':
        return await add_asset_prompt(update, context)
    elif query.data == 'remove_asset':
        return await remove_asset_prompt(update, context)
    elif query.data == 'update_asset':
        return await update_asset_prompt(update, context)
    elif query.data.startswith('update:'):
        return await update_asset_amount(update, context)
    elif query.data == 'manage_profiles':
        await manage_profiles(update, context)
    elif query.data == 'add_profile':
        return await add_profile(update, context)
    elif query.data == 'remove_profile':
        return await remove_profile(update, context)
    elif query.data.startswith('confirm_remove:'):
        return await confirm_remove_profile(update, context)
    elif query.data == 'update_prices':
        await update_prices(update, context)
    elif query.data == 'help':
        await help_command(update, context)
        
def setup_handlers(application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(handle_button)],
        states={
            CHOOSING_PROFILE: [CallbackQueryHandler(set_profile, pattern='^set_profile:')],
            ADDING_PROFILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_new_profile)],
            REMOVING_PROFILE: [CallbackQueryHandler(confirm_remove_profile, pattern='^confirm_remove:')],
            ADDING_ASSET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_asset)],
            REMOVING_ASSET: [CallbackQueryHandler(remove_asset, pattern='^remove:')],
            UPDATING_ASSET: [
                CallbackQueryHandler(update_asset_amount, pattern='^update:'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_asset_update)
            ],
        },
        fallbacks=[CommandHandler('start', start), 
                   CallbackQueryHandler(handle_button, pattern='^start$')]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))