import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from typing import Dict, List, Any

class ExternalDataService:
    def __init__(self):
        self.jma_base_url = "https://www.jma.go.jp/bosai/forecast/data/forecast"
        self.train_info_url = "https://tetsudo.rti-giken.jp/free/delay.json"
        self.j_alert_url = "https://www.data.jma.go.jp/developer/xml/feed/extra.xml"
        
        # APIキーの設定
        self.jma_api_key = os.getenv('JMA_API_KEY')
        
    async def get_weather_forecast(self, area_code: str = "130000") -> Dict[str, Any]:
        """気象庁APIから天気予報データを取得"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.jma_base_url}/{area_code}.json"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather_data(data)
                    return {"error": "天気予報データの取得に失敗しました"}
        except Exception as e:
            print(f"Weather forecast error: {e}")
            return {"error": "天気予報の取得中にエラーが発生しました"}

    def _parse_weather_data(self, data: List[Dict]) -> Dict[str, Any]:
        """天気予報データをパース"""
        try:
            forecast = data[0]['timeSeries'][0]
            return {
                'area': forecast['areas'][0]['area']['name'],
                'weather': forecast['areas'][0]['weathers'][0],
                'temperature': {
                    'min': forecast['areas'][0].get('temps', ['--', '--'])[0],
                    'max': forecast['areas'][0].get('temps', ['--', '--'])[1]
                },
                'updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Weather parsing error: {e}")
            return {"error": "天気データの解析に失敗しました"}

    async def get_train_status(self) -> List[Dict[str, Any]]:
        """鉄道運行情報を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.train_info_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{
                            'company': item['company'],
                            'name': item['name'],
                            'status': item['status'],
                            'updated': datetime.fromtimestamp(item['lastupdate']).isoformat()
                        } for item in data]
                    return [{"error": "運行情報の取得に失敗しました"}]
        except Exception as e:
            print(f"Train status error: {e}")
            return [{"error": "運行情報の取得中にエラーが発生しました"}]

    async def get_disaster_alerts(self) -> List[Dict[str, Any]]:
        """災害情報を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.j_alert_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'xml')
                        entries = soup.find_all('entry')
                        return [{
                            'title': entry.title.text if entry.title else 'Unknown',
                            'content': entry.content.text if entry.content else '',
                            'updated': entry.updated.text if entry.updated else '',
                            'area': entry.find('area').text if entry.find('area') else 'Unknown'
                        } for entry in entries[:10]]  # 最大10件まで
                    return [{"error": "災害情報の取得に失敗しました"}]
        except Exception as e:
            print(f"Disaster alert error: {e}")
            return [{"error": "災害情報の取得中にエラーが発生しました"}]

    async def update_all_data(self) -> Dict[str, Any]:
        """全てのデータを更新"""
        weather = await self.get_weather_forecast()
        trains = await self.get_train_status()
        alerts = await self.get_disaster_alerts()

        return {
            'weather': weather,
            'trains': trains,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }

# 定期的なデータ更新処理
async def periodic_data_update(socketio, service: ExternalDataService, interval: int = 300):
    """指定された間隔でデータを定期的に更新"""
    while True:
        try:
            data = await service.update_all_data()
            # WebSocketを通じてクライアントにデータを送信
            socketio.emit('external_data_update', data, broadcast=True)
        except Exception as e:
            print(f"Periodic update error: {e}")
        await asyncio.sleep(interval)  # 5分間隔でデータを更新
