import boto3
import json

ec2 = boto3.client('ec2')

def reboot_instance(instance_id):
    """
    指定された EC2 インスタンスを再起動する

    Args:
        instance_id: 再起動するインスタンスの ID

    Returns:
        成功時は True、失敗時はエラーメッセージ
    """
    try:
        response = ec2.reboot_instances(InstanceIds=[instance_id], DryRun=False)
        print(f"Rebooting instance {instance_id}: {response}")
        return True
    except Exception as e:
        print(f"Error rebooting instance {instance_id}: {e}")
        return str(e)

def lambda_handler(event, context):
    """
    Lambda 関数のエントリーポイント
    """
    print(f"Received event: {json.dumps(event)}")

    instance_id = None

    try:
        # パラメータから instanceId を取得 (Bedrock エージェント経由の場合)
        if 'parameters' in event:
            for param in event['parameters']:
                if param['name'] == 'instanceId':
                    instance_id = param['value']
                    break

        # instanceId が見つからない場合、エラーメッセージを返す
        if instance_id is None:
            raise KeyError('instanceId')

    except KeyError as e:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 400,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': f'Missing required parameter: {e}'})
                    }
                }
            }
        }
    except Exception as e:
        print(f"Error processing parameters: {e}")
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", ""),
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", ""),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': f'Error processing parameters: {e}'})
                    }
                }
            }
        }

    result = reboot_instance(instance_id)

    # event から apiPath と httpMethod を取得
    api_path = event.get("apiPath", "")
    http_method = event.get("httpMethod", "")

    if result == True:
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event["actionGroup"],
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'message': f'Successfully rebooted instance {instance_id}'})
                    }
                }
            }
        }
    else:
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event["actionGroup"],
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': result})
                    }
                }
            }
        }

    print(f"Response: {json.dumps(response)}")
    return response