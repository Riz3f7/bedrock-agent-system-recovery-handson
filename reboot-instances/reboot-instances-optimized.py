import boto3
import json

def reboot_instance(instance_id):
    """
    指定されたEC2インスタンスを再起動する

    Args:
        instance_id: 再起動するインスタンスのID

    Returns:
        成功時は {'success': True, 'message': メッセージ}
        失敗時は {'success': False, 'error': エラーメッセージ}
    """
    ec2 = boto3.client('ec2')
    try:
        ec2.reboot_instances(InstanceIds=[instance_id], DryRun=False)
        print(f"Rebooting instance {instance_id}")
        return {'success': True, 'message': f'Successfully rebooted instance {instance_id}'}
    except Exception as e:
        print(f"Error rebooting instance {instance_id}: {e}")
        return {'success': False, 'error': str(e)}

def create_response(event, status_code, body):
    """
    Bedrockエージェント用のレスポンスを生成する

    Args:
        event: 受信したイベント
        status_code: HTTPステータスコード
        body: レスポンスボディ

    Returns:
        フォーマット済みのレスポンス
    """
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(body)
                }
            }
        }
    }

def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    print(f"Received event: {json.dumps(event)}")

    # パラメータからインスタンスIDを取得
    instance_id = None
    if 'parameters' in event:
        for param in event['parameters']:
            if param['name'] == 'instanceId':
                instance_id = param['value']
                break

    # インスタンスIDが見つからない場合、エラーレスポンスを返す
    if not instance_id:
        error_response = create_response(
            event, 
            400, 
            {'error': 'Missing required parameter: instanceId'}
        )
        print(f"Response: {json.dumps(error_response)}")
        return error_response

    # インスタンスの再起動を実行
    result = reboot_instance(instance_id)
    
    # 結果に基づいてレスポンスを生成
    if result['success']:
        response = create_response(event, 200, {'message': result['message']})
    else:
        response = create_response(event, 500, {'error': result['error']})

    print(f"Response: {json.dumps(response)}")
    return response