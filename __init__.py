"""Data Agent package

提供可编程 API 与命令行两种使用方式：

- DataAgentSession: 面向对象会话，支持多轮对话、CSV 预加载与图片目录设置
- create_session: 简便工厂函数
- chat_once: 单轮对话（无历史）

示例：

    from data_agent import create_session

    session = create_session(images_dir="./images")
    session.preload_csv(df_name="df", file_path="telco_data.csv")
    print(session.send("用 df 画 tenure 的直方图并保存图像"))
"""

from .agent import DataAgentSession, create_session, chat_once, graph  # noqa: F401

__all__ = [
    "DataAgentSession",
    "create_session",
    "chat_once",
    "graph",
]


