# AWS Bedrock エージェントハンズオン手順書 (リファクタリング版)

このハンズオンでは、AWS Bedrock エージェント（Claude 3.5/4 Sonnet）を使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化するシステムを構築します。

## 🎯 ハンズオンの目標

- AWS Bedrockエージェントの基本的な使い方を学ぶ
- Lambda関数とエージェントの連携方法を理解する
- CloudWatch Logsとの統合を体験する
- 実際のトラブルシューティング自動化を実装する
- セッションマネージャーを使用した安全なEC2接続を体験する

## ⏱️ 所要時間

約 90-120 分

## 📋 前提条件

- AWSアカウントを持っていること
- AWS Management Consoleにアクセスできること
- 基本的なAWSサービス（EC2、Lambda、CloudWatch）の知識があること

## 🏗️ アーキテクチャ概要

```
[ユーザー] → [Bedrock エージェント] → [Lambda関数] → [CloudWatch Logs / EC2]
                                    ↓
                              [ログ分析・インスタンス再起動]
                                    ↑
                            [Session Manager経由でアクセス]
```

---

## 📝 ハンズオン手順

### ステップ1: EC2インスタンスの準備 (20分)

#### 1-1. EC2インスタンスの起動

1. **AWS Management Console** にログイン
2. **EC2サービス** に移動
3. **「インスタンスを起動」** をクリック

#### 1-2. インスタンス設定

```
名前: bedrock-agent-demo
AMI: Amazon Linux 2 AMI (HVM) - Kernel 5.10
インスタンスタイプ: t3.micro
キーペア: キーペアなしで続行
```

**重要**: セッションマネージャーを使用するため、キーペアは不要です。

#### 1-3. セキュリティグループ設定

**新しいセキュリティグループを作成:**
```
セキュリティグループ名: bedrock-agent-sg
説明: Security group for Bedrock Agent demo

インバウンドルール:
- タイプ: HTTP, ポート: 80, ソース: 0.0.0.0/0
```

**注意**: セッションマネージャーを使用するため、SSHポート（22）は不要です。

#### 1-4. 高度な詳細設定

**IAMインスタンスプロファイル:**
1. **「IAMインスタンスプロファイル」** で **「新しいIAMプロファイルを作成」** をクリック
2. 新しいタブが開くので、以下の設定でロールを作成:

```
ロール名: EC2-SessionManager-Role
信頼されたエンティティ: EC2
ポリシー: 
- AmazonSSMManagedInstanceCore
- CloudWatchAgentServerPolicy
```

3. ロール作成後、元のタブに戻り **「更新」** をクリック
4. 作成したロール **「EC2-SessionManager-Role」** を選択

5. **「インスタンスを起動」** をクリック

#### 1-5. セッションマネージャーでの接続

1. **EC2コンソール** でインスタンスを選択
2. **「接続」** ボタンをクリック
3. **「セッションマネージャー」** タブを選択
4. **「接続」** をクリック

#### 1-6. CloudWatch Logs エージェントの設定

**セッションマネージャー** で以下のコマンドを実行:

```bash
# システム更新
sudo yum update -y

# CloudWatch Logs エージェントのインストール
sudo yum install -y awslogs

# 設定ファイルの編集
sudo tee /etc/awslogs/awslogs.conf << 'EOF'
[general]
state_file = /var/lib/awslogs/agent-state

[/var/log/my-flask-app.log]
file = /var/log/my-flask-app.log
log_group_name = /aws/ec2/my-flask-application
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S
EOF

# サービス開始
sudo systemctl start awslogsd
sudo systemctl enable awslogsd

# ログファイル作成
sudo touch /var/log/my-flask-app.log
sudo chmod 666 /var/log/my-flask-app.log

# Python環境準備
sudo yum install -y python3 python3-pip
# Flaskとpsutilのインストール（システム全体にインストール）
sudo pip3 install flask psutil
```

#### 1-7. Flaskアプリケーションのデプロイ

1. **ホームディレクトリに移動してファイルを作成**:

```bash
# ホームディレクトリに移動
cd ~

# app.pyファイルを作成
sudo vim app.py
```

**vimエディタの操作**:
- `i` キーを押して挿入モードに入る
2. 以下のコードを **コピー&ペースト**:
   - コード入力後、`Esc` キーを押してコマンドモードに戻る
   - `:wq` と入力してファイルを保存・終了

