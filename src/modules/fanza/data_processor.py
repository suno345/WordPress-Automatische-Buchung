from typing import Dict, List, Optional, Any
from datetime import datetime
from ...config.config_manager import ConfigManager
from ...utils.error_logger import ErrorLogger

class DataProcessor:
    """FANZAデータ処理クラス"""

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        logger: Optional[ErrorLogger] = None
    ):
        """
        初期化

        Args:
            config: 設定マネージャー（オプション）
            logger: エラーロガー（オプション）
        """
        self.config = config or ConfigManager()
        self.logger = logger or ErrorLogger()

    def process_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        商品データをWordPress投稿用に整形

        Args:
            product_data: 商品データ

        Returns:
            整形されたデータ
        """
        try:
            # タイトルの生成（商品名+【キャラ名】）
            title = self._generate_title(product_data)
            
            # カテゴリの設定（FANZAのジャンル）
            categories = self._extract_categories(product_data)
            
            # タグの設定（作者・サークル名）
            tags = self._extract_tags(product_data)
            
            # 商品情報の整形
            content = self._format_content(product_data)
            
            return {
                'title': title,
                'categories': categories,
                'tags': tags,
                'content': content,
                'metadata': {
                    'product_id': product_data.get('content_id'),
                    'affiliate_url': product_data.get('affiliateURL'),
                    'price': product_data.get('prices', {}).get('price'),
                    'release_date': product_data.get('date'),
                    'image_url': self._get_main_image(product_data)
                }
            }
        except Exception as e:
            self.logger.log_error(
                "商品データの処理に失敗しました",
                error=e,
                context={'product_data': product_data}
            )
            raise

    def _generate_title(self, product_data: Dict[str, Any]) -> str:
        """
        記事タイトルを生成

        Args:
            product_data: 商品データ

        Returns:
            生成されたタイトル
        """
        title = product_data.get('title', '')
        character = product_data.get('character', [])
        
        if character:
            # キャラクター名が複数ある場合は最初のものを使用
            char_name = character[0].get('name', '')
            if char_name:
                title = f"{title}【{char_name}】"
        
        return title

    def _extract_categories(self, product_data: Dict[str, Any]) -> List[str]:
        """
        カテゴリを抽出（FANZAのジャンル）

        Args:
            product_data: 商品データ

        Returns:
            カテゴリリスト
        """
        categories = []
        genre = product_data.get('genre', [])
        
        for g in genre:
            category_name = g.get('name', '')
            if category_name:
                categories.append(category_name)
        
        return categories

    def _extract_tags(self, product_data: Dict[str, Any]) -> List[str]:
        """
        タグを抽出（作者・サークル名）

        Args:
            product_data: 商品データ

        Returns:
            タグリスト
        """
        tags = []
        
        # 作者情報の抽出
        maker = product_data.get('maker', {})
        maker_name = maker.get('name', '')
        if maker_name:
            tags.append(maker_name)
        
        # サークル情報の抽出
        circle = product_data.get('circle', {})
        circle_name = circle.get('name', '')
        if circle_name:
            tags.append(circle_name)
        
        return tags

    def _format_content(self, product_data: Dict[str, Any]) -> str:
        """
        商品情報をHTML形式に整形

        Args:
            product_data: 商品データ

        Returns:
            整形されたHTML
        """
        content = []
        
        # 商品説明
        description = product_data.get('description', '')
        if description:
            content.append(f"<p>{description}</p>")
        
        # 商品詳細
        content.append("<h2>商品詳細</h2>")
        content.append("<ul>")
        
        # 価格情報
        price = product_data.get('prices', {}).get('price')
        if price:
            content.append(f"<li>価格: {price}円</li>")
        
        # 発売日
        release_date = product_data.get('date')
        if release_date:
            content.append(f"<li>発売日: {release_date}</li>")
        
        # ジャンル
        genre = product_data.get('genre', [])
        if genre:
            genre_names = [g.get('name', '') for g in genre if g.get('name')]
            if genre_names:
                content.append(f"<li>ジャンル: {', '.join(genre_names)}</li>")
        
        # 作者・サークル
        maker = product_data.get('maker', {}).get('name', '')
        circle = product_data.get('circle', {}).get('name', '')
        if maker:
            content.append(f"<li>作者: {maker}</li>")
        if circle:
            content.append(f"<li>サークル: {circle}</li>")
        
        content.append("</ul>")
        
        # 商品画像
        image_url = self._get_main_image(product_data)
        if image_url:
            content.append(f'<p><img src="{image_url}" alt="{product_data.get("title", "")}" /></p>')
        
        # アフィリエイトリンク
        affiliate_url = product_data.get('affiliateURL')
        if affiliate_url:
            content.append(f'<p><a href="{affiliate_url}" target="_blank" rel="nofollow">商品を購入する</a></p>')
        
        return "\n".join(content)

    def _get_main_image(self, product_data: Dict[str, Any]) -> Optional[str]:
        """
        メイン画像のURLを取得

        Args:
            product_data: 商品データ

        Returns:
            画像URL
        """
        images = product_data.get('imageURL', {})
        return images.get('large') or images.get('medium') or images.get('small') 