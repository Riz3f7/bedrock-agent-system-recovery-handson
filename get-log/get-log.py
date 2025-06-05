import boto3
import json
import time

cloudwatch_logs = boto3.client('logs')

def get_error_logs(log_group_name, hours_ago=24):
    """
    CloudWatch Logs から指定された条件でログを取得し、エラー情報を抽出する

    Args:
        log_group_name: ロググループ名
        hours_ago: 何時間前からのログを取得するか

    Returns:
        エラー情報を含む文字列 (JSON 形式を想定)
    """

    end_time = int(time.time() * 1000)
    start_time = end_time - (hours_ago * 60 * 60 * 1000)

    error_logs = []

    try:
        # ログストリームの一覧を取得
        response = cloudwatch_logs.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LogStreamName',
            descending=True
        )

        for log_stream in response['logStreams']:
            log_stream_name = log_stream['logStreamName']

            # ログイベントを取得
            response = cloudwatch_logs.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                startTime=start_time,
                endTime=end_time,
                startFromHead=False
            )

            for event in response['events']:
                message = event['message']

                # エラーメッセージやスタックトレースなど、特定のパターンを抽出
                if is_error_log(message):
                    error_logs.append({
                        'timestamp': event['timestamp'],
                        'logStreamName': log_stream_name,
                        'message': message
                    })

    except Exception as e:
        print(f"Error getting logs: {e}")
        return {'error': str(e)}  # エラー時は文字列ではなく辞書を返す

    return error_logs  # JSON 文字列ではなくリストを返す

def is_error_log(message):
    """
    ログメッセージがエラーログかどうかを判定する

    Args:
        message: ログメッセージ

    Returns:
        エラーログの場合は True、それ以外は False
    """
    return "ERROR" in message or "Traceback" in message

def lambda_handler(event, context):
    """
    Lambda 関数のエントリーポイント
    """
    print(f"Received event: {json.dumps(event)}") # event の中身をプリント
    log_group_name = '/aws/ec2/my-flask-application'  # ロググループ名
    hours_ago = 24

    # Retrieve parameters from the event
    if 'parameters' in event:
      for param in event['parameters']:
          if param['name'] == 'logGroup':
              log_group_name = param['value']
          elif param['name'] == 'hoursAgo':
              hours_ago = int(param['value'])

    error_info = get_error_logs(log_group_name, hours_ago)

    response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event["actionGroup"],
            "apiPath": event["apiPath"],
            "httpMethod": event["httpMethod"],
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": error_info
                }
            }
        }
    }

    print(f"Response: {json.dumps(response)}") # レスポンスをプリント
    return response