```python
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
```

3. アプリケーションを実行:

```bash
sudo python3 app.py
```

4. **新しいセッションマネージャーセッション** を開いてテスト:

```bash
# 正常動作確認
curl http://localhost/

# エラー発生テスト
curl http://localhost/error
curl http://localhost/error/custom

# ヘルスチェック
curl http://localhost/health
```

---

### ステップ2: IAMロールの作成 (15分)

#### 2-1. EC2用IAMロールの確認

先ほど作成した **EC2-SessionManager-Role** が正しく設定されていることを確認します。

1. **IAMサービス** に移動
2. **「ロール」** → **「EC2-SessionManager-Role」** をクリック
3. 以下のポリシーがアタッチされていることを確認:
   - `AmazonSSMManagedInstanceCore`
   - `CloudWatchAgentServerPolicy`

#### 2-2. Lambda実行ロールの作成

1. **IAMサービス** に移動
2. **「ロール」** → **「ロールを作成」**
3. **信頼されたエンティティタイプ**: AWSサービス
4. **ユースケース**: Lambda
5. **「次へ」** をクリック

#### 2-3. ポリシーのアタッチ

**以下のポリシーを検索してアタッチ:**
- `AWSLambdaBasicExecutionRole`

#### 2-4. カスタムポリシーの作成

