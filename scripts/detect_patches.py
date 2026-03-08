#!/usr/bin/env python3
import argparse
import json
import math
import os
from collections import deque, defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _load_image(path):
    img = Image.open(path).convert("RGB")
    return img


def _auto_crop_bbox(img, v_thresh=20):
    """
    Rough auto-crop by finding bounding box of pixels above a value threshold.
    This will likely include UI; use --crop for precise control.
    """
    hsv = img.convert("HSV")
    h, s, v = np.array(hsv).transpose((2, 0, 1))
    mask = v > v_thresh
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _apply_crop(img, crop):
    if crop is None:
        return img, (0, 0)
    x1, y1, x2, y2 = crop
    return img.crop((x1, y1, x2, y2)), (x1, y1)


def _hsv_mask(h, s, v, ranges):
    """
    ranges: list of dicts with keys: h_min, h_max, s_min, s_max, v_min, v_max
    Hue is 0-255. Supports wrap if h_min > h_max.
    """
    mask = np.zeros(h.shape, dtype=bool)
    for r in ranges:
        hmin, hmax = r["h_min"], r["h_max"]
        smin, smax = r["s_min"], r["s_max"]
        vmin, vmax = r["v_min"], r["v_max"]

        if hmin <= hmax:
            h_ok = (h >= hmin) & (h <= hmax)
        else:
            # wraparound
            h_ok = (h >= hmin) | (h <= hmax)
        s_ok = (s >= smin) & (s <= smax)
        v_ok = (v >= vmin) & (v <= vmax)
        mask |= h_ok & s_ok & v_ok
    return mask


def _connected_components(mask):
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components = []

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            q = deque()
            q.append((y, x))
            visited[y, x] = True
            pixels = []
            while q:
                cy, cx = q.popleft()
                pixels.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        q.append((ny, nx))
            components.append(pixels)
    return components


def _centroid(pixels):
    ys = [p[0] for p in pixels]
    xs = [p[1] for p in pixels]
    return (float(np.mean(xs)), float(np.mean(ys)))


def _merge_centroids(centroids, merge_dist):
    if not centroids:
        return []
    n = len(centroids)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        for j in range(i + 1, n):
            dx = centroids[i][0] - centroids[j][0]
            dy = centroids[i][1] - centroids[j][1]
            if dx * dx + dy * dy <= merge_dist * merge_dist:
                union(i, j)

    clusters = defaultdict(list)
    for i, c in enumerate(centroids):
        clusters[find(i)].append(c)

    merged = []
    for group in clusters.values():
        xs = [c[0] for c in group]
        ys = [c[1] for c in group]
        merged.append((float(np.mean(xs)), float(np.mean(ys))))
    return merged


DEFAULT_RANGES = {
    "iron": [
        {"h_min": 105, "h_max": 175, "s_min": 20, "s_max": 180, "v_min": 110, "v_max": 255},
    ],
    "copper": [
        {"h_min": 10, "h_max": 30, "s_min": 80, "s_max": 255, "v_min": 90, "v_max": 255},
    ],
    "coal": [
        {"h_min": 0, "h_max": 255, "s_min": 0, "s_max": 60, "v_min": 0, "v_max": 80},
    ],
    "stone": [
        {"h_min": 0, "h_max": 255, "s_min": 0, "s_max": 60, "v_min": 90, "v_max": 180},
    ],
    "oil": [
        {"h_min": 165, "h_max": 235, "s_min": 60, "s_max": 255, "v_min": 60, "v_max": 220},
    ],
    "uranium": [
        {"h_min": 60, "h_max": 90, "s_min": 80, "s_max": 255, "v_min": 80, "v_max": 255},
    ],
}


def _draw_debug(img, results, offset, with_legend=False):
    draw = ImageDraw.Draw(img)
    ox, oy = offset
    colors = {
        "iron": (120, 200, 255),
        "copper": (255, 140, 0),
        "coal": (50, 50, 50),
        "stone": (170, 170, 170),
        "oil": (180, 80, 200),
        "uranium": (80, 255, 80),
    }
    plus_size = 6
    plus_thickness = 2
    for res, pts in results.items():
        color = colors.get(res, (255, 255, 255))
        for (x, y) in pts:
            cx, cy = int(x), int(y)
            draw.line((cx - plus_size, cy, cx + plus_size, cy), fill=color, width=plus_thickness)
            draw.line((cx, cy - plus_size, cx, cy + plus_size), fill=color, width=plus_thickness)

    if with_legend:
        padding = 8
        entry_gap = 12
        legend_y = img.height - 24
        x = padding
        for res, color in colors.items():
            draw.line((x, legend_y, x + 10, legend_y), fill=color, width=plus_thickness)
            draw.line((x + 5, legend_y - 5, x + 5, legend_y + 5), fill=color, width=plus_thickness)
            draw.text((x + 14, legend_y - 7), res, fill=color)
            x += 14 + len(res) * 7 + entry_gap
    return img


