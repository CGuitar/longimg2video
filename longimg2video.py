#!/usr/bin/env python3
"""
长图 → 慢速轮播视频（恒定滚动速度，无缝循环）
- 双击图标：打开参数配置窗口，保存设置。
- 拖放图片到图标：使用已保存的参数直接转换。
"""

import sys
import os
import json
import subprocess
import re
from PIL import Image

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# ---------- 预设分辨率 ----------
RESOLUTION_PRESETS = {
    "1280x720":  (1280, 720),
    "1920x1080": (1920, 1080),
    "1024x1024": (1024, 1024),
    "1080x1920": (1080, 1920),
    "1440x1080": (1440, 1080),
}

# ---------- 配置文件路径 ----------
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(get_app_dir(), "config.json")

# ---------- 默认配置 ----------
DEFAULT_CONFIG = {
    "resolution": "1280x720",
    "speed": 75,
    "crf": 36,
    "fps": 30
}

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ---------- 解析分辨率字符串为 (宽, 高) ----------
def parse_resolution(res_str):
    """支持预设键值或 '宽x高' 字符串"""
    if res_str in RESOLUTION_PRESETS:
        return RESOLUTION_PRESETS[res_str]
    # 尝试匹配 WxH 格式
    match = re.fullmatch(r"(\d+)x(\d+)", res_str)
    if match:
        w, h = int(match.group(1)), int(match.group(2))
        if w > 0 and h > 0:
            return w, h
    raise ValueError(f"无效的分辨率格式: {res_str}")

# ---------- 核心处理（无方向、纯向下滚动） ----------
def process_image(input_path, output_path, width, height, fps, speed,
                  duration, preset, crf, ffmpeg_exe):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"文件不存在: {input_path}")

    img = Image.open(input_path).convert("RGB")
    # 等比缩放
    w, h = img.size
    scale = width / w
    new_w, new_h = width, int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    if new_h < height:
        raise ValueError(f"图片高度不足（需≥{height}px），请确认输入为长图。")

    # 双图拼接实现无缝循环
    combined = Image.new("RGB", (new_w, new_h * 2))
    combined.paste(img, (0, 0))
    combined.paste(img, (0, new_h))
    total_h = new_h * 2
    move_distance = new_h

    if duration is not None:
        duration_sec = duration
    else:
        duration_sec = new_h / speed

    total_frames = int(duration_sec * fps)
    if total_frames < 1:
        raise ValueError("视频时长过短，请降低速度或检查图片。")

    ffmpeg_cmd = [
        ffmpeg_exe, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{width}x{height}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", preset, "-crf", str(crf),
        output_path
    ]

    try:
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
    except FileNotFoundError:
        raise RuntimeError("未找到 FFmpeg，请将 ffmpeg.exe 与本程序放在同一文件夹。")

    try:
        for i in range(total_frames):
            y = int(i * move_distance / total_frames)
            if y + height > total_h:
                y = total_h - height
            crop = combined.crop((0, y, new_w, y + height))
            proc.stdin.write(crop.tobytes())
    except BrokenPipeError:
        raise RuntimeError("FFmpeg 管道意外关闭，请检查磁盘空间或编码参数。")
    finally:
        proc.stdin.close()
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError("FFmpeg 处理过程中出现错误。")

    return duration_sec, new_h

