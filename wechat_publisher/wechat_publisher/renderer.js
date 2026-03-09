import path from "node:path";
import fs from "node:fs/promises";
import { getGzhContent, listThemes, addTheme, removeTheme, renderAndPublish, getNormalizeFilePath } from "@wenyan-md/core/wrapper";

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith("--")) {
        args[key] = next;
        i++;
      } else {
        args[key] = true;
      }
    } else {
      args._.push(a);
    }
  }
  return args;
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf-8");
}

function normalizeMarkdown(md) {
  if (!md) return "";
  // remove BOM and leading newlines (frontmatter must be at beginning)
  return md.replace(/^\uFEFF?[\r\n]+/, "");
}

async function getInputContent(inputContent, file, baseDir) {
  let absoluteDirPath = undefined;
  if (!inputContent && file) {
    const normalizePath = getNormalizeFilePath(file);
    inputContent = await fs.readFile(normalizePath, "utf-8");
    absoluteDirPath = path.dirname(normalizePath);
  } else if (inputContent && baseDir) {
    absoluteDirPath = baseDir;
  }
  if (!inputContent) {
    throw new Error("missing input-content (no stdin and no file).");
  }
  return { content: inputContent, absoluteDirPath };
}

async function cmdRender(args) {
  const markdown = normalizeMarkdown(await readStdin());
  const themeId = String(args.theme || "default");
  const highlight = String(args.highlight || "solarized-light");
  const macStyle = args["mac-style"] === undefined ? true : args["mac-style"] !== "false";
  const footnote = args.footnote === undefined ? true : args.footnote !== "false";

  const styled = await getGzhContent(markdown, themeId, highlight, macStyle, footnote);
  process.stdout.write(styled.content);
}

async function cmdRenderJson(args) {
  const markdown = normalizeMarkdown(await readStdin());
  const themeId = String(args.theme || "default");
  const highlight = String(args.highlight || "solarized-light");
  const macStyle = args["mac-style"] === undefined ? true : args["mac-style"] !== "false";
  const footnote = args.footnote === undefined ? true : args.footnote !== "false";

  const styled = await getGzhContent(markdown, themeId, highlight, macStyle, footnote);
  process.stdout.write(JSON.stringify(styled));
}

async function cmdPublish(args) {
  const stdinContent = normalizeMarkdown(await readStdin());
  const content = stdinContent && stdinContent.trim().length > 0 ? stdinContent : undefined;
  const file = args.file ? String(args.file) : "";
  const baseDir = args["base-dir"] ? String(args["base-dir"]) : "";

  const themeId = String(args.theme || "default");
  const highlight = String(args.highlight || "solarized-light");
  const macStyle = args["mac-style"] === undefined ? true : args["mac-style"] !== "false";
  const footnote = args.footnote === undefined ? true : args.footnote !== "false";

  const options = {
    file,
    theme: themeId,
    highlight,
    macStyle,
    footnote,
    disableStdin: true,
  };

  const mediaId = await renderAndPublish(content, options, (c, f) => getInputContent(c, f, baseDir));
  process.stdout.write(String(mediaId || ""));
}

async function cmdListThemes() {
  const themes = await listThemes();
  process.stdout.write(JSON.stringify(themes));
}

async function cmdAddTheme(args) {
  const name = String(args.name || "");
  const path = String(args.path || "");
  if (!name || !path) {
    throw new Error("Missing --name or --path.");
  }
  await addTheme(name, path);
  process.stdout.write("OK");
}

async function cmdRemoveTheme(args) {
  const name = String(args.name || "");
  if (!name) {
    throw new Error("Missing --name.");
  }
  await removeTheme(name);
  process.stdout.write("OK");
}

async function main() {
  try {
    const args = parseArgs(process.argv);
    const cmd = args._[0] || "render";

    if (cmd === "render") return await cmdRender(args);
    if (cmd === "render-json") return await cmdRenderJson(args);
    if (cmd === "publish") return await cmdPublish(args);
    if (cmd === "list-themes") return await cmdListThemes();
    if (cmd === "add-theme") return await cmdAddTheme(args);
    if (cmd === "remove-theme") return await cmdRemoveTheme(args);

    throw new Error(`Unknown command: ${cmd}`);
  } catch (e) {
    const msg = formatError(e);
    process.stderr.write(msg);
    process.exit(1);
  }
}

function formatError(e) {
  if (!e) return "Unknown error";
  const message = e?.stack || e?.message || String(e);
  const cause = e?.cause ? `\nCause: ${e.cause?.stack || e.cause?.message || String(e.cause)}` : "";
  return message + cause;
}

main();