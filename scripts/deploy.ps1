# エラーが発生したら即座に終了
$ErrorActionPreference = "Stop"

# 色の定義
$Host.UI.RawUI.ForegroundColor = "Green"
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message"
}

$Host.UI.RawUI.ForegroundColor = "Yellow"
function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message"
}

$Host.UI.RawUI.ForegroundColor = "Red"
function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message"
}

# 環境変数の読み込み
if (Test-Path .env) {
    Write-Info "環境変数を読み込み中..."
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            Set-Item -Path "env:$name" -Value $value
        }
    }
} else {
    Write-Error ".envファイルが見つかりません"
    exit 1
}

# 必要なディレクトリの作成
Write-Info "必要なディレクトリを作成中..."
New-Item -ItemType Directory -Force -Path cache, logs | Out-Null

# 仮想環境の確認と作成
if (-not (Test-Path venv)) {
    Write-Info "仮想環境を作成中..."
    python -m venv venv
}

# 仮想環境の有効化
Write-Info "仮想環境を有効化中..."
.\venv\Scripts\Activate.ps1

# 依存パッケージのインストール
Write-Info "依存パッケージをインストール中..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# 設定ファイルの確認
if (-not (Test-Path config.json)) {
    Write-Warning "config.jsonが見つかりません。デフォルト設定を作成します..."
    python -m src.config.config_manager --init
}

# テストの実行
Write-Info "テストを実行中..."
python -m unittest discover tests

# キャッシュのクリーンアップ
Write-Info "古いキャッシュをクリーンアップ中..."
python -m src.utils.cache_cleaner --days 7

# ログのクリーンアップ
Write-Info "古いログをクリーンアップ中..."
python -m src.utils.log_cleaner --days 30

# バックアップの作成
Write-Info "バックアップを作成中..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup_dir = "backups\backup_$timestamp"
New-Item -ItemType Directory -Force -Path $backup_dir | Out-Null

# 設定ファイルのバックアップ
Copy-Item .env "$backup_dir\.env"
Copy-Item config.json "$backup_dir\config.json"

# キャッシュのバックアップ
if (Test-Path cache) {
    Compress-Archive -Path cache\* -DestinationPath "$backup_dir\cache.zip"
}

# ログのバックアップ
if (Test-Path logs) {
    Compress-Archive -Path logs\* -DestinationPath "$backup_dir\logs.zip"
}

# デプロイ完了
Write-Info "デプロイが完了しました！"
Write-Info "バックアップは $backup_dir に保存されました"

# 仮想環境の無効化
deactivate 