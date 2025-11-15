from datetime import datetime
from cryptography.fernet import Fernet
import os

# 暗号化キーの設定
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    print("警告: 暗号化キーが環境変数に設定されていません。一時的なキーを生成します。")
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_message(message: str) -> bytes:
    """メッセージを暗号化する"""
    return cipher_suite.encrypt(message.encode())

def decrypt_message(encrypted_message: bytes) -> str:
    """暗号化されたメッセージを復号化する"""
    try:
        return cipher_suite.decrypt(encrypted_message).decode()
    except Exception as e:
        print(f"復号化エラー: {e}")
        return "[復号化に失敗しました]"

def secure_message_handler(db, message_data, online_users, emit_func):
    """暗号化されたメッセージを処理する"""
    try:
        # メッセージの暗号化
        encrypted_content = encrypt_message(message_data['content'])
        
        # データベースに保存
        db.execute(
            'INSERT INTO private_messages (sender_id, recipient_id, content, is_from_ai) VALUES (?, ?, ?, ?)',
            (message_data['sender_id'], message_data['recipient_id'], encrypted_content, 0)
        )
        db.commit()
        
        # 受信者がオンラインの場合、メッセージを送信
        recipient_id = str(message_data['recipient_id'])
        if recipient_id in online_users:
            decrypted_content = decrypt_message(encrypted_content)
            emit_func('new_message', {
                'sender_id': message_data['sender_id'],
                'content': decrypted_content,
                'timestamp': datetime.now().isoformat()
            }, room=online_users[recipient_id])
            
        return True
    except Exception as e:
        print(f"Error handling secure message: {e}")
        return False

def encrypt_file(file_data: bytes) -> bytes:
    """ファイルデータを暗号化する"""
    return cipher_suite.encrypt(file_data)

def decrypt_file(encrypted_data: bytes) -> bytes:
    """暗号化されたファイルデータを復号化する"""
    return cipher_suite.decrypt(encrypted_data)
