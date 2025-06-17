import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from ...config.config_manager import ConfigManager
from ...utils.error_logger import ErrorLogger
from ...utils.cache_manager import CacheManager
from .poster import WordPressPoster

class Scheduler:
    """WordPress投稿スケジューラー"""

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        cache: Optional[CacheManager] = None,
        logger: Optional[ErrorLogger] = None,
        poster: Optional[WordPressPoster] = None
    ):
        """
        初期化

        Args:
            config: 設定マネージャー（オプション）
            cache: キャッシュマネージャー（オプション）
            logger: エラーロガー（オプション）
            poster: WordPress投稿クラス（オプション）
        """
        self.config = config or ConfigManager()
        self.cache = cache or CacheManager(self.config)
        self.logger = logger or ErrorLogger()
        self.poster = poster or WordPressPoster(self.config, self.cache, self.logger)
        
        # Google Sheets APIの設定
        self.spreadsheet_id = self.config.get('SPREADSHEET_ID')
        self.credentials_file = self.config.get('GOOGLE_CREDENTIALS_FILE')
        self.sheet_name = '商品管理シート'
        
        # Google Sheets APIクライアントの初期化
        self.sheets_service = self._init_sheets_service()

    def _init_sheets_service(self):
        """
        Google Sheets APIクライアントを初期化

        Returns:
            Google Sheets APIクライアント
        """
        try:
            credentials = Credentials.from_authorized_user_file(
                self.credentials_file,
                ['https://www.googleapis.com/auth/spreadsheets']
            )
            return build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            self.logger.log_error(
                "Google Sheets APIクライアントの初期化に失敗しました",
                error=e
            )
            raise

    async def _get_last_scheduled_post_time(self) -> Optional[datetime]:
        """
        最後に予約された投稿の時間を取得

        Returns:
            最後の予約投稿時間
        """
        try:
            # スプレッドシートからデータを取得
            range_name = f'{self.sheet_name}!A:D'
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return None
            
            # 予約投稿日時でソート
            scheduled_posts = []
            for row in values[1:]:  # ヘッダーをスキップ
                if len(row) >= 3 and row[2]:  # 予約投稿日時が存在する場合
                    try:
                        post_time = datetime.fromisoformat(row[2])
                        scheduled_posts.append(post_time)
                    except ValueError:
                        continue
            
            if not scheduled_posts:
                return None
            
            return max(scheduled_posts)

        except Exception as e:
            self.logger.log_error(
                "最後の予約投稿時間の取得に失敗しました",
                error=e
            )
            return None

    async def _check_duplicate_product(self, product_url: str) -> bool:
        """
        商品の重複チェック

        Args:
            product_url: 商品URL

        Returns:
            重複しているかどうか
        """
        try:
            # スプレッドシートからデータを取得
            range_name = f'{self.sheet_name}!A:A'  # 商品URLの列
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return False
            
            # 重複チェック
            return product_url in [row[0] for row in values[1:]]  # ヘッダーをスキップ

        except Exception as e:
            self.logger.log_error(
                "商品の重複チェックに失敗しました",
                error=e,
                context={'product_url': product_url}
            )
            return False

    async def _update_spreadsheet(
        self,
        product_url: str,
        status: str,
        schedule_date: Optional[datetime] = None,
        article_url: Optional[str] = None
    ) -> bool:
        """
        スプレッドシートを更新

        Args:
            product_url: 商品URL
            status: 投稿ステータス
            schedule_date: 予約投稿日時
            article_url: 投稿済み記事URL

        Returns:
            更新の成功/失敗
        """
        try:
            # 更新するデータ
            values = [[
                product_url,
                status,
                schedule_date.isoformat() if schedule_date else '',
                article_url or ''
            ]]
            
            # スプレッドシートに追加
            body = {
                'values': values
            }
            
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:D',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True

        except Exception as e:
            self.logger.log_error(
                "スプレッドシートの更新に失敗しました",
                error=e,
                context={
                    'product_url': product_url,
                    'status': status,
                    'schedule_date': schedule_date,
                    'article_url': article_url
                }
            )
            return False

    async def schedule_article(
        self,
        product_url: str,
        article_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        記事をスケジュール投稿

        Args:
            product_url: 商品URL
            article_data: 記事データ

        Returns:
            スケジュール結果
        """
        try:
            # 重複チェック
            if await self._check_duplicate_product(product_url):
                self.logger.log_info(
                    "商品は既に投稿済みです",
                    context={'product_url': product_url}
                )
                return None
            
            # 最後の予約投稿時間を取得
            last_scheduled_time = await self._get_last_scheduled_post_time()
            
            # 次の投稿時間を設定（最後の投稿の1時間後）
            if last_scheduled_time:
                schedule_date = last_scheduled_time + timedelta(hours=1)
            else:
                # 初回の場合は翌日の0時から
                schedule_date = datetime.now() + timedelta(days=1)
                schedule_date = schedule_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            
            # 記事を投稿
            article_id = await self.poster.post_article(article_data, schedule_date)
            if not article_id:
                return None
            
            # スプレッドシートを更新
            article_url = f"{self.config.get('WP_URL')}/?p={article_id}"
            await self._update_spreadsheet(
                product_url,
                '予約済み',
                schedule_date,
                article_url
            )
            
            return {
                'article_id': article_id,
                'schedule_date': schedule_date,
                'article_url': article_url
            }

        except Exception as e:
            self.logger.log_error(
                "記事のスケジュール投稿に失敗しました",
                error=e,
                context={
                    'product_url': product_url,
                    'article_data': article_data
                }
            )
            return None 