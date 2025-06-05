import boto3
import json
import time

def reboot_instance(instance_id):
    """
    指定されたEC2インスタンスを再起動する

    Args:
        instance_id: 再起動するインスタンスのID

    Returns:
        成功時は {'success': True, 'message': メッセージ, 'details': 詳細情報}
        失敗時は {'success': False, 'error': エラーメッセージ, 'details': 詳細情報}
    """
    ec2 = boto3.client('ec2')
    try:
        # インスタンスの詳細情報を取得
        instance_details = get_instance_details(instance_id)
        
        # インスタンスを再起動
        ec2.reboot_instances(InstanceIds=[instance_id], DryRun=False)
        print(f"Rebooting instance {instance_id}")
        
        # 再起動後のステータスを確認
        wait_for_status = True
        status_info = {}
        
        if wait_for_status:
            status_info = wait_for_instance_status(instance_id)
        
        return {
            'success': True, 
            'message': f'Successfully rebooted instance {instance_id}',
            'details': {
                'instance_info': instance_details,
                'status_after_reboot': status_info
            }
        }
    except Exception as e:
        print(f"Error rebooting instance {instance_id}: {e}")
        return {
            'success': False, 
            'error': str(e),
            'details': {
                'instance_id': instance_id,
                'timestamp': int(time.time())
            }
        }

def get_instance_details(instance_id):
    """
    EC2インスタンスの詳細情報を取得する

    Args:
        instance_id: インスタンスID

    Returns:
        インスタンスの詳細情報を含む辞書
    """
    ec2 = boto3.client('ec2')
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        if response['Reservations'] and response['Reservations'][0]['Instances']:
            instance = response['Reservations'][0]['Instances'][0]
            
            # 必要な情報を抽出
            instance_info = {
                'instance_id': instance_id,
                'instance_type': instance.get('InstanceType'),
                'state': instance.get('State', {}).get('Name'),
                'availability_zone': instance.get('Placement', {}).get('AvailabilityZone'),
                'private_ip': instance.get('PrivateIpAddress'),
                'public_ip': instance.get('PublicIpAddress'),
                'launch_time': instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else None,
                'tags': instance.get('Tags', [])
            }
            return instance_info
        return {'instance_id': instance_id, 'error': 'Instance not found'}
    except Exception as e:
        print(f"Error getting instance details: {e}")
        return {'instance_id': instance_id, 'error': str(e)}

def wait_for_instance_status(instance_id, max_attempts=10, delay_seconds=5):
    """
    インスタンスのステータスが安定するまで待機する

    Args:
        instance_id: インスタンスID
        max_attempts: 最大試行回数
        delay_seconds: 試行間の待機時間（秒）

    Returns:
        インスタンスのステータス情報
    """
    ec2 = boto3.client('ec2')
    
    for attempt in range(max_attempts):
        try:
            # インスタンスのステータスを確認
            response = ec2.describe_instance_status(InstanceIds=[instance_id])
            
            if response['InstanceStatuses']:
                status = response['InstanceStatuses'][0]
                instance_status = status.get('InstanceStatus', {}).get('Status')
                system_status = status.get('SystemStatus', {}).get('Status')
                
                # 両方のステータスがokになったら成功
                if instance_status == 'ok' and system_status == 'ok':
                    return {
                        'instance_status': instance_status,
                        'system_status': system_status,
                        'attempts': attempt + 1
                    }
            
            # まだ安定していない場合は待機
            time.sleep(delay_seconds)
            
        except Exception as e:
            print(f"Error checking instance status: {e}")
            time.sleep(delay_seconds)
    
    # 最大試行回数に達した場合
    return {
        'instance_status': 'unknown',
        'system_status': 'unknown',
        'attempts': max_attempts,
        'message': 'Max attempts reached while waiting for status'
    }

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
        response = create_response(event, 200, {
            'message': result['message'],
            'details': result['details']
        })
    else:
        response = create_response(event, 500, {
            'error': result['error'],
            'details': result.get('details', {})
        })

    print(f"Response: {json.dumps(response)}")
    return response