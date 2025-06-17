import os
import asyncio
import argparse
from datetime import datetime
from dotenv import load_dotenv
from src.scheduler.scheduler_orchestrator import Scheduler_Orchestrator
from src.monitor.monitor import Monitor

def parse_arguments():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(description='FANZAコンテンツ自動投稿プログラム')
    
    # 実行モードの選択
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--daily', action='store_true',
                          help='最新商品の日次スケジュールを実行')
    mode_group.add_argument('--keyword', type=str,
                          help='指定したキーワードで検索してスケジュールを実行')
    
    # オプション引数
    parser.add_argument('--limit', type=int,
                      help='処理する商品数の上限（デフォルト: 環境変数のPOSTS_PER_DAY）')
    parser.add_argument('--debug', action='store_true',
                      help='デバッグモードで実行（より詳細なログを出力）')
    
    return parser.parse_args()

async def main():
    """メイン処理"""
    # 環境変数の読み込み
    load_dotenv()
    
    # コマンドライン引数の解析
    args = parse_arguments()
    
    # モニターの初期化
    monitor = Monitor()
    monitor.log_info("Starting FANZA Content Auto Blogger")
    
    try:
        # スケジューラーの初期化
        scheduler = Scheduler_Orchestrator()
        
        # デバッグモードの設定
        if args.debug:
            monitor.set_debug_mode(True)
            monitor.log_debug("Debug mode enabled")
        
        # 処理件数の設定
        if args.limit:
            scheduler.posts_per_day = args.limit
            monitor.log_info(f"Processing limit set to {args.limit} products")
        
        # 実行モードに応じた処理
        if args.daily:
            monitor.log_info("Starting daily schedule")
            await scheduler.run_daily_schedule()
        elif args.keyword:
            monitor.log_info(f"Starting keyword schedule for: {args.keyword}")
            await scheduler.run_keyword_schedule(args.keyword)
        
        monitor.log_info("Schedule execution completed")
    
    except Exception as e:
        monitor.log_error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        exit(1) 