# AWS Bedrock エージェントハンズオン セットアップ手順

このドキュメントでは、AWS Bedrock エージェントハンズオンの詳細なセットアップ手順を説明します。

## 前提条件

- AWS アカウント
- AWS CLI のインストールと設定
- 適切な IAM 権限
- Python 3.8 以上
- AWS Bedrock で以下のモデルへのアクセス権を有効化していること
  - **Anthropic Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0) - 推奨
  - **Anthropic Claude 3 Haiku** (anthropic.claude-3-haiku-20240307-v1:0) - 代替オプション
  - いずれかのモデルが使用可能であること

## 1. EC2 インスタンスと Flask アプリケーションのセットアップ

### 1.1 EC2 インスタンスの作成

1. AWS マネジメントコンソールにログイン
2. **Bedrock モデル（Claude 3 Sonnet/Haiku）が有効化されているリージョンを選択**
   - 例: `us-east-1` (バージニア北部)、`us-west-2` (オレゴン)、`ap-northeast-1` (東京) など
   - 注意: Bedrock エージェントとモデルは同じリージョンで使用する必要があります
3. EC2 ダッシュボードに移動
4. 「インスタンスを起動」をクリック
5. **Amazon Linux 2023 AMI** を選択
   - 名前: "Amazon Linux 2023 AMI" を検索
   - アーキテクチャ: x86_64 を選択
6. t2.micro インスタンスタイプを選択（無料利用枠対象）
6. 以下の IAM ロールを持つインスタンスプロファイルを作成・選択
   ```json
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
       }
     ]
   }
   ```
7. セキュリティグループで SSH (ポート 22) と HTTP (ポート 80) を許可
8. インスタンスを起動

### 1.2 Flask アプリケーションのデプロイ

1. SSH で EC2 インスタンスに接続
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

2. 必要なパッケージをインストール (Amazon Linux 2023 用)
   ```bash
   sudo dnf update -y
   sudo dnf install -y python3 python3-pip git
   sudo pip3 install flask requests
   ```

3. アプリケーションディレクトリを作成
   ```bash
   mkdir -p ~/flask-app
   cd ~/flask-app
   ```

4. app.py ファイルを作成
   ```bash
   vi app.py
   ```
   最適化された app.py の内容をコピー＆ペースト

5. アプリケーションを systemd サービスとして設定
   ```bash
   sudo vi /etc/systemd/system/flask-app.service
   ```
   以下の内容を記述:
   ```
   [Unit]
   Description=Flask Application
   After=network.target

   [Service]
   User=ec2-user
   WorkingDirectory=/home/ec2-user/flask-app
   ExecStart=/usr/bin/python3 app.py
   Restart=always
   Environment=PORT=80
   Environment=FLASK_DEBUG=False

   [Install]
   WantedBy=multi-user.target
   ```

6. サービスを有効化して起動
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable flask-app
   sudo systemctl start flask-app
   ```

7. ログディレクトリを作成し、権限を設定
   ```bash
   sudo mkdir -p /var/log
   sudo touch /var/log/my-flask-app.log
   sudo chown ec2-user:ec2-user /var/log/my-flask-app.log
   ```

### 1.3 CloudWatch エージェントのセットアップ

1. CloudWatch エージェントをインストール (Amazon Linux 2023 用)
   ```bash
   sudo dnf install -y amazon-cloudwatch-agent
   ```

2. CloudWatch エージェント設定ファイルを作成
   ```bash
   sudo vi /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
   ```
   以下の内容を記述:
   ```json
   {
     "logs": {
       "logs_collected": {
         "files": {
           "collect_list": [
             {
               "file_path": "/var/log/my-flask-app.log",
               "log_group_name": "/aws/ec2/my-flask-application",
               "log_stream_name": "{instance_id}",
               "retention_in_days": 14
             }
           ]
         }
       }
     }
   }
   ```

3. CloudWatch エージェントを設定して起動
   ```bash
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
   ```

4. エラーログを生成してテスト
   ```bash
   curl http://localhost/error
   ```

## 2. Lambda 関数のデプロイ

### 2.1 get-log Lambda 関数のデプロイ

1. AWS マネジメントコンソールで Lambda サービスに移動
2. 「関数の作成」をクリック
3. 「一から作成」を選択
4. 関数名: `get-log` を入力
5. ランタイム: Python 3.9 を選択
6. 「関数の作成」をクリック
7. 以下の IAM ポリシーを Lambda 実行ロールに追加
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:FilterLogEvents",
           "logs:GetLogEvents",
           "logs:DescribeLogStreams"
         ],
         "Resource": "arn:aws:logs:*:*:log-group:/aws/ec2/my-flask-application:*"
       }
     ]
   }
   ```
