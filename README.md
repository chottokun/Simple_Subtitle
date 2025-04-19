# 字幕翻訳ツール

このアプリは、動画や音声ファイルから音声を抽出し、Whisperモデルで文字起こしを行い、OpenAI GPT-4oで翻訳、字幕（SRT）ファイルを生成し、さらにffmpegで字幕を焼き込んだ動画を作成できるStreamlitアプリです。

## 主な機能
- MP4動画またはWAV音声ファイルのアップロード
- Whisperによる自動文字起こし
- OpenAI GPT-4oによる多言語翻訳
- SRT字幕ファイルの生成とダウンロード
- ffmpegによる字幕焼き込み動画の生成とダウンロード
- 編集可能な字幕テーブル

## 必要な環境
- Python 3.8以上
- Linux（他OSでも動作する可能性あり）

## インストール
1. リポジトリをクローン
2. 必要なパッケージをインストール

```
pip install -r requirements.txt
```

3. OpenAI APIキーを取得し、`.env` ファイルに `OPENAI_API_KEY=your-key` を記載

## 使い方
1. 以下のコマンドでアプリを起動

```
streamlit run app.py
```

2. ブラウザで表示されるUIから動画または音声ファイルをアップロードし、翻訳先言語を選択
3. 文字起こし・翻訳結果を編集し、SRTファイルや字幕付き動画をダウンロード

## ファイル構成
- `app.py` : Streamlitアプリ本体
- `requirements.txt` : 必要なPythonパッケージ

## 注意事項
- WhisperモデルのダウンロードやOpenAI APIの利用にはインターネット接続が必要です。
- ffmpegがシステムにインストールされている必要があります。

## ライセンス
MIT License
