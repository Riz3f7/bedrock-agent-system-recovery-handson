# AWS Bedrock エージェントハンズオン

このプロジェクトは、AWS Bedrock エージェントを使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化するデモです。

## 機能

- CloudWatch Logsからエラーログを取得
- エラーログの分析
- EC2インスタンスの再起動

## プロジェクト構成

```
bedrock-agent-handson/
├── app.py                           # Flaskアプリケーション
├── get-log/                         # ログ取得Lambda
│   └── get-log.py
├── reboot-instances/                # インスタンス再起動Lambda
│   └── reboot-instances.py
└── エージェント/                     # エージェント関連ファイル
    ├── エージェントへの指示.txt
    ├── GetLogActionGroup_APIスキーマ.txt
    └── reboot-instances-actiongroup_APIスキーマ.txt
```

## セットアップ手順

1. Flaskアプリケーションをデプロイ
   - EC2インスタンスにデプロイ
   - CloudWatch Logsの設定

2. Lambda関数のデプロイ
   - get-log Lambda関数
   - reboot-instances Lambda関数

3. Bedrockエージェントの設定
   - アクショングループの作成
   - APIスキーマの設定
   - エージェントへの指示の設定

## 使用方法

1. Bedrockエージェントに対して、システムエラーのトラブルシューティングを依頼
2. エージェントはCloudWatch Logsからエラーログを取得
3. エラーの原因を分析し、必要に応じてEC2インスタンスの再起動を提案
4. ユーザーの確認後、EC2インスタンスを再起動

## 注意事項

- このプロジェクトはデモ用です
- 本番環境での使用には適切なセキュリティ設定が必要です