8. コードエディタで、最適化された get-log.py の内容をコピー＆ペースト
9. 「デプロイ」をクリック

### 2.2 reboot-instances Lambda 関数のデプロイ

1. AWS マネジメントコンソールで Lambda サービスに移動
2. 「関数の作成」をクリック
3. 「一から作成」を選択
4. 関数名: `reboot-instances` を入力
5. ランタイム: Python 3.9 を選択
6. 「関数の作成」をクリック
7. 以下の IAM ポリシーを Lambda 実行ロールに追加
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:RebootInstances",
           "ec2:DescribeInstances"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
8. コードエディタで、最適化された reboot-instances.py の内容をコピー＆ペースト
9. 「デプロイ」をクリック

## 3. Bedrock エージェントの設定

### 3.1 Bedrock エージェントの作成

1. AWS マネジメントコンソールで Bedrock サービスに移動
   - EC2インスタンスと**同じリージョン**を選択していることを確認
2. 左側のナビゲーションから「エージェント」を選択
3. 「エージェントを作成」をクリック
4. エージェント名: `TroubleshootingAgent` を入力
5. 基盤モデル: 以下のいずれかを選択
   - **Anthropic Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0) - 推奨
   - **Anthropic Claude 3 Haiku** (anthropic.claude-3-haiku-20240307-v1:0) - 代替オプション
6. 「エージェントを作成」をクリック

### 3.2 アクショングループの作成

#### GetLogActionGroup の作成

1. 作成したエージェントの詳細ページで「アクショングループ」タブを選択
2. 「アクショングループを追加」をクリック
3. アクショングループ名: `GetLogActionGroup` を入力
4. 説明: `CloudWatch Logs からエラーログを取得する` を入力
5. API スキーマ: GetLogActionGroup_APIスキーマ.txt の内容をコピー＆ペースト
6. Lambda 関数: 先ほど作成した `get-log` Lambda 関数を選択
7. 「アクショングループを追加」をクリック

#### RebootInstancesActionGroup の作成

1. 「アクショングループを追加」をクリック
2. アクショングループ名: `RebootInstancesActionGroup` を入力
3. 説明: `EC2 インスタンスを再起動する` を入力
4. API スキーマ: reboot-instances-actiongroup_APIスキーマ.txt の内容をコピー＆ペースト
5. Lambda 関数: 先ほど作成した `reboot-instances` Lambda 関数を選択
6. 「アクショングループを追加」をクリック

### 3.3 エージェントの指示を設定

1. 「指示」タブを選択
2. エージェントへの指示.txt の内容をコピー＆ペースト
3. 「保存」をクリック

### 3.4 エージェントのテストと準備

1. 「テスト」タブを選択
2. エージェントをテストするためのプロンプトを入力
   例: `システムにエラーが発生しているようです。確認して対処してください。`
3. エージェントの応答を確認
4. 問題がなければ「準備」をクリック
5. 「エージェントを準備」をクリック

## 4. 動作確認

1. EC2 インスタンスでエラーを発生させる
   ```bash
   curl http://your-instance-ip/error
   ```

2. Bedrock エージェントに以下のようなメッセージを送信
   ```
   システムにエラーが発生しているようです。ログを確認して問題を特定してください。
   ```

3. エージェントが CloudWatch Logs からエラーログを取得し、分析結果を表示
4. エージェントが EC2 インスタンスの再起動を提案
5. 再起動を承認すると、エージェントが EC2 インスタンスを再起動

## トラブルシューティング

### CloudWatch Logs にログが表示されない場合

1. CloudWatch エージェントのステータスを確認
   ```bash
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
   ```

2. ログファイルのアクセス権を確認
   ```bash
   ls -la /var/log/my-flask-app.log
   ```

### Lambda 関数が失敗する場合

1. Lambda 関数のログを CloudWatch Logs で確認
2. IAM ロールに必要な権限があることを確認
3. Lambda 関数のタイムアウト設定を確認（デフォルトは 3 秒）

### Bedrock エージェントが正しく応答しない場合

1. エージェントの指示を見直す
2. API スキーマが正しいことを確認
3. Lambda 関数のレスポンス形式が正しいことを確認