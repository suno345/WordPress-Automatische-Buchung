#!/usr/bin/env python3
"""
VPS向けメインエントリーポイント
cron実行に最適化された軽量版
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime

# パスの設定
sys.path.append(str(Path(__file__).parent.parent))

from src.scheduler.vps_orchestrator import VPS_Simple_Orchestrator
from src.utils.logger import Logger

def setup_logging():
    """ログ設定"""
    logger = Logger.get_logger("vps_main")
    return logger

async def run_daily_posts(max_posts: int = 5):
    """日次投稿実行"""
    logger = setup_logging()
    orchestrator = VPS_Simple_Orchestrator()
    
    try:
        logger.info(f"VPS日次投稿開始 - 最大{max_posts}件")
        await orchestrator.run_simple_posting(max_posts)
        logger.info("VPS日次投稿完了")
        
    except Exception as e:
        logger.error(f"VPS日次投稿エラー: {str(e)}")
        sys.exit(1)

async def run_keyword_posts(keyword: str, max_posts: int = 3):
    """キーワード投稿実行"""
    logger = setup_logging()
    orchestrator = VPS_Simple_Orchestrator()
    
    try:
        logger.info(f"VPSキーワード投稿開始: {keyword}")
        await orchestrator.run_keyword_posting(keyword, max_posts)
        logger.info(f"VPSキーワード投稿完了: {keyword}")
        
    except Exception as e:
        logger.error(f"VPSキーワード投稿エラー: {str(e)}")
        sys.exit(1)

async def run_scheduled_posts(posts_per_batch: int = 1):
    """24時間予約投稿実行（30分間隔）"""
    logger = setup_logging()
    orchestrator = VPS_Simple_Orchestrator()
    
    try:
        logger.info(f"VPS予約投稿開始 - バッチサイズ: {posts_per_batch}")
        success_count = await orchestrator.run_scheduled_posting(posts_per_batch)
        logger.info(f"VPS予約投稿完了 - 成功: {success_count}件")
        
    except Exception as e:
        logger.error(f"VPS予約投稿エラー: {str(e)}")
        sys.exit(1)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="VPS WordPress Auto Poster")
    parser.add_argument('--mode', choices=['daily', 'keyword', 'scheduled'], required=True,
                       help='実行モード: daily=日次投稿, keyword=キーワード投稿, scheduled=予約投稿')
    parser.add_argument('--keyword', type=str,
                       help='キーワード投稿時のキーワード')
    parser.add_argument('--max-posts', type=int, default=5,
                       help='最大投稿数（デフォルト: 5）')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='予約投稿時のバッチサイズ（デフォルト: 1）')
    parser.add_argument('--debug', action='store_true',
                       help='デバッグモード')
    
    args = parser.parse_args()
    
    # デバッグ設定
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f"[{datetime.now()}] VPS WordPress Auto Poster 開始")
    print(f"モード: {args.mode}")
    
    if args.mode == 'daily':
        asyncio.run(run_daily_posts(args.max_posts))
    elif args.mode == 'keyword':
        if not args.keyword:
            print("エラー: キーワードモードではキーワードの指定が必要です")
            sys.exit(1)
        asyncio.run(run_keyword_posts(args.keyword, args.max_posts))
    elif args.mode == 'scheduled':
        asyncio.run(run_scheduled_posts(args.batch_size))
    
    print(f"[{datetime.now()}] 処理完了")

if __name__ == "__main__":
    main()