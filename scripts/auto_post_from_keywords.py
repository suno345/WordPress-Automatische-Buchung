import asyncio
from dotenv import load_dotenv
from src.spreadsheet.spreadsheet_manager import SpreadsheetManager
from src.utils.fanza_scraper import search_fanza_products_by_keyword, extract_product_id_from_url
from src.scheduler.scheduler_orchestrator import Scheduler_Orchestrator

load_dotenv('API.env')

async def main():
    mgr = SpreadsheetManager()
    scheduler = Scheduler_Orchestrator()
    # キーワード管理シートからキーワード取得（1件だけ）
    keywords = mgr.get_active_keywords()
    if not keywords:
        print("キーワードがありません")
        return
    keyword = keywords[0]['keyword']
    print(f"[INFO] 検索キーワード: {keyword}")
    urls = await search_fanza_products_by_keyword(keyword)
    print(f"[INFO] 取得URL件数: {len(urls)}")
    if not urls:
        print("URLが見つかりません")
        return
    pid = urls[0]
    print(f"[INFO] 投稿対象商品ID: {pid}")
    # 自動投稿フロー実行
    await scheduler.schedule_articles([pid])

if __name__ == "__main__":
    asyncio.run(main()) 