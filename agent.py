import os
import base64
import io
from typing import List, Tuple, Optional, Any

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import matplotlib
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import pymysql
from langchain_tavily import TavilySearch


# 默认图片输出目录（可通过环境变量 IMAGE_OUTPUT_DIR 覆盖）
IMAGE_OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR") or os.path.join(os.getcwd(), "images")


def set_image_output_dir(path: str) -> None:
    global IMAGE_OUTPUT_DIR
    IMAGE_OUTPUT_DIR = path


# 加载环境变量
load_dotenv(override=True)

# ✅ 创建Tavily搜索工具
search_tool = TavilySearch(max_results=5, topic="general")


# ✅ 创建SQL查询工具
_sql_description = (
    """
当用户需要进行数据库查询工作时，请调用该函数。
该函数用于在指定MySQL服务器上运行一段SQL代码，完成数据查询相关工作，
并且当前函数是使用pymsql连接MySQL数据库。
本函数只负责运行SQL代码并进行数据查询，若要进行数据提取，则使用另一个extract_data函数。
"""
)


class SQLQuerySchema(BaseModel):
    sql_query: str = Field(description=_sql_description)


@tool(args_schema=SQLQuerySchema)
def sql_inter(sql_query: str) -> str:
    """在 MySQL 上执行只读 SQL 查询并以 JSON 字符串返回查询结果。"""
    load_dotenv(override=True)
    host = os.getenv('HOST')
    user = os.getenv('USER')
    mysql_pw = os.getenv('MYSQL_PW')
    db = os.getenv('DB_NAME')
    port = os.getenv('PORT')

    connection = pymysql.connect(
        host=host,
        user=user,
        passwd=mysql_pw,
        db=db,
        port=int(port),
        charset='utf8'
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            results = cursor.fetchall()
    finally:
        connection.close()
    return json.dumps(results, ensure_ascii=False)


# ✅ 数据提取工具
class ExtractQuerySchema(BaseModel):
    sql_query: str = Field(description="用于从 MySQL 提取数据的 SQL 查询语句。")
    df_name: str = Field(description="指定用于保存结果的 pandas 变量名称（字符串形式）。")


@tool(args_schema=ExtractQuerySchema)
def extract_data(sql_query: str, df_name: str) -> str:
    """执行 SQL 并将结果加载为 pandas DataFrame，保存到全局变量 `df_name`。"""
    load_dotenv(override=True)
    host = os.getenv('HOST')
    user = os.getenv('USER')
    mysql_pw = os.getenv('MYSQL_PW')
    db = os.getenv('DB_NAME')
    port = os.getenv('PORT')

    connection = pymysql.connect(
        host=host,
        user=user,
        passwd=mysql_pw,
        db=db,
        port=int(port),
        charset='utf8'
    )
    try:
        df = pd.read_sql(sql_query, connection)
        globals()[df_name] = df
        return f"✅ 成功创建 pandas 对象 `{df_name}`，包含从 MySQL 提取的数据。"
    except Exception as e:
        return f"❌ 执行失败：{e}"
    finally:
        connection.close()


# ✅ CSV 读取工具
class ReadData(BaseModel):
    df_name: str = Field(description="指定用于保存结果的 pandas 变量名称（字符串形式）。")
    file_path: Optional[str] = Field(default=None, description="服务器本地文件路径（.csv）")
    file_url: Optional[str] = Field(default=None, description="文件的可直连 URL（含 LangSmith Studio 拖拽上传后的预签名链接）")
    file_b64: Optional[str] = Field(default=None, description="CSV 原始内容的 Base64 编码字符串")
    csv_text: Optional[str] = Field(default=None, description="纯文本的 CSV 内容（直接粘贴）")
    sep: Optional[str] = Field(default=None, description="分隔符，留空时自动嗅探。常见为 ',' 或 '\t'")
    encoding: Optional[str] = Field(default=None, description="文件编码，留空则由 pandas 猜测或使用系统默认")


@tool(args_schema=ReadData)
def read_data(
    df_name: str,
    file_path: Optional[str] = None,
    file_url: Optional[str] = None,
    file_b64: Optional[str] = None,
    csv_text: Optional[str] = None,
    sep: Optional[str] = None,
    encoding: Optional[str] = None,
):
    """从本地/URL/Base64/纯文本读取 CSV，创建 DataFrame 并保存为变量 `df_name`。"""
    try:
        read_kwargs = {}
        if sep is None:
            read_kwargs["sep"] = None
            read_kwargs["engine"] = "python"
        else:
            read_kwargs["sep"] = sep
        if encoding is not None:
            read_kwargs["encoding"] = encoding

        if file_path:
            df = pd.read_csv(file_path, **read_kwargs)
        elif file_url:
            df = pd.read_csv(file_url, **read_kwargs)
        elif file_b64:
            try:
                raw = base64.b64decode(file_b64)
            except Exception:
                return "❌ Base64 内容无法解码，请确认编码是否正确。"
            df = pd.read_csv(io.BytesIO(raw), **read_kwargs)
        elif csv_text:
            df = pd.read_csv(io.StringIO(csv_text), **read_kwargs)
        else:
            return "⚠️ 未提供文件来源。请在 file_path、file_url、file_b64 或 csv_text 中至少提供一个。"

        globals()[df_name] = df
        return f"✅ 成功创建 pandas 对象 `{df_name}`，包含从 CSV 读取的数据，形状为 {df.shape}。"
    except Exception as e:
        return f"❌ 执行失败：{e}"


# ✅ Python 代码执行工具（非绘图）
class PythonCodeInput(BaseModel):
    py_code: str = Field(description="一段合法的 Python 代码字符串，例如 '2 + 2' 或 'x = 3\ny = x * 2'")


@tool(args_schema=PythonCodeInput)
def python_inter(py_code):
    """执行非绘图类 Python 代码，返回表达式结果或新建变量字典。"""
    g = globals()
    try:
        result = eval(py_code, g)
        return _format_value(result)
    except Exception:
        global_vars_before = set(g.keys())
        try:
            exec(py_code, g)
        except Exception as e:
            return f"代码执行时报错{e}"
        global_vars_after = set(g.keys())
        new_vars = global_vars_after - global_vars_before
        if new_vars:
            result = {var: g[var] for var in new_vars}
            return _format_value(result)
        else:
            return "已经顺利执行代码"


# ✅ 绘图工具
class FigCodeInput(BaseModel):
    py_code: str = Field(description="要执行的 Python 绘图代码，必须使用 matplotlib/seaborn 创建图像并赋值给变量")
    fname: str = Field(description="图像对象的变量名，例如 'fig'，用于从代码中提取并保存为图片")


@tool(args_schema=FigCodeInput)
def fig_inter(py_code: str, fname: str) -> str:
    """执行绘图代码并将变量 `fname` 指向的图对象保存为 PNG 文件。"""
    current_backend = matplotlib.get_backend()
    matplotlib.use('Agg')

    local_vars = {"plt": plt, "pd": pd, "sns": sns}

    images_dir = IMAGE_OUTPUT_DIR
    os.makedirs(images_dir, exist_ok=True)

    try:
        g = globals()
        exec(py_code, g, local_vars)
        g.update(local_vars)
        fig = local_vars.get(fname, None)
        if fig:
            image_filename = f"{fname}.png"
            abs_path = os.path.join(images_dir, image_filename)
            fig.savefig(abs_path, bbox_inches='tight')
            rel_path = os.path.relpath(abs_path, os.getcwd())
            return f"✅ 图片已保存，路径为: {rel_path}"
        else:
            return "⚠️ 图像对象未找到，请确认变量名正确并为 matplotlib 图对象。代码中需包含例如 `fig = plt.figure()` 或 `fig, ax = plt.subplots()`，并以 `fname` 命名。"
    except Exception as e:
        return f"❌ 执行失败：{e}"
    finally:
        plt.close('all')
        matplotlib.use(current_backend)


# ✅ 提示词模板
prompt = (
    """
你是一名经验丰富的智能数据分析助手，擅长帮助用户高效完成以下任务：

1. 数据库查询：
   - 当用户需要获取数据库中某些数据或进行SQL查询时，请调用`sql_inter`工具。
2. 数据表提取：
   - 当用户希望将数据库中的表格导入Python环境进行后续分析时，请调用`extract_data`工具。
3. 非绘图类任务的Python代码执行：
   - 当用户需要执行Python脚本或进行数据处理、统计计算时，请调用`python_inter`工具。
4. 绘图类Python代码执行：
   - 当用户需要进行可视化展示（如生成图表、绘制分布等）时，请调用`fig_inter`工具。
   - 请确保使用图像对象变量并保存到文件。
5. 文件读取（CSV）：
   - 当用户上传或提供 CSV 文件时，请调用`read_data`工具。

回答要求：简体中文、简洁清晰；若生成图片，请返回 Markdown 图片链接（相对路径）。
"""
)


# ✅ 组装 Agent 图
tools = [search_tool, python_inter, fig_inter, sql_inter, extract_data, read_data]
model = ChatDeepSeek(model="deepseek-chat")
graph = create_react_agent(model=model, tools=tools, prompt=prompt)


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if isinstance(chunk, dict):
                if "text" in chunk:
                    parts.append(str(chunk.get("text")))
                elif "content" in chunk:
                    parts.append(str(chunk.get("content")))
                else:
                    parts.append(str(chunk))
            else:
                parts.append(str(chunk))
        return "\n".join(parts)
    return str(content)


# ---------- Safe formatting helpers to avoid oversized tool outputs ----------
def _truncate_text(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 100] + "\n... [truncated]" + f" (total {len(text)} chars)"


def _format_value(value: Any, depth: int = 0) -> str:
    try:
        import pandas as _pd  # local alias
    except Exception:
        _pd = None

    if depth > 2:
        return "<max depth reached>"

    # Pandas-friendly printing
    if _pd is not None:
        if isinstance(value, _pd.DataFrame):
            preview = value.head(5).to_string(index=False)
            return _truncate_text(
                f"DataFrame shape: {value.shape}\nhead(5):\n{preview}",
                max_chars=6000,
            )
        if isinstance(value, _pd.Series):
            uniques = list(value.dropna().unique())[:20]
            return _truncate_text(
                f"Series shape: {value.shape}; dtype: {value.dtype}; unique(sample<=20): {uniques}",
                max_chars=4000,
            )

    # Basic containers
    if isinstance(value, dict):
        items = list(value.items())[:30]
        rendered = []
        for k, v in items:
            rendered.append(f"{k!r}: {_format_value(v, depth+1)}")
        suffix = "" if len(value) <= 30 else f", ... (total_keys={len(value)})"
        return _truncate_text("{" + ", ".join(rendered) + "}" + suffix, max_chars=7000)
    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        head = seq[:30]
        inner = ", ".join(_format_value(v, depth+1) for v in head)
        closing = "]" if isinstance(value, list) else ")" if isinstance(value, tuple) else "}"
        prefix = "[" if isinstance(value, list) else "(" if isinstance(value, tuple) else "{"
        suffix = "" if len(seq) <= 30 else f", ... (total_len={len(seq)})"
        return _truncate_text(prefix + inner + suffix + closing, max_chars=7000)

    # Fallback
    try:
        return _truncate_text(str(value), max_chars=7000)
    except Exception:
        return f"<unprintable {type(value).__name__}>"


class DataAgentSession:
    """可复用的会话对象，支持多轮对话、CSV 预加载与图片目录设置。"""

    def __init__(self, images_dir: Optional[str] = None) -> None:
        self.history: List[Tuple[str, str]] = []
        if images_dir:
            set_image_output_dir(images_dir)

    def preload_csv(
        self,
        df_name: str,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        file_b64: Optional[str] = None,
        csv_text: Optional[str] = None,
        sep: Optional[str] = None,
        encoding: Optional[str] = None,
    ) -> str:
        payload = {
            "df_name": df_name,
            "file_path": file_path,
            "file_url": file_url,
            "file_b64": file_b64,
            "csv_text": csv_text,
            "sep": sep,
            "encoding": encoding,
        }
        return str(read_data.invoke(payload))

    def send(self, user_input: str) -> str:
        state = graph.invoke({
            "messages": (self.history + [("human", user_input)]) if self.history else [("human", user_input)]
        })
        messages = state.get("messages", [])
        if messages:
            self.history = messages
        # 返回最后一条 AI 消息文本
        last = messages[-1] if messages else None
        content = getattr(last, "content", None)
        if content is None and isinstance(last, dict):
            content = last.get("content")
        return _content_to_text(content)


def create_session(images_dir: Optional[str] = None) -> DataAgentSession:
    return DataAgentSession(images_dir=images_dir)


def chat_once(
    prompt_text: str,
    images_dir: Optional[str] = None,
    preload: Optional[dict] = None,
) -> str:
    session = DataAgentSession(images_dir=images_dir)
    if preload:
        session.preload_csv(**preload)
    return session.send(prompt_text)