# ---------- 配置窗口（含自定义分辨率） ----------
class SettingsWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("长图转视频 — 参数设置")
        self.window.resizable(False, False)

        # 加载已有配置
        self.config = load_config()
        for key, val in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = val

        # ----- 分辨率 -----
        tk.Label(self.window, text="分辨率:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        res_str = self.config["resolution"]
        aspect_map = {
            "1280x720": "16:9",
            "1920x1080": "16:9",
            "1024x1024": "1:1",
            "1080x1920": "9:16",
            "1440x1080": "4:3"
        }
        # 判断当前分辨率是否为预设
        if res_str in RESOLUTION_PRESETS:
            display_res = f"{res_str} ({aspect_map.get(res_str, '')})"
        else:
            display_res = "自定义"
        self.res_var = tk.StringVar(value=display_res)
        res_choices = [f"{r} ({aspect_map[r]})" for r in RESOLUTION_PRESETS] + ["自定义"]
        self.res_combo = ttk.Combobox(self.window, textvariable=self.res_var,
                                      values=res_choices, state="readonly", width=25)
        self.res_combo.grid(row=0, column=1, sticky="w", padx=5)
        self.res_combo.bind("<<ComboboxSelected>>", self.on_resolution_change)

        # 自定义宽高输入框（初始可能显示）
        self.custom_width_label = tk.Label(self.window, text="宽:")
        self.custom_width_entry = tk.Entry(self.window, width=8)
        self.custom_height_label = tk.Label(self.window, text="高:")
        self.custom_height_entry = tk.Entry(self.window, width=8)

        # 根据当前设置决定是否显示自定义输入框
        if display_res == "自定义":
            self.show_custom_fields()
            # 从配置的 resolution 字符串中解析宽高
            try:
                w, h = parse_resolution(res_str)
                self.custom_width_entry.delete(0, tk.END)
                self.custom_width_entry.insert(0, str(w))
                self.custom_height_entry.delete(0, tk.END)
                self.custom_height_entry.insert(0, str(h))
            except:
                self.custom_width_entry.insert(0, "1920")
                self.custom_height_entry.insert(0, "1080")
        else:
            self.hide_custom_fields()

        # ----- 滚动速度 -----
        tk.Label(self.window, text="滚动速度:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        speed_map = {65:"极快 (75)", 50:"快 (60)", 35:"慢 (40)", 20:"极慢 (25)"}
        speed_disp = speed_map.get(self.config["speed"], "极快 (75)")
        self.speed_var = tk.StringVar(value=speed_disp)
        ttk.Combobox(self.window, textvariable=self.speed_var, values=list(speed_map.values()),
                     state="readonly", width=25).grid(row=1, column=1, sticky="w", padx=5)

        # ----- 画质 CRF -----
        tk.Label(self.window, text="画质 (CRF):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        crf_map = {24:"高 (24)", 30:"中 (30)", 34:"低 (36)"}
        crf_disp = crf_map.get(self.config["crf"], "低 (36)")
        self.crf_var = tk.StringVar(value=crf_disp)
        ttk.Combobox(self.window, textvariable=self.crf_var, values=list(crf_map.values()),
                     state="readonly", width=25).grid(row=2, column=1, sticky="w", padx=5)

        # ----- 帧率 -----
        tk.Label(self.window, text="帧率 (FPS):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.fps_var = tk.StringVar(value=str(self.config["fps"]))
        ttk.Combobox(self.window, textvariable=self.fps_var, values=["30","60","90"],
                     state="readonly", width=25).grid(row=3, column=1, sticky="w", padx=5)

        # ----- 保存按钮 -----
        self.save_btn = tk.Button(self.window, text="保存设置", command=self.save_settings,
                                  bg="#2196F3", fg="white", font=("Arial", 11))
        self.save_btn.grid(row=4, column=0, columnspan=2, pady=15)

        # 状态标签
        # self.status_var = tk.StringVar()
        # tk.Label(self.window, textvariable=self.status_var, relief="sunken",
        #          anchor="w").grid(row=5, column=0, columnspan=2, sticky="we", padx=5, pady=5)
        self.window.mainloop()

    def show_custom_fields(self):
        self.custom_width_label.grid(row=0, column=2, sticky="w", padx=(0,2))
        self.custom_width_entry.grid(row=0, column=3, sticky="w", padx=(0,5))
        self.custom_height_label.grid(row=0, column=4, sticky="w", padx=(0,2))
        self.custom_height_entry.grid(row=0, column=5, sticky="w")

    def hide_custom_fields(self):
        self.custom_width_label.grid_forget()
        self.custom_width_entry.grid_forget()
        self.custom_height_label.grid_forget()
        self.custom_height_entry.grid_forget()

    def on_resolution_change(self, event=None):
        if self.res_var.get() == "自定义":
            self.show_custom_fields()
            # 若输入框为空，填入默认值
            if not self.custom_width_entry.get():
                self.custom_width_entry.insert(0, "1280")
            if not self.custom_height_entry.get():
                self.custom_height_entry.insert(0, "720")
        else:
            self.hide_custom_fields()

    def save_settings(self):
        # 分辨率处理
        sel = self.res_var.get()
        if sel == "自定义":
            w_str = self.custom_width_entry.get().strip()
            h_str = self.custom_height_entry.get().strip()
            try:
                w = int(w_str)
                h = int(h_str)
                if w <= 0 or h <= 0:
                    raise ValueError
            except:
                messagebox.showerror("错误", "自定义分辨率必须为正整数。")
                return
            self.config["resolution"] = f"{w}x{h}"
        else:
            # 预设格式 "1280x720 (16:9)"
            res_key = sel.split()[0]
            if res_key not in RESOLUTION_PRESETS:
                messagebox.showerror("错误", "未知分辨率预设。")
                return
            self.config["resolution"] = res_key

        # 速度
        speed_str = self.speed_var.get()
        speed_val = int(speed_str.split('(')[1].rstrip(')'))
        self.config["speed"] = speed_val

        # CRF
        crf_str = self.crf_var.get()
        crf_val = int(crf_str.split('(')[1].rstrip(')'))
        self.config["crf"] = crf_val

        # FPS
        self.config["fps"] = int(self.fps_var.get())

        save_config(self.config)
        # self.status_var.set("设置已保存，可关闭窗口")
        messagebox.showinfo("提示", "参数已保存。\n下次拖放图片时将使用这些设置。")

# ---------- 主入口 ----------
def main():
    if len(sys.argv) > 1:
        # 拖放模式：直接转换
        input_path = sys.argv[1]
        if not os.path.isfile(input_path):
            sys.exit(f"错误：文件不存在 - {input_path}")

        config = load_config()
        for key, val in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = val

        try:
            width, height = parse_resolution(config["resolution"])
        except Exception as e:
            sys.exit(f"分辨率解析错误：{e}")

        fps = config["fps"]
        speed = config["speed"]
        crf = config["crf"]

        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(os.path.dirname(input_path), f"{base}_video.mp4")

        app_dir = get_app_dir()
        if getattr(sys, 'frozen', False):
            ffmpeg_exe = os.path.join(app_dir, "ffmpeg.exe")
            if not os.path.isfile(ffmpeg_exe):
                ffmpeg_exe = "ffmpeg"
        else:
            ffmpeg_exe = "ffmpeg"

        try:
            dur, new_h = process_image(input_path, output_path, width, height,
                                       fps, speed, None, "medium", crf, ffmpeg_exe)
            print(f"视频已生成: {output_path}")
            print(f"分辨率: {width}x{height} | 图片高度: {new_h}px | 速度: {speed} px/s | 时长: {dur:.1f} 秒")
        except Exception as e:
            sys.exit(f"错误：{e}")
    else:
        if not GUI_AVAILABLE:
            sys.exit("未检测到 tkinter，无法启动 GUI。请使用拖放方式运行。")
        SettingsWindow()

if __name__ == "__main__":
    main()
