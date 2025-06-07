# AWS Bedrock エージェントハンズオン

このプロジェクトは、AWS Bedrock エージェント（Claude 3.5/4 Sonnet）を使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化する高度なデモシステムです。

## 🚀 新機能・改善点

### Claude 3.5/4 Sonnet 最適化
- **構造化ログ**: JSON形式の詳細なログ出力
- **高度なエラー分析**: パターン認識と重要度判定
- **インテリジェントな問題解決**: 根本原因分析と適切な対策提案
- **安全性向上**: 検証機能とドライラン対応

### アーキテクチャ改善
- **クラスベース設計**: 保守性と拡張性の向上
- **型ヒント**: Python 3.7+ の型システム活用
- **エラーハンドリング**: 包括的な例外処理
- **テスト機能**: ローカルテスト環境の提供

## 📁 プロジェクト構成

```
bedrock-agent-handson/
├── app.py                    # 🆕 Flaskアプリケーション
├── app.py                               # オリジナル版（参考用）
├── get-log/
│   ├── get-log.py           # 🆕 高度なログ分析Lambda
│   └── get-log.py                      # オリジナル版（参考用）
├── reboot-instances/
│   ├── reboot-instances.py  # 🆕 安全な再起動Lambda
│   └── reboot-instances.py             # オリジナル版（参考用）
├── エージェント/
│   ├── エージェントへの指示.txt # 🆕 Claude最適化指示
│   ├── エージェントへの指示.txt          # オリジナル版（参考用）
│   ├── GetLogActionGroup_APIスキーマ.txt
│   └── reboot-instances-actiongroup_APIスキーマ.txt
└── README.md                # 🆕 このファイル
```

## 🔧 主要コンポーネント

### 1. Flask アプリケーション (`app.py`)

#### 新機能
- **構造化ログ**: JSON形式での詳細なログ出力
- **ヘルスチェック**: `/health` エンドポイントでシステム状態監視
- **エラー追跡**: 一意のエラーIDによる問題追跡
- **設定管理**: 環境変数による柔軟な設定

#### エンドポイント
```
GET  /           # アプリケーション情報
GET  /health     # ヘルスチェック
GET  /error      # テスト用エラー発生
GET  /error/custom # 複雑なエラーシナリオ
```

#### 環境変数
```bash
LOG_FILE=/var/log/my-flask-app.log
LOG_LEVEL=INFO
FLASK_HOST=0.0.0.0
FLASK_PORT=80
FLASK_DEBUG=False
```

### 2. ログ取得Lambda (`get-log.py`)

#### 高度な分析機能
- **重要度判定**: CRITICAL, ERROR, WARNING の自動分類
- **インスタンスID抽出**: 正規表現による正確な抽出
- **エラータイプ分析**: Python例外の詳細分類
- **統計情報**: エラー傾向とパターン分析

#### 出力例
```json
{
  "status": "success",
  "error_logs": [...],
  "summary": {
    "total_errors": 15,
    "severity_breakdown": {
      "ERROR": 10,
      "WARNING": 5
    },
    "error_types": {
      "Exception": 8,
      "ConnectionError": 2
    },
    "affected_instances": ["i-1234567890abcdef0"],
    "latest_error": {
      "timestamp": "2025-01-28T10:30:00Z",
      "severity": "ERROR",
      "message": "Application error occurred..."
    }
  }
}
```

### 3. インスタンス再起動Lambda (`reboot-instances.py`)

#### 安全機能
- **検証システム**: インスタンスID形式と存在確認
- **状態チェック**: 再起動可能状態の確認
- **保護機能**: タグベースの再起動保護
- **ドライラン**: 実際の実行前のテスト

#### パラメータ
```json
{
  "instanceId": "i-1234567890abcdef0",
  "force": false,        // 保護を無視して強制実行
  "dryRun": false        // テスト実行（実際には再起動しない）
}
```

### 4. エージェント指示 (`エージェントへの指示.txt`)

#### Claude 3.5/4 Sonnet 最適化
- **詳細な分析手順**: ステップバイステップの問題解決
- **応答フォーマット**: 構造化された報告形式
- **安全性重視**: ユーザー確認の徹底
- **高度な分析**: パターン認識と予防的提案

## 🛠️ セットアップ手順

### 1. 前提条件
```bash
# Python 3.7+ が必要
python --version

# 必要なライブラリ
pip install flask boto3 psutil
```

### 2. Flaskアプリケーションのデプロイ

#### EC2インスタンスでの実行
```bash
# アプリケーションファイルをコピー
scp app.py ec2-user@your-instance:/home/ec2-user/

# インスタンスにSSH接続
ssh ec2-user@your-instance

# アプリケーション実行
sudo python3 app.py
```

#### CloudWatch Logs設定
```bash
# CloudWatch Logsエージェントの設定
sudo yum install -y awslogs

# 設定ファイル編集
sudo vi /etc/awslogs/awslogs.conf
```

### 3. Lambda関数のデプロイ

#### ログ取得Lambda
```bash
# デプロイパッケージ作成
cd get-log/
zip -r get-log.zip get-log.py

# Lambda関数作成（AWS CLI）
aws lambda create-function \
  --function-name get-log \
  --runtime python3.9 \
  --role arn:aws:iam::account:role/lambda-execution-role \
  --handler get-log.lambda_handler \
  --zip-file fileb://get-log.zip
```

