import os
from typing import Dict, Any
from pathlib import Path

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(__file__).parent.parent.parent

# ログ設定
LOG_CONFIG = {
    "log_dir": ROOT_DIR / "logs",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# API設定
API_CONFIG = {
    "base_url": os.getenv("GROK_API_BASE_URL", "https://api.grok.ai/v1"),
    "api_key": os.getenv("GROK_API_KEY", ""),
    "timeout": 30,  # 秒
    "max_retries": 3,
    "retry_delay": 1,  # 秒
    "rate_limit": {
        "requests_per_minute": 60,
        "burst_limit": 10
    }
}

# 顔検出設定
FACE_DETECTION_CONFIG = {
    "models": {
        "regular_face": "haarcascade_frontalface_default.xml",
        "anime_face": "haarcascade_anime_face.xml"
    },
    "detection_params": {
        "scale_factor": 1.1,
        "min_neighbors": 5,
        "min_size": (30, 30)
    },
    "cropping": {
        "padding": 0.2,  # 顔の大きさに対する割合
        "max_faces": 5,  # 1枚の画像から切り出す最大顔数
        "min_face_size": 100  # 最小顔サイズ（ピクセル）
    }
}

# 説明生成設定
DESCRIPTION_CONFIG = {
    "max_length": 1000,  # 文字数
    "min_length": 100,   # 文字数
    "tone": "professional",  # トーン
    "style": "informative",  # スタイル
    "language": "ja",  # 言語
    "batch_size": 5,  # 一括処理のサイズ
    "quality_threshold": 0.7  # 品質スコアの閾値
}

# コンテンツ最適化設定
OPTIMIZATION_CONFIG = {
    "content_types": {
        "product_description": {
            "max_length": 1000,
            "min_length": 100,
            "required_elements": ["title", "features", "benefits"],
            "tone": "professional"
        },
        "article": {
            "max_length": 2000,
            "min_length": 300,
            "required_elements": ["introduction", "main_content", "conclusion"],
            "tone": "informative"
        },
        "review": {
            "max_length": 500,
            "min_length": 50,
            "required_elements": ["rating", "pros", "cons"],
            "tone": "casual"
        }
    },
    "quality_metrics": {
        "readability": {
            "threshold": 0.7,
            "weight": 0.3
        },
        "engagement": {
            "threshold": 0.6,
            "weight": 0.3
        },
        "seo": {
            "threshold": 0.8,
            "weight": 0.4
        }
    }
}

# エラーメッセージ設定
ERROR_MESSAGES = {
    "api": {
        "authentication": "API認証に失敗しました",
        "rate_limit": "APIレート制限に達しました",
        "timeout": "APIリクエストがタイムアウトしました",
        "validation": "APIリクエストの検証に失敗しました"
    },
    "face_detection": {
        "model_load": "顔検出モデルの読み込みに失敗しました",
        "no_faces": "画像から顔が検出できませんでした",
        "processing": "画像処理中にエラーが発生しました"
    },
    "description": {
        "generation": "説明の生成に失敗しました",
        "optimization": "説明の最適化に失敗しました",
        "validation": "説明の検証に失敗しました"
    },
    "optimization": {
        "content": "コンテンツの最適化に失敗しました",
        "quality": "品質分析に失敗しました",
        "validation": "コンテンツの検証に失敗しました"
    }
}

def get_config() -> Dict[str, Any]:
    """
    設定を取得

    Returns:
        Dict[str, Any]: 設定の辞書
    """
    return {
        "log": LOG_CONFIG,
        "api": API_CONFIG,
        "face_detection": FACE_DETECTION_CONFIG,
        "description": DESCRIPTION_CONFIG,
        "optimization": OPTIMIZATION_CONFIG,
        "error_messages": ERROR_MESSAGES
    } 