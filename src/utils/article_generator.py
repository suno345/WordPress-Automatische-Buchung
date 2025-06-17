import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .error_logger import ErrorLogger

class WordPressArticleGenerator:
    """WordPress記事生成クラス"""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = template_dir
        self.error_logger = ErrorLogger()
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True
        )
        
        # テンプレートの読み込み
        self.template = self.env.get_template("article.html")
    
    def generate_article_content(
        self,
        product_data: Dict,
        grok_results: Optional[Dict] = None
    ) -> Dict:
        """記事コンテンツを生成"""
        if product_data is None:
            raise ValueError("product_data is required")
        try:
            # タクソノミー情報の準備
            taxonomies = self._prepare_taxonomies(product_data, grok_results)
            
            # 記事データの準備
            article_data = {
                "title": self._generate_title(product_data, taxonomies),
                "content": self._generate_content(product_data, taxonomies),
                "categories": taxonomies["categories"],
                "tags": taxonomies["tags"],
                "custom_taxonomies": taxonomies["custom"],
                "eyecatch_image": product_data.get("eyecatch_image_url", ""),
                "meta": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            return article_data
            
        except Exception as e:
            self.error_logger.log_error(
                "WordPressArticleGenerator",
                "generate_article_content",
                str(e)
            )
            return {}
    
    def _prepare_taxonomies(
        self,
        product_data: Dict,
        grok_results: Optional[Dict]
    ) -> Dict:
        """タクソノミー情報を準備"""
        taxonomies = {
            "categories": [],
            "tags": [],
            "custom": {
                "original_work": [],
                "character_name": [],
                "product_format": [],
                "circle_name": []
            }
        }
        
        # カテゴリー（FANZAジャンル）の処理
        if "genres" in product_data:
            taxonomies["categories"] = [
                genre for genre in product_data["genres"]
                if not any(ng in genre for ng in ["新作", "準新作", "旧作"])
            ]
        
        # タグ（作者名）の処理
        if "authors" in product_data:
            taxonomies["tags"] = product_data["authors"]
        
        # カスタムタクソノミーの処理
        if grok_results:
            if "original_work" in grok_results:
                taxonomies["custom"]["original_work"] = [grok_results["original_work"]]
            if "character_name" in grok_results:
                taxonomies["custom"]["character_name"] = [grok_results["character_name"]]
        
        # 商品形式の処理
        if "product_format" in product_data:
            taxonomies["custom"]["product_format"] = [product_data["product_format"]]
        
        # サークル名の処理
        if "circle_name" in product_data:
            taxonomies["custom"]["circle_name"] = [product_data["circle_name"]]
        
        return taxonomies
    
    def _generate_title(
        self,
        product_data: Dict,
        taxonomies: Dict
    ) -> str:
        """記事タイトルを生成"""
        title_parts = []
        
        # 商品名
        if "title" in product_data:
            title_parts.append(product_data["title"])
        
        # キャラ名
        if taxonomies["custom"]["character_name"]:
            title_parts.append(f"【{taxonomies['custom']['character_name'][0]}】")
        
        return "".join(title_parts)
    
    def _generate_content(
        self,
        product_data: Dict,
        taxonomies: Dict
    ) -> str:
        """記事本文を生成"""
        try:
            # テンプレートに渡すデータ
            template_data = {
                "product": product_data,
                "taxonomies": taxonomies,
                "current_year": datetime.now().year
            }
            
            # テンプレートをレンダリング
            return self.template.render(**template_data)
            
        except Exception as e:
            self.error_logger.log_error(
                "WordPressArticleGenerator",
                "_generate_content",
                str(e)
            )
            return "" 