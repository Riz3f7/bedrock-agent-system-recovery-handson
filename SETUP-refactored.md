# セットアップガイド (リファクタリング版)

このガイドでは、AWS Bedrock エージェントハンズオン（リファクタリング版）の詳細なセットアップ手順を説明します。

## 📋 前提条件

### システム要件
- **Python**: 3.7 以上
- **AWS CLI**: 2.0 以上
- **AWS アカウント**: Bedrock、Lambda、EC2、CloudWatch Logs へのアクセス権限
- **OS**: Linux/macOS/Windows（WSL推奨）

### 必要な AWS サービス
- Amazon Bedrock (Claude 3.5/4 Sonnet)
- AWS Lambda
- Amazon EC2
- Amazon CloudWatch Logs
- AWS IAM

## 🔧 ステップ1: 開発環境の準備

### Python環境のセットアップ
```bash
# Python バージョン確認
python3 --version  # 3.7+ が必要

# 仮想環境の作成（推奨）
python3 -m venv bedrock-agent-env
source bedrock-agent-env/bin/activate  # Linux/macOS
# または
bedrock-agent-env\Scripts\activate     # Windows

# 依存関係のインストール
pip install -r requirements-refactored.txt
```

### AWS CLI の設定
```bash
# AWS CLI のインストール確認
aws --version

# 認証情報の設定
aws configure
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: us-east-1  # Bedrock利用可能リージョン
# Default output format: json

# 設定確認
aws sts get-caller-identity
```

## 🏗️ ステップ2: IAM ロールとポリシーの作成

### Lambda実行ロールの作成
```bash
# 信頼ポリシーファイルの作成
cat > lambda-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# IAMロールの作成
aws iam create-role \
  --role-name BedrockAgentLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json
```

### Lambda権限ポリシーの作成
```bash
# 権限ポリシーファイルの作成
cat > lambda-permissions-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
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
          "ec2:ResourceTag/Environment": ["development", "staging", "demo"]
        }
      }
    }
  ]
}
EOF

# ポリシーの作成
aws iam create-policy \
  --policy-name BedrockAgentLambdaPolicy \
  --policy-document file://lambda-permissions-policy.json

# ロールにポリシーをアタッチ
aws iam attach-role-policy \
  --role-name BedrockAgentLambdaRole \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/BedrockAgentLambdaPolicy

# AWS管理ポリシーもアタッチ
aws iam attach-role-policy \
  --role-name BedrockAgentLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

## 🖥️ ステップ3: EC2インスタンスのセットアップ

### インスタンスの起動
```bash
# キーペアの作成（既存のものがない場合）
aws ec2 create-key-pair \
  --key-name bedrock-agent-key \
  --query 'KeyMaterial' \
  --output text > bedrock-agent-key.pem

chmod 400 bedrock-agent-key.pem

# セキュリティグループの作成
aws ec2 create-security-group \
  --group-name bedrock-agent-sg \
  --description "Security group for Bedrock Agent demo"

# HTTP/HTTPSアクセスを許可
aws ec2 authorize-security-group-ingress \
  --group-name bedrock-agent-sg \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name bedrock-agent-sg \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# EC2インスタンスの起動
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \  # Amazon Linux 2 AMI
  --count 1 \
  --instance-type t3.micro \
  --key-name bedrock-agent-key \
  --security-groups bedrock-agent-sg \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=bedrock-agent-demo},{Key=Environment,Value=demo}]'
```

### CloudWatch Logs エージェントの設定
```bash
# インスタンスにSSH接続
ssh -i bedrock-agent-key.pem ec2-user@[INSTANCE-IP]

# CloudWatch Logs エージェントのインストール
sudo yum update -y
sudo yum install -y awslogs

# 設定ファイルの編集
sudo tee /etc/awslogs/awslogs.conf << EOF
[general]
state_file = /var/lib/awslogs/agent-state

[/var/log/my-flask-app.log]
file = /var/log/my-flask-app.log
log_group_name = /aws/ec2/my-flask-application
log_stream_name = {instance_id}
datetime_format = %Y-%m-%d %H:%M:%S
EOF

