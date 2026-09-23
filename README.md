# 离线小册子拼版 API

基于 Python + FastAPI 的**离线**小册子（按帖装订）拼版服务。输入全书总页数、每帖最多纸张数和左/右装订方向，服务按原页顺序分帖，并按纸张**从外到内**返回每帖各张纸正/反面的**左、右页码**；补白页用 `null` 表示。

## 一条命令启动

需要本机已安装 Docker 与 Docker Compose v2：

```bash
docker compose up --build -d
```

镜像构建时自动安装全部依赖，容器启动时自动完成初始化并拉起服务（`docker-entrypoint.sh` → `uvicorn`），无需任何额外步骤。停止服务用 `docker compose down`。

## 必要配置

所有配置均有默认值，**不配置也能直接用**；需要修改时在项目根目录创建 `.env` 文件（Compose 会自动读取）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST_PORT` | `8000` | 宿主机映射端口（容器内固定监听 8000） |
| `MAX_TOTAL_PAGES` | `100000` | 允许的最大总页数，超过返回 `400` |

`.env` 示例：

```dotenv
HOST_PORT=9000
MAX_TOTAL_PAGES=50000
```

## API 地址与端口

默认地址：**http://localhost:8000**

- 交互文档（Swagger UI）：http://localhost:8000/docs
- OpenAPI 描述：http://localhost:8000/openapi.json
- 健康检查：http://localhost:8000/healthz

## 拼版接口

```
GET /api/v1/impose?total_pages=16&max_sheets=4&binding=left
```

### 请求参数（Query）

| 参数 | 类型 | 必填 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `total_pages` | int | 是 | ≥ 1 正整数 | 全书总页数 |
| `max_sheets` | int | 是 | ≥ 1 正整数 | 每帖最多纸张数；每帖最多容纳 **4 × 纸张数** 个页位 |
| `binding` | string | 是 | `left` / `right` | 左装订 / 右装订 |

### 拼版规则

1. **分帖**：按原页码顺序切分，非末帖均为满帖（`4 × max_sheets` 页）；仅**最后一帖**在帖末补空白至 4 的倍数，空白页为 `null`。
2. **左装订**（以帖内页位 `p[0..n-1]`、纸张由外到内第 `k` 张，`k` 从 0 起）：
   - 正面：左 = `p[n-1-2k]`（末页），右 = `p[2k]`（首页）
   - 背面：左 = `p[2k+1]`（次页），右 = `p[n-2-2k]`（倒数第二页）
3. **右装订**：在左装订基础上对每个面**镜像交换左、右页位**。

### 返回示例

`total_pages=18&max_sheets=4&binding=right`（前 16 页为满帖，末帖 2 张真实页 + 2 张补白，共 1 张纸）：

```json
{
  "total_pages": 18,
  "max_sheets_per_signature": 4,
  "binding": "right",
  "signature_count": 2,
  "signatures": [
    {
      "number": 1,
      "sheets": 4,
      "blank_pages": 0,
      "pages": [
        {
          "sheet": 1,
          "front": { "left": 1, "right": 16 },
          "back":  { "left": 15, "right": 2 }
        }
      ]
    },
    {
      "number": 2,
      "sheets": 1,
      "blank_pages": 2,
      "pages": [
        {
          "sheet": 1,
          "front": { "left": 17, "right": null },
          "back":  { "left": null, "right": 18 }
        }
      ]
    }
  ]
}
```

字段说明：

- `number`：帖号，从 1 开始。
- `sheets`：该帖实际纸张数；`pages` 按纸张**从外到内**排列。
- `sheet`：帖内纸张序号，从最外张开始为 1。
- `front` / `back`：该张纸正面 / 背面的 `left`、`right` 页码；`null` 表示空白页。

快速验证（左装订 16 页、每帖 4 张纸）：

```bash
curl "http://localhost:8000/api/v1/impose?total_pages=16&max_sheets=4&binding=left"
```

### 错误响应（4xx）

参数非法时返回 4xx 并带明细：

- `422`：`total_pages` 或 `max_sheets` 不是 ≥ 1 的整数、`binding` 不是 `left`/`right`、缺少必填参数等（FastAPI 校验）。
- `400`：`total_pages` 超过服务上限 `MAX_TOTAL_PAGES`。

```bash
curl -i "http://localhost:8000/api/v1/impose?total_pages=0&max_sheets=4&binding=left"
# HTTP/1.1 422 Unprocessable Content
```

## 本地开发与测试（不使用 Docker）

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000  # 启动开发服务器
pytest -q                                    # 运行测试(23 个用例)
```

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── imposition.py     # 拼版核心逻辑(分帖 / 左右装订)
│   └── main.py           # FastAPI 路由、参数校验、响应模型
├── tests/                # pytest 用例(核心逻辑 + HTTP 层)
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh  # 容器初始化与启动
├── requirements.txt      # 运行时依赖
└── requirements-dev.txt  # 测试依赖
```
