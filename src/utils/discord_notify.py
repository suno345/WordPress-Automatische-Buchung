import os
import aiohttp
import asyncio
from dotenv import load_dotenv

# API.envを明示的にロード
load_dotenv(dotenv_path="同人WordPress自動投稿/API.env")
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')

async def send_discord_error(message: str):
    """
    指定したDiscordチャンネルにエラーメッセージを送信する
    """
    if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
        print("[Discord通知エラー] トークンまたはチャンネルIDが未設定です")
        return
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "content": f"🚨 エラー通知\n{message}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status != 200 and resp.status != 201:
                print(f"[Discord通知エラー] ステータス: {resp.status}")
                print(await resp.text()) 