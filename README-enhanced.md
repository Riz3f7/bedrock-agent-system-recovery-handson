# AWS Bedrock エージェントハンズオン（高度版）

このプロジェクトは、AWS Bedrock エージェントを使用して、EC2インスタンス上で動作するFlaskアプリケーションのトラブルシューティングを自動化するデモです。高度版では、Claude 3 Opusの高度な推論能力を活かした詳細な分析と対応を実現します。

## 機能

- CloudWatch Logsからエラーログを取得し、高度な分析を実行
- エラーパターンの特定と根本原因の分析
- EC2インスタンスの詳細情報取得と再起動
- 構造化されたエラーログの生成と分析

## プロジェクト構成

```
bedrock-agent-handson/
├── app.py                           # 基本的なFlaskアプリケーション
├── app-enhanced.py                  # 強化版Flaskアプリケーション（構造化ログ対応）
├── get-log/                         # ログ取得Lambda
│   ├── get-log.py                   # 基本版Lambda関数
│   └── get-log-enhanced.py          # 強化版Lambda関数（高度な分析機能）
├── reboot-instances/                # インスタンス再起動Lambda
│   ├── reboot-instances.py          # 基本版Lambda関数
│   └── reboot-instances-enhanced.py # 強化版Lambda関数（詳細情報提供）
└── エージェント/                     # エージェント関連ファイル
    ├── エージェントへの指示.txt        # 基本的な指示
    ├── エージェントへの指示-enhanced.txt # 強化版の指示（詳細分析用）
    ├── GetLogActionGroup_APIスキーマ.txt
    └── reboot-instances-actiongroup_APIスキーマ.txt
```

## 高度版の特徴

### 1. 構造化されたエラーログ

強化版Flaskアプリケーション（app-enhanced.py）は以下の機能を提供します：

- JSON形式の構造化ログ出力
- リクエストIDによるトレーサビリティ
- システム情報の自動収集
- スタックトレースの詳細な記録
- タイムスタンプの正確な記録

### 2. 高度なログ分析

強化版get-log Lambda関数（get-log-enhanced.py）は以下の分析機能を提供します：

- エラーパターンの自動検出
- 時間的な分布分析
- エラータイプの分類
- 繰り返し発生するエラーの特定
- インスタンスIDの自動抽出

### 3. 詳細なインスタンス情報

強化版reboot-instances Lambda関数（reboot-instances-enhanced.py）は以下の機能を提供します：

- インスタンスの詳細情報の取得
- 再起動後のステータス確認
- インスタンスの状態変化の追跡
- 詳細なエラー情報の提供

### 4. 高度なエージェント指示

強化版エージェント指示（エージェントへの指示-enhanced.txt）は以下の特徴があります：

- より詳細な分析手順
- 複数の解決策の検討
- 長期的な解決策の提案
- より詳細な説明要求

## セットアップ手順

SETUP.mdファイルの手順に従い、各コンポーネントで強化版（enhanced）を選択してください。

## 注意事項

- 強化版は Claude 3 Opus モデルでの使用を推奨します
- 強化版は基本版よりも詳細な分析と対応が可能ですが、コストが高くなる可能性があります
- 本番環境での使用には適切なセキュリティ設定が必要です