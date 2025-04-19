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

# 関数：翻訳
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

# 関数：GPT-4oで翻訳（文脈考慮版）
def translate_with_context(segments, idx, target_lang):
    """
    segments: Whisperのセグメントリスト
    idx: 翻訳対象のインデックス
    target_lang: 翻訳先言語
    """
    # 前後の文脈を取得
    prev_text = segments[idx - 1].text if idx > 0 else ""
    curr_text = segments[idx].text
    next_text = segments[idx + 1].text if idx < len(segments) - 1 else ""
    # プロンプトを作成
    prompt = (
        f"前後の文脈を考慮して中央の文だけを{target_lang}に翻訳してください。\n"
        f"前の文: {prev_text}\n"
        f"中央の文: {curr_text}\n"
        f"次の文: {next_text}"
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": f"Translate only the center sentence into {target_lang}, considering the context."},
                {"role": "user", "content": prompt}
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
        # seg.start/seg.endがtimedelta型ならtotal_seconds()でfloatに変換
        start_sec = seg.start.total_seconds() if isinstance(seg.start, datetime.timedelta) else seg.start
        end_sec = seg.end.total_seconds() if isinstance(seg.end, datetime.timedelta) else seg.end
        start = datetime.timedelta(seconds=start_sec + start_offsets[i])
        end = datetime.timedelta(seconds=end_sec + end_offsets[i])
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

uploaded_files = st.file_uploader(
    "動画（MP4）・音声（WAV）・字幕（SRT）ファイルをアップロード",
    type=["mp4", "wav", "srt"],
    accept_multiple_files=True
)
target_lang = st.selectbox("翻訳先言語を選択", ["ja", "en", "zh", "fr", "es", "de", "ko"])

mp4_file = None
wav_file = None
srt_file = None

if uploaded_files:
    for f in uploaded_files:
        if f.name.endswith(".mp4"):
            mp4_file = f
        elif f.name.endswith(".wav"):
            wav_file = f
        elif f.name.endswith(".srt"):
            srt_file = f

    file_name = mp4_file.name if mp4_file else (wav_file.name if wav_file else (srt_file.name if srt_file else None))
    st.info("ファイルを処理中...")

    # SRTファイルがある場合はSRTをベースに（音声から文字起こしはしない）
    if srt_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".srt") as f:
            f.write(srt_file.read())
            srt_path = f.name
        with open(srt_path, "r", encoding="utf-8") as f:
            srt_content = f.read()
        try:
            srt_subs = list(srt.parse(srt_content))
            if not srt_subs:
                st.error("SRTファイルに有効な字幕データがありません。ファイル形式を確認してください。")
                st.stop()
        except Exception as e:
            st.error(f"SRTファイルの解析中にエラーが発生しました。ファイル形式を確認してください。\n詳細: {e}")
            st.stop()
        data = []
        for sub in srt_subs:
            data.append({
                "start": f"{sub.start.total_seconds():.2f}",
                "original": sub.content,
                "translation": translate(sub.content, target_lang),
                "end": f"{sub.end.total_seconds():.2f}",
                "start_offset": 0.0,
                "end_offset": 0.0,
            })
        st.session_state[file_name] = {
            'df': pd.DataFrame(data),
            'segments': srt_subs,
            'original_texts': [sub.content for sub in srt_subs],
            'input_path': srt_path
        }
        segments = srt_subs
        input_path = srt_path
    elif mp4_file or wav_file:
        # mp4/wavの場合は従来通り
        file = mp4_file if mp4_file else wav_file
        if file.name not in st.session_state:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as f:
                f.write(file.read())
                input_path = f.name
            audio_path = extract_audio(input_path) if input_path.endswith(".mp4") else input_path
            segments = list(transcribe(audio_path))
            original_texts = [seg.text for seg in segments]

            data = []
            for i, orig in enumerate(original_texts):
                data.append({
                    "start": f"{segments[i].start:.2f}",
                    "original": orig,
                    "translation": translate_with_context(segments, i, target_lang),
                    "end": f"{segments[i].end:.2f}",
                    "start_offset": 0.0,
                    "end_offset": 0.0,
                })
            st.session_state[file.name] = {
                'df': pd.DataFrame(data),
                'audio_path': audio_path,
                'segments': segments,
                'original_texts': original_texts,
                'input_path': input_path
            }
        df = st.session_state[file.name]['df']
        audio_path = st.session_state[file.name].get('audio_path', None)
        segments = st.session_state[file.name]['segments']
        original_texts = st.session_state[file.name]['original_texts']
        input_path = st.session_state[file.name]['input_path']
    # SRT/音声共通
    if "df" in st.session_state:
        data_editor_df = st.session_state.df
    else:
        data_editor_df = st.session_state[file_name]['df']

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
    if mp4_file and "srt_path" in st.session_state:
        st.subheader("🎥 字幕付き動画を生成")
        if st.button("▶️ 動画に字幕を焼き込む"):
            # mp4_fileがある場合はmp4のパスを使う
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
                f.write(mp4_file.read())
                video_path = f.name
            output_video_path = burn_subtitles(video_path, st.session_state["srt_path"])
            with open(output_video_path, "rb") as f:
                st.download_button("⬇️ 字幕付き動画をダウンロード (.mp4)", f, file_name="subtitled_video.mp4")
