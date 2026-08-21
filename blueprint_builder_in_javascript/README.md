# Blueprint Builder in JavaScript

Vite/npm browser port of the blueprint builder. It currently implements the
standalone solar generator and the shared `Station` graph model without calling
the Python application.

```sh
npm install
npm run dev
npm test
npm run build
```

The browser uses the native `CompressionStream` API for Factorio-compatible
zlib compression and copies generated blueprint strings to the clipboard.
Production-station template transformation is the next parity layer.
