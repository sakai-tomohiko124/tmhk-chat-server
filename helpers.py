
def is_valid_message_content(message):
	"""メッセージ内容が有効かチェック（テキスト、リンク、絵文字のみ許可）"""
	import re
	basic_chars = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u0020-\u007E]'
	emoji_chars = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001f900-\U0001f9ff\U0001f018-\U0001f270]'
	url_pattern = r'https?://[\w\-._~:/?#\[\]@!$&\'()*+,;=%]+'
	allowed_pattern = f'({basic_chars}|{emoji_chars}|{url_pattern})+'
	return re.fullmatch(allowed_pattern, message) is not None
