# Project 04: Image Management System — 設計書

## 1. 目的

ファイル処理・バックグラウンド処理・ストレージ設計を経験する。
これまでの CRUD / 外部API / 認証 に対し、本プロジェクトは **バイナリ（画像）データの取り扱い** という新しい次元を追加する。

## 2. 学習テーマ

- ファイルアップロード（`UploadFile` / `multipart/form-data`）
- バリデーション（MIMEタイプ・拡張子・サイズ制限）
- 画像処理（Pillow：サムネイル生成・寸法取得）
- バックグラウンド処理（FastAPI `BackgroundTasks` でサムネイル生成）
- ストレージ設計（`StorageBackend` 抽象 → `LocalStorage` 実装、将来 S3/R2 へ差し替え可能）
- ストリーム配信（画像の返却）

## 3. MVP（今回作る範囲）

### バックエンド
- 画像アップロード（**ストリーム保存** + MIME/拡張子/サイズ検証 + **Pillowで画像検証** + UUID命名）
- **SHA-256による重複検知**（同一内容は二重保存しない）
- **処理状態管理**（PENDING → PROCESSING → READY / FAILED）
- メタデータ保存（元ファイル名・content_type・サイズ・幅・高さ・sha256・status）
- サムネイル生成（バックグラウンド, **EXIF除去** + 256×256固定）
- 画像一覧取得（ページネーション + **ソート**）
- 画像本体・サムネイルの取得（配信）
- 画像の削除（論理削除 + ファイル削除）
- ヘルスチェック（`/health` と `/health/storage`）

### フロントエンド
- ドラッグ&ドロップアップロード
- アップロード進捗表示
- サムネイル一覧（グリッド）
- プレビュー・削除

### 発展（Project 04.5相当）
- EXIF削除 / WebP変換 / ZIP一括DL / ハッシュ重複検知 / 画像検索
- Project 05 との連携（アップロード → AI画像解析）

## 4. 技術選定

| 項目 | 採用 | 理由 |
|---|---|---|
| ファイル受信 | FastAPI `UploadFile` | ストリームで受け取れる標準機能 |
| 画像処理 | **Pillow** | サムネイル生成・寸法取得の定番 |
| 非同期 | **BackgroundTasks** | サムネイル生成をレスポンス後に実行 |
| ストレージ | **StorageBackend 抽象 + LocalStorage 実装** | 実装差し替え可能（将来 S3/R2）。無料・追加アカウント不要 |
| メタデータDB | **PostgreSQL（本番） / SQLite（開発）** | 既存 deploy.ps1 -WithPostgres を活用 |
| ORM/Migration | SQLAlchemy 2.0 / Alembic | 既存プロジェクトと統一 |

> 認証は本プロジェクトのテーマではないため MVP では設けない（認証は Project 03 で実装済み）。
> 将来 `owner_id` を足せば multi-user 化できる構造にしておく。

## 5. ストレージ設計（本プロジェクトの核）

```text
Service
  │ 依存
  ▼
StorageBackend (抽象IF)   save(key, bytes) / open(key) / delete(key) / url(key)
  ▲ 実装
LocalStorage (ローカルディスク: uploads/ と thumbnails/)
  （将来: S3Storage / R2Storage へ差し替え可能）
```

- 保存パスはUUIDベース（元ファイル名は衝突・パストラバーサルの原因になるため保存キーには使わない）
- 本体は `uploads/{uuid}.{ext}`、サムネイルは `thumbnails/{uuid}.jpg`
- **無料枠のディスクは揮発**するため本番ではデータが再起動でリセットされる（README明記）。実運用は S3/R2 実装に差し替える想定。

## 6. システム構成

```text
Next.js UI (D&D, 進捗, グリッド)
  │ multipart/form-data
FastAPI (api/images)
  │
Service (image_service)  ── 検証 → 保存 → メタデータ登録 → サムネイルをBackgroundTasksで生成
  ├─ StorageBackend (抽象) ─ LocalStorage
  └─ ImageRepository (抽象) ─ SQLAlchemy 実装
  │
PostgreSQL / SQLite
```

## 7. API設計

| Method | Path | 説明 |
|---|---|---|
| POST | /images | 画像アップロード（multipart, field名 `file`）。同一sha256は既存を返す |
| GET | /images?page=1&limit=20&sort=created_at&order=desc | 一覧（ページネーション + ソート） |
| GET | /images/{id} | メタデータ取得 |
| GET | /images/{id}/file | 画像本体を配信 |
| GET | /images/{id}/thumbnail | サムネイルを配信（未生成なら本体で代替） |
| DELETE | /images/{id} | 論理削除 + ファイル削除 |
| GET | /health | ヘルスチェック |
| GET | /health/storage | Storage書き込み + DB接続の個別確認 |

