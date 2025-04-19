# 字幕翻訳・生成Webアプリ

## 概要
このアプリは、動画（MP4）、音声（WAV）、字幕（SRT）ファイルをアップロードし、Whisper（fast-whisper）による文字起こしとOpenAI GPT-4.1-nanoによる翻訳を行い、字幕ファイル（SRT）の生成や、字幕を焼き込んだ動画の作成ができるStreamlitベースのWebアプリです。

## 主な機能
- MP4動画・WAV音声ファイルからの自動文字起こし（fast-whisper使用）
- SRT字幕ファイルのアップロード・翻訳
- OpenAI GPT-4.1-nanoによる高精度な翻訳（文脈考慮）
- 翻訳結果の手動編集・タイミング補正
- SRT字幕ファイルのダウンロード
- ffmpegによる字幕焼き込み動画（MP4）の生成・ダウンロード

## 必要環境
- Linux（他OSでも動作する可能性あり）
- Python 3.8以降

## 依存ライブラリ
- streamlit
- fast-whisper
- openai
- python-dotenv
- moviepy
- srt
- pandas
- ffmpeg（コマンドラインツールとしてインストール必須）

requirements.txtに必要なPythonパッケージが記載されています。

## セットアップ手順
1. 必要なPythonパッケージをインストール

   ```bash
   pip install -r requirements.txt
   ```

2. ffmpegをインストール（未導入の場合）

   ```bash
   sudo apt-get install ffmpeg
   # または
   brew install ffmpeg
   ```

3. OpenAI APIキーを取得し、.envファイルに記載

   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## 使い方
1. Streamlitアプリを起動

   ```bash
   streamlit run app.py
   ```

2. Webブラウザで表示されるUIから、MP4/WAV/SRTファイルをアップロード
3. 翻訳先言語を選択
4. 自動で文字起こし・翻訳が実行され、字幕内容が表形式で表示されます
5. 必要に応じて翻訳やタイミング補正を編集
6. 「OK」ボタンでSRT字幕ファイルを生成・ダウンロード
7. MP4動画の場合、「動画に字幕を焼き込む」ボタンで字幕付き動画を生成・ダウンロード

## 注意事項
- OpenAI APIの利用にはAPIキーと利用料が必要です
- fast-whisperはCPUで動作します（高速化にはGPU環境推奨）
- ffmpegがシステムにインストールされている必要があります
- SRTファイルの形式が正しくない場合、エラーとなることがあります


---

本アプリは研究・個人利用を想定しています。商用利用時は各APIやライブラリのライセンスをご確認ください。