# リージョン設定
sudo sed -i 's/region = us-east-1/region = us-east-1/' /etc/awslogs/awscli.conf

# サービスの開始
sudo systemctl start awslogsd
sudo systemctl enable awslogsd

# ログファイルの作成と権限設定
sudo touch /var/log/my-flask-app.log
sudo chmod 666 /var/log/my-flask-app.log
```

### Flaskアプリケーションのデプロイ
```bash
# アプリケーションファイルの転送
scp -i bedrock-agent-key.pem app-refactored.py ec2-user@[INSTANCE-IP]:/home/ec2-user/

# インスタンスでの実行
ssh -i bedrock-agent-key.pem ec2-user@[INSTANCE-IP]

# Python3とpipのインストール
sudo yum install -y python3 python3-pip

# 必要なライブラリのインストール
pip3 install flask psutil

# アプリケーションの実行
sudo python3 app-refactored.py
```

## ⚡ ステップ4: Lambda関数のデプロイ

### ログ取得Lambda関数
```bash
# デプロイパッケージの作成
cd get-log/
zip get-log-refactored.zip get-log-refactored.py

# Lambda関数の作成
aws lambda create-function \
  --function-name get-log-refactored \
  --runtime python3.9 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/BedrockAgentLambdaRole \
  --handler get-log-refactored.lambda_handler \
  --zip-file fileb://get-log-refactored.zip \
  --timeout 300 \
  --memory-size 512 \
  --description "Enhanced log retrieval for Bedrock Agent"

# 環境変数の設定（必要に応じて）
aws lambda update-function-configuration \
  --function-name get-log-refactored \
  --environment Variables='{LOG_LEVEL=INFO}'
```

### インスタンス再起動Lambda関数
```bash
# デプロイパッケージの作成
cd ../reboot-instances/
zip reboot-instances-refactored.zip reboot-instances-refactored.py

# Lambda関数の作成
aws lambda create-function \
  --function-name reboot-instances-refactored \
  --runtime python3.9 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/BedrockAgentLambdaRole \
  --handler reboot-instances-refactored.lambda_handler \
  --zip-file fileb://reboot-instances-refactored.zip \
  --timeout 300 \
  --memory-size 256 \
  --description "Safe instance reboot for Bedrock Agent"
```

### Lambda関数のテスト
```bash
# ログ取得Lambda のテスト
aws lambda invoke \
  --function-name get-log-refactored \
  --payload '{"parameters":[{"name":"logGroup","value":"/aws/ec2/my-flask-application"},{"name":"hoursAgo","value":"24"}],"actionGroup":"test","apiPath":"/get-logs","httpMethod":"GET"}' \
  response.json

cat response.json

# インスタンス再起動Lambda のテスト（ドライラン）
aws lambda invoke \
  --function-name reboot-instances-refactored \
  --payload '{"parameters":[{"name":"instanceId","value":"i-1234567890abcdef0"},{"name":"dryRun","value":"true"}],"actionGroup":"test","apiPath":"/reboot","httpMethod":"POST"}' \
  response.json

cat response.json
```

## 🤖 ステップ5: Bedrock エージェントの設定

### エージェントの作成
1. AWS Bedrockコンソールにアクセス
2. 左側メニューから「エージェント」を選択
3. 「エージェントを作成」をクリック

### 基本設定
```
エージェント名: bedrock-troubleshooting-agent
説明: EC2インスタンスのトラブルシューティングを自動化するエージェント
モデル: Claude 3.5 Sonnet または Claude 4 Sonnet
```

### エージェント指示の設定
`エージェント/エージェントへの指示-refactored.txt` の内容をコピーして、エージェントの指示欄に貼り付け

### アクショングループの作成

#### ログ取得アクショングループ
```
アクショングループ名: RetrieveLogsActionGroup
説明: CloudWatch Logsからエラーログを取得
Lambda関数: get-log-refactored
```

APIスキーマ:
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

#### インスタンス再起動アクショングループ
```
アクショングループ名: RebootInstancesActionGroup
説明: EC2インスタンスの安全な再起動
Lambda関数: reboot-instances-refactored
```

APIスキーマ:
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

### エージェントの準備とテスト
1. 「エージェントを準備」をクリック
2. 準備完了後、「テスト」タブでエージェントをテスト
3. 動作確認後、「エージェントを作成」をクリック

## 🧪 ステップ6: 動作確認とテスト

### 基本動作テスト
```bash
# Flaskアプリケーションでエラーを発生
curl http://[INSTANCE-IP]/error
curl http://[INSTANCE-IP]/error/custom

