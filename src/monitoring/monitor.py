import os
import psutil
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp
import asyncio
from pathlib import Path

class SystemMonitor:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.metrics_dir = Path("metrics")
        self.metrics_dir.mkdir(exist_ok=True)
        self.api_metrics: Dict[str, Dict] = {
            "fanza": {"requests": 0, "errors": 0, "last_request": None},
            "wordpress": {"requests": 0, "errors": 0, "last_request": None},
            "grok": {"requests": 0, "errors": 0, "last_request": None}
        }
        self.start_time = time.time()

    async def collect_metrics(self) -> Dict:
        """システムメトリクスを収集"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": self._get_network_io()
            },
            "application": {
                "uptime": time.time() - self.start_time,
                "api_metrics": self.api_metrics,
                "cache_size": self._get_cache_size(),
                "log_size": self._get_log_size()
            }
        }
        return metrics

    def _get_network_io(self) -> Dict:
        """ネットワークI/O情報を取得"""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }

    def _get_cache_size(self) -> int:
        """キャッシュディレクトリのサイズを取得"""
        cache_dir = Path("cache")
        if not cache_dir.exists():
            return 0
        return sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())

    def _get_log_size(self) -> int:
        """ログディレクトリのサイズを取得"""
        log_dir = Path("logs")
        if not log_dir.exists():
            return 0
        return sum(f.stat().st_size for f in log_dir.rglob("*") if f.is_file())

    def record_api_request(self, api_name: str, success: bool = True):
        """APIリクエストを記録"""
        if api_name in self.api_metrics:
            self.api_metrics[api_name]["requests"] += 1
            if not success:
                self.api_metrics[api_name]["errors"] += 1
            self.api_metrics[api_name]["last_request"] = datetime.now().isoformat()

    async def save_metrics(self, metrics: Dict):
        """メトリクスをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.metrics_dir / f"metrics_{timestamp}.json"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8086/write?db=monitoring",
                data=json.dumps(metrics)
            ) as response:
                if response.status == 204:
                    with open(metrics_file, "w") as f:
                        json.dump(metrics, f, indent=2)

    async def check_alerts(self, metrics: Dict) -> List[str]:
        """アラート条件をチェック"""
        alerts = []
        
        # CPU使用率のチェック
        if metrics["system"]["cpu_percent"] > 80:
            alerts.append(f"CPU使用率が高い: {metrics['system']['cpu_percent']}%")
        
        # メモリ使用率のチェック
        if metrics["system"]["memory_percent"] > 80:
            alerts.append(f"メモリ使用率が高い: {metrics['system']['memory_percent']}%")
        
        # ディスク使用率のチェック
        if metrics["system"]["disk_usage"] > 80:
            alerts.append(f"ディスク使用率が高い: {metrics['system']['disk_usage']}%")
        
        # APIエラー率のチェック
        for api_name, api_metrics in metrics["application"]["api_metrics"].items():
            if api_metrics["requests"] > 0:
                error_rate = api_metrics["errors"] / api_metrics["requests"]
                if error_rate > 0.1:  # 10%以上のエラー率
                    alerts.append(f"{api_name}のエラー率が高い: {error_rate:.1%}")
        
        return alerts

    async def start_monitoring(self, interval: int = 60):
        """モニタリングを開始"""
        while True:
            try:
                metrics = await self.collect_metrics()
                await self.save_metrics(metrics)
                
                alerts = await self.check_alerts(metrics)
                if alerts:
                    print("\n=== アラート ===")
                    for alert in alerts:
                        print(f"- {alert}")
                    print("==============\n")
                
                await asyncio.sleep(interval)
            except Exception as e:
                print(f"モニタリングエラー: {e}")
                await asyncio.sleep(interval)

    def get_api_metrics(self) -> Dict:
        """APIメトリクスを取得"""
        return self.api_metrics

    def get_system_metrics(self) -> Dict:
        """システムメトリクスを取得"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": self._get_network_io()
        } 