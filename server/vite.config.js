import { defineConfig } from "vite";
import fs from "fs";
import path from "path";

function getNewestImageFile() {
  const imagePattern = /\.(png|jpe?g|webp)$/i;
  const ignoredNames = new Set(["patches_overlay.png", "patches_debug.png"]);
  const candidateDirs = [
    path.join(process.env.HOME || "", "Pictures", "Screenshots"),
    path.join(__dirname, ".."),
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

export default defineConfig({
  root: __dirname,
  server: {
    port: 5173,
    configureServer(server) {
      server.middlewares.use("/api/default-image", (req, res) => {
        const defaultImagePath = getNewestImageFile();
        if (!defaultImagePath) {
          res.statusCode = 404;
          res.end("No default image found");
          return;
        }
        const ext = path.extname(defaultImagePath).toLowerCase();
        res.setHeader(
          "Content-Type",
          ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : ext === ".webp" ? "image/webp" : "image/png"
        );
        fs.createReadStream(defaultImagePath).pipe(res);
      });

      server.middlewares.use("/api/patches-overlay", (req, res) => {
        const overlayPath = path.join(__dirname, "..", "patches_overlay.png");
        fs.readFile(overlayPath, (err, data) => {
          if (err) {
            res.statusCode = 404;
            res.end("patches_overlay.png not found");
            return;
          }
          res.statusCode = 200;
          res.setHeader("Content-Type", "image/png");
          res.end(data);
        });
      });

      server.middlewares.use("/api/update-resource-ranges", (req, res) => {
        if (req.method !== "POST") {
          res.statusCode = 405;
          res.end("Method not allowed");
          return;
        }
        let body = "";
        req.on("data", (chunk) => {
          body += chunk;
          if (body.length > 5 * 1024 * 1024) {
            res.statusCode = 413;
            res.end("Payload too large");
            req.destroy();
          }
        });
        req.on("end", () => {
          try {
            const parsed = JSON.parse(body || "{}");
            if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
              res.statusCode = 400;
              res.end("Body must be a JSON object");
              return;
            }
            const outPath = path.join(__dirname, "resources_separated_by_color_ranges.json");
            fs.writeFile(outPath, `${JSON.stringify(parsed, null, 2)}\n`, "utf8", (err) => {
              if (err) {
                res.statusCode = 500;
                res.end(`Failed to write file: ${err.message}`);
                return;
              }
              res.statusCode = 200;
              res.setHeader("Content-Type", "application/json; charset=utf-8");
              res.end(JSON.stringify({ ok: true, path: outPath }));
            });
          } catch (err) {
            res.statusCode = 400;
            res.end(`Invalid JSON: ${err.message}`);
          }
        });
      });

      server.middlewares.use("/api/latest-screenshot", (req, res) => {
        const dir = path.join(process.env.HOME || "", "Pictures", "Screenshots");
        let files = [];
        try {
          files = fs
            .readdirSync(dir)
            .filter((f) => f.toLowerCase().endsWith(".png"))
            .map((f) => ({
              name: f,
              time: fs.statSync(path.join(dir, f)).mtimeMs,
            }))
            .sort((a, b) => b.time - a.time);
        } catch (err) {
          res.statusCode = 500;
          res.end("Failed to read screenshots directory");
          return;
        }
        if (files.length === 0) {
          res.statusCode = 404;
          res.end("No screenshots found");
          return;
        }
        const latest = path.join(dir, files[0].name);
        res.setHeader("Cache-Control", "no-store, max-age=0");
        res.setHeader("Content-Type", "image/png");
        fs.createReadStream(latest).pipe(res);
      });
    },
  },
});
