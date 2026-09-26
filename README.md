# Experience Capture

把人类自然语言中的经验，转换成可读、可检查、可供 Agent 使用的标准结构。

当前版本聚焦一个明确问题：**一段经验到底应该如何表达**。它不负责数据库入库、向量检索或自动学习，先把结构化标准做清楚。

## 这是什么

Experience Capture 是一个面向任意 Agent 的经验结构化插件原型：

- 输入：一段自然语言经验；
- 输出：`experience-standard/v1` JSON 与人可读经验卡；
- 关键设计：区分原文明示内容 `explicit` 与模型推导内容 `inferred`；
- 防止幻觉：无法从原文确定的信息进入 `knowledge_gaps`，不会静默补造。

## 经验标准

一条经验会被拆成十个部分：

| 字段 | 含义 |
|---|---|
| `source` | 原始文本、语言和来源 |
| `identity` | 标题、摘要、主类型和次类型 |
| `situation` | 目标、触发条件、上下文和相关对象 |
| `guidance` | 原则、判断规则、步骤和应避免的行为 |
| `applicability` | 适用条件、前置条件、例外和边界 |
| `outcome` | 预期结果、成功信号和失败信号 |
| `evidence` | 观察、反例、验证方法和置信度 |
| `indexing` | 领域、任务、标签、别名和跨领域关联 |
| `knowledge_gaps` | 仍需向人确认的问题 |
| `schema_version` | 固定为 `experience-standard/v1` |

完整定义见 [EXPERIENCE_STANDARD.md](EXPERIENCE_STANDARD.md)，可运行示例见 [examples/constitutive-model-selection.v1.json](examples/constitutive-model-selection.v1.json)。

## 快速开始

环境要求：

- Python 3.10+
- 一个 OpenAI 兼容的 Chat Completions 接口

```powershell
cd experience-capture

$env:OPENAI_BASE_URL = "https://your-provider.example/v1"
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "your-model"

$env:PORT = "8091"
python scripts/server.py
```

打开 <http://127.0.0.1:8091/>。

无需模型也可以验证结构定义与输出渲染：

```powershell
python scripts/test_experience_standard.py
python scripts/test_structure_api.py
```

## 接入外部 Agent

结构化接口：

```http
POST /v1/structure
Content-Type: application/json
X-API-Key: dev-key
```

请求：

```json
{
  "text": "仿真中本构的选择要根据材料、损伤预期来决定，断裂和拉伸用的本构是不一样的。"
}
```

响应：

```json
{
  "ok": true,
  "record": {},
  "markdown": "人可读经验卡",
  "model": "your-model"
}
```

该接口不会写入数据库。

### 环境变量

| 变量 | 用途 |
|---|---|
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址 |
| `OPENAI_API_KEY` | API 密钥，不要提交到仓库 |
| `OPENAI_MODEL` | 模型名称 |
| `EXPERIENCE_API_KEY` | 本地 HTTP 接口鉴权值，默认 `dev-key` |
| `PORT` | 服务端口，默认 `8080` |

也支持 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 作为通用变量名。仓库中的 `.env.local` 会被自动加载，并且已经被 Git 忽略。

## 测试

```powershell
python scripts/test_experience_standard.py
python scripts/test_structure_api.py
python scripts/test_vertical_slice.py
python -m py_compile scripts/server.py scripts/experience_standard.py
```

当前验证结果：

```text
experience standard: PASS
structure API: PASS
vertical slice: PASS
```

## 目录结构

```text
experience-capture/
├── .codex-plugin/plugin.json       Codex 插件清单
├── EXPERIENCE_STANDARD.md          经验标准 V1
├── examples/                       完整结构化示例
├── scripts/
│   ├── experience_standard.py      标准结构、提示词与校验
│   ├── server.py                   本地 HTTP 服务
│   ├── schema.sql                  未来的 PostgreSQL/pgvector 设计草稿
│   └── test_*.py                   测试
├── skills/                         Codex Skills
└── web/index.html                  浏览器测试页
```

## 当前边界

这是一个“结构化优先”的原型，已经实现：

- 自然语言到标准结构的转换；
- 明示内容与推导内容分离；
- 结构化字段校验；
- 人可读经验卡渲染；
- 浏览器测试页；
- 可替换的 OpenAI 兼容模型接口。

以下内容尚未纳入当前里程碑：

- 经验入库和去重；
- PostgreSQL + pgvector 检索；
- 分类树和标签词表；
- 冲突检测；
- 主动提问；
- 多租户权限；
- MCP 工具暴露。

旧版 SQLite 接口仍保留在 `server.py` 中用于对照，见 `scripts/test_vertical_slice.py`。

## License

[MIT](LICENSE)
