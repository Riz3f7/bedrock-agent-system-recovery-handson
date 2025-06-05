"""
AWS Bedrock エージェント対応 Flask アプリケーション (リファクタリング版)
Claude 3.5/4 Sonnet 最適化
"""

from flask import Flask, jsonify, request
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import traceback

class FlaskAppConfig:
    """アプリケーション設定クラス"""
    
    def __init__(self):
        self.log_file = os.getenv('LOG_FILE', '/var/log/my-flask-app.log')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.host = os.getenv('FLASK_HOST', '0.0.0.0')
        self.port = int(os.getenv('FLASK_PORT', '80'))
        self.debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

class StructuredLogger:
    """構造化ログ出力クラス"""
    
    def __init__(self, config: FlaskAppConfig):
        self.logger = logging.getLogger(__name__)
        self.setup_logging(config)
    
    def setup_logging(self, config: FlaskAppConfig):
        """ログ設定の初期化"""
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        # ファイルハンドラー
        file_handler = logging.FileHandler(config.log_file)
        file_handler.setFormatter(formatter)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(getattr(logging, config.log_level))
    
    def log_structured(self, level: str, message: str, **kwargs):
        """構造化ログの出力"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': message,
            'metadata': kwargs
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data, ensure_ascii=False))

class ErrorHandler:
    """エラーハンドリングクラス"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """エラーの統一処理"""
        error_id = f"ERR_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        error_info = {
            'error_id': error_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'traceback': traceback.format_exc()
        }
        
        self.logger.log_structured(
            'error',
            f"Application error occurred: {error_info['error_message']}",
            error_id=error_id,
            error_type=error_info['error_type'],
            context=context
        )
        
        return error_info

class HealthChecker:
    """ヘルスチェック機能"""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
    
    def check_health(self) -> Dict[str, Any]:
        """アプリケーションの健全性チェック"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'logging': self._check_logging(),
                'memory': self._check_memory(),
                'disk': self._check_disk()
            }
        }
        
        # 全体的な健全性判定
        if not all(check['status'] == 'ok' for check in health_status['checks'].values()):
            health_status['status'] = 'unhealthy'
        
        return health_status
    
    def _check_logging(self) -> Dict[str, str]:
        """ログ機能のチェック"""
        try:
            self.logger.log_structured('info', 'Health check: logging test')
            return {'status': 'ok', 'message': 'Logging is functional'}
        except Exception as e:
            return {'status': 'error', 'message': f'Logging error: {str(e)}'}
    
    def _check_memory(self) -> Dict[str, str]:
        """メモリ使用量のチェック"""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                return {'status': 'warning', 'message': f'High memory usage: {memory_percent}%'}
            return {'status': 'ok', 'message': f'Memory usage: {memory_percent}%'}
        except ImportError:
            return {'status': 'unknown', 'message': 'psutil not available'}
        except Exception as e:
            return {'status': 'error', 'message': f'Memory check error: {str(e)}'}
    
    def _check_disk(self) -> Dict[str, str]:
        """ディスク使用量のチェック"""
        try:
            import shutil
            disk_usage = shutil.disk_usage('/')
            used_percent = (disk_usage.used / disk_usage.total) * 100
            if used_percent > 90:
                return {'status': 'warning', 'message': f'High disk usage: {used_percent:.1f}%'}
            return {'status': 'ok', 'message': f'Disk usage: {used_percent:.1f}%'}
        except Exception as e:
            return {'status': 'error', 'message': f'Disk check error: {str(e)}'}

def create_app() -> Flask:
    """Flaskアプリケーションファクトリー"""
    app = Flask(__name__)
    
    # 設定の初期化
    config = FlaskAppConfig()
    logger = StructuredLogger(config)
    error_handler = ErrorHandler(logger)
    health_checker = HealthChecker(logger)
    
    # アプリケーションコンテキストに追加
    app.config['APP_CONFIG'] = config
    app.config['LOGGER'] = logger
    app.config['ERROR_HANDLER'] = error_handler
    app.config['HEALTH_CHECKER'] = health_checker
    
    @app.route('/')
    def home():
        """ホームページ"""
        logger.log_structured('info', 'Home page accessed')
        return jsonify({
            'message': 'Hello from Flask application!',
            'version': '2.0.0-refactored',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @app.route('/health')
    def health():
        """ヘルスチェックエンドポイント"""
        health_status = health_checker.check_health()
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    @app.route('/error')
    def trigger_error():
        """意図的なエラー発生（テスト用）"""
        try:
            # より詳細なエラー情報を含む例外を発生
            error_details = {
                'user_action': 'trigger_error_endpoint',
                'request_id': request.headers.get('X-Request-ID', 'unknown'),
                'user_agent': request.headers.get('User-Agent', 'unknown')
            }
            raise Exception(f"Test error triggered with details: {json.dumps(error_details)}")
        except Exception as e:
            error_info = error_handler.handle_error(e, "error_endpoint")
            return jsonify({
                'error': 'Internal Server Error',
                'error_id': error_info['error_id'],
                'message': 'An error occurred while processing your request'
            }), 500
    
    @app.route('/error/custom')
    def trigger_custom_error():
        """カスタムエラーの発生（より複雑なテストケース）"""
        try:
            # 複数の処理ステップでエラーを発生
            step1_data = {'step': 1, 'data': 'processing'}
            logger.log_structured('info', 'Starting custom error simulation', **step1_data)
            
            step2_data = {'step': 2, 'calculation': 10 / 0}  # ZeroDivisionError
            
        except ZeroDivisionError as e:
            error_info = error_handler.handle_error(e, "custom_error_endpoint")
            return jsonify({
                'error': 'Calculation Error',
                'error_id': error_info['error_id'],
                'message': 'A calculation error occurred during processing'
            }), 500
        except Exception as e:
            error_info = error_handler.handle_error(e, "custom_error_endpoint")
            return jsonify({
                'error': 'Unexpected Error',
                'error_id': error_info['error_id'],
                'message': 'An unexpected error occurred'
            }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """404エラーハンドラー"""
        logger.log_structured('warning', f'404 error: {request.url}', 
                             path=request.path, method=request.method)
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500エラーハンドラー"""
        error_info = error_handler.handle_error(error, "internal_server_error")
        return jsonify({
            'error': 'Internal Server Error',
            'error_id': error_info['error_id'],
            'message': 'An internal server error occurred'
        }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    config = app.config['APP_CONFIG']
    logger = app.config['LOGGER']
    
    logger.log_structured('info', 'Starting Flask application', 
                         host=config.host, port=config.port, debug=config.debug)
    
    app.run(debug=config.debug, host=config.host, port=config.port)
