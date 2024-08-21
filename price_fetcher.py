import aiohttp
import logging
from cache import price_cache

logger = logging.getLogger(__name__)

async def fetch_prices(portfolio):
    prices = {}
    async with aiohttp.ClientSession() as session:
        for symbol, asset_data in portfolio.items():
            token_address = asset_data['token_address']
            cached_price = price_cache.get(token_address)
            if cached_price is not None:
                prices[symbol] = cached_price
                continue

            try:
                url = f'https://api.dexscreener.com/latest/dex/tokens/{token_address}'
                logger.debug(f"Requesting URL: {url}")
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'pairs' in data and data['pairs']:
                            pair_data = data['pairs'][0]
                            if 'priceUsd' in pair_data:
                                price = float(pair_data['priceUsd'])
                                prices[symbol] = price
                                price_cache.set(token_address, price)
                                logger.info(f"Successfully fetched price for {symbol} ({token_address}): ${price}")
                            else:
                                logger.warning(f"No priceUsd found for {symbol} ({token_address})")
                                prices[symbol] = None
                        else:
                            logger.warning(f"No pairs data found for {symbol} ({token_address})")
                            prices[symbol] = None
                    elif response.status == 400:
                        error_data = await response.text()
                        logger.error(f"Bad request for {symbol} ({token_address}). Response: {error_data}")
                        prices[symbol] = None
                    else:
                        logger.warning(f"Failed to fetch price for {symbol} ({token_address}). Status: {response.status}")
                        prices[symbol] = None
            except aiohttp.ClientError as e:
                logger.error(f"Network error when fetching price for {symbol} ({token_address}): {str(e)}")
                prices[symbol] = None
            except Exception as e:
                logger.error(f"Unexpected error when fetching price for {symbol} ({token_address}): {str(e)}")
                prices[symbol] = None
    return prices