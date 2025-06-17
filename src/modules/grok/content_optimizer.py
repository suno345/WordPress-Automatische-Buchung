from typing import Dict, List, Optional, Union
from .api_client import GrokApiClient, GrokApiError
from ...utils.logger import Logger
from ...utils.config_manager import ConfigManager

class ContentOptimizerError(Exception):
    """ContentOptimizerのエラー基底クラス"""
    pass

class RequirementsError(ContentOptimizerError):
    """要件エラー"""
    pass

class ContentValidationError(ContentOptimizerError):
    """コンテンツ検証エラー"""
    pass

class OptimizationError(ContentOptimizerError):
    """最適化エラー"""
    pass

class QualityAnalysisError(ContentOptimizerError):
    """品質分析エラー"""
    pass

class ContentOptimizer:
    """コンテンツ最適化クラス"""

    def __init__(self):
        """初期化"""
        self.logger = Logger()
        self.config_manager = ConfigManager()
        self.optimization_config = self.config_manager.get_optimization_config()
        self.api_config = self.config_manager.get_api_config()

        try:
            self.api_client = GrokApiClient()
            self.logger.info("ContentOptimizer initialized successfully")
        except GrokApiError as e:
            error_msg = self.config_manager.get_error_message("api", "authentication")
            self.logger.error(f"Failed to initialize API client: {str(e)}")
            raise ContentOptimizerError(f"{error_msg}: {str(e)}")

    def _prepare_optimization_requirements(
        self,
        content_type: str,
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        最適化要件を準備

        Args:
            content_type: コンテンツタイプ
            requirements: 追加要件

        Returns:
            Dict: 最適化要件

        Raises:
            RequirementsError: 要件準備失敗
        """
        try:
            self.logger.debug(
                "Preparing optimization requirements",
                extra={"content_type": content_type}
            )

            # デフォルトの要件を取得
            default_requirements = self.optimization_config["content_types"].get(
                content_type,
                self.optimization_config["content_types"]["product_description"]
            )

            # 追加要件で上書き
            if requirements:
                default_requirements.update(requirements)

            self.logger.debug(
                "Optimization requirements prepared successfully",
                extra={"requirements": default_requirements}
            )

            return default_requirements

        except Exception as e:
            error_msg = self.config_manager.get_error_message("optimization", "validation")
            self.logger.error(f"Failed to prepare optimization requirements: {str(e)}")
            raise RequirementsError(f"{error_msg}: {str(e)}")

    def _validate_content(self, content: str) -> None:
        """
        コンテンツを検証

        Args:
            content: 検証するコンテンツ

        Raises:
            ContentValidationError: 検証失敗
        """
        try:
            self.logger.debug("Validating content")

            if not content or not isinstance(content, str):
                error_msg = self.config_manager.get_error_message("optimization", "validation")
                raise ContentValidationError(error_msg)

            if not content.strip():
                error_msg = self.config_manager.get_error_message("optimization", "validation")
                raise ContentValidationError(error_msg)

            self.logger.debug("Content validation successful")

        except ContentValidationError as e:
            self.logger.error(f"Content validation failed: {str(e)}")
            raise
        except Exception as e:
            error_msg = self.config_manager.get_error_message("optimization", "validation")
            self.logger.error(f"Content validation failed: {str(e)}")
            raise ContentValidationError(f"{error_msg}: {str(e)}")

    def optimize_content(
        self,
        content: str,
        content_type: str = "product_description",
        requirements: Optional[Dict] = None
    ) -> Dict:
        """
        コンテンツを最適化

        Args:
            content: 最適化するコンテンツ
            content_type: コンテンツタイプ
            requirements: 追加要件

        Returns:
            Dict: 最適化結果

        Raises:
            OptimizationError: 最適化失敗
        """
        try:
            self.logger.info(
                "Starting content optimization",
                extra={"content_type": content_type}
            )

            # コンテンツの検証
            self._validate_content(content)

            # 最適化要件の準備
            optimization_requirements = self._prepare_optimization_requirements(
                content_type,
                requirements
            )

            # コンテンツの最適化
            try:
                self.logger.debug("Optimizing content")
                optimized_result = self.api_client.optimize_content(
                    content,
                    content_type,
                    optimization_requirements
                )
                self.logger.debug("Content optimization completed")
            except GrokApiError as e:
                error_msg = self.config_manager.get_error_message("optimization", "content")
                self.logger.error(f"Failed to optimize content: {str(e)}")
                raise OptimizationError(f"{error_msg}: {str(e)}")

            self.logger.info("Content optimization completed successfully")

            return optimized_result

        except (ContentValidationError, RequirementsError) as e:
            error_msg = self.config_manager.get_error_message("optimization", "validation")
            self.logger.error(f"Content optimization failed: {str(e)}")
            raise OptimizationError(f"{error_msg}: {str(e)}")
        except Exception as e:
            error_msg = self.config_manager.get_error_message("optimization", "content")
            self.logger.error(f"Content optimization failed: {str(e)}")
            raise OptimizationError(f"{error_msg}: {str(e)}")

    def optimize_batch_contents(
        self,
        contents: List[Dict],
        content_type: str = "product_description",
        requirements: Optional[Dict] = None
    ) -> List[Dict]:
        """
        複数のコンテンツを一括最適化

        Args:
            contents: 最適化するコンテンツのリスト
            content_type: コンテンツタイプ
            requirements: 追加要件

        Returns:
            List[Dict]: 最適化結果のリスト

        Raises:
            OptimizationError: 一括最適化失敗
        """
        try:
            self.logger.info(
                "Starting batch content optimization",
                extra={
                    "content_count": len(contents),
                    "content_type": content_type
                }
            )

            if not contents:
                error_msg = self.config_manager.get_error_message("optimization", "validation")
                raise OptimizationError(error_msg)

            results = []
            for i, content_data in enumerate(contents, 1):
                try:
                    self.logger.debug(
                        f"Processing content {i}/{len(contents)}",
                        extra={"item_index": i}
                    )

                    result = self.optimize_content(
                        content_data["content"],
                        content_type,
                        requirements
                    )
                    results.append(result)

                except OptimizationError as e:
                    self.logger.warning(
                        f"Failed to optimize content {i}: {str(e)}",
                        extra={"item_index": i}
                    )
                    # エラーが発生しても処理を継続
                    results.append({
                        "optimized_content": content_data["content"],
                        "improvement_suggestions": [],
                        "error": str(e)
                    })

            self.logger.info(
                "Batch content optimization completed",
                extra={
                    "success_count": len([r for r in results if "error" not in r]),
                    "error_count": len([r for r in results if "error" in r])
                }
            )

            return results

        except Exception as e:
            error_msg = self.config_manager.get_error_message("optimization", "content")
            self.logger.error(f"Batch content optimization failed: {str(e)}")
            raise OptimizationError(f"{error_msg}: {str(e)}")

    def analyze_content_quality(
        self,
        content: str,
        metrics: Optional[List[str]] = None
    ) -> Dict:
        """
        コンテンツの品質を分析

        Args:
            content: 分析するコンテンツ
            metrics: 分析するメトリクスのリスト

        Returns:
            Dict: 品質分析結果

        Raises:
            QualityAnalysisError: 品質分析失敗
        """
        try:
            self.logger.info("Starting content quality analysis")

            # コンテンツの検証
            self._validate_content(content)

            # デフォルトのメトリクスを設定
            if metrics is None:
                metrics = list(self.optimization_config["quality_metrics"].keys())

            # 品質分析
            try:
                self.logger.debug(
                    "Analyzing content quality",
                    extra={"metrics": metrics}
                )
                quality_result = self.api_client.analyze_content_quality(
                    content,
                    metrics
                )
                self.logger.debug("Content quality analysis completed")
            except GrokApiError as e:
                error_msg = self.config_manager.get_error_message("optimization", "quality")
                self.logger.error(f"Failed to analyze content quality: {str(e)}")
                raise QualityAnalysisError(f"{error_msg}: {str(e)}")

            self.logger.info("Content quality analysis completed successfully")

            return quality_result

        except ContentValidationError as e:
            error_msg = self.config_manager.get_error_message("optimization", "validation")
            self.logger.error(f"Content quality analysis failed: {str(e)}")
            raise QualityAnalysisError(f"{error_msg}: {str(e)}")
        except Exception as e:
            error_msg = self.config_manager.get_error_message("optimization", "quality")
            self.logger.error(f"Content quality analysis failed: {str(e)}")
            raise QualityAnalysisError(f"{error_msg}: {str(e)}") 