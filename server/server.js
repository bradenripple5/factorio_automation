const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3000;
const ROOT = __dirname;
const RESOURCE_RANGES_PATH = path.join(ROOT, "resources_separated_by_color_ranges.json");
const PATCHES_OVERLAY_PATH = path.join(ROOT, "..", "patches_overlay.png");
const PROJECT_ROOT = path.join(ROOT, "..");

function getNewestImageFile() {
  const imagePattern = /\.(png|jpe?g|webp)$/i;
  const ignoredNames = new Set(["patches_overlay.png", "patches_debug.png"]);
  const candidateDirs = [
    path.join(process.env.HOME || "", "Pictures", "Screenshots"),
    PROJECT_ROOT,
  ];
  const candidates = [];

  for (const dir of candidateDirs) {
    if (!dir) {
      continue;
    }
    let names = [];
    try {
      names = fs.readdirSync(dir);
    } catch (_err) {
      continue;
    }
    for (const name of names) {
      if (ignoredNames.has(name) || !imagePattern.test(name)) {
        continue;
      }
      const filePath = path.join(dir, name);
      let stat;
      try {
        stat = fs.statSync(filePath);
      } catch (_err) {
        continue;
      }
      if (!stat.isFile()) {
        continue;
      }
      candidates.push({ filePath, mtimeMs: stat.mtimeMs });
    }
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates.length > 0 ? candidates[0].filePath : null;
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url && req.url.startsWith("/api/default-image")) {
    const defaultImagePath = getNewestImageFile();
    if (!defaultImagePath) {
      res.statusCode = 404;
      res.setHeader("Content-Type", "text/plain; charset=utf-8");
      res.end("No default image found");
      return;
    }
    const ext = path.extname(defaultImagePath).toLowerCase();
    res.statusCode = 200;
    res.setHeader(
      "Content-Type",
      ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : ext === ".webp" ? "image/webp" : "image/png"
    );
    fs.createReadStream(defaultImagePath).pipe(res);
    return;
  }

  if (req.method === "GET" && req.url && req.url.startsWith("/api/patches-overlay")) {
    fs.readFile(PATCHES_OVERLAY_PATH, (err, data) => {
      if (err) {
        res.statusCode = 404;
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.end("patches_overlay.png not found");
        return;
      }
      res.statusCode = 200;
      res.setHeader("Content-Type", "image/png");
      res.end(data);
    });
    return;
  }

  if (req.method === "POST" && req.url === "/api/update-resource-ranges") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 5 * 1024 * 1024) {
        res.statusCode = 413;
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.end("Payload too large");
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        const parsed = JSON.parse(body || "{}");
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          res.statusCode = 400;
          res.setHeader("Content-Type", "text/plain; charset=utf-8");
          res.end("Body must be a JSON object");
          return;
        }
        const serialized = `${JSON.stringify(parsed, null, 2)}\n`;
        fs.writeFile(RESOURCE_RANGES_PATH, serialized, "utf8", (err) => {
          if (err) {
            res.statusCode = 500;
            res.setHeader("Content-Type", "text/plain; charset=utf-8");
            res.end(`Failed to write file: ${err.message}`);
            return;
          }
          res.statusCode = 200;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ ok: true, path: RESOURCE_RANGES_PATH }));
        });
      } catch (err) {
        res.statusCode = 400;
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.end(`Invalid JSON: ${err.message}`);
      }
    });
    return;
  }

  const urlPath = req.url === "/" ? "/index.html" : req.url;
  const filePath = path.join(ROOT, urlPath);

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.statusCode = 404;
      res.setHeader("Content-Type", "text/plain; charset=utf-8");
      res.end("Not found");
      return;
    }

    if (filePath.endsWith(".html")) {
      res.setHeader("Content-Type", "text/html; charset=utf-8");
    } else if (filePath.endsWith(".js")) {
      res.setHeader("Content-Type", "text/javascript; charset=utf-8");
    } else if (filePath.endsWith(".css")) {
      res.setHeader("Content-Type", "text/css; charset=utf-8");
    } else if (filePath.endsWith(".json")) {
      res.setHeader("Content-Type", "application/json; charset=utf-8");
    } else if (filePath.endsWith(".png")) {
      res.setHeader("Content-Type", "image/png");
    }

    res.statusCode = 200;
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
