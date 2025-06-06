# AWS Bedrock エージェントハンズオン手順書 (リファクタリング版)

このハンズオンでは、AWS Bedrock エージェント（Claude 3.5/4 Sonnet）を使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化するシステムを構築します。

## 🎯 ハンズオンの目標

- AWS Bedrockエージェントの基本的な使い方を学ぶ
- Lambda関数とエージェントの連携方法を理解する
- CloudWatch Logsとの統合を体験する
- 実際のトラブルシューティング自動化を実装する
- セッションマネージャーを使用した安全なEC2接続を体験する

## ⏱️ 所要時間

約 85-105 分（事前準備5分 + CloudFormation自動化により短縮）

## 📋 前提条件

- AWSアカウントを持っていること
- AWS Management Consoleにアクセスできること
- 基本的なAWSサービス（EC2、Lambda、CloudWatch）の知識があること
- Amazon Nova Proが利用可能なリージョンを使用すること（推奨: us-east-1, us-west-2）

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

### 事前準備: Amazon Nova Proの有効化 (5分)

#### 事前-1. Bedrockサービスへのアクセス

1. **AWS Management Console** にログイン
2. **リージョンの確認**: Amazon Nova Pro対応リージョン（us-east-1, us-west-2等）を選択
3. **Amazon Bedrock** サービスに移動

#### 事前-2. モデルアクセスの有効化

1. 左側メニューから **「モデルアクセス」** を選択
2. **「モデルアクセスを変更」** ボタンをクリック
3. **Amazon Nova Pro** を探してチェックボックスを選択
4. 利用規約がある場合は確認して同意
5. **「次へ」** → **「送信」** をクリック
6. ステータスが **「アクセスが付与されました」** になることを確認

**重要**: モデルアクセスの有効化には数分かかる場合があります。

#### 事前-3. 動作確認

1. 左側メニューから **「テキスト」** または **「チャット」** を選択
2. **「モデルを選択」** で **Amazon Nova Pro** を選択
3. 簡単なテスト入力（例：「こんにちは」）で動作確認
4. 正常に応答が返ることを確認

---

### ステップ1: CloudFormationを使用したEC2インスタンスの準備 (20分)

#### 1-1. CloudFormationテンプレートの確認

**事前準備として、プロジェクトに含まれる `ec2-flask-template.yaml` を確認します。**

このテンプレートには以下が含まれています：
- Amazon Linux 2023を使用したEC2インスタンス
- Session Manager接続用のIAMロール
- HTTP接続用のセキュリティグループ
- CloudWatch Agent設定
- Flask アプリケーションの自動デプロイ

#### 1-2. CloudFormationスタックの作成

1. **AWS Management Console** にログイン
2. **CloudFormation** サービスに移動
3. **「スタックの作成」** → **「新しいリソースを使用 (標準)」** をクリック

#### 1-3. テンプレートのアップロード

1. **「テンプレートファイルのアップロード」** を選択
2. **「ファイルを選択」** をクリック
3. ローカルの `ec2-flask-template.yaml` ファイルを選択
4. **「次へ」** をクリック

#### 1-4. スタックの詳細設定

**スタックの詳細:**
```
スタック名: bedrock-agent-demo-stack
```

**パラメータ設定:**
```
InstanceType: t3.micro (デフォルト)
VpcId: [利用可能なVPCを選択]
SubnetId: [パブリックサブネットを選択]
```

**重要**: パブリックIPが自動割り当てされるサブネットを選択してください。

5. **「次へ」** をクリック

#### 1-5. スタックオプションの設定

1. **スタックオプション** はデフォルトのまま
2. **「次へ」** をクリック

#### 1-6. 確認と作成

1. 設定内容を確認
2. **「AWS CloudFormation によって IAM リソースが作成される場合があることを承認します」** にチェック
3. **「スタックの作成」** をクリック

#### 1-7. スタック作成の完了確認

1. **「イベント」** タブでスタック作成の進行状況を確認
2. ステータスが **「CREATE_COMPLETE」** になるまで待機（約5-10分）
3. **「出力」** タブで以下の情報を確認:
   - **InstanceId**: 作成されたEC2インスタンスのID
   - **PublicIP**: パブリックIPアドレス
   - **WebsiteURL**: FlaskアプリケーションのURL
   - **SessionManagerURL**: Session Managerアクセス用URL

#### 1-8. Session Managerでの接続確認

1. CloudFormation出力の **SessionManagerURL** をクリック、または
2. **EC2コンソール** → 作成されたインスタンスを選択 → **「接続」** → **「セッションマネージャー」** → **「接続」**

#### 1-9. アプリケーションの動作確認

**CloudFormationテンプレートにより、FlaskアプリケーションとCloudWatch Agentは自動的にインストール・設定されています。**

1. **ブラウザでアプリケーションにアクセス:**
   - CloudFormation出力の **WebsiteURL** をクリック
   - または パブリックIP に直接アクセス: `http://[PublicIP]/`

2. **Session Managerで接続してアプリケーションをテスト:**

```bash
# アプリケーションの状態確認
sudo systemctl status flask-app

# 正常動作確認
curl http://localhost/

# エラー発生テスト（Lambda関数テストに重要）
curl http://localhost/error
curl http://localhost/error/custom

# ヘルスチェック
curl http://localhost/health

# ログファイルの確認（重要：ここでERRORが出力されているか確認）
sudo tail -f /var/log/my-flask-app.log
```

**重要**: `curl http://localhost/error` を実行後、CloudWatch Logsでエラーログが記録されることを確認してください。これがLambda関数テストの前提条件です。

#### 1-10. CloudWatch Logsの確認

1. **CloudWatch** サービスに移動
2. **「ログ」** → **「ロググループ」**
3. `/aws/ec2/my-flask-application` でログが記録されていることを確認

---

### ステップ2: IAMロールの作成 (10分)

#### 2-1. EC2用IAMロールの確認

**CloudFormationテンプレートにより、EC2インスタンス用のIAMロールは自動的に作成されています。**

