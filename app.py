import streamlit as st
import os
import tempfile
import moviepy as mp
import srt
import datetime
import ffmpeg
import openai
import pandas as pd
from dotenv import load_dotenv
from faster_whisper import WhisperModel
import subprocess

# セッションステートのキー
INPUT_PATH = "input_path"
AUDIO_PATH = "audio_path"
SEGMENTS = "segments"
ORIGINAL_TEXTS = "original_texts"
DF = "df"

# Whisperモデルのロード
model_size = "small"
model = WhisperModel(model_size, device="cpu", compute_type="int8")

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキー
openai.api_key = os.getenv("OPENAI_API_KEY")

# 関数：動画から音声抽出
def extract_audio(video_path):
    audio_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    video = mp.VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    return audio_path

# 関数：Whisperで文字起こし
def transcribe(audio_path):
    segments, info = model.transcribe(audio_path, beam_size=5)
    return segments

# 関数：GPT-4oで翻訳
def translate(text, target_lang):
    try:
        response = openai.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": f"Translate into {target_lang}."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"翻訳中にエラーが発生しました: {e}")
        return ""

# 関数：SRT生成
def generate_srt(segments, translations, start_offsets, end_offsets):
    subtitles = []
    for i, seg in enumerate(segments):
        start = datetime.timedelta(seconds=seg.start + start_offsets[i])
        end = datetime.timedelta(seconds=seg.end + end_offsets[i])
        subtitles.append(srt.Subtitle(i + 1, start, end, translations[i]))
    return srt.compose(subtitles)

# 関数：動画に字幕を焼き込み（ffmpeg）
def burn_subtitles(video_path, srt_path):
    try:
        output_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
        command = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles='{srt_path}'",
            output_path,
            "-y"  # 上書きオプション
        ]
        subprocess.run(command, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        st.error(f"ffmpegの実行中にエラーが発生しました: {e}")
        return None
    except Exception as e:
        st.error(f"字幕焼き込み中にエラーが発生しました: {e}")
        return None

# Streamlit UI
st.set_page_config(page_title="字幕翻訳ツール", layout="wide")
st.title("🎞️ 動画音声翻訳・字幕作成ツール")

uploaded_file = st.file_uploader("動画（MP4）または音声（WAV）ファイルをアップロード", type=["mp4", "wav"])
target_lang = st.selectbox("翻訳先言語を選択", ["ja", "en", "zh", "fr", "es", "de", "ko"])

if uploaded_file:
    file_name = uploaded_file.name
    st.info("ファイルを処理中...")

    if file_name not in st.session_state:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_name.split('.')[-1]}") as f:
            f.write(uploaded_file.read())
            input_path = f.name
        audio_path = extract_audio(input_path) if input_path.endswith(".mp4") else input_path
        segments = list(transcribe(audio_path))
        original_texts = [seg.text for seg in segments]

        data = []
        for i, orig in enumerate(original_texts):
            data.append({
                "start": f"{segments[i].start:.2f}",
                "original": orig,
                "translation": translate(orig, target_lang),
                "end": f"{segments[i].end:.2f}",
                "start_offset": 0.0,
                "end_offset": 0.0,
            })
        st.session_state[file_name] = {
            'df': pd.DataFrame(data),
            'audio_path': audio_path,
            'segments': segments,
            'original_texts': original_texts,
            'input_path': input_path
        }
    
    df = st.session_state[file_name]['df']
    audio_path = st.session_state[file_name]['audio_path']
    segments = st.session_state[file_name]['segments']
    original_texts = st.session_state[file_name]['original_texts']
    input_path = st.session_state[file_name]['input_path']

    # 編集可能なテーブル
    if "df" in st.session_state:
        data_editor_df = st.session_state.df
    else:
        data_editor_df = df

    edited_df = st.data_editor(
        data_editor_df,
        column_config={
            "start": st.column_config.TextColumn(disabled=True),
            "original": st.column_config.TextColumn(disabled=True),
            "translation": st.column_config.TextColumn(label="翻訳"),
            "end": st.column_config.TextColumn(disabled=True),
            "start_offset": st.column_config.NumberColumn(label="開始補正(s)"),
            "end_offset": st.column_config.NumberColumn(label="終了補正(s)"),
        },
        use_container_width=True,
        key="data_editor"
    )

    # 編集内容をセッションステートに反映
    st.session_state.df = edited_df

    # SRT生成＆ダウンロード
    if st.button("OK", key="ok_generate_srt"):
        edited_texts = edited_df["translation"].tolist()
        start_offsets = edited_df["start_offset"].tolist()
        end_offsets = edited_df["end_offset"].tolist()
        srt_text = generate_srt(segments, edited_texts, start_offsets, end_offsets)
        srt_path = tempfile.NamedTemporaryFile(suffix=".srt", delete=False).name
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)
        st.session_state["srt_path"] = srt_path  # srt_pathをセッションステートに保存
        st.download_button("⬇️ 字幕ファイルをダウンロード (.srt)", srt_text, file_name="translated_subtitles.srt")

    # 字幕付き動画生成 (OKボタンが押された後)
    if uploaded_file.name.endswith(".mp4") and "srt_path" in st.session_state:
        st.subheader("🎥 字幕付き動画を生成")
        if st.button("▶️ 動画に字幕を焼き込む"):
            output_video_path = burn_subtitles(input_path, st.session_state["srt_path"])
            with open(output_video_path, "rb") as f:
                st.download_button("⬇️ 字幕付き動画をダウンロード (.mp4)", f, file_name="subtitled_video.mp4")