# ログの確認
aws logs describe-log-streams \
  --log-group-name /aws/ec2/my-flask-application

# 最新ログの取得
aws logs get-log-events \
  --log-group-name /aws/ec2/my-flask-application \
  --log-stream-name [LOG-STREAM-NAME] \
  --start-from-head
```

### エージェントテスト例
Bedrockエージェントに以下のような質問をしてテスト:

```
1. "システムの状況を確認してください"
2. "過去24時間のエラーログを分析してください"
3. "最新のエラーについて詳しく教えてください"
4. "インスタンス i-xxxxx を再起動してください"
```

## 🔧 ステップ7: 監視とメンテナンス

### CloudWatch アラームの設定
```bash
# エラー率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name "FlaskApp-HighErrorRate" \
  --alarm-description "High error rate in Flask application" \
  --metric-name ErrorCount \
  --namespace FlaskApp/Errors \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Lambda関数エラーアラーム
aws cloudwatch put-metric-alarm \
  --alarm-name "Lambda-GetLog-Errors" \
  --alarm-description "Errors in get-log Lambda function" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=get-log-refactored
```

### ログ保持期間の設定
```bash
# CloudWatch Logsの保持期間設定（30日）
aws logs put-retention-policy \
  --log-group-name /aws/ec2/my-flask-application \
  --retention-in-days 30
```

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. Lambda関数がタイムアウトする
```bash
# タイムアウト時間を延長
aws lambda update-function-configuration \
  --function-name get-log-refactored \
  --timeout 600
```

#### 2. CloudWatch Logsにログが表示されない
```bash
# EC2インスタンスでawslogsサービスの状態確認
sudo systemctl status awslogsd

# ログファイルの権限確認
ls -la /var/log/my-flask-app.log

# 手動でログエントリを追加してテスト
echo "$(date) [ERROR] Test error message" | sudo tee -a /var/log/my-flask-app.log
```

#### 3. Bedrockエージェントがアクションを実行できない
- IAMロールの権限を確認
- Lambda関数のログを確認
- APIスキーマの形式を確認

#### 4. EC2インスタンスに接続できない
```bash
# セキュリティグループの確認
aws ec2 describe-security-groups --group-names bedrock-agent-sg

# インスタンスの状態確認
aws ec2 describe-instances --filters "Name=tag:Name,Values=bedrock-agent-demo"
```

## 🔄 更新とメンテナンス

### Lambda関数の更新
```bash
# 新しいコードでパッケージを再作成
zip -r get-log-refactored.zip get-log-refactored.py

# 関数コードの更新
aws lambda update-function-code \
  --function-name get-log-refactored \
  --zip-file fileb://get-log-refactored.zip
```

### エージェント指示の更新
1. Bedrockコンソールでエージェントを選択
2. 「編集」をクリック
3. 指示を更新
4. 「エージェントを準備」を再実行

## 📊 パフォーマンス最適化

### Lambda関数の最適化
```bash
# メモリサイズの調整
aws lambda update-function-configuration \
  --function-name get-log-refactored \
  --memory-size 1024

# 同時実行数の制限
aws lambda put-provisioned-concurrency-config \
  --function-name get-log-refactored \
  --qualifier '$LATEST' \
  --provisioned-concurrency-config ProvisionedConcurrencyConfigs=10
```

### CloudWatch Logs の最適化
```bash
# ログストリームの数を制限
aws logs put-retention-policy \
  --log-group-name /aws/ec2/my-flask-application \
  --retention-in-days 7  # 開発環境では短期間に設定
```

これで、AWS Bedrock エージェントハンズオン（リファクタリング版）のセットアップが完了です。各ステップを順番に実行し、問題が発生した場合はトラブルシューティングセクションを参照してください。
