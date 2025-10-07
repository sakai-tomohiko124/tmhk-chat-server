
import requests
from bs4 import BeautifulSoup

def get_weather_info():
	"""気象庁から東京の天気予報を取得"""
	try:
		url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
			'Accept': 'application/json, text/plain, */*',
			'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
			'Referer': 'https://www.jma.go.jp/',
			'Cache-Control': 'no-cache'
		}
		response = requests.get(url, headers=headers, timeout=15)
		response.raise_for_status()
		if response.status_code != 200:
			raise Exception(f"HTTP {response.status_code}")
		data = response.json()
		if not data or len(data) == 0:
			raise Exception("データが空です")
		forecast = data[0]['timeSeries'][0]
		today_weather = forecast['areas'][0]['weathers'][0]
		max_temp = "情報なし"
		min_temp = "情報なし"
		try:
			if len(data[0]['timeSeries']) > 2:
				temp_data = data[0]['timeSeries'][2]['areas'][0]
				if 'temps' in temp_data and temp_data['temps']:
					max_temp = temp_data['temps'][0] if temp_data['temps'][0] else "情報なし"
					min_temp = temp_data['temps'][1] if len(temp_data['temps']) > 1 and temp_data['temps'][1] else "情報なし"
		except:
			pass
		return {
			'status': 'success',
			'weather': today_weather,
			'max_temp': max_temp,
			'min_temp': min_temp,
			'area': '東京'
		}
	except Exception as e:
		print(f"天気情報取得エラー: {str(e)}")
		return {
			'status': 'error',
			'message': '未実装'
		}

def get_train_delay_info():
	"""Yahoo!乗換案内から関東地方の電車遅延情報を取得"""
	try:
		url = "https://transit.yahoo.co.jp/diainfo/area/4"
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
			'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
			'Accept-Encoding': 'gzip, deflate, br',
			'Referer': 'https://transit.yahoo.co.jp/',
			'Connection': 'keep-alive',
			'Upgrade-Insecure-Requests': '1',
			'Cache-Control': 'no-cache'
		}
		response = requests.get(url, headers=headers, timeout=15)
		response.raise_for_status()
		if response.status_code != 200:
			raise Exception(f"HTTP {response.status_code}")
		soup = BeautifulSoup(response.content, 'html.parser')
		delay_info = []
		selectors_to_try = [
			'li.trouble',
			'.trouble',
			'.diainfo-trouble',
			'.lineinfo',
			'tr.trouble'
		]
		for selector in selectors_to_try:
			trouble_elements = soup.select(selector)
			if trouble_elements:
				for item in trouble_elements[:5]:
					line_link = item.find('a')
					if line_link:
						line_name = line_link.get_text(strip=True)
						if line_name and '線' in line_name:
							delay_info.append({
								'line': line_name,
								'status': '遅延'
							})
				break
		if not delay_info:
			line_links = soup.find_all('a', href=lambda x: x and 'diainfo' in str(x))
			for item in line_links[:3]:
				line_name = item.get_text(strip=True)
				if line_name and '線' in line_name:
					delay_info.append({
						'line': line_name,
						'status': '平常運転'
					})
		if not delay_info:
			raise Exception("遅延情報を取得できませんでした")
		return {
			'status': 'success',
			'delays': delay_info
		}
	except Exception as e:
		print(f"電車遅延情報取得エラー: {str(e)}")
		return {
			'status': 'error',
			'message': '未実装'
		}