#### インスタンス再起動Lambda
```bash
# デプロイパッケージ作成
cd reboot-instances/
zip -r reboot-instances.zip reboot-instances.py

# Lambda関数作成
aws lambda create-function \
  --function-name reboot-instances \
  --runtime python3.9 \
  --role arn:aws:iam::account:role/lambda-execution-role \
  --handler reboot-instances.lambda_handler \
  --zip-file fileb://reboot-instances.zip
```

### 4. Bedrockエージェントの設定

#### アクショングループの作成
1. AWS Bedrockコンソールにアクセス
2. エージェントを作成
3. アクショングループを追加:
   - **RetrieveLogs**: get-log Lambda
   - **RebootInstances**: reboot-instances Lambda

#### エージェント指示の設定
`エージェント/エージェントへの指示.txt` の内容をエージェントの指示として設定

## 🧪 テスト方法

### ローカルテスト

#### Flaskアプリケーション
```bash
python app.py
# ブラウザで http://localhost:80 にアクセス
```

#### Lambda関数
```bash
# ログ取得Lambda
cd get-log/
python get-log.py

# インスタンス再起動Lambda
cd reboot-instances/
python reboot-instances.py
```

### エラーシナリオテスト
```bash
# 基本エラー
curl http://your-instance/error

# 複雑なエラー
curl http://your-instance/error/custom

# ヘルスチェック
curl http://your-instance/health
```

## 📊 監視とログ

### CloudWatch Logs
- **ロググループ**: `/aws/ec2/my-flask-application`
- **ログ形式**: JSON構造化ログ
- **保持期間**: 30日（推奨）

### メトリクス監視
```bash
# カスタムメトリクス例
aws cloudwatch put-metric-data \
  --namespace "FlaskApp/Errors" \
  --metric-data MetricName=ErrorCount,Value=1
```

## 🔒 セキュリティ考慮事項

### IAMロール設定
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
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
          "ec2:ResourceTag/Environment": ["development", "staging"]
        }
      }
    }
  ]
}
```

### 保護機能
- **タグベース保護**: `RebootProtection=enabled`
- **ドライラン**: 実行前のテスト
- **ユーザー確認**: 重要操作の明示的承認

## 🚀 使用方法

### 基本的なトラブルシューティング
1. Bedrockエージェントに問題を報告
2. エージェントがログを自動取得・分析
3. 根本原因と解決策を提示
4. ユーザー確認後、必要に応じて自動修復

### 高度な分析
```
ユーザー: "過去24時間のエラーを分析して、パターンを教えて"
エージェント: 
- ログ取得・分析実行
- エラーパターンの特定
- 時系列分析
- 予防策の提案
```

## 🔧 カスタマイズ

### ログ分析のカスタマイズ
```python
# get-log.py の LogAnalyzer クラス
class LogAnalyzer:
    def __init__(self):
        # カスタムエラーパターンを追加
        self.custom_patterns = {
            'BUSINESS_ERROR': [
                re.compile(r'PaymentError|OrderError')
            ]
        }
```

### 保護ルールのカスタマイズ
```python
# reboot-instances.py の InstanceValidator クラス
def can_reboot_instance(self, instance_info):
    # カスタム保護ルールを追加
    if instance_info.tags.get('CriticalSystem') == 'true':
        return {'can_reboot': False, 'reason': 'Critical system protection'}
```

## 📈 パフォーマンス最適化

### ログ取得の最適化
- **並列処理**: 複数ログストリームの同時処理
- **フィルタリング**: 不要なログの事前除外
- **キャッシュ**: 頻繁にアクセスされるデータのキャッシュ

### Lambda最適化
- **メモリ設定**: 512MB-1024MB推奨
- **タイムアウト**: 5分推奨
- **同時実行数**: 適切な制限設定

## 🐛 トラブルシューティング

### よくある問題

#### 1. ログが取得できない
```bash
# CloudWatch Logsの権限確認
aws logs describe-log-groups --log-group-name-prefix "/aws/ec2"

# ログエージェントの状態確認
sudo systemctl status awslogsd
```

#### 2. インスタンス再起動が失敗
```bash
# インスタンス状態確認
aws ec2 describe-instances --instance-ids i-1234567890abcdef0

# IAM権限確認
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:role/lambda-role \
  --action-names ec2:RebootInstances \
  --resource-arns "*"
```

## 📚 参考資料

- [AWS Bedrock エージェント開発ガイド](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Claude 3.5 Sonnet 最適化ガイド](https://docs.anthropic.com/claude/docs)
- [CloudWatch Logs API リファレンス](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/)
- [EC2 API リファレンス](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/)

## 🤝 コントリビューション

改善提案やバグ報告は、以下の形式でお願いします：

1. **問題の詳細**: 発生している問題の具体的な説明
2. **再現手順**: 問題を再現するための手順
3. **期待される動作**: 本来期待される動作
4. **環境情報**: Python版、AWS SDK版、その他関連情報

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**注意**: このプロジェクトはデモ用です。本番環境での使用には、適切なセキュリティ設定、監視、バックアップ戦略が必要です。
