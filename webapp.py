import os
import base64
import re
from typing import List, Optional, Tuple

import gradio as gr

from .agent import create_session, DataAgentSession


def _ensure_str_or_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _extract_image_paths(text: str) -> List[str]:
    if not text:
        return []
    # Match typical saved paths like "images/fig.png" optionally with backslashes
    pattern = r"(?:^|\s)(images[\\/][\w\-\.]+\.png)"
    return re.findall(pattern, text)


def _init_session() -> DataAgentSession:
    images_dir = os.path.join(os.getcwd(), "images")
    os.makedirs(images_dir, exist_ok=True)
    return create_session(images_dir=images_dir)


def load_csv(
    uploaded_file: Optional[gr.File],
    df_name: str,
    sep: Optional[str],
    encoding: Optional[str],
    session: DataAgentSession,
) -> str:
    if session is None:
        return "❌ 会话未初始化。"
    df_name = df_name.strip() if df_name else "df"
    sep = _ensure_str_or_none(sep)
    encoding = _ensure_str_or_none(encoding)

    if uploaded_file is None:
        return "⚠️ 请先上传一个 CSV 文件。"

    try:
        with open(uploaded_file.name, "rb") as f:
            raw_bytes = f.read()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        msg = session.preload_csv(
            df_name=df_name,
            file_b64=b64,
            sep=sep,
            encoding=encoding,
        )
        return msg
    except Exception as e:
        return f"❌ 加载失败：{e}"


def chat(
    message: str,
    history: List[Tuple[str, str]],
    gallery_paths: List[str],
    session: DataAgentSession,
):
    if session is None:
        return history, gallery_paths, "❌ 会话未初始化。"
    user_text = message or ""
    history = history + [(user_text, "")]  # placeholder
    try:
        reply = session.send(user_text)
    except Exception as e:
        reply = f"❌ 调用失败：{e}"

    # Append possible image paths to gallery
    new_image_paths = []
    for rel in _extract_image_paths(reply):
        abs_path = os.path.abspath(rel)
        if os.path.exists(abs_path):
            new_image_paths.append(abs_path)

    updated_gallery = gallery_paths + new_image_paths if new_image_paths else gallery_paths
    history[-1] = (user_text, reply)
    return history, updated_gallery, ""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Data Agent - CSV Q&A") as demo:
        gr.Markdown("**Data Agent** · 上传 CSV 后与智能体对话进行分析与可视化。")

        session_state = gr.State(_init_session())

        with gr.Row():
            csv_file = gr.File(label="上传 CSV", file_types=[".csv"])
            df_name = gr.Textbox(label="DataFrame 名称", value="df")
            sep = gr.Textbox(label="分隔符 (可选)")
            encoding = gr.Textbox(label="编码 (可选)")
            load_btn = gr.Button("加载 CSV")

        load_status = gr.Markdown()

        with gr.Row():
            chatbot = gr.Chatbot(height=420)
            gallery = gr.Gallery(
                label="生成的图片",
                columns=2,
                preview=True,
                height=420,
            )

        with gr.Row():
            msg = gr.Textbox(show_label=False, placeholder="输入你的问题，例如：‘查看 df 的列信息’ 或 ‘用 df 画 tenure 的直方图’")
            send = gr.Button("发送", variant="primary")
            clear = gr.Button("清空对话")

        def _on_load_csv(file, df_name_val, sep_val, enc_val, sess):
            return load_csv(file, df_name_val, sep_val, enc_val, sess)

        load_btn.click(
            _on_load_csv,
            inputs=[csv_file, df_name, sep, encoding, session_state],
            outputs=[load_status],
        )

        def _on_send(user_msg, hist, gal, sess):
            new_hist, new_gal, err = chat(user_msg, hist or [], gal or [], sess)
            # Clear input if success
            if not err:
                return "", new_hist, new_gal, gr.update()
            return user_msg, new_hist, new_gal, gr.update(value=f"⚠️ {err}")

        send.click(
            _on_send,
            inputs=[msg, chatbot, gallery, session_state],
            outputs=[msg, chatbot, gallery, load_status],
        )
        msg.submit(
            _on_send,
            inputs=[msg, chatbot, gallery, session_state],
            outputs=[msg, chatbot, gallery, load_status],
        )

        def _on_clear():
            return [], []

        clear.click(_on_clear, None, [chatbot, gallery])

    return demo


if __name__ == "__main__":
    ui = build_ui()
    ui.launch()


