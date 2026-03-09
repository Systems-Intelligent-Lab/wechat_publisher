import subprocess
import os
import shutil
import json


class WechatPublisher:
    def __init__(self):
        # 自动定位包内 JS 文件的路径
        self.base_path = os.path.dirname(__file__)
        self.js_path = os.path.join(self.base_path, "renderer.js")
        self.node_project_dir = self.base_path

    def _ensure_node_runtime(self):
        node = shutil.which("node")
        if not node:
            return None
        return node

    def _ensure_docker_runtime(self):
        docker = shutil.which("docker")
        if not docker:
            return None
        return docker

    def _run_renderer(self, args, md_text, extra_env=None):
        """
        Run renderer.js with either:
        - local node runtime (preferred), or
        - docker node runtime (fallback, no host node required).
        """
        merged_env = os.environ.copy()
        if extra_env:
            merged_env.update({k: v for k, v in extra_env.items() if v is not None})

        node = self._ensure_node_runtime()
        if node:
            self._ensure_node_deps()
            return subprocess.run([node, self.js_path, *args], input=md_text, capture_output=True, text=True, encoding="utf-8", env=merged_env)

        docker = self._ensure_docker_runtime()
        if not docker:
            raise RuntimeError(
                "未检测到 Node.js（找不到 `node` 命令），同时也未检测到 Docker。\n" "渲染依赖文颜核心引擎：\n" "- 方案 A：安装 Node.js 18+（并确保 node/npm 在 PATH 里）\n" "- 方案 B：安装并启动 Docker（本工具可自动用容器执行渲染）"
            )

        # Use an official Node image. Dependencies will be installed into the mounted project dir
        # (node_modules persisted on host), so subsequent runs are fast.
        node_image = os.environ.get("WECHAT_PUBLISHER_NODE_IMAGE", "node:20-bookworm-slim")

        # If publishing with local images, we need to mount the base dir into the container.
        # We rewrite "--base-dir <host_path>" to "--base-dir /data".
        docker_volumes = ["-v", f"{self.node_project_dir}:/app"]
        rewritten_args = list(args)
        host_base_dir = _get_flag_value(rewritten_args, "--base-dir")
        if host_base_dir:
            docker_volumes += ["-v", f"{host_base_dir}:/data"]
            _set_flag_value(rewritten_args, "--base-dir", "/data")
        docker_env = []
        for key in ("WECHAT_APP_ID", "WECHAT_APP_SECRET"):
            val = merged_env.get(key)
            if val:
                docker_env.extend(["-e", f"{key}={val}"])
        cmd = [
            docker,
            "run",
            "--rm",
            "-i",
            *docker_env,
            *docker_volumes,
            "-w",
            "/app",
            node_image,
            "sh",
            "-lc",
            "npm install --omit=dev >/dev/null 2>&1 || npm install --omit=dev; " + "node /app/renderer.js " + " ".join(shlex_quote(a) for a in rewritten_args),
        ]
        return subprocess.run(cmd, input=md_text, capture_output=True, text=True, encoding="utf-8")

    def _normalize_markdown(self, md_text: str) -> str:
        """
        Wenyan frontmatter 需要出现在文本最开头。这里仅去掉 BOM + 开头的空行，
        避免三引号字符串默认带来的首行空行导致 title 解析失败。
        """
        if md_text is None:
            return ""
        # remove UTF-8 BOM and leading newlines
        return md_text.lstrip("\ufeff\r\n")

    def _ensure_node_deps(self):
        package_json = os.path.join(self.node_project_dir, "package.json")
        if not os.path.exists(package_json):
            raise RuntimeError(f"缺少 JS 依赖描述文件: {package_json}")

        node_modules = os.path.join(self.node_project_dir, "node_modules")
        if os.path.isdir(node_modules):
            return

        npm = shutil.which("npm")
        if not npm:
            raise RuntimeError("未检测到 npm（找不到 `npm` 命令）。\n" f"请在目录 `{self.node_project_dir}` 下手动执行 `npm install --omit=dev`，" "以安装渲染所需的 JS 依赖。")

        subprocess.run([npm, "install", "--omit=dev"], cwd=self.node_project_dir, check=True)

    def render_html(self, md_text, theme="default", highlight="solarized-light", mac_style=True, footnote=True):
        """将 Markdown 转换为带样式的 HTML"""
        args = ["render", "--theme", theme, "--highlight", highlight, "--mac-style", "true" if mac_style else "false", "--footnote", "true" if footnote else "false"]
        process = self._run_renderer(args, self._normalize_markdown(md_text))
        if process.returncode != 0:
            raise Exception(f"渲染失败: {process.stderr}")
        return process.stdout.strip()

    def render_styled(self, md_text, theme="default", highlight="solarized-light", mac_style=True, footnote=True):
        """渲染并返回包含元信息的结构化结果（title/cover/author 等）"""
        args = ["render-json", "--theme", theme, "--highlight", highlight, "--mac-style", "true" if mac_style else "false", "--footnote", "true" if footnote else "false"]
        process = self._run_renderer(args, self._normalize_markdown(md_text))
        if process.returncode != 0:
            raise Exception(f"渲染失败: {process.stderr}")
        return json.loads(process.stdout)

    def list_themes(self):
        process = self._run_renderer(["list-themes"], "")
        if process.returncode != 0:
            raise Exception(f"列出主题失败: {process.stderr}")
        return process.stdout.strip()

    def add_theme(self, name: str, path: str):
        process = self._run_renderer(["add-theme", "--name", name, "--path", path], "")
        if process.returncode != 0:
            raise Exception(f"添加主题失败: {process.stderr}")
        return process.stdout.strip()

    def remove_theme(self, name: str):
        process = self._run_renderer(["remove-theme", "--name", name], "")
        if process.returncode != 0:
            raise Exception(f"删除主题失败: {process.stderr}")
        return process.stdout.strip()

    def publish_article(self, md_text=None, *, file=None, theme="default", highlight="solarized-light", mac_style=True, footnote=True, base_dir=None, app_id=None, app_secret=None):
        """
        发布到微信公众号草稿箱（返回 media_id）。

        说明：
        - 推荐在 Markdown 顶部提供 frontmatter 的 title 字段，否则可能会报“未能找到文章标题”。
        - app_id/app_secret 如不传，默认从环境变量 WECHAT_APP_ID/WECHAT_APP_SECRET 读取。
        """
        extra_env = {}
        if app_id:
            extra_env["WECHAT_APP_ID"] = app_id
        if app_secret:
            extra_env["WECHAT_APP_SECRET"] = app_secret

        args = ["publish", "--theme", theme, "--highlight", highlight, "--mac-style", "true" if mac_style else "false", "--footnote", "true" if footnote else "false"]
        if base_dir:
            args += ["--base-dir", base_dir]
        if file:
            args += ["--file", file]

        normalized = self._normalize_markdown(md_text or "")
        process = self._run_renderer(args, normalized, extra_env=extra_env)
        if process.returncode != 0:
            raise Exception(f"发布失败: {process.stderr}")
        return process.stdout.strip()


def shlex_quote(s: str) -> str:
    """
    Minimal POSIX shell escaping for docker sh -lc command.
    """
    if s == "":
        return "''"
    if all(c.isalnum() or c in ("@", "%", "+", "=", ":", ",", ".", "/", "-", "_") for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _get_flag_value(argv, flag: str):
    try:
        i = argv.index(flag)
    except ValueError:
        return None
    if i + 1 >= len(argv):
        return None
    v = argv[i + 1]
    if isinstance(v, str) and not v.startswith("--"):
        return v
    return None


def _set_flag_value(argv, flag: str, value: str):
    try:
        i = argv.index(flag)
    except ValueError:
        return
    if i + 1 >= len(argv):
        argv.append(value)
        return
    argv[i + 1] = value
