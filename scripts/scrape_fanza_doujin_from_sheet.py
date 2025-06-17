from dotenv import load_dotenv
load_dotenv("API.env")

import asyncio
from src.spreadsheet.spreadsheet_manager import SpreadsheetManager
from src.utils.fanza_scraper import search_fanza_products_by_keyword

async def main():
    sheet = SpreadsheetManager()
    keywords = sheet.get_active_keywords()
    for kw in keywords:
        keyword = kw['keyword']
        char_name = kw['character_name']
        print(f"キーワード: {keyword} / キャラクター名: {char_name}")
        urls = await search_fanza_products_by_keyword(keyword)
        for i, url in enumerate(urls, 1):
            print(f"  {i:2d}: {url}")
        print()

if __name__ == "__main__":
    asyncio.run(main()) 