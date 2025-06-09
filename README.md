# AWS Bedrock エージェント システム復旧ハンズオン

このプロジェクトは、AWS Bedrock エージェント（Amazon Nova Pro）を使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化するシステムの構築手順を提供します。

## 🎯 プロジェクト概要

AWS Bedrockエージェントの力を活用して、システム障害の検出、分析、復旧を自動化する実践的なデモシステムです。

### 主な機能
- **自動ログ分析**: CloudWatch Logsからエラーログを取得・分析
- **インテリジェントな障害診断**: AIによる根本原因の特定
- **安全な自動復旧**: EC2インスタンスの自動再起動
- **自然言語でのシステム操作**: 日本語での直感的な操作

## 🏗️ アーキテクチャ

```
[ユーザー] → [Bedrock エージェント] → [Lambda関数] → [CloudWatch Logs / EC2]
                                    ↓
                              [ログ分析・インスタンス再起動]
                                    ↑
                            [Session Manager経由でアクセス]
```

## 📁 プロジェクト構成

```
bedrock-agent-system-recovery-handson/
├── README.md                          # このファイル
├── ハンズオン手順書.md                 # 詳細な構築手順
├── ec2-flask-template.yaml            # CloudFormationテンプレート
├── lambda/
│   ├── get-log.py                     # ログ取得Lambda関数
│   └── reboot-instances.py            # インスタンス再起動Lambda関数
└── エージェント/
    ├── GetLogActionGroup_APIスキーマ.txt
    ├── reboot-instances-actiongroup_APIスキーマ.txt
    └── エージェントへの指示.txt
```

## 🚀 クイックスタート

### 前提条件
- AWSアカウント
- Amazon Nova Pro が利用可能なリージョン（推奨: us-east-1, us-west-2）
- 基本的なAWSサービスの知識

### 所要時間
約 1 時間

### 手順概要
1. **事前準備**: Amazon Nova Pro の有効化
2. **EC2インスタンスの準備**: CloudFormationによる自動構築
3. **IAMロールの作成**: Lambda実行用権限設定
4. **Lambda関数の作成**: ログ分析・再起動機能の実装
5. **Bedrock エージェントの作成**: エージェントとアクショングループの設定
6. **テストと動作確認**: 実際のトラブルシューティングテスト

詳細な手順は [ハンズオン手順書.md](./ハンズオン手順書.md) を参照してください。

## 🔧 主要コンポーネント

### 1. CloudFormationテンプレート (`ec2-flask-template.yaml`)
- Amazon Linux 2023ベースのEC2インスタンス
- Flaskアプリケーションの自動デプロイ
- Session Manager接続設定
- CloudWatch Agent設定

### 2. ログ取得Lambda (`lambda/get-log.py`)
- CloudWatch Logsからエラーログを取得
- ログの重要度分析
- インスタンスID抽出
- 統計情報の生成

### 3. インスタンス再起動Lambda (`lambda/reboot-instances.py`)
- EC2インスタンスの安全な再起動
- 事前チェックと検証
- ドライラン機能

### 4. Bedrockエージェント設定
- 自然言語でのシステム操作
- アクショングループによるLambda連携
- 安全性を重視した操作確認

## 🎮 使用例

### 基本的なトラブルシューティング
```
ユーザー: "システムの状況を確認してください"
エージェント: 
- CloudWatch Logsを確認
- エラーログの分析
- システム状態の報告
- 必要に応じて復旧提案
```

### 自動復旧
```
ユーザー: "エラーが発生しているインスタンスを再起動してください"
エージェント:
- エラーログの詳細分析
- 影響度の評価
- ユーザー確認後の安全な再起動実行
```

## 📊 特徴

### Amazon Nova Pro最適化
- 高いコスト効率性
- 優れた推論能力
- 日本語での自然な対話
- 技術的なトラブルシューティングに最適化

### セキュリティ
- IAMロールによる適切な権限制御
- Session Managerによる安全な接続
- ドライラン機能
- タグベースの保護機能

### 運用性
- CloudWatch Logsとの統合
- 構造化ログ出力
- 詳細な監査ログ
- エラーハンドリング

## 🧹 クリーンアップ

ハンズオン完了後は、コストを避けるため以下の順序でリソースを削除してください：

1. Bedrock エージェント
2. Lambda関数
3. IAMロール・ポリシー
4. CloudFormationスタック
5. CloudWatch Logs

詳細な削除手順は [ハンズオン手順書.md](./ハンズオン手順書.md) の「クリーンアップ」セクションを参照してください。

## 🤝 サポート

### トラブルシューティング
よくある問題と解決方法については、[ハンズオン手順書.md](./ハンズオン手順書.md) の「トラブルシューティング」セクションを参照してください。

### 改善提案
このプロジェクトへの改善提案やバグ報告は、Issues経由でお知らせください。

## 📚 参考資料

- [AWS Bedrock エージェント開発ガイド](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Amazon Nova Pro モデル詳細](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-nova.html)
- [CloudWatch Logs API リファレンス](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/)
- [EC2 API リファレンス](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/)

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**注意**: このプロジェクトはデモ・学習目的です。本番環境での使用には、適切なセキュリティ設定、監視、バックアップ戦略の実装が必要です。