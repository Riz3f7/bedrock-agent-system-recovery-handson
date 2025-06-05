"""
EC2 インスタンス再起動 Lambda 関数 (リファクタリング版)
Claude 3.5/4 Sonnet 最適化
"""

import boto3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from botocore.exceptions import ClientError, BotoCoreError
import time

@dataclass
class InstanceInfo:
    """インスタンス情報のデータクラス"""
    instance_id: str
    state: str
    instance_type: str
    availability_zone: str
    launch_time: Optional[str] = None
    tags: Optional[Dict[str, str]] = None

class EC2Client:
    """EC2 クライアントのラッパークラス"""
    
    def __init__(self):
        self.client = boto3.client('ec2')
    
    def get_instance_info(self, instance_id: str) -> Optional[InstanceInfo]:
        """インスタンス情報を取得"""
        try:
            response = self.client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                return None
            
            instance = response['Reservations'][0]['Instances'][0]
            
            # タグを辞書形式に変換
            tags = {}
            if 'Tags' in instance:
                tags = {tag['Key']: tag['Value'] for tag in instance['Tags']}
            
            return InstanceInfo(
                instance_id=instance['InstanceId'],
                state=instance['State']['Name'],
                instance_type=instance['InstanceType'],
                availability_zone=instance['Placement']['AvailabilityZone'],
                launch_time=instance.get('LaunchTime', '').isoformat() if instance.get('LaunchTime') else None,
                tags=tags
            )
            
        except ClientError as e:
            print(f"Error getting instance info for {instance_id}: {e}")
            return None
    
    def reboot_instance(self, instance_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """インスタンスを再起動"""
        try:
            response = self.client.reboot_instances(
                InstanceIds=[instance_id], 
                DryRun=dry_run
            )
            
            return {
                'success': True,
                'message': f'Successfully initiated reboot for instance {instance_id}',
                'response_metadata': response.get('ResponseMetadata', {})
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'DryRunOperation':
                return {
                    'success': True,
                    'message': f'Dry run successful for instance {instance_id}',
                    'dry_run': True
                }
            elif error_code == 'InvalidInstanceID.NotFound':
                return {
                    'success': False,
                    'error': f'Instance {instance_id} not found',
                    'error_code': error_code
                }
            elif error_code == 'IncorrectInstanceState':
                return {
                    'success': False,
                    'error': f'Instance {instance_id} is in incorrect state for reboot',
                    'error_code': error_code
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to reboot instance {instance_id}: {error_message}',
                    'error_code': error_code
                }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error rebooting instance {instance_id}: {str(e)}'
            }
    
    def wait_for_instance_state(self, instance_id: str, target_state: str, 
                               max_wait_time: int = 300) -> Dict[str, Any]:
        """インスタンスの状態変化を待機"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            instance_info = self.get_instance_info(instance_id)
            
            if not instance_info:
                return {
                    'success': False,
                    'error': f'Instance {instance_id} not found during state check'
                }
            
            if instance_info.state == target_state:
                return {
                    'success': True,
                    'message': f'Instance {instance_id} reached state {target_state}',
                    'current_state': instance_info.state,
                    'wait_time': time.time() - start_time
                }
            
            time.sleep(10)  # 10秒間隔でチェック
        
        return {
            'success': False,
            'error': f'Timeout waiting for instance {instance_id} to reach state {target_state}',
            'current_state': instance_info.state if instance_info else 'unknown',
            'wait_time': time.time() - start_time
        }

class InstanceValidator:
    """インスタンス検証クラス"""
    
    def __init__(self, ec2_client: EC2Client):
        self.ec2_client = ec2_client
    
    def validate_instance_id(self, instance_id: str) -> Dict[str, Any]:
        """インスタンスIDの形式と存在を検証"""
        # インスタンスIDの形式チェック
        if not instance_id or not instance_id.startswith('i-'):
            return {
                'valid': False,
                'error': f'Invalid instance ID format: {instance_id}. Must start with "i-"'
            }
        
        if len(instance_id) < 10:
            return {
                'valid': False,
                'error': f'Invalid instance ID length: {instance_id}'
            }
        
        # インスタンスの存在確認
        instance_info = self.ec2_client.get_instance_info(instance_id)
        if not instance_info:
            return {
                'valid': False,
                'error': f'Instance {instance_id} not found'
            }
        
        return {
            'valid': True,
            'instance_info': instance_info
        }
    
    def can_reboot_instance(self, instance_info: InstanceInfo) -> Dict[str, Any]:
        """インスタンスが再起動可能かチェック"""
        rebootable_states = ['running', 'stopped']
        
        if instance_info.state not in rebootable_states:
            return {
                'can_reboot': False,
                'reason': f'Instance is in state "{instance_info.state}". Can only reboot instances in states: {rebootable_states}'
            }
        
        # 特定のタグによる制限チェック（例：本番環境の保護）
        if instance_info.tags:
            environment = instance_info.tags.get('Environment', '').lower()
            if environment == 'production':
                protection = instance_info.tags.get('RebootProtection', '').lower()
                if protection == 'enabled':
                    return {
                        'can_reboot': False,
                        'reason': 'Instance has reboot protection enabled (RebootProtection=enabled tag)'
                    }
        
        return {
            'can_reboot': True,
            'reason': 'Instance is in valid state for reboot'
        }

class RebootManager:
    """再起動管理メインクラス"""
    
    def __init__(self):
        self.ec2_client = EC2Client()
        self.validator = InstanceValidator(self.ec2_client)
    
    def reboot_instance_with_validation(self, instance_id: str, 
                                      force: bool = False,
                                      dry_run: bool = False) -> Dict[str, Any]:
        """検証付きインスタンス再起動"""
        operation_start = datetime.utcnow()
        
        try:
            # インスタンスIDの検証
            validation_result = self.validator.validate_instance_id(instance_id)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'operation_time': datetime.utcnow().isoformat(),
                    'instance_id': instance_id
                }
            
            instance_info = validation_result['instance_info']
            
            # 再起動可能性のチェック
            if not force:
                reboot_check = self.validator.can_reboot_instance(instance_info)
                if not reboot_check['can_reboot']:
                    return {
                        'success': False,
                        'error': reboot_check['reason'],
                        'operation_time': datetime.utcnow().isoformat(),
                        'instance_id': instance_id,
                        'instance_state': instance_info.state
                    }
            
            # 再起動の実行
            reboot_result = self.ec2_client.reboot_instance(instance_id, dry_run)
            
            if not reboot_result['success']:
                return {
                    'success': False,
                    'error': reboot_result['error'],
                    'operation_time': datetime.utcnow().isoformat(),
                    'instance_id': instance_id,
                    'instance_state': instance_info.state
                }
            
            # 成功レスポンス
            response = {
                'success': True,
                'message': reboot_result['message'],
                'operation_time': datetime.utcnow().isoformat(),
                'instance_id': instance_id,
                'instance_info': {
                    'state': instance_info.state,
                    'instance_type': instance_info.instance_type,
                    'availability_zone': instance_info.availability_zone,
                    'tags': instance_info.tags
                }
            }
            
            if dry_run:
                response['dry_run'] = True
                response['message'] = f'Dry run successful - would reboot instance {instance_id}'
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error during reboot operation: {str(e)}',
                'operation_time': datetime.utcnow().isoformat(),
                'instance_id': instance_id
            }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda関数のエントリーポイント"""
    print(f"Received event: {json.dumps(event, ensure_ascii=False)}")
    
    try:
        # パラメータの取得
        instance_id = None
        force = False
        dry_run = False
        
        if 'parameters' in event:
            for param in event['parameters']:
                if param['name'] == 'instanceId':
                    instance_id = param['value']
                elif param['name'] == 'force':
                    force = param['value'].lower() == 'true'
                elif param['name'] == 'dryRun':
                    dry_run = param['value'].lower() == 'true'
        
        # 必須パラメータのチェック
        if not instance_id:
            return create_error_response(
                event, 400, 
                'Missing required parameter: instanceId'
            )
        
        # 再起動の実行
        reboot_manager = RebootManager()
        result = reboot_manager.reboot_instance_with_validation(
            instance_id, force=force, dry_run=dry_run
        )
        
        # レスポンスの構築
        if result['success']:
            return create_success_response(event, result)
        else:
            return create_error_response(event, 400, result['error'], result)
            
    except Exception as e:
        print(f"Unexpected error in lambda_handler: {e}")
        return create_error_response(
            event, 500, 
            f'Internal server error: {str(e)}'
        )

def create_success_response(event: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """成功レスポンスを作成"""
    return {
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

def create_error_response(event: Dict[str, Any], status_code: int, 
                         error_message: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """エラーレスポンスを作成"""
    error_body = {
        'success': False,
        'error': error_message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if additional_data:
        error_body.update(additional_data)
    
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "apiPath": event.get("apiPath", ""),
            "httpMethod": event.get("httpMethod", ""),
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": error_body
                }
            }
        }
    }

# テスト用の関数
def test_locally():
    """ローカルテスト用の関数"""
    test_events = [
        {
            "parameters": [
                {"name": "instanceId", "value": "i-1234567890abcdef0"},
                {"name": "dryRun", "value": "true"}
            ],
            "actionGroup": "test-action-group",
            "apiPath": "/reboot-instance",
            "httpMethod": "POST"
        },
        {
            "parameters": [
                {"name": "instanceId", "value": "invalid-id"}
            ],
            "actionGroup": "test-action-group",
            "apiPath": "/reboot-instance",
            "httpMethod": "POST"
        }
    ]
    
    for i, test_event in enumerate(test_events):
        print(f"\n=== Test Case {i+1} ===")
        result = lambda_handler(test_event, None)
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_locally()