1. **IAMサービス** に移動
2. **「ロール」** で **「bedrock-agent-demo-stack-FlaskAppRole-xxxxxxxxx」** を確認
3. 以下のポリシーがアタッチされていることを確認:
   - `AmazonSSMManagedInstanceCore`
   - `CloudWatchAgentServerPolicy`

#### 2-2. カスタムポリシーの作成

**まず、Lambda関数用のカスタムポリシーを作成します。**

1. **IAMサービス** に移動
2. **「ポリシー」** → **「ポリシーを作成」** をクリック
3. **JSON** タブを選択
4. 以下のポリシーをコピー&ペースト（```json と ``` は除く）:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/ec2/my-flask-application:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "*"
    }
  ]
}

5. **ポリシー名**: `BedrockAgentLambdaPolicy`
6. **「ポリシーを作成」**

#### 2-3. Lambda実行ロールの作成

1. **IAMサービス** に移動
2. **「ロール」** → **「ロールを作成」**
3. **信頼されたエンティティタイプ**: AWSサービス
4. **ユースケース**: Lambda
5. **「次へ」** をクリック

#### 2-4. ポリシーのアタッチ

**以下のポリシーを検索してアタッチ:**

1. **`AWSLambdaBasicExecutionRole`** を検索
2. **チェックボックスにチェックを入れる**
3. **`BedrockAgentLambdaPolicy`** を検索（先ほど作成したポリシー）
4. **チェックボックスにチェックを入れる**
5. **「次へ」** をクリック

#### 2-5. ロールの完成

1. **ロール名**: `BedrockAgentLambdaRole`
2. **「ロールを作成」**

---

### ステップ3: Lambda関数の作成 (25分)

#### 3-1. ログ取得Lambda関数の作成

1. **Lambdaサービス** に移動
2. **「関数の作成」** をクリック
3. **「一から作成」** を選択

**基本情報:**
```
関数名: get-log-refactored
ランタイム: Python 3.13
アーキテクチャ: x86_64
デフォルトの実行ロールの変更: 既存のロールを使用する → BedrockAgentLambdaRole
```

4. **「関数の作成」** をクリック

#### 3-2. ログ取得Lambda関数のコード

**重要**: デフォルトのコードを完全に削除して、以下のコードに **置き換え** してください。

1. **「コード」** タブをクリック
2. **lambda_function.py** の内容をすべて削除
3. 以下のコードを **コピー&ペースト**:

