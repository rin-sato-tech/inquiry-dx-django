# 社内問い合わせ管理システム — Django版

社員が新規登録、追加情報の提供、状況確認を一つのWebアプリで行える問い合わせ管理システムを開発しています。既存の[Streamlit版](https://github.com/rin-sato-tech/inquiry-DXsystem)とは独立したプロジェクトです。

## 現在の実装範囲

最初の実装では、以下を利用できます。

- 社員アカウントによるログイン・ログアウト・パスワード変更
- 問い合わせ新規登録（依頼者をログイン利用者に固定）
- 自分の問い合わせ一覧・件名検索・状態絞り込み・ページ分割
- 自分の問い合わせ詳細・受付番号・状態・対応チームの確認
- 利用者・部署・対応チーム・カテゴリの管理
- 受付時の部署と登録履歴の保存、登録の二重送信防止

担当者向け画面、代理登録、担当割当、状態変更、公開コメント・内部メモ、追加情報の投稿は後続の実装です。FAQ・通知・分析も未実装です。状態の定義とDB制約は先に用意していますが、現在の画面からは受付済みの案件のみ作成できます。

## 技術構成

Python 3.12、Django 5.2系、PostgreSQL 16、Djangoテンプレート、uvを使用します。JavaScriptのビルドや独立したAPIサーバーは不要です。

## 開発環境の準備

uvとDocker Composeを使用する例です。Dockerを使わず、手元のPostgreSQLに接続することもできます。

```bash
uv sync --locked
cp .env.example .env
```

`.env`の`DJANGO_SECRET_KEY`と`POSTGRES_PASSWORD`を自分の開発用の値に置き換えてください。秘密鍵の生成例：

```bash
uv run python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

PostgreSQLを起動します。

```bash
docker compose up -d --wait db
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py createsuperuser
uv run --env-file .env python manage.py runserver
```

<http://127.0.0.1:8000/>を開きます。管理設定は<http://127.0.0.1:8000/admin/>です。登録するには、有効な対応チームと、そのチームを受付先とするカテゴリが必要です。

### デモデータ

`.env`へ十分な強度の`DEMO_PASSWORD`を追加してから実行します。固定の公開パスワードは設けません。

```bash
uv run --env-file .env python manage.py seed_demo
```

`demo_employee`、`demo_agent`、`demo_coordinator`を作成します。全員が社員としてログインできますが、担当者向け画面はまだありません。再実行しても既存利用者のパスワードや権限は変更しません。コマンドはDEBUGが有効な開発環境でのみ動作します。

## 検証

テストはPostgreSQLを使用します。接続利用者にはテストDB作成権限が必要です。上記Composeで初期作成される利用者はその権限を持ちます。本番用DBでテストしないでください。

```bash
uv run --env-file .env python manage.py check
uv run --env-file .env python manage.py makemigrations --check --dry-run
uv run --env-file .env python manage.py test inquiry_dx_django
uv run ruff check .
uv run ruff format --check .
```

GitHub ActionsでもPostgreSQLを起動し、上記の検証を行います。

## ディレクトリ

- `src/inquiry_dx_django/`：設定、URL、Djangoアプリ
- `accounts/`：利用者、部署、対応チーム
- `inquiries/`：問い合わせ、登録処理、社員向け画面、テスト
- `templates/`：社員向け画面とログイン画面
- `static/`：CSS
- `docs/basic_design.md`：目指す全体構成
- `docs/development.md`：初期実装の範囲と検証記録

## 運用時の注意

`.env`は自動では読み込みません。上記の`--env-file .env`を指定するか、実行環境で環境変数を設定します。開発用Composeと`runserver`は本番運用向けの構成ではありません。

DEBUG未設定時は無効になり、HTTPSへのリダイレクトとセキュアCookieが有効になります。秘密鍵は環境変数で必須です。一般社員にDjango adminの権限を付与せず、問い合わせと受付履歴はadminでも閲覧専用とします。業務データのadmin閲覧は保守用superuserに限定しています。

本番公開は未設定です。HTTPS終端、静的ファイル配信、DBバックアップ、ログイン試行制限、アカウント運用は公開前に整備します。実データではなく架空データで検証してください。
