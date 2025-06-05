from flask import Flask, jsonify, request
import logging
from logging.handlers import RotatingFileHandler
import os
import json
import platform
import socket
import traceback
from datetime import datetime
import uuid

app = Flask(__name__)

# リクエストIDを生成する関数
def generate_request_id():
    return str(uuid.uuid4())

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
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(request_id)s - %(message)s')
handler.setFormatter(formatter)

# アプリケーションロガーの設定
app.logger.addHandler(handler)
app.logger.setLevel(logging.ERROR)

# EC2インスタンスIDを取得する関数
def get_instance_id():
    instance_id = "i-unknown"  # デフォルト値
    try:
        import requests
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        if response.status_code == 200:
            instance_id = response.text
    except Exception:
        pass  # メタデータサービスへのアクセスに失敗した場合は無視
    return instance_id

# システム情報を取得する関数
def get_system_info():
    system_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "instance_id": get_instance_id()
    }
    return system_info

# リクエストIDをログに含めるためのフィルター
class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', 'no-request-id')
        return True

# フィルターを追加
for handler in app.logger.handlers:
    handler.addFilter(RequestIDLogFilter())

@app.before_request
def before_request():
    request.request_id = generate_request_id()

@app.route('/')
def home():
    """アプリケーションのホームページ"""
    return 'Hello from Flask application!'

@app.route('/error')
def trigger_error():
    """テスト用のエラーを発生させるエンドポイント"""
    try:
        # システム情報を取得
        system_info = get_system_info()
            
        # テストエラーを発生させる
        error_message = f"This is a test error triggered on purpose. Instance ID: {system_info['instance_id']}"
        raise Exception(error_message)
    except Exception as e:
        # スタックトレースを取得
        stack_trace = traceback.format_exc()
        
        # 構造化されたエラーログを作成
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "request_id": getattr(request, 'request_id', 'no-request-id'),
            "error_message": str(e),
            "system_info": get_system_info(),
            "stack_trace": stack_trace
        }
        
        # エラーログを出力
        app.logger.error(json.dumps(error_log), extra={"request_id": error_log["request_id"]})
        
        return jsonify({
            "error": "Internal Server Error", 
            "message": str(e),
            "request_id": error_log["request_id"]
        }), 500

@app.route('/health')
def health_check():
    """ヘルスチェック用エンドポイント"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_info": get_system_info()
    }), 200

if __name__ == '__main__':
    # 本番環境ではdebug=Falseにする
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug, host='0.0.0.0', port=int(os.environ.get('PORT', 80)))