```python
"""
CloudWatch Logs 取得 Lambda 関数 (リファクタリング版)
Claude 3.5/4 Sonnet 最適化
"""

import boto3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import re
from botocore.exceptions import ClientError, BotoCoreError

@dataclass
class LogEntry:
    """ログエントリのデータクラス"""
    timestamp: int
    log_stream_name: str
    message: str
    severity: str
    instance_id: Optional[str] = None
    error_type: Optional[str] = None

class CloudWatchLogsClient:
    """CloudWatch Logs クライアントのラッパークラス"""
    
    def __init__(self):
        self.client = boto3.client('logs')
        self.instance_id_pattern = re.compile(r'i-[a-f0-9]{8,17}')
        self.error_patterns = {
            'ERROR': re.compile(r'ERROR|Error|error'),
            'CRITICAL': re.compile(r'CRITICAL|Critical|critical|FATAL|Fatal|fatal'),
            'WARNING': re.compile(r'WARNING|Warning|warning|WARN|Warn|warn'),
            'EXCEPTION': re.compile(r'Exception|exception|Traceback|traceback')
        }
    
    def get_log_streams(self, log_group_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """ログストリームの一覧を取得"""
        try:
            response = self.client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=limit
            )
            return response.get('logStreams', [])
        except ClientError as e:
            raise Exception(f"Failed to get log streams: {e}")
    
    def filter_log_events(self, log_group_name: str, start_time: int, end_time: int,
                         filter_pattern: str = '?ERROR ?Exception ?Traceback') -> List[Dict[str, Any]]:
        """フィルターパターンを使用してログイベントを効率的に取得"""
        try:
            all_events = []
            next_token = None
            max_iterations = 10  # 無限ループ防止
            iteration = 0
            
            while iteration < max_iterations:
                kwargs = {
                    'logGroupName': log_group_name,
                    'startTime': start_time,
                    'endTime': end_time,
                    'filterPattern': filter_pattern,
                    'limit': 1000  # 一度に取得する最大イベント数
                }
                
                if next_token:
                    kwargs['nextToken'] = next_token
                
                response = self.client.filter_log_events(**kwargs)
                events = response.get('events', [])
                all_events.extend(events)
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
                    
                iteration += 1
            
            return all_events
        except ClientError as e:
            print(f"Warning: Failed to filter log events: {e}")
            return []

class LogAnalyzer:
    """ログ分析クラス"""
    
    def __init__(self):
        self.instance_id_pattern = re.compile(r'i-[a-f0-9]{8,17}')
        self.error_patterns = {
            'CRITICAL': [
                re.compile(r'CRITICAL|Critical|critical|FATAL|Fatal|fatal'),
                re.compile(r'OutOfMemoryError|MemoryError'),
                re.compile(r'ConnectionRefusedError|ConnectionError'),
                re.compile(r'TimeoutError|timeout')
            ],
            'ERROR': [
                re.compile(r'ERROR|Error(?!.*warning)'),
                re.compile(r'Exception(?!.*test)'),
                re.compile(r'Traceback'),
                re.compile(r'Failed|failed(?!.*warning)')
            ],
            'WARNING': [
                re.compile(r'WARNING|Warning|warning|WARN|Warn|warn'),
                re.compile(r'deprecated|Deprecated')
            ]
        }
    
    def extract_instance_id(self, message: str) -> Optional[str]:
        """メッセージからインスタンスIDを抽出"""
        match = self.instance_id_pattern.search(message)
        return match.group(0) if match else None
    
    def determine_severity(self, message: str) -> str:
        """メッセージの重要度を判定"""
        message_lower = message.lower()
        
        # 重要度の高い順にチェック
        for severity, patterns in self.error_patterns.items():
            for pattern in patterns:
                if pattern.search(message):
                    return severity
        
        return 'INFO'
    
    def extract_error_type(self, message: str) -> Optional[str]:
        """エラータイプを抽出"""
        # 一般的なPythonの例外タイプ
        exception_patterns = [
            r'(\w+Error)',
            r'(\w+Exception)',
            r'(TimeoutError)',
            r'(ConnectionError)',
            r'(ValueError)',
            r'(TypeError)',
            r'(AttributeError)',
            r'(KeyError)',
            r'(IndexError)'
        ]
        
        for pattern in exception_patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        
        return None
    
    def is_error_log(self, message: str) -> bool:
        """エラーログかどうかを判定"""
        severity = self.determine_severity(message)
        return severity in ['ERROR', 'CRITICAL', 'WARNING']
    
    def analyze_log_entry(self, event: Dict[str, Any], log_stream_name: str) -> LogEntry:
        """ログエントリを分析"""
        message = event['message']
        severity = self.determine_severity(message)
        instance_id = self.extract_instance_id(message)
        error_type = self.extract_error_type(message) if severity in ['ERROR', 'CRITICAL'] else None
        
        return LogEntry(
            timestamp=event['timestamp'],
            log_stream_name=log_stream_name,
            message=message,
            severity=severity,
            instance_id=instance_id,
            error_type=error_type
        )

class LogRetriever:
    """ログ取得メインクラス"""
    
    def __init__(self):
        self.cloudwatch_client = CloudWatchLogsClient()
        self.analyzer = LogAnalyzer()
    
    def get_error_logs(self, log_group_name: str, hours_ago: int = 24, 
                      filter_pattern: str = '?ERROR ?Exception ?Traceback') -> Dict[str, Any]:
        """エラーログを取得して分析（フィルターパターン使用）"""
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours_ago * 60 * 60 * 1000)
            
            # フィルターパターンを使用してエラーログを直接取得
            print(f"Searching logs: group={log_group_name}, hours_ago={hours_ago}, pattern={filter_pattern}")
            print(f"Time range: {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(end_time/1000)}")
            
            filtered_events = self.cloudwatch_client.filter_log_events(
                log_group_name, start_time, end_time, filter_pattern
            )
            
            print(f"Found {len(filtered_events)} events")
            
            if not filtered_events:
                return {
                    'status': 'no_errors',
                    'message': f'No error logs found in {log_group_name} for the past {hours_ago} hours',
                    'error_logs': [],
                    'summary': self._create_empty_summary()
                }
            
            error_logs = []
            log_stream_names = set()
            
            for event in filtered_events:
                log_stream_name = event.get('logStreamName', 'unknown')
                log_stream_names.add(log_stream_name)
                
                # ログエントリを分析
                log_entry = self.analyzer.analyze_log_entry(event, log_stream_name)
                
                error_logs.append({
                    'timestamp': log_entry.timestamp,
                    'datetime': datetime.fromtimestamp(log_entry.timestamp / 1000).isoformat(),
                    'logStreamName': log_entry.log_stream_name,
                    'message': log_entry.message,
                    'severity': log_entry.severity,
                    'instanceId': log_entry.instance_id,
                    'errorType': log_entry.error_type
                })
            
            # 結果をタイムスタンプでソート（新しい順）
            error_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'status': 'success',
                'error_logs': error_logs,
                'summary': self._create_summary(error_logs, len(log_stream_names), hours_ago),
                'metadata': {
                    'log_group': log_group_name,
                    'time_range_hours': hours_ago,
                    'processed_streams': len(log_stream_names),
                    'filter_pattern': filter_pattern,
                    'query_time': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'error_logs': [],
                'summary': self._create_empty_summary()
            }
    
    def _create_summary(self, error_logs: List[Dict], processed_streams: int, hours_ago: int) -> Dict[str, Any]:
        """エラーログのサマリーを作成"""
        if not error_logs:
            return self._create_empty_summary()
        
        # 重要度別の集計
        severity_counts = {}
        error_type_counts = {}
        instance_ids = set()
        
        for log in error_logs:
            # 重要度別カウント
            severity = log['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # エラータイプ別カウント
            error_type = log.get('errorType')
            if error_type:
                error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            
            # インスタンスID収集
            instance_id = log.get('instanceId')
            if instance_id:
                instance_ids.add(instance_id)
        
        # 最新のエラー
        latest_error = error_logs[0] if error_logs else None
        
        return {
            'total_errors': len(error_logs),
            'severity_breakdown': severity_counts,
            'error_types': error_type_counts,
            'affected_instances': list(instance_ids),
            'latest_error': {
                'timestamp': latest_error['datetime'],
                'severity': latest_error['severity'],
                'message': latest_error['message'][:200] + '...' if len(latest_error['message']) > 200 else latest_error['message']
            } if latest_error else None,
            'time_range_hours': hours_ago,
            'processed_streams': processed_streams
        }
    
    def _create_empty_summary(self) -> Dict[str, Any]:
        """空のサマリーを作成"""
        return {
            'total_errors': 0,
            'severity_breakdown': {},
            'error_types': {},
            'affected_instances': [],
            'latest_error': None,
            'time_range_hours': 0,
            'processed_streams': 0
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のエントリーポイント"""
    print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
    
    # デフォルト値
    log_group_name = '/aws/ec2/my-flask-application'
    hours_ago = 24
    
    try:
        # パラメータの取得
        if 'parameters' in event:
            for param in event['parameters']:
                if param['name'] == 'logGroup':
                    log_group_name = param['value']
                elif param['name'] == 'hoursAgo':
                    hours_ago = int(param['value'])
        
        # ログ取得の実行
        log_retriever = LogRetriever()
        result = log_retriever.get_error_logs(log_group_name, hours_ago)
        
        # レスポンスの構築
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": result
                    }
                }
            }
        }
        
        print(f"Response: {json.dumps(response, ensure_ascii=False)}")
        return response
        
    except Exception as e:
        error_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": {
                            "status": "error",
                            "error": str(e),
                            "error_logs": [],
                            "summary": {
                                "total_errors": 0,
                                "severity_breakdown": {},
                                "error_types": {},
                                "affected_instances": [],
                                "latest_error": None
                            }
                        }
                    }
                }
            }
        }
        
        print(f"Error response: {json.dumps(error_response, ensure_ascii=False)}")
        return error_response

# テスト用の関数
def test_locally():
    """ローカルテスト用の関数"""
    test_event = {
        "parameters": [
            {"name": "logGroup", "value": "/aws/ec2/my-flask-application"},
            {"name": "hoursAgo", "value": "24"}
        ],
        "actionGroup": "test-action-group",
        "apiPath": "/get-logs",
        "httpMethod": "GET"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_locally()
```

