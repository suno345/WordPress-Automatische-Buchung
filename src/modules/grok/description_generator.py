from typing import Dict, List, Optional, Union
from .api_client import GrokApiClient, GrokApiError
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager

class DescriptionGeneratorError(Exception):
    """DescriptionGeneratorのエラー基底クラス"""
    pass

class ProductInfoError(DescriptionGeneratorError):
    """商品情報エラー"""
    pass

class CharacterInfoError(DescriptionGeneratorError):
    """キャラクター情報エラー"""
    pass

class DescriptionGenerationError(DescriptionGeneratorError):
    """説明生成エラー"""
    pass

class DescriptionOptimizationError(DescriptionGeneratorError):
    """説明最適化エラー"""
    pass

class DescriptionGenerator:
    """商品説明生成クラス"""

    def __init__(self):
        """初期化"""
        self.logger = Logger()
        self.config_manager = ConfigManager()
        self.description_config = self.config_manager.get_description_config()
        self.api_config = self.config_manager.get_api_config()

        try:
            self.api_client = GrokApiClient()
            self.logger.info("DescriptionGenerator initialized successfully")
        except GrokApiError as e:
            error_msg = self.config_manager.get_error_message("api", "authentication")
            self.logger.error(f"Failed to initialize API client: {str(e)}")
            raise DescriptionGeneratorError(f"{error_msg}: {str(e)}")

    def _prepare_product_info(self, product_data: Dict) -> Dict:
        """
        商品情報を整形

        Args:
            product_data: 商品データ

        Returns:
            Dict: 整形された商品情報

        Raises:
            ProductInfoError: 商品情報の整形失敗
        """
        try:
            self.logger.debug("Preparing product information")

            if not product_data:
                error_msg = self.config_manager.get_error_message("description", "validation")
                raise ProductInfoError(error_msg)

            product_info = {
                "title": str(product_data.get("title", "")),
                "price": int(product_data.get("price", 0)),
                "list_price": int(product_data.get("list_price", 0)),
                "delivery_type": str(product_data.get("delivery_type", "")),
                "genre": list(product_data.get("genre", [])),
                "series": str(product_data.get("series", "")),
                "maker": str(product_data.get("maker", "")),
                "actor": list(product_data.get("actor", [])),
                "director": str(product_data.get("director", "")),
                "volume": str(product_data.get("volume", "")),
                "review_count": int(product_data.get("review_count", 0)),
                "review_average": float(product_data.get("review_average", 0.0))
            }

            self.logger.debug(
                "Product information prepared successfully",
                extra={"product_info": product_info}
            )

            return product_info

        except (ValueError, TypeError) as e:
            error_msg = self.config_manager.get_error_message("description", "validation")
            self.logger.error(f"Invalid product data format: {str(e)}")
            raise ProductInfoError(f"{error_msg}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to prepare product info: {str(e)}")
            raise ProductInfoError(f"Failed to prepare product info: {str(e)}")

    def _prepare_character_info(self, character_data: Dict) -> Dict:
        """
        キャラクター情報を整形

        Args:
            character_data: キャラクターデータ

        Returns:
            Dict: 整形されたキャラクター情報

        Raises:
            CharacterInfoError: キャラクター情報の整形失敗
        """
        try:
            self.logger.debug("Preparing character information")

            if not character_data:
                error_msg = self.config_manager.get_error_message("description", "validation")
                raise CharacterInfoError(error_msg)

            character_info = {
                "character_name": str(character_data.get("character_name", "")),
                "original_work": str(character_data.get("original_work", "")),
                "confidence_score": float(character_data.get("confidence_score", 0.0))
            }

            self.logger.debug(
                "Character information prepared successfully",
                extra={"character_info": character_info}
            )

            return character_info

        except (ValueError, TypeError) as e:
            error_msg = self.config_manager.get_error_message("description", "validation")
            self.logger.error(f"Invalid character data format: {str(e)}")
            raise CharacterInfoError(f"{error_msg}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to prepare character info: {str(e)}")
            raise CharacterInfoError(f"Failed to prepare character info: {str(e)}")

    def generate_description(
        self,
        product_data: Dict,
        character_data: Dict,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        商品説明を生成

        Args:
            product_data: 商品データ
            character_data: キャラクターデータ
            requirements: 生成要件

        Returns:
            Dict: 生成された説明

        Raises:
            DescriptionGenerationError: 説明生成失敗
            DescriptionOptimizationError: 説明最適化失敗
        """
        try:
            self.logger.info("Starting description generation")

            # 商品情報とキャラクター情報を整形
            product_info = self._prepare_product_info(product_data)
            character_info = self._prepare_character_info(character_data)

            # デフォルトの生成要件を設定
            if requirements is None:
                requirements = {
                    "max_length": self.description_config["max_length"],
                    "min_length": self.description_config["min_length"],
                    "tone": self.description_config["tone"],
                    "style": self.description_config["style"],
                    "language": self.description_config["language"]
                }

            # 説明を生成
            try:
                self.logger.debug("Generating product description")
                description_result = self.api_client.generate_product_description(
                    product_info,
                    character_info,
                    requirements
                )
                self.logger.debug("Product description generated successfully")
            except GrokApiError as e:
                error_msg = self.config_manager.get_error_message("description", "generation")
                self.logger.error(f"Failed to generate description: {str(e)}")
                raise DescriptionGenerationError(f"{error_msg}: {str(e)}")

            # 説明を最適化
            try:
                self.logger.debug("Optimizing generated description")
                optimized_result = self.api_client.optimize_content(
                    description_result["description"],
                    "product_description",
                    requirements
                )
                self.logger.debug("Description optimization completed")
            except GrokApiError as e:
                error_msg = self.config_manager.get_error_message("description", "optimization")
                self.logger.error(f"Failed to optimize description: {str(e)}")
                raise DescriptionOptimizationError(f"{error_msg}: {str(e)}")

            self.logger.info("Description generation completed successfully")

            return {
                "description": optimized_result["optimized_content"],
                "catch_copy": description_result["catch_copy"],
                "tags": description_result["tags"],
                "improvement_suggestions": optimized_result["improvement_suggestions"]
            }

        except (ProductInfoError, CharacterInfoError) as e:
            error_msg = self.config_manager.get_error_message("description", "validation")
            self.logger.error(f"Input data preparation failed: {str(e)}")
            raise DescriptionGenerationError(f"{error_msg}: {str(e)}")
        except Exception as e:
            error_msg = self.config_manager.get_error_message("description", "generation")
            self.logger.error(f"Description generation failed: {str(e)}")
            raise DescriptionGenerationError(f"{error_msg}: {str(e)}")

    def generate_batch_descriptions(
        self,
        products_data: List[Dict],
        characters_data: List[Dict],
        requirements: Optional[Dict] = None
    ) -> List[Dict]:
        """
        複数の商品説明を一括生成

        Args:
            products_data: 商品データのリスト
            characters_data: キャラクターデータのリスト
            requirements: 生成要件

        Returns:
            List[Dict]: 生成された説明のリスト

        Raises:
            DescriptionGeneratorError: 一括生成失敗
        """
        try:
            batch_size = self.description_config["batch_size"]
            self.logger.info(
                "Starting batch description generation",
                extra={
                    "product_count": len(products_data),
                    "character_count": len(characters_data),
                    "batch_size": batch_size
                }
            )

            if not products_data or not characters_data:
                error_msg = self.config_manager.get_error_message("description", "validation")
                raise DescriptionGeneratorError(error_msg)

            if len(products_data) != len(characters_data):
                error_msg = self.config_manager.get_error_message("description", "validation")
                raise DescriptionGeneratorError(
                    f"{error_msg}: Mismatched data lengths: products={len(products_data)}, "
                    f"characters={len(characters_data)}"
                )

            results = []
            for i, (product_data, character_data) in enumerate(zip(products_data, characters_data), 1):
                try:
                    self.logger.debug(
                        f"Processing item {i}/{len(products_data)}",
                        extra={"item_index": i}
                    )

                    result = self.generate_description(
                        product_data,
                        character_data,
                        requirements
                    )
                    results.append(result)

                except (DescriptionGenerationError, DescriptionOptimizationError) as e:
                    self.logger.warning(
                        f"Failed to generate description for item {i}: {str(e)}",
                        extra={"item_index": i}
                    )
                    # エラーが発生しても処理を継続
                    results.append({
                        "description": "",
                        "catch_copy": "",
                        "tags": [],
                        "improvement_suggestions": [],
                        "error": str(e)
                    })

            self.logger.info(
                "Batch description generation completed",
                extra={
                    "success_count": len([r for r in results if "error" not in r]),
                    "error_count": len([r for r in results if "error" in r])
                }
            )

            return results

        except Exception as e:
            error_msg = self.config_manager.get_error_message("description", "generation")
            self.logger.error(f"Batch description generation failed: {str(e)}")
            raise DescriptionGeneratorError(f"{error_msg}: {str(e)}") 