メタデータのレスポンス（共通形式 `{success,data,message}`）:
```json
{
  "id": 1,
  "original_filename": "photo.png",
  "content_type": "image/png",
  "size": 20345,
  "width": 800,
  "height": 600,
  "sha256": "…",
  "status": "READY",
  "has_thumbnail": true,
  "created_at": "2026-07-06T09:00:00"
}
```

### バリデーション（多層で堅牢に）
- 許可 MIME: `image/png`, `image/jpeg`, `image/webp`, `image/gif`
- 拡張子と MIME の整合チェック
- **ストリーム保存中にサイズ上限を監視**（超過で 413、既定10MB・環境変数で変更可）
- **Pillow `Image.verify()` で本当に画像として開けるか検証**（拡張子偽装対策）
- 保存キーはUUID（パストラバーサル対策。ユーザー入力のパスは使わない）

### ソート
- `sort`: `created_at`（既定） / `size`
- `order`: `desc`（既定） / `asc`

| ステータス | 意味 |
|---|---|
| 201 | アップロード成功（新規） |
| 200 | 既存（sha256重複で既存を返す） |
| 400 | 不正なファイル（MIME/拡張子/画像として開けない） |
| 404 | 対象なし |
| 413 | サイズ超過 |
| 422 | 入力不正 |

## 8. データベース設計

### images
| カラム | 型 | 制約 |
|---|---|---|
| id | PK | |
| storage_key | VARCHAR(255) | NOT NULL（UUIDベースの保存キー） |
| thumbnail_key | VARCHAR(255) | NULL可（生成後に設定） |
| original_filename | VARCHAR(255) | NOT NULL |
| content_type | VARCHAR(100) | NOT NULL |
| size | INTEGER | NOT NULL |
| width | INTEGER | NULL可 |
| height | INTEGER | NULL可 |
| sha256 | VARCHAR(64) | NOT NULL, INDEX（重複検知） |
| status | VARCHAR(20) | NOT NULL, default 'PENDING'（PENDING/PROCESSING/READY/FAILED） |
| deleted_at | TIMESTAMP | NULL可（論理削除） |
| created_at / updated_at | TIMESTAMP | NOT NULL |

> 重複検知は「未削除かつ同一sha256」で判定する。サムネイル生成の状態は status で管理し、
> フロントで「生成中／完了／エラー」を表示できるようにする。

## 9. ディレクトリ構成

```text
portfolio-04-image-manager/
  backend/
    app/
      api/          # images, deps
      core/         # config
      models/       # image
      schemas/      # image, response
      services/     # image_service, thumbnail
      repositories/ # base(抽象) + sqlalchemy 実装
      storage/      # base(抽象 StorageBackend) + local(LocalStorage)
      db/
      main.py
    migrations/     # Alembic
    tests/          # アップロード検証 / 一覧 / 削除 / サムネイル / バリデーション
    Dockerfile
    requirements.txt
  frontend/
    app/
    components/
    features/images/  # Uploader(D&D), ImageGrid, ImageCard
    services/
    types/
    lib/
  docs/requirements.md
  render.yaml
```

## 10. テスト観点

- アップロード成功（メタデータ・寸法が正しい）
- 不正MIME/拡張子 → 400
- サイズ超過 → 413
- 一覧のページネーション
- 削除後は一覧・取得から除外（論理削除 + ファイル削除）
- サムネイル生成（バックグラウンド処理の結果 has_thumbnail=true）
- 存在しないID → 404
- パストラバーサル対策（storage_keyはUUID、任意パスを受け付けない）

## 11. 完成条件（Definition of Done）

- [ ] アップロード（ストリーム保存）・一覧・取得・配信・削除が動作
- [ ] MIME/拡張子/サイズ検証 + Pillow画像検証
- [ ] SHA-256重複検知
- [ ] 状態管理（PENDING→READY/FAILED）
- [ ] サムネイル生成（バックグラウンド, EXIF除去, 256×256）
- [ ] 一覧のソート（created_at/size, asc/desc）
- [ ] ストレージ抽象化（LocalStorage実装）
- [ ] /health/storage
- [ ] pytest（アップロード/検証/重複/一覧・ソート/削除/サムネイル/画像偽装拒否）
- [ ] Ruff / ESLint / build（CI）
- [ ] README（アーキテクチャ図・ストレージ抽象の説明）・スクリーンショット
- [ ] Render(PostgreSQL) + Vercel デプロイ（`deploy.ps1 -WithPostgres`）