4. **「Deploy」** ボタンをクリックして **必ずデプロイ** してください

**重要**: Deployしないとコードの変更が反映されません！Deploy完了まで待機してください。

**チェックリスト:**
- [ ] コードを完全に置き換えた
- [ ] **「Deploy」** ボタンをクリックした
- [ ] Deploy完了を確認した（「Deployment successful」メッセージ）
- [ ] テスト実行で期待する結果が返される

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
ランタイム: Python 3.13
アーキテクチャ: x86_64
デフォルトの実行ロールの変更: 既存のロールを使用する → BedrockAgentLambdaRole
```

3. **「関数の作成」** をクリック

#### 3-5. インスタンス再起動Lambda関数のコード

**重要**: デフォルトのコードを完全に削除して、以下のコードに **置き換え** してください。

1. **「コード」** タブをクリック
2. **lambda_function.py** の内容をすべて削除
3. `reboot-instances-refactored.py` の完全なコードを **コピー&ペースト**
4. **「Deploy」** ボタンをクリックして **必ずデプロイ** してください

**重要**: Deployしないとコードの変更が反映されません！Deploy完了まで待機してください。

#### 3-6. Lambda関数の設定

1. **「設定」** タブをクリック
2. **「一般設定」** → **「編集」**

**設定値:**
```
タイムアウト: 5分
メモリ: 256 MB
```

3. **「保存」** をクリック

#### 3-7. Lambda関数の権限設定

**ログ取得Lambda関数の権限設定:**
1. **get-log-refactored** 関数ページで **「設定」** タブをクリック
2. **「アクセス権限」** をクリック
3. **リソースベースのポリシーステートメント** セクションで **「アクセス権限を追加」** をクリック
4. 以下の設定を入力：

```
ステートメントID: bedrock-agent-access
プリンシパル: bedrock.amazonaws.com
アクション: lambda:InvokeFunction
```

**重要**: 
- `[アカウントID]` を実際のAWSアカウントIDに置き換えてください
- 初回作成時にはソースARN入力欄がない場合があります
- 作成後、ステートメントを編集して以下を追加:
  ```
  ソースARN: arn:aws:bedrock:us-east-1:[アカウントID]:agent/*
  ```

**AWSアカウントIDの確認方法:**
- AWS Management Consoleの右上のアカウント名をクリック
- 表示される12桁の数字がアカウントID

5. **「保存」** をクリック

**インスタンス再起動Lambda関数の権限設定:**
1. **reboot-instances-refactored** 関数ページで同様の手順を実行
2. 同じ設定でリソースベースポリシーを追加

**代替方法（AWS CLIを使用する場合）:**
```bash
# ログ取得Lambda関数の権限追加
aws lambda add-permission \
  --function-name get-log-refactored \
  --statement-id bedrock-agent-access \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:[アカウントID]:agent/*"

# インスタンス再起動Lambda関数の権限追加
aws lambda add-permission \
  --function-name reboot-instances-refactored \
  --statement-id bedrock-agent-access \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:[アカウントID]:agent/*"
```

#### 3-8. Lambda関数のテスト

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
  "actionGroup": "RetrieveLogsActionGroup",
  "apiPath": "/get-logs",
  "httpMethod": "GET"
}
```

5. **「テスト」** をクリック

**注意**: テスト実行前に必ず **「Deploy」** が完了していることを確認してください！

6. **実行結果を確認:**
   - ステータスコードが200であること
   - レスポンス形式が正しいこと
   - エラーがないこと
   - **"Hello from Lambda!"** が返される場合は、Deployが完了していません

**レスポンス確認ポイント:**
```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "RetrieveLogsActionGroup",
    "apiPath": "/get-logs",
    "httpMethod": "GET",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": {
          "status": "success",
          "error_logs": [...],
          "summary": {...}
        }
      }
    }
  }
}
```

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

#### 4-1. Bedrockエージェントの作成

**事前準備でAmazon Nova Proを有効化済みの前提で進めます。**

1. **Amazon Bedrock** サービスに移動
2. 左側メニューから **「エージェント」** を選択
3. **「エージェントを作成」** をクリック

#### 4-2. エージェントの基本設定

**エージェントの詳細:**
```
エージェント名: bedrock-troubleshooting-agent
説明: EC2インスタンスのトラブルシューティングを自動化するエージェント
```

**重要**: エージェント向けの指示を入力後、一度 **「保存」** を押してからアクショングループを作成してください。指示内容が消える場合があります。

**モデル選択:**
```
モデル: Amazon Nova Pro（推奨）または Claude 3.5 Sonnet
```

**Nova Proの利点:**
- Amazonの最新ファウンデーションモデル（2024年12月リリース）
- 高いコスト効率性
- 優れた推論能力とコード理解
- 日本語サポート
- 技術的なトラブルシューティングタスクに最適化

**注意事項:**
- Nova Proが利用可能なリージョンであることを確認
- モデルのアクセス許可が有効になっていることを確認

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
アクショングループタイプ: API スキーマで定義
```

3. **アクショングループの呼び出し:**
   - **既存の Lambda 関数を選択** → `get-log-refactored`

4. **APIスキーマの定義:**
   **インラインスキーマエディタで定義** を選択し、以下をコピー&ペースト:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Log Retrieval API",
    "version": "1.0.0",
    "description": "API for retrieving CloudWatch error logs"
  },
  "paths": {
    "/get-logs": {
      "get": {
        "summary": "Retrieve error logs from CloudWatch",
        "description": "Retrieves and analyzes error logs from CloudWatch Logs for troubleshooting purposes",
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
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "error_logs": {
                      "type": "array"
                    },
                    "summary": {
                      "type": "object"
                    }
                  }
                }
              }
            }
          },
          "500": {
            "description": "Internal server error",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "error": {
                      "type": "string"
                    }
                  }
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

5. **「作成」** をクリック

**インスタンス再起動アクショングループ:**
1. **「アクショングループを追加」** をクリック
2. **アクショングループの詳細:**

```
アクショングループ名: RebootInstancesActionGroup
説明: EC2インスタンスの安全な再起動
アクショングループタイプ: API スキーマで定義
```

3. **アクショングループの呼び出し:**
   - **既存の Lambda 関数を選択** → `reboot-instances-refactored`

4. **APIスキーマの定義:**
   **インラインスキーマエディタで定義** を選択し、以下をコピー&ペースト:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Instance Reboot API",
    "version": "1.0.0",
    "description": "API for safely rebooting EC2 instances"
  },
  "paths": {
    "/reboot-instance": {
      "post": {
        "summary": "Reboot EC2 instance",
        "description": "Safely reboots EC2 instances with validation and confirmation steps",
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
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "instance_id": {
                      "type": "string"
                    },
                    "action": {
                      "type": "string"
                    },
                    "message": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          },
          "400": {
            "description": "Bad request",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "error": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          },
          "500": {
            "description": "Internal server error",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    },
                    "error": {
                      "type": "string"
                    }
                  }
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

5. **「作成」** をクリック

#### 4-5. エージェントの準備

1. アクショングループ作成後、**「保存」** をクリック
2. **「準備」** をクリック
3. 準備プロセスが完了するまで待機（数分かかります）

---

### ステップ5: エージェントのテスト (20分)

#### 5-1. エージェントテストの実行

**エージェント準備完了後、画面右側にテストエージェントが表示されます。**

**テスト画面の見やすさ改善:**
- **画面を広くする**: ブラウザを全画面表示にする
- **ズームアウト**: ブラウザのズームを75-80%に設定
- **チャット履歴の確認**: 左側のチャット履歴で過去の応答を確認可能
- **コピー機能**: 応答をクリックしてコピー → メモ帳等に貼り付けて確認

#### 5-2. 基本動作テスト

**テスト1: システム状況確認**
```
ユーザー入力: "システムの状況を確認してください"
```

**期待される動作:**
- エージェントがRetrieveLogsアクションを実行
- ログ分析結果を表示
- エラーの有無を報告

**成功例の応答内容:**
```
## EC2インスタンス再起動の提案

### 対象インスタンス
- インスタンスID: i-046d77ef6ecd2f058
- 現在の状態: 稼働中
- 問題: テストエラー（意図的にトリガーされたエラー）

### 再起動の理由
テストエラーはシステムの健全性に影響を与えるものではありません...

### 予想される効果
再起動は不要です...

**この操作を実行してもよろしいですか？ 「はい」と回答いただければ再起動を実行します。**
ただし、この場合、再起動は推奨されません。
```

**✅ 正常動作の確認ポイント:**
- インスタンスIDが正確に抽出されている
- テストエラーであることを適切に認識
- 再起動が不要であることを正しく判断

**応答例の確認ポイント:**
- インスタンスID（i-xxxxxxxxx）が正しく抽出されているか
- エラーの重要度が適切に分析されているか
- 再起動の必要性が適切に判断されているか

**表示改善のコツ:**
1. **応答の全文をコピー**: 応答エリアをクリック → Ctrl+A → Ctrl+C
2. **メモ帳に貼り付け**: 改行が正しく表示される
3. **ブラウザの開発者ツール**: F12キー → Console タブで詳細確認

**代替テスト方法（より見やすい）:**
1. **AWS CLI使用**:
   ```bash
   aws bedrock-agent-runtime invoke-agent \
     --agent-id [エージェントID] \
     --agent-alias-id [エイリアスID] \
     --session-id test-session \
     --input-text "システムの状況を確認してください" \
     response.json
   ```
2. **別のブラウザタブで確認**: 新しいタブでエージェントを開く
3. **画面分割**: エージェント画面とメモ帳を左右に分割表示

**テスト2: 実際の再起動テスト**
```
ユーザー入力: "インスタンス i-046d77ef6ecd2f058 を再起動してください"
ユーザー確認: "はい"
```

**再起動確認方法:**

1. **EC2コンソールでの確認**:
   - EC2サービス → インスタンス
   - 対象インスタンスの **「状態」** カラムを確認
   - `running` → `stopping` → `pending` → `running` の遷移を確認

2. **AWS CLIでの確認**:
   ```bash
   # インスタンス状態の確認
   aws ec2 describe-instances --instance-ids i-046d77ef6ecd2f058 \
     --query 'Reservations[0].Instances[0].State.Name'
   
   # 起動時刻の確認（再起動後は新しい時刻になる）
   aws ec2 describe-instances --instance-ids i-046d77ef6ecd2f058 \
     --query 'Reservations[0].Instances[0].LaunchTime'
   ```

3. **Session Managerでの確認**:
   ```bash
   # システムの起動時刻確認（再起動後は新しくなる）
   uptime
   
   # 最新の再起動ログ確認
   sudo journalctl -b 0 | head -20
   
   # システム起動ログの確認
   who -b
   ```

4. **CloudWatch メトリクスでの確認**:
   - CloudWatch → メトリクス → EC2 → Per-Instance Metrics
   - インスタンスIDで検索 → **StatusCheckFailed** メトリクス
   - 再起動時にメトリクスが一時的に途切れることを確認

5. **Flask アプリケーションでの確認**:
   ```bash
   # アプリケーションの再起動確認
   curl http://[PublicIP]/
   
   # プロセス起動時刻の確認
   ps -eo pid,lstart,cmd | grep python3
   ```

**再起動完了の確認ポイント:**
- ✅ EC2コンソールで状態が `running` に戻る
- ✅ Session Manager で接続できる  
- ✅ Flask アプリケーションが応答する
- ✅ `uptime` コマンドで短い稼働時間が表示される

**最も簡単な確認方法:**
1. **EC2コンソール**を開いたまま再起動を実行
2. **「更新」**ボタンを数回クリックして状態変化を確認
3. **Session Manager**で `uptime` コマンド実行:
   ```bash
   uptime
   # 出力例: 15:45:23 up 2 min, 0 users, load average: 0.12, 0.24, 0.18
   #        ↑ 2分間しか稼働していない = 最近再起動された
   ```

**再起動前の準備:**
```bash
# 再起動前に現在の稼働時間を記録
uptime
# 例: 15:30:15 up 2 days, 3:45, 0 users...
```

**注意**: 再起動には通常2-3分かかります。Session Managerの接続も一時的に切断されます。

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
# Session ManagerでEC2インスタンスに接続して確認
sudo systemctl status amazon-cloudwatch-agent
sudo journalctl -u amazon-cloudwatch-agent

# CloudWatch Agent設定の確認
sudo cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# IAMロールの確認
# EC2コンソールでインスタンスのIAMロール（FlaskAppRole）が正しく設定されているか確認
```

**問題2: Session Managerで接続できない**
- CloudFormationスタックが正常に作成されているか確認
- EC2インスタンスにIAMロール（FlaskAppRole）が正しくアタッチされているか確認
- Systems Manager エージェントが実行されているか確認:
```bash
sudo systemctl status amazon-ssm-agent
```

**問題3: Flaskアプリケーションが起動していない**
```bash
# アプリケーションの状態確認
sudo systemctl status flask-app
sudo journalctl -u flask-app

# 手動で起動テスト
sudo python3 /opt/flask-app/app.py
```

**問題4: Lambda関数がタイムアウトする**
- タイムアウト時間を延長
- メモリサイズを増加

**問題5: エージェントがLambda関数にアクセスできない**
```
エラー: "Access denied while invoking Lambda function"
```
**解決方法:**
1. Lambda関数の **「設定」** → **「アクセス権限」** → **「リソースベースのポリシーステートメント」**
2. Bedrockからの呼び出しを許可するポリシーが設定されているか確認
3. ソースARNが正しいアカウントIDになっているか確認

**問題6: Lambda関数のレスポンスエラー**
```
エラー: "The server encountered an error processing the Lambda response"
```
**解決方法:**
1. **Lambda関数のログを確認:**
   ```bash
   # CloudWatch Logsでエラー詳細を確認
   aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/get-log-refactored"
   ```
2. **よくある原因:**
   - レスポンス形式が不正（JSON構造エラー）
   - 必須フィールドの欠如
   - 文字エンコーディングの問題
   - タイムアウトエラー

3. **Lambda関数のテスト実行で詳細確認:**
   - Lambda Console → テスト → 実行結果とログを確認

**緊急対応手順:**
1. **Lambda関数を直接テスト:**
   ```json
   {
     "parameters": [
       {"name": "logGroup", "value": "/aws/ec2/my-flask-application"},
       {"name": "hoursAgo", "value": "24"}
     ],
     "actionGroup": "RetrieveLogsActionGroup",
     "apiPath": "/get-logs",
     "httpMethod": "GET"
   }
   ```

2. **CloudWatch Logsでエラー確認:**
   - AWS Console → CloudWatch → ログ
   - `/aws/lambda/get-log-refactored` を確認
   - 最新のエラーログを確認

3. **よくある修正点:**
   - **Deploy忘れ**: コード変更後にDeployボタンを押していない
   - レスポンスのJSON形式確認
   - `ensure_ascii=False` の設定確認
   - 例外処理の見直し

**問題0: Lambda関数が古いコードを実行している**
```
症状: "Hello from Lambda!" が返される
```
**解決方法:**
1. Lambda関数のコードを正しく置き換えたか確認
2. **「Deploy」** ボタンをクリックしたか確認
3. Deploy完了後に再テスト実行

**問題1: エラーログが見つからない（CloudWatchには存在）**
```
症状: "No error logs found" だが、CloudWatchにはErrorログが存在
```
**原因と解決方法:**

1. **ロググループ名の不一致:**
   ```bash
   # CloudWatchで実際のロググループ名を確認
   aws logs describe-log-groups --log-group-name-prefix "/aws/ec2"
   ```
   - `/aws/ec2/my-flask-application` が存在するか確認
   - 実際の名前が異なる場合は Lambda関数のパラメータを修正

2. **時間範囲の問題:**
   ```json
   # テスト時に時間範囲を短くして確認
   {
     "parameters": [
       {"name": "logGroup", "value": "/aws/ec2/my-flask-application"},
       {"name": "hoursAgo", "value": "1"}
     ],
     "actionGroup": "RetrieveLogsActionGroup",
     "apiPath": "/get-logs",
     "httpMethod": "GET"
   }
   ```

3. **時間の問題（最も可能性が高い）:**
   - ログの記録時刻とLambda実行時刻の差
   - タイムゾーンの違い（UTC vs JST）
   
**時間範囲の確認:**
```json
# テスト時に時間範囲を1時間に短縮
{
  "parameters": [
    {"name": "logGroup", "value": "/aws/ec2/my-flask-application"},
    {"name": "hoursAgo", "value": "1"}
  ],
  "actionGroup": "RetrieveLogsActionGroup",
  "apiPath": "/get-logs",
  "httpMethod": "GET"
}
```

4. **フィルターパターンの確認:**
   - `?ERROR ?Exception ?Traceback` は正しいパターン
   - CloudWatchで手動検索して確認

4. **IAM権限の問題（現在の問題）:**
   ```
   エラー: "User: arn:aws:sts::730335541232:assumed-role/BedrockAgentLambdaRole/get-log-refactored is not authorized to perform: logs:FilterLogEvents"
   ```
   
   **緊急修正手順:**
   1. **IAMサービス** に移動
   2. **「ポリシー」** → **「BedrockAgentLambdaPolicy」** を検索・選択
   3. **「編集」** をクリック
   4. **「JSON」** タブで以下を確認・追加:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "logs:DescribeLogGroups",
       "logs:DescribeLogStreams",
       "logs:GetLogEvents",
       "logs:FilterLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:log-group:/aws/ec2/my-flask-application:*"
   }
   ```
   5. **「変更を保存」** をクリック
   6. 数分待機後、Lambda関数を再テスト

**問題2: インスタンス再起動でアクセス拒否**
```
エラー: "Instance i-xxxxxxxxx not found"
```
**原因と解決方法:**

1. **IAMポリシーの条件が厳しすぎる**:
   - 現在のポリシーに `ec2:ResourceTag/Environment` 条件がある
   - CloudFormationで作成したインスタンスにはこのタグがない

2. **緊急修正手順**:
   ```
   1. IAMサービス → ポリシー → BedrockAgentLambdaPolicy
   2. 編集 → JSON タブ
   3. EC2権限の部分を以下に修正:
   ```
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "ec2:DescribeInstances",
       "ec2:RebootInstances"
     ],
     "Resource": "*"
   }
   ```
   ```
   4. Condition部分を削除
   5. 変更を保存
   ```

3. **代替案（タグを追加する方法）**:
   
   **方法A: AWS CLIでタグ追加**
   ```bash
   # EC2インスタンスにタグを追加
   aws ec2 create-tags \
     --resources i-046d77ef6ecd2f058 \
     --tags Key=Environment,Value=demo
   ```
   
   **方法B: EC2コンソールでタグ追加**
   ```
   1. EC2サービス → インスタンス
   2. 対象インスタンスを選択
   3. 「タグ」タブ → 「タグを管理」
   4. 「タグを追加」をクリック
   5. キー: Environment, 値: demo
   6. 「変更を保存」
   ```

**推奨**: IAMポリシーの条件を削除する方法（方法2）が最も簡単です。

**問題3: インスタンス再起動Lambda関数のデバッグ**
```
症状: IAMポリシーは正しいが、まだ "Instance not found" エラー
```

**デバッグ手順:**

1. **Lambda関数 `reboot-instances-refactored` の直接テスト**:
   ```json
   {
     "parameters": [
       {"name": "instanceId", "value": "i-046d77ef6ecd2f058"},
       {"name": "dryRun", "value": "true"}
     ],
     "actionGroup": "RebootInstancesActionGroup",
     "apiPath": "/reboot-instance",
     "httpMethod": "POST"
   }
   ```

2. **Lambda関数のログ確認**:
   - CloudWatch → ログ → `/aws/lambda/reboot-instances-refactored`
   - 実際のエラーメッセージを確認

3. **インスタンスIDの確認**:
   ```bash
   # AWS CLIでインスタンスが存在するか確認
   aws ec2 describe-instances --instance-ids i-046d77ef6ecd2f058
   ```

4. **最も可能性が高い問題: Lambda関数のコード未設定**:
   - `reboot-instances-refactored` の **「コード」** タブを確認
   - **デフォルトコード（"Hello from Lambda!"）のままでないか確認**
   - `reboot-instances-refactored.py` のコードが正しく設定されているか
   - **Deploy** ボタンをクリックしたか確認

**緊急対応: Lambda関数がデフォルトコードの場合**
1. **Lambda関数のコードを完全に置き換え**
2. `reboot-instances-refactored.py` の全コードをコピー&ペースト
3. **「Deploy」** ボタンをクリック（重要！）
4. 数分待機後に再テスト

5. **Lambda関数のデバッグ出力追加**:
   ```python
   # Lambda関数の最初に追加
   print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
   print(f"Instance ID to process: {instance_id}")
   ```

**問題4: Lambda関数が出力なしで終了**
```
症状: ログに "Received event" のみ表示され、その後出力がない
```

**原因: Python例外またはBedrockエージェント用レスポンス形式の問題**

**緊急対応:**
1. **Lambda関数に詳細なデバッグを追加**:
   ```python
   def lambda_handler(event, context):
       print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
       
       try:
           # パラメータの取得
           instance_id = None
           dry_run = False
           force = False
           
           print("Processing parameters...")
           if 'parameters' in event:
               for param in event['parameters']:
                   print(f"Parameter: {param['name']} = {param['value']}")
                   if param['name'] == 'instanceId':
                       instance_id = param['value']
                   elif param['name'] == 'dryRun':
                       dry_run = param['value'].lower() == 'true'
                   elif param['name'] == 'force':
                       force = param['value'].lower() == 'true'
           
           print(f"Extracted parameters - Instance: {instance_id}, DryRun: {dry_run}, Force: {force}")
           
           if not instance_id:
               raise ValueError("Instance ID is required")
           
           # ここでEC2処理を実行
           # ...
           
       except Exception as e:
           print(f"ERROR in lambda_handler: {str(e)}")
           import traceback
           print(f"Traceback: {traceback.format_exc()}")
           raise e
   ```

2. **Deployして再テスト**
3. **エラーログを詳細確認**

**一時的な簡易テスト用Lambda関数（動作確認用）:**
```python
import json

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
    
    try:
        # パラメータの取得
        instance_id = None
        dry_run = False
        
        if 'parameters' in event:
            for param in event['parameters']:
                if param['name'] == 'instanceId':
                    instance_id = param['value']
                elif param['name'] == 'dryRun':
                    dry_run = param['value'].lower() == 'true'
        
        print(f"Processing instance: {instance_id}, dry_run: {dry_run}")
        
        # 簡易レスポンス
        result = {
            "status": "success",
            "action": "dry_run" if dry_run else "reboot",
            "instance_id": instance_id,
            "message": f"Instance {instance_id} would be {'checked' if dry_run else 'rebooted'}"
        }
        
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": result
                    }
                }
            }
        }
        
        print(f"Response: {json.dumps(response, ensure_ascii=False)}")
        return response
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        error_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": {
                            "status": "error",
                            "error": str(e)
                        }
                    }
                }
            }
        }
        return error_response
```

**この簡易版をテストして動作を確認してから、完全版に戻してください。**

**問題解決: 簡易版が動作する場合の完全版Lambda関数**

簡易版が正常に動作したので、以下の完全版に置き換えてください：

```python
import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
    
    try:
        # パラメータの取得
        instance_id = None
        dry_run = False
        force = False
        
        print("Processing parameters...")
        if 'parameters' in event:
            for param in event['parameters']:
                print(f"Parameter: {param['name']} = {param['value']}")
                if param['name'] == 'instanceId':
                    instance_id = param['value']
                elif param['name'] == 'dryRun':
                    dry_run = param['value'].lower() == 'true'
                elif param['name'] == 'force':
                    force = param['value'].lower() == 'true'
        
        print(f"Extracted parameters - Instance: {instance_id}, DryRun: {dry_run}, Force: {force}")
        
        if not instance_id:
            raise ValueError("Instance ID is required")
        
        # EC2クライアントの初期化
        ec2_client = boto3.client('ec2')
        
        # インスタンス情報の確認
        print(f"Checking instance {instance_id}...")
        try:
            response = ec2_client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                raise Exception(f"Instance {instance_id} not found")
            
            instance = response['Reservations'][0]['Instances'][0]
            instance_state = instance['State']['Name']
            instance_type = instance['InstanceType']
            
            print(f"Instance found - State: {instance_state}, Type: {instance_type}")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidInstanceID.NotFound':
                raise Exception(f"Instance {instance_id} not found")
            else:
                raise Exception(f"Failed to describe instance: {str(e)}")
        
        # 再起動処理
        if dry_run:
            print("Dry run mode - no actual reboot will be performed")
            result = {
                "status": "success",
                "action": "dry_run",
                "instance_id": instance_id,
                "message": f"Dry run successful. Instance {instance_id} is in state '{instance_state}' and would be rebooted.",
                "instance_state": instance_state,
                "instance_type": instance_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            print(f"Performing actual reboot of instance {instance_id}...")
            try:
                reboot_response = ec2_client.reboot_instances(
                    InstanceIds=[instance_id],
                    DryRun=False
                )
                print("Reboot command sent successfully")
                
                result = {
                    "status": "success",
                    "action": "reboot",
                    "instance_id": instance_id,
                    "message": f"Instance {instance_id} reboot initiated successfully.",
                    "instance_state": instance_state,
                    "instance_type": instance_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'IncorrectInstanceState':
                    raise Exception(f"Cannot reboot instance {instance_id} in current state '{instance_state}'")
                elif error_code == 'InvalidInstanceID.NotFound':
                    raise Exception(f"Instance {instance_id} not found")
                else:
                    raise Exception(f"Failed to reboot instance: {str(e)}")
        
        # レスポンスの構築
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": result
                    }
                }
            }
        }
        
        print(f"Response: {json.dumps(response, ensure_ascii=False)}")
        return response
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        error_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": {
                            "status": "error",
                            "error": str(e),
                            "instance_id": instance_id if 'instance_id' in locals() else "unknown",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                }
            }
        }
        return error_response
```

**Deploy後のテスト手順:**
1. **「Deploy」** をクリック
2. **ドライランテスト**:
   ```json
   {
     "parameters": [
       {"name": "instanceId", "value": "i-046d77ef6ecd2f058"},
       {"name": "dryRun", "value": "true"}
     ],
     "actionGroup": "RebootInstancesActionGroup",
     "apiPath": "/reboot-instance",
     "httpMethod": "POST"
   }
   ```
3. **実際の再起動テスト**:
   ```json
   {
     "parameters": [
       {"name": "instanceId", "value": "i-046d77ef6ecd2f058"},
       {"name": "dryRun", "value": "false"}
     ],
     "actionGroup": "RebootInstancesActionGroup",
     "apiPath": "/reboot-instance",
     "httpMethod": "POST"
   }
   ```

**✅ ドライランテスト成功例:**
```
Processing parameters...
Parameter: instanceId = i-046d77ef6ecd2f058
Parameter: dryRun = true
Extracted parameters - Instance: i-046d77ef6ecd2f058, DryRun: True, Force: False
Checking instance i-046d77ef6ecd2f058...
Instance found - State: running, Type: t3.micro
Dry run mode - no actual reboot will be performed
Response: {"messageVersion": "1.0", "response": {...}}
```

**✅ 実際の再起動テスト成功例:**
```
Processing parameters...
Parameter: instanceId = i-046d77ef6ecd2f058
Parameter: dryRun = false
Extracted parameters - Instance: i-046d77ef6ecd2f058, DryRun: False, Force: False
Checking instance i-046d77ef6ecd2f058...
Instance found - State: running, Type: t3.micro
Performing actual reboot of instance i-046d77ef6ecd2f058...
Reboot command sent successfully
Response: {"messageVersion": "1.0", "response": {...}}
```

**🎉 Lambda関数による再起動が完全に動作確認済み！**

**次のステップ: Bedrockエージェントでの実際のテスト**
1. **「エージェントを準備」** (未実行の場合)
2. **「テスト」** タブでエージェントをテスト:
   ```
   ユーザー入力: "インスタンス i-046d77ef6ecd2f058 をドライランで再起動してください"
   ```
3. **実際の再起動テスト**:
   ```
   ユーザー入力: "インスタンス i-046d77ef6ecd2f058 を再起動してください"
   ユーザー確認: "はい"
   ```

**デバッグ手順:**
1. **CloudWatchで手動確認:**
   - ロググループ `/aws/ec2/my-flask-application` を開く
   - フィルターパターン `ERROR` で検索
   - 結果が表示されるか確認

2. **Lambda関数のログ確認:**
   - CloudWatch → ログ → `/aws/lambda/get-log-refactored`
   - 実行時のエラーメッセージを確認

3. **テスト用の簡単なフィルター:**
   ```python
   # Lambda関数で一時的にフィルターパターンを変更
   filter_pattern = ''  # 空文字でフィルターなし
   # または
   filter_pattern = 'ERROR'  # シンプルなERRORパターン
   ```

**緊急デバッグ手順:**
1. Lambda関数の `get-log-refactored` を開く
2. デバッグ出力を追加済みのコードをDeployする
3. テスト実行後、CloudWatch Logsで `/aws/lambda/get-log-refactored` を確認
4. 以下の情報を確認:
   - 検索時間範囲
   - 検出されたイベント数
   - 実際のエラーメッセージ

**最も可能性が高い原因: 時間範囲**
- エラーログが24時間以内に記録されているか確認
- テスト時に `"hoursAgo": "1"` を使用

**問題7: エージェントがアクションを実行できない**
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
