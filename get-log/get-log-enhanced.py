import boto3
import json
import time
from datetime import datetime
import re

def get_error_logs(log_group_name, hours_ago=24):
    """
    CloudWatch Logsから指定された条件でエラーログを効率的に取得し、高度な分析を行う

    Args:
        log_group_name: ロググループ名
        hours_ago: 何時間前からのログを取得するか

    Returns:
        エラー情報を含むリストと分析結果
    """
    logs_client = boto3.client('logs')
    end_time = int(time.time() * 1000)
    start_time = end_time - (hours_ago * 60 * 60 * 1000)
    
    try:
        # filter_log_eventsを使用して直接エラーログをフィルタリング
        paginator = logs_client.get_paginator('filter_log_events')
        response_iterator = paginator.paginate(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            filterPattern='ERROR OR Exception OR Traceback',
            PaginationConfig={'MaxItems': 100}
        )
        
        error_logs = []
        for page in response_iterator:
            for event in page.get('events', []):
                # JSONフォーマットのログを解析
                try:
                    message = event['message']
                    log_data = message
                    
                    # JSONフォーマットの場合は解析
                    if message.strip().startswith('{') and message.strip().endswith('}'):
                        try:
                            log_data = json.loads(message)
                        except:
                            pass
                    
                    error_logs.append({
                        'timestamp': event['timestamp'],
                        'logStreamName': event['logStreamName'],
                        'message': message,
                        'parsed_data': log_data if isinstance(log_data, dict) else None,
                        'time': datetime.fromtimestamp(event['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    print(f"Error parsing log event: {e}")
        
        # エラーログの分析
        analysis_result = analyze_error_logs(error_logs)
        
        return {
            'logs': error_logs,
            'analysis': analysis_result
        }
        
    except Exception as e:
        print(f"Error getting logs: {e}")
        return {'error': str(e)}

def analyze_error_logs(error_logs):
    """
    エラーログを分析して、パターンや傾向を特定する

    Args:
        error_logs: エラーログのリスト

    Returns:
        分析結果を含む辞書
    """
    if not error_logs:
        return {
            'count': 0,
            'message': 'エラーログが見つかりませんでした'
        }
    
    # インスタンスIDを抽出
    instance_ids = set()
    instance_id_pattern = r'i-[0-9a-f]{8,17}'
    
    # エラーメッセージの頻度を集計
    error_types = {}
    timestamps = []
    
    for log in error_logs:
        # インスタンスIDの抽出
        message = log.get('message', '')
        matches = re.findall(instance_id_pattern, message)
        for match in matches:
            instance_ids.add(match)
        
        # JSONデータからインスタンスIDを抽出
        parsed_data = log.get('parsed_data', {})
        if parsed_data and isinstance(parsed_data, dict):
            system_info = parsed_data.get('system_info', {})
            if system_info and isinstance(system_info, dict):
                instance_id = system_info.get('instance_id')
                if instance_id and re.match(instance_id_pattern, instance_id):
                    instance_ids.add(instance_id)
        
        # エラータイプの集計
        error_type = 'Unknown Error'
        if 'Exception' in message:
            exception_match = re.search(r'([A-Za-z]+Error|[A-Za-z]+Exception)', message)
            if exception_match:
                error_type = exception_match.group(1)
        
        error_types[error_type] = error_types.get(error_type, 0) + 1
        timestamps.append(log.get('timestamp', 0))
    
    # 時間的な分布を分析
    timestamps.sort()
    time_distribution = {}
    if timestamps:
        first_error = datetime.fromtimestamp(timestamps[0]/1000).strftime('%Y-%m-%d %H:%M:%S')
        last_error = datetime.fromtimestamp(timestamps[-1]/1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # エラーの時間間隔を計算
        intervals = []
        for i in range(1, len(timestamps)):
            interval_seconds = (timestamps[i] - timestamps[i-1]) / 1000
            intervals.append(interval_seconds)
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        time_distribution = {
            'first_error': first_error,
            'last_error': last_error,
            'average_interval_seconds': avg_interval
        }
    
    # 分析結果をまとめる
    analysis = {
        'count': len(error_logs),
        'instance_ids': list(instance_ids),
        'error_types': error_types,
        'time_distribution': time_distribution,
        'recurring': len(error_logs) > 1 and len(error_types) == 1  # 同じエラーが複数回発生している場合は繰り返しエラーと判断
    }
    
    return analysis

def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    print(f"Received event: {json.dumps(event)}")
    
    # デフォルト値の設定
    log_group_name = '/aws/ec2/my-flask-application'
    hours_ago = 24
    
    # イベントからパラメータを取得
    if 'parameters' in event:
        for param in event['parameters']:
            if param['name'] == 'logGroup':
                log_group_name = param['value']
            elif param['name'] == 'hoursAgo':
                try:
                    hours_ago = int(param['value'])
                except ValueError:
                    print(f"Invalid hoursAgo value: {param['value']}, using default")
    
    error_info = get_error_logs(log_group_name, hours_ago)
    
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
                    "body": error_info
                }
            }
        }
    }
    
    print(f"Response: {json.dumps(response)}")
    return response