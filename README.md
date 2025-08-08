## Data Agent 命令行使用指南

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
  - 在项目根目录运行内层脚本：
    ```bash
    python data_agent/graph.py [OPTIONS]
    ```
  - 或进入内层目录运行：
    ```bash
    cd data_agent
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
  python data_agent/graph.py --interactive --csv_path telco_data.csv --df_name df
  # 进入后直接对话：
  # You > 帮我看看 df 的缺失值比例，并给出前 5 行示例
  ```

- **示例：指定图片输出目录（Windows）**
  ```bash
  python data_agent/graph.py --csv_path telco_data.csv --df_name df --images_dir "E:\\AI Coding Explore\\data_agent\\outputs" --prompt "用 df 画 tenure 直方图并保存为 fig.png"
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
