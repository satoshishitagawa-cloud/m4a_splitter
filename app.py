import os
import glob
import subprocess
import tempfile
import zipfile
import streamlit as st

st.set_page_config(page_title="M4A Splitter", page_icon="✂️", layout="centered")
st.title("✂️ M4A Audio Splitter")
st.caption("スマホなどの長時間のm4a音声を、指定分数ごとに無劣化・高速分割します。")

uploaded_file = st.file_uploader("M4Aファイルを選択", type=["m4a"])
split_minutes = st.slider("分割間隔（分）", min_value=5, max_value=60, value=15, step=5)

if "processed_data" not in st.session_state:
    st.session_state.processed_data = None

if uploaded_file is not None:
    file_details = {"FileName": uploaded_file.name, "FileSize": f"{uploaded_file.size / (1024*1024):.2f} MB"}
    st.write(f"📁 ファイル名: **{file_details['FileName']}** ({file_details['FileSize']})")

    if st.button("分割を開始する", type="primary"):
        with st.spinner("音声を無劣化分割中..."):
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, "input.m4a")
                with open(input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                output_pattern = os.path.join(temp_dir, "output_%03d.m4a")
                segment_time = split_minutes * 60

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", input_path,
                    "-f", "segment",
                    "-segment_time", str(segment_time),
                    "-c", "copy",
                    output_pattern
                ]

                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    st.error("分割処理中にエラーが発生しました。")
                    st.code(result.stderr)
                    st.session_state.processed_data = None
                else:
                    output_files = sorted(glob.glob(os.path.join(temp_dir, "output_*.m4a")))
                    base_name = os.path.splitext(uploaded_file.name)[0]

                    if not output_files:
                        st.warning("分割されたファイルが見つかりませんでした。")
                        st.session_state.processed_data = None
                    elif len(output_files) == 1:
                        with open(output_files[0], "rb") as f:
                            single_data = f.read()
                        st.session_state.processed_data = {
                            "type": "single",
                            "file_name": f"split_{uploaded_file.name}",
                            "data": single_data
                        }
                    else:
                        parts = []
                        for idx, f_path in enumerate(output_files):
                            part_name = f"{base_name}_part{idx+1:02d}.m4a"
                            with open(f_path, "rb") as f:
                                parts.append((part_name, f.read()))

                        zip_path = os.path.join(temp_dir, "split_audios.zip")
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for part_name, data in parts:
                                zip_file.writestr(part_name, data)

                        with open(zip_path, "rb") as zf:
                            zip_data = zf.read()

                        st.session_state.processed_data = {
                            "type": "multiple",
                            "base_name": base_name,
                            "count": len(output_files),
                            "zip_name": f"{base_name}_split.zip",
                            "zip_data": zip_data,
                            "parts": parts
                        }

    if st.session_state.processed_data is not None:
        pdata = st.session_state.processed_data

        if pdata["type"] == "single":
            st.info("音声の長さが指定した分割間隔以下のため、分割されませんでした。")
            st.download_button(
                label="音声をダウンロード",
                data=pdata["data"],
                file_name=pdata["file_name"],
                mime="audio/mp4"
            )
        elif pdata["type"] == "multiple":
            st.success(f"{pdata['count']} 個のファイルに分割されました。")

            st.download_button(
                label="📦 すべての分割ファイルをZIPで一括ダウンロード",
                data=pdata["zip_data"],
                file_name=pdata["zip_name"],
                mime="application/zip"
            )

            with st.expander("個別にダウンロード"):
                for idx, (part_name, part_data) in enumerate(pdata["parts"]):
                    st.download_button(
                        label=f"⬇️ {part_name}",
                        data=part_data,
                        file_name=part_name,
                        mime="audio/mp4",
                        key=f"dl_{idx}"
                    )