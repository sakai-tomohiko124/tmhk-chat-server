import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Any

class ExternalDataService:
    def __init__(self):
        self.jma_base_url = "https://www.jma.go.jp/bosai/forecast/data/forecast"
        self.train_info_url = "https://tetsudo.rti-giken.jp/free/delay.json"
        
    async def get_weather_forecast(self, area_code: str = "130000") -> Dict[str, Any]:
        """気象庁APIから天気予報データを取得"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.jma_base_url}/{area_code}.json"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather_data(data)
                    return {"error": f"天気予報データの取得に失敗しました (status: {response.status})"}
        except asyncio.TimeoutError:
            return {"error": "天気予報APIがタイムアウトしました"}
        except Exception as e:
            print(f"Weather forecast error: {e}")
            return {"error": "天気予報の取得中にエラーが発生しました"}

    def _parse_weather_data(self, data: List[Dict]) -> Dict[str, Any]:
        """天気予報データをパース"""
        try:
            forecast = data[0]['timeSeries'][0]
            area_data = forecast['areas'][0]
            
            return {
                'area': area_data['area']['name'],
                'weather': area_data['weathers'][0] if 'weathers' in area_data else '情報なし',
                'updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Weather parsing error: {e}")
            return {"error": "天気データの解析に失敗しました"}

    async def get_train_status(self) -> List[Dict[str, Any]]:
        """鉄道運行情報を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.train_info_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{
                            'company': item.get('company', '不明'),
                            'name': item.get('name', '不明'),
                            'status': item.get('status', '情報なし'),
                            'updated': datetime.fromtimestamp(item.get('lastupdate', 0)).isoformat()
                        } for item in data]
                    return [{"error": f"運行情報の取得に失敗しました (status: {response.status})"}]
        except asyncio.TimeoutError:
            return [{"error": "運行情報APIがタイムアウトしました"}]
        except Exception as e:
            print(f"Train status error: {e}")
            return [{"error": "運行情報の取得中にエラーが発生しました"}]

    async def update_all_data(self) -> Dict[str, Any]:
        """全てのデータを更新"""
        weather = await self.get_weather_forecast()
        trains = await self.get_train_status()

        return {
            'weather': weather,
            'trains': trains,
            'timestamp': datetime.now().isoformat()
        }
