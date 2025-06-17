import os
import json
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, List, Optional
from .error_logger import ErrorLogger

class Monitor:
    """システムモニタリングクラス"""
    
    def __init__(self, config_path: str = "config/monitoring.json"):
        self.config_path = config_path
        self.error_logger = ErrorLogger()
        self.logger = logging.getLogger(__name__)
        self.debug_mode = False  # デバッグモードのフラグを追加
        
        # モニタリング設定の読み込み
        self.config = self._load_config()
        
        # メトリクスの保存用
        self.metrics: Dict[str, List[Dict]] = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
    
    def _load_config(self) -> Dict:
        """モニタリング設定を読み込む"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return self._create_default_config()
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] _load_config: {str(e)}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """デフォルトのモニタリング設定を作成"""
        default_config = {
            "interval": 60,  # モニタリング間隔（秒）
            "metrics": {
                "cpu": True,
                "memory": True,
                "disk": True,
                "network": True
            },
            "thresholds": {
                "cpu_percent": 80,
                "memory_percent": 80,
                "disk_percent": 80
            },
            "alert": {
                "enabled": True,
                "email": "",
                "slack_webhook": ""
            }
        }
        
        # 設定ファイルの保存
        config_dir = os.path.dirname(self.config_path)
        if config_dir:  # パスにディレクトリが含まれる場合
            os.makedirs(config_dir, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        return default_config
    
    def collect_metrics(self) -> Dict:
        """システムメトリクスを収集"""
        try:
            metrics = {}
            
            if self.config["metrics"]["cpu"]:
                metrics["cpu"] = {
                    "percent": psutil.cpu_percent(interval=1),
                    "count": psutil.cpu_count(),
                    "timestamp": datetime.now().isoformat()
                }
            
            if self.config["metrics"]["memory"]:
                memory = psutil.virtual_memory()
                metrics["memory"] = {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "timestamp": datetime.now().isoformat()
                }
            
            if self.config["metrics"]["disk"]:
                disk = psutil.disk_usage('/')
                metrics["disk"] = {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                    "timestamp": datetime.now().isoformat()
                }
            
            if self.config["metrics"]["network"]:
                net_io = psutil.net_io_counters()
                metrics["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "timestamp": datetime.now().isoformat()
                }
            
            # メトリクスの保存
            for key, value in metrics.items():
                self.metrics[key].append(value)
                # 最新の100件のみ保持
                if len(self.metrics[key]) > 100:
                    self.metrics[key].pop(0)
            
            return metrics
        
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] collect_metrics: {str(e)}")
            return {}
    
    def check_thresholds(self, metrics: Dict) -> List[str]:
        """閾値を超えたメトリクスをチェック"""
        alerts = []
        
        try:
            thresholds = self.config["thresholds"]
            
            if "cpu" in metrics and metrics["cpu"]["percent"] > thresholds["cpu_percent"]:
                alerts.append(f"CPU使用率が閾値を超えています: {metrics['cpu']['percent']}%")
            
            if "memory" in metrics and metrics["memory"]["percent"] > thresholds["memory_percent"]:
                alerts.append(f"メモリ使用率が閾値を超えています: {metrics['memory']['percent']}%")
            
            if "disk" in metrics and metrics["disk"]["percent"] > thresholds["disk_percent"]:
                alerts.append(f"ディスク使用率が閾値を超えています: {metrics['disk']['percent']}%")
        
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] check_thresholds: {str(e)}")
        
        return alerts
    
    def send_alert(self, alerts: List[str]) -> bool:
        """アラートを送信"""
        if not alerts or not self.config["alert"]["enabled"]:
            return False
        
        try:
            message = "\n".join(alerts)
            self.logger.warning(f"アラート: {message}")
            
            # TODO: メールやSlackへの通知実装
            
            return True
        
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] send_alert: {str(e)}")
            return False
    
    def get_metrics_history(self, metric_type: str, limit: int = 10) -> List[Dict]:
        """メトリクスの履歴を取得"""
        try:
            if metric_type in self.metrics:
                return self.metrics[metric_type][-limit:]
            return []
        
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] get_metrics_history: {str(e)}")
            return []
    
    def update_config(self, new_config: Dict) -> bool:
        """モニタリング設定を更新"""
        try:
            self.config.update(new_config)
            config_dir = os.path.dirname(self.config_path)
            if config_dir:  # パスにディレクトリが含まれる場合
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        
        except Exception as e:
            self.error_logger.log_error(f"[Monitor] update_config: {str(e)}")
            return False
    
    def set_debug_mode(self, enabled: bool = True) -> None:
        """デバッグモードを設定する
        
        Args:
            enabled: デバッグモードを有効にするかどうか
        """
        self.debug_mode = enabled
        if enabled:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO) 