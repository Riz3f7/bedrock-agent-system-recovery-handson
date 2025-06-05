from flask import Flask, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__)

# ログディレクトリの確認と作成
log_dir = '/var/log'
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# ログの設定 - RotatingFileHandlerを使用してログファイルのサイズを制限
handler = RotatingFileHandler(
    '/var/log/my-flask-app.log', 
    maxBytes=10485760,  # 10MB
    backupCount=5
)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# アプリケーションロガーの設定
app.logger.addHandler(handler)
app.logger.setLevel(logging.ERROR)

@app.route('/')
def home():
    """アプリケーションのホームページ"""
    return 'Hello from Flask application!'

@app.route('/error')
def trigger_error():
    """テスト用のエラーを発生させるエンドポイント"""
    try:
        # EC2インスタンスIDを取得（メタデータサービスを使用）
        instance_id = "i-unknown"  # デフォルト値
        try:
            import requests
            response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
            if response.status_code == 200:
                instance_id = response.text
        except Exception:
            pass  # メタデータサービスへのアクセスに失敗した場合は無視
            
        # テストエラーを発生させる
        raise Exception(f"This is a test error triggered on purpose. Instance ID: {instance_id}")
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # 本番環境ではdebug=Falseにする
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug, host='0.0.0.0', port=int(os.environ.get('PORT', 80)))