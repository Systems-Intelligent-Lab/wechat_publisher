# wechat_publisher

> GitHub 地址：[https://github.com/Systems-Intelligent-Lab/wechat_publisher](https://github.com/Systems-Intelligent-Lab/wechat_publisher)

将 Markdown 一键渲染为 **微信公众号可直接粘贴的富文本 HTML**，并支持发布到公众号「草稿箱」。

## 功能特性

- **Markdown → 公众号 HTML**：内置多套主题（如 `default`、`orangeheart`、`lapis`、`phycat` 等）
- **主题管理**：列出/添加/删除自定义主题
- **发布到公众号草稿箱**：输入 Markdown（含 frontmatter），发布后返回 `media_id`
- **本地图片上传**：Markdown 中使用本地相对路径图片（如 `./assets/a.png`），发布时自动解析并上传
- **无需本机 Node.js（可选）**：若未安装 `node`，会自动使用 Docker 运行渲染/发布（更易部署）

## 依赖与环境要求

- **Python**: 3.7+
- 满足其一即可：
  - **方案 A（推荐开发）**：本机安装 Node.js 18+（`node`/`npm` 在 PATH）
  - **方案 B（推荐部署/无 Node 环境）**：安装并启动 Docker（会自动拉取 `node:20-bookworm-slim` 镜像）

你也可以通过环境变量指定 Node 镜像：

- `WECHAT_PUBLISHER_NODE_IMAGE`: 默认 `node:20-bookworm-slim`

## 安装

### 方式一：直接通过 GitHub URL 安装（推荐）

无需克隆仓库，一行命令即可安装最新版本：

```bash
pip install git+https://github.com/Systems-Intelligent-Lab/wechat_publisher.git
```

安装指定分支或 Tag：

```bash
# 安装指定分支
pip install git+https://github.com/Systems-Intelligent-Lab/wechat_publisher.git@main

# 安装指定 Tag（如 v1.0.0）
pip install git+https://github.com/Systems-Intelligent-Lab/wechat_publisher.git@v1.0.0
```

### 方式二：克隆后本地安装

先克隆仓库，再在项目根目录安装：

```bash
git clone https://github.com/Systems-Intelligent-Lab/wechat_publisher.git
cd wechat_publisher
pip install .
```

（开发时推荐使用可编辑安装，代码修改后无需重新安装）

```bash
pip install -e .
```

## 快速开始：渲染 HTML

```python
from wechat_publisher.engine import WechatPublisher

bot = WechatPublisher()
md = """---\n\
title: 渲染示例\n\
---\n\
\n\
# 标题\n\
> 这是一个测试。\n\
"""

html = bot.render_html(md, theme="orangeheart")
print(html)
```

## 主题管理

```python
from wechat_publisher.engine import WechatPublisher

bot = WechatPublisher()

print(bot.list_themes())  # JSON 字符串

# 添加一个自定义主题（本地路径或 URL 均可）
bot.add_theme("mytheme", "https://wenyan.yuzhi.tech/manhua.css")

# 删除自定义主题
bot.remove_theme("mytheme")
```

## 发布到公众号草稿箱

### 准备环境变量

发布到微信需要配置：

- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

```bash
export WECHAT_APP_ID="your_app_id"
export WECHAT_APP_SECRET="your_app_secret"
```

> 注意：微信公众号接口通常要求把运行机器的公网 IP 加到后台的 **IP 白名单**，否则会报错。

### 发布示例（含本地图片上传）

下面是一段可直接运行的端到端示例：会先下载一张图片到本地，然后在 Markdown 的 `cover` 和正文图片中都引用该本地文件，最后发布到公众号草稿箱。

````python
from wechat_publisher.engine import WechatPublisher
import os
from urllib.request import Request, urlopen

# 初始化
bot = WechatPublisher()

# 下载一张图片到本地，用于测试“本地图片上传”
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "_tmp_assets")
os.makedirs(ASSET_DIR, exist_ok=True)
LOCAL_IMG = os.path.join(ASSET_DIR, "cover.png")
if not os.path.exists(LOCAL_IMG):
    req = Request("https://www.baidu.com/img/flexible/logo/pc/result.png", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as resp, open(LOCAL_IMG, "wb") as f:
        f.write(resp.read())

# 准备 Markdown
md = """---
title: 微信公众号测试发布
author: 桥豆麻袋
cover: ./_tmp_assets/cover.png
---
# 标题
> 这是一个测试。

![示例图片](./_tmp_assets/cover.png)
```python
print('hello')
```
"""

media_id = bot.publish_article(
    md,
    theme="lapis",
    base_dir=BASE_DIR,
    app_id=os.getenv("WECHAT_APP_ID"),
    app_secret=os.getenv("WECHAT_APP_SECRET"),
)
print("published media_id:", media_id)
````

## 本地图片上传（相对路径）

微信发布要求 **必须有封面或正文至少一张图片**。

如果你的 Markdown 使用本地图片（相对路径）：

```md
---
title: 本地图片示例
cover: ./_tmp_assets/cover.png
---

![正文图片](./_tmp_assets/cover.png)
```

发布时请传 `base_dir`（用于解析相对路径）：

```python
import os
from wechat_publisher.engine import WechatPublisher

bot = WechatPublisher()
base_dir = os.path.dirname(os.path.abspath(__file__))

media_id = bot.publish_article(
    md,
    theme="orangeheart",
    base_dir=base_dir,
)
```

在 Docker 兜底模式下，`base_dir` 会自动挂载进容器（无需你手动处理挂载）。

> 提示：如果你用的是 `publish_article(file="xxx.md")` 从文件发布，那么 `base_dir` 可以不传；
> 程序会自动使用该 Markdown 文件所在目录作为图片相对路径的基准目录。

## 测试

项目提供了多组渲染相关的自动化测试（不依赖公众号发布）：

```bash
python -m unittest -v tests/test_render_unittest.py
```

首次运行可能会较慢（需要拉取 Node 镜像并安装 JS 依赖），后续会更快（`node_modules` 会缓存到项目目录）。

## 常见问题排查

- **报错 `未检测到 Node.js`**：
  - 安装 Node.js 18+，或安装并启动 Docker（本项目会自动走容器兜底）
- **报错 `fetch failed`**：
  - 通常是图片 URL 域名无法解析/网络不可达；优先换成你环境可访问的图片域名，或改用本地图片路径
- **发布失败（鉴权/IP 白名单）**：
  - 检查 `WECHAT_APP_ID/WECHAT_APP_SECRET`
  - 检查公众号后台的 IP 白名单配置

## 贡献与反馈

欢迎提交 Issue 或 PR：[https://github.com/Systems-Intelligent-Lab/wechat_publisher](https://github.com/Systems-Intelligent-Lab/wechat_publisher)