def main():
    parser = argparse.ArgumentParser(description="Detect Factorio resource patches from a map screenshot.")
    parser.add_argument("image", help="Path to screenshot")
    parser.add_argument("--crop", help="Crop box x1,y1,x2,y2 (map area only)")
    parser.add_argument("--auto-crop", action="store_true", help="Auto-crop non-dark region (rough)")
    parser.add_argument("--min-area", type=int, default=50, help="Min component area (pixels)")
    parser.add_argument("--merge-dist", type=float, default=25.0, help="Merge centroids within this pixel distance")
    parser.add_argument("--out", default="patches.json", help="Output JSON path")
    parser.add_argument("--debug-image", default="patches_debug.png", help="Debug image path")
    parser.add_argument("--config", help="JSON file to override HSV ranges")
    parser.add_argument("--center-zero", action="store_true", help="Shift coordinates so crop center is (0,0)")
    parser.add_argument("--overlay", action="store_true", help="Write overlay image with plus markers and legend")
    parser.add_argument("--overlay-image", default="patches_overlay.png", help="Overlay image path")
    parser.add_argument("--edges", action="store_true", help="Write edge-detected image")
    parser.add_argument("--edges-image", default="edges.png", help="Edges image path")
    parser.add_argument("--edges-threshold", type=int, default=80, help="Edge threshold (0-255)")
    args = parser.parse_args()

    img = _load_image(args.image)

    crop = None
    if args.crop:
        parts = [int(p.strip()) for p in args.crop.split(",")]
        if len(parts) != 4:
            raise SystemExit("Crop must be x1,y1,x2,y2")
        crop = tuple(parts)
    elif args.auto_crop:
        auto = _auto_crop_bbox(img)
        if auto:
            crop = auto

    img_cropped, offset = _apply_crop(img, crop)
    center_offset = (0, 0)
    if args.center_zero:
        cx = img_cropped.width / 2.0
        cy = img_cropped.height / 2.0
        center_offset = (cx, cy)
    hsv = img_cropped.convert("HSV")
    h, s, v = np.array(hsv).transpose((2, 0, 1))

    ranges = DEFAULT_RANGES
    if args.config:
        with open(args.config) as f:
            ranges = json.load(f)

    results = {}
    for res, res_ranges in ranges.items():
        mask = _hsv_mask(h, s, v, res_ranges)
        components = _connected_components(mask)
        centroids = []
        for pixels in components:
            if len(pixels) < args.min_area:
                continue
            centroids.append(_centroid(pixels))
        merged = _merge_centroids(centroids, args.merge_dist)
        # adjust back to original image coords and optional center shift
        merged = [
            (x + offset[0] - center_offset[0], y + offset[1] - center_offset[1])
            for (x, y) in merged
        ]
        results[res] = merged

    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    debug = img.copy()
    _draw_debug(debug, results, offset)
    debug.save(args.debug_image)

    if args.overlay:
        overlay = img.copy()
        _draw_debug(overlay, results, offset, with_legend=True)
        overlay.save(args.overlay_image)
    if args.edges:
        gray = np.array(img.convert("L"), dtype=np.float32)
        # Sobel kernels
        kx = np.array([[-1, 0, 1],
                       [-2, 0, 2],
                       [-1, 0, 1]], dtype=np.float32)
        ky = np.array([[1, 2, 1],
                       [0, 0, 0],
                       [-1, -2, -1]], dtype=np.float32)
        gx = np.zeros_like(gray)
        gy = np.zeros_like(gray)
        # Convolution (simple, no padding)
        for y in range(1, gray.shape[0] - 1):
            for x in range(1, gray.shape[1] - 1):
                region = gray[y - 1:y + 2, x - 1:x + 2]
                gx[y, x] = np.sum(region * kx)
                gy[y, x] = np.sum(region * ky)
        mag = np.sqrt(gx * gx + gy * gy)
        mag = np.clip(mag, 0, 255).astype(np.uint8)
        edges = (mag > args.edges_threshold).astype(np.uint8) * 255
        Image.fromarray(edges).save(args.edges_image)

    counts = {k: len(v) for k, v in results.items()}
    print(json.dumps(counts, indent=2))
    print(f"Wrote: {args.out}")
    print(f"Wrote: {args.debug_image}")
    if args.overlay:
        print(f"Wrote: {args.overlay_image}")
    if args.edges:
        print(f"Wrote: {args.edges_image}")


if __name__ == "__main__":
    main()
