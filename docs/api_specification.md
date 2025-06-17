# API仕様書

## 目次
1. [FANZA Data Retriever](#fanza-data-retriever)
2. [WordPress Poster](#wordpress-poster)
3. [Scheduler Orchestrator](#scheduler-orchestrator)
4. [Error Logger](#error-logger)
5. [Config Manager](#config-manager)

## FANZA Data Retriever

### クラス: `FANZA_Data_Retriever`

FANZAからの商品情報取得を担当するクラス。

#### 初期化
```python
retriever = FANZA_Data_Retriever()
```

#### メソッド

##### `get_product_info(product_id: str) -> dict`
商品IDに基づいて商品情報を取得します。

**パラメータ:**
- `product_id` (str): 商品ID

**戻り値:**
- `dict`: 商品情報（タイトル、説明、画像URL等）

**使用例:**
```python
product_info = await retriever.get_product_info("abc123")
```

##### `get_latest_products(limit: int = 10) -> List[dict]`
最新の商品情報を取得します。

**パラメータ:**
- `limit` (int): 取得する商品数（デフォルト: 10）

**戻り値:**
- `List[dict]`: 商品情報のリスト

**使用例:**
```python
latest_products = await retriever.get_latest_products(5)
```

## WordPress Poster

### クラス: `WordPress_Poster`

WordPressへの記事投稿を管理するクラス。

#### 初期化
```python
poster = WordPress_Poster()
```

#### メソッド

##### `post_article(article_data: dict) -> int`
記事を投稿します。

**パラメータ:**
- `article_data` (dict): 記事データ
  ```python
  {
      'title': str,          # 記事タイトル
      'content': str,        # 記事本文
      'featured_image': str, # アイキャッチ画像URL
      'gallery_images': List[str], # ギャラリー画像URLリスト
      'categories': List[str],     # カテゴリーリスト
      'tags': List[str]           # タグリスト
  }
  ```

**戻り値:**
- `int`: 投稿された記事のID

**使用例:**
```python
article_id = await poster.post_article({
    'title': 'テスト記事',
    'content': 'テスト本文',
    'featured_image': 'http://example.com/image.jpg',
    'categories': ['カテゴリー1'],
    'tags': ['タグ1', 'タグ2']
})
```

##### `update_article_status(post_id: int, status: str) -> bool`
記事のステータスを更新します。

**パラメータ:**
- `post_id` (int): 記事ID
- `status` (str): 新しいステータス（'publish', 'draft', 'private'等）

**戻り値:**
- `bool`: 更新の成功/失敗

**使用例:**
```python
success = await poster.update_article_status(123, 'publish')
```

## Scheduler Orchestrator

### クラス: `Scheduler_Orchestrator`

記事のスケジュール投稿を管理するクラス。

#### 初期化
```python
scheduler = Scheduler_Orchestrator()
```

#### メソッド

##### `schedule_articles(product_ids: List[str]) -> None`
記事のスケジュール投稿を行います。

**パラメータ:**
- `product_ids` (List[str]): 商品IDのリスト

**使用例:**
```python
await scheduler.schedule_articles(['id1', 'id2', 'id3'])
```

## Error Logger

### クラス: `Error_Logger`

エラー情報をログファイルに記録するクラス。

#### 初期化
```python
logger = Error_Logger()
```

#### メソッド

##### `log_error(message: str, module: str = None, function: str = None, additional_info: dict = None) -> None`
エラー情報を記録します。

**パラメータ:**
- `message` (str): エラーメッセージ
- `module` (str, optional): エラーが発生したモジュール名
- `function` (str, optional): エラーが発生した関数名
- `additional_info` (dict, optional): 追加情報

**使用例:**
```python
logger.log_error(
    "API request failed",
    module="FANZA_Data_Retriever",
    function="get_product_info",
    additional_info={"product_id": "abc123"}
)
```

##### `log_warning(message: str, module: str = None, function: str = None, additional_info: dict = None) -> None`
警告情報を記録します。

**パラメータ:**
- `message` (str): 警告メッセージ
- `module` (str, optional): 警告が発生したモジュール名
- `function` (str, optional): 警告が発生した関数名
- `additional_info` (dict, optional): 追加情報

**使用例:**
```python
logger.log_warning(
    "Rate limit approaching",
    module="FANZA_Data_Retriever",
    additional_info={"current_requests": 95}
)
```

## Config Manager

### クラス: `Config_Manager`

設定値を管理するクラス。

#### 初期化
```python
config = Config_Manager()
```

#### メソッド

##### `get(key: str, default: Any = None) -> Any`
設定値を取得します。

**パラメータ:**
- `key` (str): 設定キー
- `default` (Any, optional): デフォルト値

**戻り値:**
- `Any`: 設定値

**使用例:**
```python
api_key = config.get('FANZA_API_KEY')
```

##### `set(key: str, value: Any) -> None`
設定値を設定します。

**パラメータ:**
- `key` (str): 設定キー
- `value` (Any): 設定値

**使用例:**
```python
config.set('MAX_RETRIES', 3)
```

##### `update(updates: dict) -> None`
複数の設定値を一括更新します。

**パラメータ:**
- `updates` (dict): 更新する設定値の辞書

**使用例:**
```python
config.update({
    'MAX_RETRIES': 3,
    'TIMEOUT': 30
})
```

##### `reset() -> None`
設定値をデフォルトに戻します。

**使用例:**
```python
config.reset()
``` 