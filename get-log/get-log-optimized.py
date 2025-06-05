import boto3
import json
import time
from datetime import datetime

def get_error_logs(log_group_name, hours_ago=24):
    """
    CloudWatch Logsから指定された条件でエラーログを効率的に取得する

    Args:
        log_group_name: ロググループ名
        hours_ago: 何時間前からのログを取得するか

    Returns:
        エラー情報を含むリスト
    """
    logs_client = boto3.client('logs')
    end_time = int(time.time() * 1000)
    start_time = end_time - (hours_ago * 60 * 60 * 1000)
    
    try:
        # filter_log_eventsを使用して直接エラーログをフィルタリング
        # これにより複数のAPI呼び出しを削減
        paginator = logs_client.get_paginator('filter_log_events')
        response_iterator = paginator.paginate(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            filterPattern='ERROR OR Exception OR Traceback',
            PaginationConfig={'MaxItems': 100}  # 取得する最大イベント数を制限
        )
        
        error_logs = []
        for page in response_iterator:
            for event in page.get('events', []):
                error_logs.append({
                    'timestamp': event['timestamp'],
                    'logStreamName': event['logStreamName'],
                    'message': event['message'],
                    'time': datetime.fromtimestamp(event['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return error_logs
        
    except Exception as e:
        print(f"Error getting logs: {e}")
        return {'error': str(e)}

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