import { defineConfig } from "vite";
import fs from "fs";
import path from "path";

export default defineConfig({
  root: __dirname,
  server: {
    port: 5173,
    configureServer(server) {
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
