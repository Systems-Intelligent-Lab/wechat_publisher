import json
import os
import unittest


def _has_docker() -> bool:
    # WechatPublisher can run either with local node or docker fallback.
    # Most CI/dev boxes without node will need docker for these tests.
    from shutil import which

    return which("docker") is not None or which("node") is not None


@unittest.skipUnless(_has_docker(), "Requires either `node` or `docker` to render.")
class TestWechatPublisherRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from wechat_publisher.engine import WechatPublisher

        cls.bot = WechatPublisher()

    def test_render_html_basic(self):
        md = """---
title: 渲染测试
author: hzq
---

# 标题

> 这是一个测试。

```python
print("hello")
```
"""
        html = self.bot.render_html(md, theme="orangeheart")
        self.assertIn('id="wenyan"', html)
        self.assertIn("标题", html)
        self.assertIn("hljs", html)

    def test_render_html_multiple_themes(self):
        md = """---
title: 多主题测试
---

# Hello
正文
"""
        for theme in ["default", "orangeheart", "lapis", "phycat"]:
            with self.subTest(theme=theme):
                html = self.bot.render_html(md, theme=theme)
                self.assertTrue(html.strip())
                self.assertIn('data-provider="WenYan"', html)

    def test_render_styled_frontmatter_metadata(self):
        md = """---
title: 元信息测试
author: 单元测试
source_url: https://example.com/post
---

内容
"""
        styled = self.bot.render_styled(md, theme="default")
        self.assertEqual(styled.get("title"), "元信息测试")
        self.assertEqual(styled.get("author"), "单元测试")
        self.assertEqual(styled.get("source_url"), "https://example.com/post")
        self.assertIn("content", styled)
        self.assertIn("内容", styled.get("content", ""))

    def test_frontmatter_with_leading_newlines_is_handled(self):
        md = """

---
title: 前置空行测试
---

hello
"""
        styled = self.bot.render_styled(md, theme="default")
        self.assertEqual(styled.get("title"), "前置空行测试")

    def test_unicode_encoding_roundtrip(self):
        md = """---
title: 编码测试
---

中文 / 日本語 / Español / naïve / 𝛑

`inline code` and <tag> should remain readable.
"""
        html = self.bot.render_html(md, theme="default")
        self.assertIn("中文", html)
        self.assertIn("日本語", html)
        self.assertIn("Español", html)

    def test_list_themes_contains_orangeheart(self):
        raw = self.bot.list_themes()
        themes = json.loads(raw)
        ids = {t.get("id") for t in themes if isinstance(t, dict)}
        self.assertIn("orangeheart", ids)


if __name__ == "__main__":
    unittest.main()
