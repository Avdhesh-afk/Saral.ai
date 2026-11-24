import io
import json
import os
from flask import Flask, jsonify, render_template, request, send_file
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

app = Flask(__name__)

ASPECT_DIMENSIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "4:5": (1080, 1350),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
}

BG_COLORS = {
    "Black": (14, 15, 18, 255),
    "Light Grey": (214, 217, 222, 255),
    "White": (248, 249, 250, 255),
    "Blue": (24, 58, 128, 255),
    "Green": (22, 110, 62, 255),
    "Transparent": (14, 15, 18, 255),
}


def apply_tiles(img: Image.Image, cols: int = 2, rows: int = 2, mirror: bool = True) -> Image.Image:
    cols = max(1, min(8, int(cols)))
    rows = max(1, min(8, int(rows)))
    w, h = img.size
    tile_w = max(1, w // cols)
    tile_h = max(1, h // rows)
    base_tile = img.resize((tile_w, tile_h), Image.Resampling.BILINEAR)

    out = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    for r in range(rows):
        for c in range(cols):
            piece = base_tile.copy()
            if mirror:
                if c % 2 == 1:
                    piece = piece.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if r % 2 == 1:
                    piece = piece.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            out.paste(piece, (c * tile_w, r * tile_h))
    return out


def render_project_frame(state: dict) -> Image.Image:
    ratio = state.get("ratio", "9:16")
    base_w, base_h = ASPECT_DIMENSIONS.get(ratio, (1080, 1920))

    scale_map = {
        "Full (100%)": 1.0,
        "Half (50%)": 0.5,
        "Third (33%)": 0.3333,
        "Quarter (25%)": 0.25,
    }
    q_factor = scale_map.get(state.get("preview_quality", "Half (50%)"), 0.5)
    w = max(160, int(base_w * q_factor))
    h = max(160, int(base_h * q_factor))

    bg_rgba = BG_COLORS.get(state.get("background", "Black"), (14, 15, 18, 255))
    canvas = Image.new("RGBA", (w, h), bg_rgba)
    draw = ImageDraw.Draw(canvas)

    layer = state.get("layer", {})
    layer_type = layer.get("type", "shape")
    shape_kind = layer.get("shape", "rect")
    fill_hex = layer.get("color", "#D4AF37")
    opacity = max(0.0, min(1.0, float(layer.get("opacity", 1.0))))
    pos_x_norm = float(layer.get("pos_x", 0.0))  # -1.0 to 1.0
    pos_y_norm = float(layer.get("pos_y", 0.0))  # -1.0 to 1.0
    layer_scale = max(0.1, min(3.0, float(layer.get("scale", 1.0))))
    rotation = float(layer.get("rotation", 0.0))
    border_width = max(0, int(layer.get("border_width", 0) * q_factor))

    # Convert hex color + opacity
    hex_clean = fill_hex.lstrip("#")
    if len(hex_clean) == 6:
        r, g, b = tuple(int(hex_clean[i : i + 2], 16) for i in (0, 2, 4))
    else:
        r, g, b = 212, 175, 55
    alpha = int(255 * opacity)

    box_w = max(24, int(min(w, h) * 0.42 * layer_scale))
    box_h = max(24, int(min(w, h) * 0.42 * layer_scale))
    sprite = Image.new("RGBA", (box_w + border_width * 2 + 8, box_h + border_width * 2 + 8), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(sprite)

    ox = border_width + 4
    oy = border_width + 4
    outline_rgba = (255, 232, 140, alpha) if border_width > 0 else None

    if layer_type == "text":
        text_str = layer.get("text", "NEXUS MOTION")
        font = ImageFont.load_default()
        s_draw.text((ox + 6, oy + box_h // 2), text_str, fill=(r, g, b, alpha), font=font)
    elif shape_kind == "circle":
        s_draw.ellipse([ox, oy, ox + box_w, oy + box_h], fill=(r, g, b, alpha), outline=outline_rgba, width=border_width)
    else:
        s_draw.rectangle([ox, oy, ox + box_w, oy + box_h], fill=(r, g, b, alpha), outline=outline_rgba, width=border_width)

    if abs(rotation) > 0.01:
        sprite = sprite.rotate(-rotation, resample=Image.Resampling.BILINEAR, expand=True)

    cx = int(w * 0.5 + pos_x_norm * (w * 0.35))
    cy = int(h * 0.5 + pos_y_norm * (h * 0.35))
    canvas.alpha_composite(sprite, (cx - sprite.width // 2, cy - sprite.height // 2))

    # Active effect pipeline
    effect = state.get("effect", "none")
    if effect == "tiles":
        canvas = apply_tiles(canvas, cols=2, rows=2, mirror=True)
    elif effect == "gaussian_blur":
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=max(1, int(6 * q_factor))))
    elif effect == "sharpen":
        canvas = canvas.filter(ImageFilter.SHARPEN)

    return canvas.convert("RGB")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/render_frame", methods=["POST"])
def api_render_frame():
    data = request.get_json(force=True) or {}
    img = render_project_frame(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/export_project", methods=["POST"])
def api_export_project():
    data = request.get_json(force=True) or {}
    payload = json.dumps(data, indent=2)
    return app.response_class(
        response=payload,
        status=200,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=nexus_project.json"},
    )


@app.route("/api/export_mp4", methods=["POST"])
def api_export_mp4():
    try:
        from moviepy import ImageSequenceClip
    except ImportError:
        return jsonify({"error": "Install moviepy to export MP4: pip install moviepy imageio imageio-ffmpeg"}), 400

    data = request.get_json(force=True) or {}
    fps = max(12, min(60, int(data.get("fps", 24))))
    duration = max(0.5, min(5.0, float(data.get("duration", 2.0))))
    total_frames = int(fps * duration)

    base_layer = data.get("layer", {})
    start_x = float(base_layer.get("pos_x", 0.0))
    frames = []

    for i in range(total_frames):
        t_norm = i / max(1, total_frames - 1)
        frame_state = json.loads(json.dumps(data))
        frame_state["preview_quality"] = "Half (50%)"
        frame_state["layer"]["pos_x"] = start_x + 0.15 * np.sin(2 * np.pi * t_norm)
        img = render_project_frame(frame_state)
        frames.append(np.array(img))

    out_path = os.path.join(os.getcwd(), "nexus_export.mp4")
    clip = ImageSequenceClip(frames, fps=fps)
    clip.write_videofile(out_path, codec="libx264", audio=False, fps=fps, logger=None)
    clip.close()

    return send_file(out_path, mimetype="video/mp4", as_attachment=True, download_name="nexus_export.mp4")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)