1. **「ポリシーを作成」** をクリック
2. **JSON** タブを選択
3. 以下のポリシーを **コピー&ペースト**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/ec2/my-flask-application:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Environment": ["demo", "development", "staging"]
        }
      }
    }
  ]
}
```

4. **ポリシー名**: `BedrockAgentLambdaPolicy`
5. **「ポリシーを作成」**

#### 2-5. ロールの完成

1. 作成したカスタムポリシーもアタッチ
2. **ロール名**: `BedrockAgentLambdaRole`
3. **「ロールを作成」**

---

### ステップ3: Lambda関数の作成 (25分)

#### 3-1. ログ取得Lambda関数の作成

1. **Lambdaサービス** に移動
2. **「関数の作成」** をクリック
3. **「一から作成」** を選択

**基本情報:**
```
関数名: get-log-refactored
ランタイム: Python 3.9
アーキテクチャ: x86_64
実行ロール: 既存のロールを使用 → BedrockAgentLambdaRole
```

4. **「関数の作成」** をクリック

#### 3-2. ログ取得Lambda関数のコード

**lambda_function.py** の内容を以下に **置き換え**:

[ここに get-log-refactored.py の完全なコードを貼り付け]

#### 3-3. Lambda関数の設定

1. **「設定」** タブをクリック
2. **「一般設定」** → **「編集」**

**設定値:**
```
タイムアウト: 5分
メモリ: 512 MB
```

3. **「保存」** をクリック

#### 3-4. インスタンス再起動Lambda関数の作成

1. **「関数の作成」** をクリック
2. **「一から作成」** を選択

**基本情報:**
```
関数名: reboot-instances-refactored
ランタイム: Python 3.9
アーキテクチャ: x86_64
実行ロール: 既存のロールを使用 → BedrockAgentLambdaRole
```

3. **「関数の作成」** をクリック

#### 3-5. インスタンス再起動Lambda関数のコード

**lambda_function.py** の内容を以下に **置き換え**:

[ここに reboot-instances-refactored.py の完全なコードを貼り付け]

#### 3-6. Lambda関数の設定

1. **「設定」** タブをクリック
2. **「一般設定」** → **「編集」**

**設定値:**
```
タイムアウト: 5分
メモリ: 256 MB
```

3. **「保存」** をクリック

#### 3-7. Lambda関数のテスト

**ログ取得Lambda関数のテスト:**
1. **「テスト」** タブをクリック
2. **「新しいイベントを作成」**
3. **イベント名**: `test-get-logs`
4. **イベントJSON**:

```json
{
  "parameters": [
    {"name": "logGroup", "value": "/aws/ec2/my-flask-application"},
    {"name": "hoursAgo", "value": "24"}
  ],
  "actionGroup": "test",
  "apiPath": "/get-logs",
  "httpMethod": "GET"
}
```

5. **「テスト」** をクリック

**インスタンス再起動Lambda関数のテスト:**
1. **「テスト」** タブをクリック
2. **「新しいイベントを作成」**
3. **イベント名**: `test-reboot-dryrun`
4. **イベントJSON** (インスタンスIDを実際のものに変更):

```json
{
  "parameters": [
    {"name": "instanceId", "value": "i-xxxxxxxxxxxxxxxxx"},
    {"name": "dryRun", "value": "true"}
  ],
  "actionGroup": "test",
  "apiPath": "/reboot",
  "httpMethod": "POST"
}
```

5. **「テスト」** をクリック

---

### ステップ4: Bedrock エージェントの作成 (30分)

#### 4-1. Bedrockサービスへのアクセス

1. **Amazon Bedrock** サービスに移動
2. 左側メニューから **「エージェント」** を選択
3. **「エージェントを作成」** をクリック

#### 4-2. エージェントの基本設定

**エージェントの詳細:**
```
エージェント名: bedrock-troubleshooting-agent
説明: EC2インスタンスのトラブルシューティングを自動化するエージェント
```

**モデル選択:**
```
モデル: Claude 3.5 Sonnet または Claude 4 Sonnet
```

#### 4-3. エージェント指示の設定

**指示** 欄に以下の内容を **コピー&ペースト**:

[ここに エージェントへの指示-refactored.txt の完全な内容を貼り付け]

#### 4-4. アクショングループの作成

**ログ取得アクショングループ:**
1. **「アクショングループを追加」** をクリック
2. **アクショングループの詳細:**

```
アクショングループ名: RetrieveLogsActionGroup
説明: CloudWatch Logsからエラーログを取得
アクショングループの状態: 有効
```

3. **Lambda関数の選択:**
   - **Lambda関数**: `get-log-refactored`

4. **APIスキーマの定義:**
   **「APIスキーマを定義」** を選択し、以下をコピー&ペースト:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Log Retrieval API",
    "version": "1.0.0"
  },
  "paths": {
    "/get-logs": {
      "get": {
        "summary": "Retrieve error logs from CloudWatch",
        "operationId": "RetrieveLogs",
        "parameters": [
          {
            "name": "logGroup",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string",
              "default": "/aws/ec2/my-flask-application"
            },
            "description": "CloudWatch log group name"
          },
          {
            "name": "hoursAgo",
            "in": "query",
            "required": false,
            "schema": {
              "type": "integer",
              "default": 24
            },
            "description": "Number of hours to look back for logs"
          }
        ],
        "responses": {
          "200": {
            "description": "Successfully retrieved logs",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

5. **「追加」** をクリック

**インスタンス再起動アクショングループ:**
1. **「アクショングループを追加」** をクリック
2. **アクショングループの詳細:**

```
アクショングループ名: RebootInstancesActionGroup
説明: EC2インスタンスの安全な再起動
アクショングループの状態: 有効
```

3. **Lambda関数の選択:**
   - **Lambda関数**: `reboot-instances-refactored`

4. **APIスキーマの定義:**
   **「APIスキーマを定義」** を選択し、以下をコピー&ペースト:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Instance Reboot API",
    "version": "1.0.0"
  },
  "paths": {
    "/reboot-instance": {
      "post": {
        "summary": "Reboot EC2 instance",
        "operationId": "RebootInstances",
        "parameters": [
          {
            "name": "instanceId",
            "in": "query",
            "required": true,
            "schema": {
              "type": "string"
            },
            "description": "EC2 instance ID to reboot"
          },
          {
            "name": "force",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "default": false
            },
            "description": "Force reboot ignoring protection"
          },
          {
            "name": "dryRun",
            "in": "query",
            "required": false,
            "schema": {
              "type": "boolean",
              "default": false
            },
            "description": "Test run without actual reboot"
          }
        ],
        "responses": {
          "200": {
            "description": "Successfully rebooted instance",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

5. **「追加」** をクリック

#### 4-5. エージェントの準備

1. **「エージェントを準備」** をクリック
2. 準備プロセスが完了するまで待機（数分かかります）

---

### ステップ5: エージェントのテスト (20分)

#### 5-1. エージェントテストの実行

1. **「テスト」** タブをクリック
2. **テストセッション** を開始

#### 5-2. 基本動作テスト

**テスト1: システム状況確認**
```
ユーザー入力: "システムの状況を確認してください"
```

**期待される動作:**
- エージェントがRetrieveLogsアクションを実行
- ログ分析結果を表示
- エラーの有無を報告

**テスト2: エラーログ分析**
```
ユーザー入力: "過去24時間のエラーログを詳しく分析してください"
```

**期待される動作:**
- 詳細なログ分析を実行
- エラーパターンの特定
- 重要度別の分類表示

**テスト3: インスタンス再起動（ドライラン）**
```
ユーザー入力: "インスタンス i-xxxxxxxxxxxxxxxxx をドライランで再起動してください"
```

**期待される動作:**
- インスタンス情報の確認
- ドライラン実行
- 実際の再起動は行わない

#### 5-3. エラーシナリオテスト

1. **セッションマネージャー** でEC2インスタンスに接続
2. 意図的にエラーを発生:

```bash
# エラー発生
curl http://localhost/error
curl http://localhost/error/custom
```

3. **エージェント** でエラー分析:

```
ユーザー入力: "最新のエラーを分析して、解決策を提案してください"
```

**期待される動作:**
- 最新エラーの検出
- 根本原因の分析
- 適切な解決策の提案

#### 5-4. 実際の再起動テスト（注意深く実行）

```
ユーザー入力: "インスタンス i-xxxxxxxxxxxxxxxxx に問題があるようです。再起動が必要でしょうか？"
```

**期待される動作:**
- エラー状況の確認
- 再起動の提案
- ユーザー確認の要求

**ユーザー確認後:**
```
ユーザー入力: "はい、再起動してください"
```

**期待される動作:**
- 実際の再起動実行
- 結果の報告

---

### ステップ6: 動作確認とトラブルシューティング (10分)

#### 6-1. CloudWatch Logsの確認

1. **CloudWatch** サービスに移動
2. **「ログ」** → **「ロググループ」**
3. `/aws/ec2/my-flask-application` を確認
4. ログエントリが正しく記録されているか確認

#### 6-2. Lambda関数の実行ログ確認

1. **Lambda** サービスに移動
2. 各関数の **「監視」** タブを確認
3. **「CloudWatch Logsでログを表示」** をクリック
4. エラーがないか確認

#### 6-3. よくある問題と解決方法

**問題1: CloudWatch Logsにログが表示されない**
```bash
# セッションマネージャーでEC2インスタンスに接続して確認
sudo systemctl status awslogsd
sudo journalctl -u awslogsd

