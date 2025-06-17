from typing import Dict, List

def generate_wp_article(product: Dict, keyword_info: Dict) -> Dict:
    """
    FANZA商品情報とキーワード情報からWordPress投稿用の記事データを生成する。
    戻り値: {
        'title': str,
        'content': str,
        'categories': List[str],
        'tags': List[str],
        'eyecatch': str (画像URL),
        'custom_taxonomies': Dict[str, str]
    }
    """
    # タイトル
    title = f"{product.get('title', '')}【{keyword_info.get('character_name', '')}】"
    # アイキャッチ
    main_image = product.get('sampleImageURL', {}).get('sample_l', [''])[0] if product.get('sampleImageURL', {}).get('sample_l') else ''
    # サンプル画像（全て縦並び・クリック不可）
    sample_imgs = product.get('sampleImageURL', {}).get('sample_l', [])
    sample_imgs_html = "\n".join([
        f"<img src=\"{img}\" alt=\"{product.get('title', '')} サンプル画像\" loading=\"lazy\" style=\"display:block;margin-bottom:16px;pointer-events:none;\">"
        for img in sample_imgs
    ])
    # 作品情報テーブル
    table_html = f"""
    <table class="swell-block-table">
      <tr><th>サークル名</th><td>{product.get('maker', [''])[0] if isinstance(product.get('maker'), list) else product.get('maker', '')}</td></tr>
      <tr><th>作者名</th><td>{', '.join([a['name'] for a in product.get('iteminfo', {}).get('author', [])]) if 'iteminfo' in product and 'author' in product['iteminfo'] else ''}</td></tr>
      <tr><th>原作名</th><td>{product.get('iteminfo', {}).get('original', [''])[0] if 'iteminfo' in product and 'original' in product['iteminfo'] else ''}</td></tr>
      <tr><th>キャラ名</th><td>{keyword_info.get('character_name', '')}</td></tr>
      <tr><th>作品形式</th><td>{product.get('iteminfo', {}).get('product', [''])[0] if 'iteminfo' in product and 'product' in product['iteminfo'] else ''}</td></tr>
      <tr><th>ページ数</th><td>{product.get('iteminfo', {}).get('page_count', [''])[0] if 'iteminfo' in product and 'page_count' in product['iteminfo'] else ''}</td></tr>
    </table>
    """
    # リード文
    lead = product.get('catch_copy', '') or product.get('description', '')[:80]
    # 紹介文
    intro = product.get('description', '')
    # アフィリエイトボタン
    affiliate_url = product.get('affiliateURL', product.get('URL', ''))
    button_html = f'<a href="{affiliate_url}" class="swell-block-button" style="background:#ff6600;color:#fff;padding:12px 24px;border-radius:6px;display:inline-block;text-align:center;font-weight:bold;" rel="nofollow noopener" target="_blank">FANZAでこの作品をチェックする</a>'
    # 無料で読める？
    free_html = '<div class="swell-block-group"><h2>無料で読める？</h2><p>本作品は有料コンテンツです。FANZA公式サイトで試し読みが可能な場合もあります。</p></div>'
    # 関連記事（SWELLのショートコード例）
    related_html = '[swell_related_posts count="4" criteria="category,tag"]'
    # 本文構成
    content = f"""
    <h1>{title}</h1>
    <div class="swell-eyecatch">{f'<img src="{main_image}" alt="アイキャッチ" loading="lazy">' if main_image else ''}</div>
    <div class="swell-lead">{lead}</div>
    {table_html}
    <div class="swell-sample-images">{sample_imgs_html}</div>
    <div class="swell-intro">{intro}</div>
    <div class="swell-affiliate">{button_html}</div>
    {free_html}
    {related_html}
    """
    # カテゴリー・タグ
    categories = [g['name'] for g in product.get('iteminfo', {}).get('genre', [])] if 'iteminfo' in product and 'genre' in product['iteminfo'] else []
    tags = [product.get('maker', [''])[0] if isinstance(product.get('maker'), list) else product.get('maker', '')]
    # カスタムタクソノミー
    custom_taxonomies = {
        'original_work': product.get('iteminfo', {}).get('original', [''])[0] if 'iteminfo' in product and 'original' in product['iteminfo'] else '',
        'character_name': keyword_info.get('character_name', ''),
        'circle_name': product.get('maker', [''])[0] if isinstance(product.get('maker'), list) else product.get('maker', ''),
        'product_format': product.get('iteminfo', {}).get('product', [''])[0] if 'iteminfo' in product and 'product' in product['iteminfo'] else ''
    }
    return {
        'title': title,
        'content': content,
        'categories': categories,
        'tags': tags,
        'eyecatch': main_image,
        'custom_taxonomies': custom_taxonomies
    } 