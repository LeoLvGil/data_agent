## Data Agent 使用指南（包 + 命令行）

- **环境准备**
  - Python 3.9+
  - 安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
  - 可选：为数据库查询在项目根目录放置 `.env`（用于 `sql_inter` / `extract_data`）：
    ```env
    HOST=your_mysql_host
    USER=your_mysql_user
    MYSQL_PW=your_mysql_password
    DB_NAME=your_db_name
    PORT=3306
    ```

- **运行位置**
  - 作为模块运行（推荐）：
    ```bash
    python -m data_agent --interactive [OPTIONS]
    ```
  - 或在项目根目录使用兼容入口：
    ```bash
    python graph.py [OPTIONS]
    ```

- **常用参数**
  - `--prompt`：单轮对话；不提供则进入交互模式。
  - `--interactive`：强制进入交互模式（输入 `exit`/`quit` 退出）。
  - 预加载 CSV 到 pandas DataFrame：
    - `--csv_path` 本地 CSV 路径
    - `--csv_url` 直连 URL（含 LangSmith/LangGraph Studio 拖拽上传后的预签名链接）
    - `--csv_b64` Base64 编码的 CSV 内容
    - `--csv_text` 纯文本 CSV 内容
    - `--df_name` DataFrame 名称（默认 `df`）
    - `--sep` 分隔符（默认自动嗅探）
    - `--encoding` 文件编码（留空由 pandas 推断）
  - 图像输出目录：
    - `--images_dir` 自定义图片保存目录（默认 `./images`）
    - 或设置环境变量 `IMAGE_OUTPUT_DIR` 覆盖默认目录

- **示例：单轮对话**
  ```bash
  python data_agent/graph.py --csv_path telco_data.csv --df_name df --prompt "用 df 画 tenure 的直方图并保存图像"
  ```

- **示例：交互模式**
  ```bash
  python -m data_agent --interactive --csv_path telco_data.csv --df_name df
  # 进入后直接对话：
  # You > 帮我看看 df 的缺失值比例，并给出前 5 行示例
  ```

- **示例：指定图片输出目录（Windows）**
  ```bash
  python -m data_agent --csv_path telco_data.csv --df_name df --images_dir "E:\\AI Coding Explore\\data_agent\\outputs" --prompt "用 df 画 tenure 直方图并保存为 fig.png"
  ```

- **关于绘图（`fig_inter`）**
  - Agent 生成并执行绘图代码，保存 PNG 到 `--images_dir` 或默认 `./images`。
  - 若你自行提供绘图代码给 Agent 执行，请确保创建图像对象并赋值给变量（如 `fig`），且不要调用 `plt.show()`。
  - 执行成功后会返回相对当前工作目录的图片路径（如 `images/fig.png`）。

- **关于 LangSmith/LangGraph Studio 拖拽上传 CSV**
  - 拖拽后会得到可访问的预签名 URL，Agent 会用 `read_data` 从该 URL 读取；命令行也可手动指定：
    ```bash
    python data_agent/graph.py --csv_url https://.../presigned.csv --df_name df --prompt "描述 df 的列信息与基本统计"
    ```

---

### Web 界面（Gradio）

- 启动服务（本地）：
  ```bash
  python -m pip install -r requirements.txt
  python -m data_agent.webapp
  ```
  打开浏览器访问：`http://127.0.0.1:7860`

- 使用步骤：
  1. 在页面左上方上传 `.csv` 文件。
  2. 设置 `DataFrame 名称`（默认 `df`），必要时填写分隔符与编码。
  3. 点击“加载 CSV”，页面顶部将显示加载成功及形状信息（例如 `形状为 (7043, 21)`）。
  4. 在聊天框直接提问（无需再次要求读取文件），示例：
     - “df 有多少行？”
     - “给出 df 的列名与基本统计”
     - “用 df 画 tenure 的直方图，保存为 fig.png”
  5. 生成的图片会显示在右侧“生成的图片”区域，同时文件保存在项目 `./images/` 目录。

- 模型如何“看见”数据：
  - 成功加载 CSV 后，系统会自动注入一条 `system` 消息，明确告诉模型当前进程中已有名为 `df` 的 DataFrame（包括形状与部分列名）。因此你可以直接围绕 `df` 提问和作图。

- 常见问题：
  - 页面已提示“成功创建 pandas 对象 df …”，但模型仍让你提供文件路径：请点击“清空对话”，再点击“加载 CSV”，然后直接提问如“df 有多少行？”。
  - 端口冲突：可编辑 `data_agent/webapp.py` 末尾，将 `ui.launch()` 改为 `ui.launch(server_port=7861)` 后重新运行。
  - 依赖冲突：建议在全新虚拟环境中安装 `requirements.txt` 再运行。

---

### 可编程 API

作为包引入并以编程方式对话与作图：

```python
from data_agent import create_session, chat_once

# 单轮对话
print(chat_once(
    "用 df 画 tenure 直方图并保存为 fig.png",
    images_dir="./images",
    preload={"df_name": "df", "file_path": "telco_data.csv"}
))

# 会话式（多轮）
session = create_session(images_dir="./images")
print(session.preload_csv(df_name="df", file_path="telco_data.csv"))
print(session.send("查看 df 的列和行数"))
print(session.send("用 df 画 tenure 的直方图，保存为 fig.png"))
```