# IAMロールの確認
# EC2コンソールでインスタンスのIAMロールが正しく設定されているか確認
```

**問題2: セッションマネージャーで接続できない**
- EC2インスタンスにIAMロール（EC2-SessionManager-Role）が正しくアタッチされているか確認
- Systems Manager エージェントが実行されているか確認:
```bash
sudo systemctl status amazon-ssm-agent
```

**問題3: Lambda関数がタイムアウトする**
- タイムアウト時間を延長
- メモリサイズを増加

**問題4: エージェントがアクションを実行できない**
- IAMロールの権限を確認
- APIスキーマの形式を確認
- Lambda関数のテスト実行

---

## 🎉 ハンズオン完了

### 🎯 達成したこと

✅ **セッションマネージャーを使用した安全なEC2接続**
- キーペア不要の安全な接続方法を体験
- IAMロールベースのアクセス制御

✅ **AWS Bedrockエージェントの構築**
- Claude 3.5/4 Sonnet を活用した高度なAIエージェント
- 自然言語でのシステム操作

✅ **Lambda関数との連携**
- ログ分析の自動化
- インスタンス管理の自動化

✅ **CloudWatch Logsとの統合**
- 構造化ログの活用
- リアルタイムログ監視

✅ **実用的なトラブルシューティング自動化**
- エラー検出から解決までの自動化
- 安全性を考慮した操作確認

### 🚀 次のステップ

1. **本番環境への適用検討**
   - より厳密なIAMポリシーの設定
   - 複数環境での運用

2. **機能拡張**
   - 他のAWSサービスとの連携
   - より高度な分析機能の追加

3. **監視強化**
   - アラート機能の追加
   - ダッシュボードの構築

### 📚 参考資料

- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [Amazon Bedrock エージェント](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Claude 3.5 Sonnet](https://docs.anthropic.com/claude/docs)
- [AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)

---

**お疲れ様でした！** 🎊

このハンズオンを通じて、最新のAI技術とAWSサービスを組み合わせた実用的なシステムを構築することができました。セッションマネージャーによる安全な接続方法も含め、実際の業務で活用できる知識を習得していただけたと思います。
