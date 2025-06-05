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
    
    def get_log_events(self, log_group_name: str, log_stream_name: str, 
                      start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """ログイベントを取得"""
        try:
            response = self.client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                startTime=start_time,
                endTime=end_time,
                startFromHead=False
            )
            return response.get('events', [])
        except ClientError as e:
            print(f"Warning: Failed to get events from stream {log_stream_name}: {e}")
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
                      max_streams: int = 50) -> Dict[str, Any]:
        """エラーログを取得して分析"""
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours_ago * 60 * 60 * 1000)
            
            # ログストリームを取得
            log_streams = self.cloudwatch_client.get_log_streams(log_group_name, max_streams)
            
            if not log_streams:
                return {
                    'status': 'no_streams',
                    'message': f'No log streams found in {log_group_name}',
                    'error_logs': [],
                    'summary': self._create_empty_summary()
                }
            
            error_logs = []
            processed_streams = 0
            
            for log_stream in log_streams:
                log_stream_name = log_stream['logStreamName']
                
                # ログイベントを取得
                events = self.cloudwatch_client.get_log_events(
                    log_group_name, log_stream_name, start_time, end_time
                )
                
                for event in events:
                    log_entry = self.analyzer.analyze_log_entry(event, log_stream_name)
                    
                    # エラーログのみを収集
                    if self.analyzer.is_error_log(log_entry.message):
                        error_logs.append({
                            'timestamp': log_entry.timestamp,
                            'datetime': datetime.fromtimestamp(log_entry.timestamp / 1000).isoformat(),
                            'logStreamName': log_entry.log_stream_name,
                            'message': log_entry.message,
                            'severity': log_entry.severity,
                            'instanceId': log_entry.instance_id,
                            'errorType': log_entry.error_type
                        })
                
                processed_streams += 1
            
            # 結果をタイムスタンプでソート（新しい順）
            error_logs.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'status': 'success',
                'error_logs': error_logs,
                'summary': self._create_summary(error_logs, processed_streams, hours_ago),
                'metadata': {
                    'log_group': log_group_name,
                    'time_range_hours': hours_ago,
                    'processed_streams': processed_streams,
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
