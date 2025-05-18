import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from scipy import signal
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
from matplotlib.widgets import RectangleSelector
import platform
import sys

# ---- 中文显示兼容 ----
if sys.platform.startswith("win"):
    zh_font = "Microsoft YaHei"
elif sys.platform.startswith("darwin"):
    zh_font = "PingFang SC"
else:
    zh_font = "Noto Sans CJK SC"
plt.rcParams["font.sans-serif"] = [zh_font]
plt.rcParams["axes.unicode_minus"] = False

CHINASAT_SATELLITES = [
    {
        "name": "中星6A",
        "position": "125.0°E",
        "bands": [
            {"name": "C波段下行", "min": 3700, "max": 4200, "center": 3950, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国、亚太地区",
        "carriers": [
            {"freq": 3920, "bw": 36, "power": -42, "name": "电视转发", "modulation": "DVB-S"},
            {"freq": 4015, "bw": 27, "power": -46, "name": "数据", "modulation": "QPSK"}
        ]
    },
    {
        "name": "中星9号",
        "position": "92.2°E",
        "bands": [
            {"name": "Ku波段下行", "min": 12250, "max": 12750, "center": 12500, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国全境及周边",
        "carriers": [
            {"freq": 12380, "bw": 36, "power": -44, "name": "直播星", "modulation": "QPSK"}
        ]
    },
    {
        "name": "中星10号",
        "position": "110.5°E",
        "bands": [
            {"name": "C波段下行", "min": 3700, "max": 4200, "center": 3950, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国全境、东南亚",
        "carriers": [
            {"freq": 3850, "bw": 36, "power": -45, "name": "电视传输", "modulation": "DVB-S2"},
            {"freq": 3950, "bw": 54, "power": -40, "name": "数据链路", "modulation": "8PSK"},
            {"freq": 4050, "bw": 27, "power": -50, "name": "通信系统", "modulation": "QPSK"}
        ]
    },
    {
        "name": "中星16号",
        "position": "110.5°E",
        "bands": [
            {"name": "Ka波段下行", "min": 19500, "max": 20200, "center": 19850, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国全境、重点覆盖东部",
        "carriers": [
            {"freq": 19800, "bw": 250, "power": -30, "name": "宽带互联网", "modulation": "QAM"}
        ]
    },
    {
        "name": "中星6C",
        "position": "130.0°E",
        "bands": [
            {"name": "C波段下行", "min": 3700, "max": 4200, "center": 3950, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国及周边",
        "carriers": [
            {"freq": 4000, "bw": 36, "power": -43, "name": "电视", "modulation": "DVB-S2"}
        ]
    },
    {
        "name": "中星9B",
        "position": "101.4°E",
        "bands": [
            {"name": "Ku波段下行", "min": 12200, "max": 12700, "center": 12450, "unit": "MHz", "noise_floor": -110}
        ],
        "cover": "中国全境",
        "carriers": [
            {"freq": 12400, "bw": 54, "power": -46, "name": "直播星", "modulation": "QPSK"}
        ]
    }
]

def set_light_style(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background='#f8fafc')
    style.configure('TLabel', background='#f8fafc', foreground='#394867', font=(zh_font, 10))
    style.configure('TButton', background='#bedaf7', foreground='#003366', font=(zh_font, 10, 'bold'), borderwidth=0, focusthickness=2, focuscolor='#bedaf7', padding=6)
    style.map('TButton', background=[('active', '#98c1fe')], foreground=[('active', '#003366')])
    style.configure('TCombobox', fieldbackground='#e3e9f0', background='#e3e9f0', foreground='#003366', selectbackground='#bedaf7', font=(zh_font, 10))
    style.configure('Horizontal.TScale', background='#f8fafc', troughcolor='#e3e9f0', bordercolor='#bedaf7', sliderthickness=18)
    style.configure('TLabelframe', background='#f8fafc', foreground='#5e81ac', font=(zh_font, 11, 'bold'), borderwidth=2)
    style.configure('TLabelframe.Label', background='#f8fafc', foreground='#5e81ac', font=(zh_font, 11, 'bold'))
    style.configure('Status.TLabel', background='#e3e9f0', foreground='#bedaf7', font=(zh_font, 9, 'italic'))
    return style

class SatelliteSpectrumMonitor:
    def __init__(self, root):
        self.root = root
        set_light_style(root)
        self.root.title("中国卫通卫星频谱监测系统")
        self.root.geometry("1520x900")
        self.root.configure(bg="#f8fafc")

        self.current_utc = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.user = "piaosir"

        self.satellites = CHINASAT_SATELLITES
        self.sat_names = [sat["name"] for sat in self.satellites]
        self.selected_sat_idx = 2
        self.selected_sat = self.satellites[self.selected_sat_idx]
        self.selected_band_idx = 0
        self.current_band = self.selected_sat["bands"][self.selected_band_idx]
        self.noise_floor = self.current_band["noise_floor"]
        self.carrier_configs = self.selected_sat["carriers"]
        self.rb = 1000.0     # Hz
        self.vb = 100.0      # Hz

        self.zoom_freq_min = None
        self.zoom_freq_max = None
        self.zoom_active = False

        self.markers = []
        self.rect_selector = None

        self.traces = []  # 记录trace数据
        self.traces_max = 5
        self.peak_search_enabled = False
        self.avg_enabled = False
        self.avg_count = 5
        self.avg_data = []
        self.ylim_scale = 10   # dB/div
        self.ref_level = -30   # dBm, 参考电平

        self.create_color_scheme()
        self.create_widgets()
        self.running = True
        self.update_thread = threading.Thread(target=self.update_simulation)
        self.update_thread.daemon = True
        self.update_thread.start()

    def create_color_scheme(self):
        self.colors = {
            "bg_light": "#f8fafc",
            "bg_panel": "#e3e9f0",
            "panel_highlight": "#bedaf7",
            "fg_primary": "#394867",
            "fg_secondary": "#5e81ac",
            "fg_muted": "#9baec8",
            "accent_blue": "#98c1fe",
            "accent_cyan": "#8ecae6",
            "accent_purple": "#9d8df1",
            "accent_red": "#ef476f",
            "accent_green": "#06d6a0",
            "accent_orange": "#ffd166",
            "grid": "#dbeafe",
            "spectrum": "#1976d2",
            "spectrum_max": "#ef476f",
            "noise_floor": "#06d6a0",
            "marker": "#d2691e",
            "trace": "#f08080"
        }
        n_colors = 256
        colors = []
        for i in range(n_colors):
            r1, g1, b1 = self.hex_to_rgb(self.colors["accent_blue"])
            r2, g2, b2 = self.hex_to_rgb(self.colors["accent_purple"])
            r = r1 + (r2 - r1) * i / (n_colors - 1)
            g = g1 + (g2 - g1) * i / (n_colors - 1)
            b = b1 + (b2 - b1) * i / (n_colors - 1)
            colors.append((r/255, g/255, b/255))
        self.spectrum_cmap = mcolors.LinearSegmentedColormap.from_list("spectrum", colors)

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def create_widgets(self):
        self.root.grid_columnconfigure(0, minsize=295)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.panel = ttk.Frame(self.root, style='TFrame')
        self.panel.grid(row=0, column=0, sticky="ns", padx=(22, 0), pady=18)
        self.panel.grid_propagate(False)
        self.display_frame = ttk.Frame(self.root, style='TFrame')
        self.display_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 18), pady=18)

        self.create_control_panel()
        self.create_display_area()

    def create_control_panel(self):
        title = ttk.Label(self.panel, text="中国卫通卫星频谱仪", font=(zh_font, 16, "bold"),
                          background=self.colors["bg_panel"], foreground=self.colors["accent_blue"])
        title.pack(fill="x", pady=(6, 10))

        user_box = ttk.Frame(self.panel, style='TFrame')
        user_box.pack(fill="x", pady=2)
        ttk.Label(user_box, text=f"用户: {self.user}", font=(zh_font, 10, "bold")).pack(side="left")
        self.time_label = ttk.Label(user_box, text=f"UTC: {self.current_utc}", font=(zh_font, 10))
        self.time_label.pack(side="right")

        sat_box = ttk.LabelFrame(self.panel, text="卫星选择", style='TLabelframe')
        sat_box.pack(fill="x", pady=(18, 2), padx=3)
        self.sat_var = tk.StringVar(value=self.sat_names[self.selected_sat_idx])
        self.sat_combo = ttk.Combobox(sat_box, textvariable=self.sat_var, values=self.sat_names, state="readonly", style='TCombobox')
        self.sat_combo.pack(fill="x", padx=5, pady=6)
        self.sat_combo.bind("<<ComboboxSelected>>", self.on_satellite_select)

        satinfo_box = ttk.LabelFrame(self.panel, text="卫星信息", style='TLabelframe')
        satinfo_box.pack(fill="x", pady=(8,2), padx=3)
        self.satellite_labels = {}
        for key in ["卫星名称", "卫星位置", "主频段", "覆盖区域"]:
            row = ttk.Frame(satinfo_box, style='TFrame')
            row.pack(fill="x", pady=1, padx=3)
            ttk.Label(row, text=f"{key}:", style='TLabel').pack(side="left", anchor="w")
            label = ttk.Label(row, text="", style='TLabel', foreground=self.colors["accent_green"])
            label.pack(side="right", anchor="e")
            self.satellite_labels[key] = label
        self.update_satellite_labels()

        rbvb_box = ttk.LabelFrame(self.panel, text="分辨率/视频带宽", style='TLabelframe')
        rbvb_box.pack(fill="x", pady=(12,2), padx=3)
        rb_frame = ttk.Frame(rbvb_box, style='TFrame')
        rb_frame.pack(fill="x", pady=5, padx=2)
        ttk.Label(rb_frame, text="RB (1Hz-40kHz):", font=(zh_font, 10)).pack(side="left")
        self.rb_var = tk.StringVar(value=f"{int(self.rb)} Hz")
        rb_scale = ttk.Scale(rb_frame, from_=1, to=40000, orient="horizontal", command=self.update_rb, style='Horizontal.TScale')
        rb_scale.set(self.rb)
        rb_scale.pack(fill="x", padx=(6,0), expand=True)
        rb_label = ttk.Label(rb_frame, textvariable=self.rb_var, foreground=self.colors["accent_blue"], width=9, anchor="e")
        rb_label.pack(side="right", padx=(5,3))

        vb_frame = ttk.Frame(rbvb_box, style='TFrame')
        vb_frame.pack(fill="x", pady=5, padx=2)
        ttk.Label(vb_frame, text="VB (1Hz-400Hz):", font=(zh_font, 10)).pack(side="left")
        self.vb_var = tk.StringVar(value=f"{int(self.vb)} Hz")
        vb_scale = ttk.Scale(vb_frame, from_=1, to=400, orient="horizontal", command=self.update_vb, style='Horizontal.TScale')
        vb_scale.set(self.vb)
        vb_scale.pack(fill="x", padx=(6,0), expand=True)
        vb_label = ttk.Label(vb_frame, textvariable=self.vb_var, foreground=self.colors["accent_blue"], width=9, anchor="e")
        vb_label.pack(side="right", padx=(5,3))

        # 现代频谱仪功能
        trace_box = ttk.LabelFrame(self.panel, text="现代频谱仪功能", style='TLabelframe')
        trace_box.pack(fill="x", pady=(14,2), padx=3)
        ttk.Button(trace_box, text="保持当前曲线 (Trace Hold)", command=self.hold_trace).pack(fill="x", padx=4, pady=2)
        ttk.Button(trace_box, text="清除所有曲线", command=self.clear_traces).pack(fill="x", padx=4, pady=2)
        ttk.Checkbutton(trace_box, text="峰值搜索 (Peak Search)", command=self.toggle_peak_search, variable=tk.IntVar()).pack(fill="x", padx=4, pady=2)
        ttk.Checkbutton(trace_box, text="平均 (Average)", command=self.toggle_avg, variable=tk.IntVar()).pack(fill="x", padx=4, pady=2)
        ttk.Button(trace_box, text="清除所有标点", command=self.clear_markers).pack(fill="x", padx=4, pady=2)
        ttk.Button(trace_box, text="导出当前频谱数据", command=self.export_spectrum).pack(fill="x", padx=4, pady=2)
        ttk.Button(trace_box, text="重置最大/最小保持", command=self.reset_zoom).pack(fill="x", padx=4, pady=2)
        ttk.Button(trace_box, text="全部重置", command=self.reset_all).pack(fill="x", padx=4, pady=2)

        # Scale和Ref Level设置
        scale_box = ttk.LabelFrame(self.panel, text="Y轴设置", style='TLabelframe')
        scale_box.pack(fill="x", pady=(14,2), padx=3)
        scale_frame = ttk.Frame(scale_box, style='TFrame')
        scale_frame.pack(fill="x", pady=4, padx=4)
        ttk.Label(scale_frame, text="Scale (dB/div):").pack(side="left")
        self.scale_var = tk.DoubleVar(value=self.ylim_scale)
        scale_entry = ttk.Entry(scale_frame, textvariable=self.scale_var, width=6)
        scale_entry.pack(side="left", padx=(4,8))
        ttk.Button(scale_frame, text="设置", command=self.set_scale).pack(side="left")

        reflevel_frame = ttk.Frame(scale_box, style='TFrame')
        reflevel_frame.pack(fill="x", pady=4, padx=4)
        ttk.Label(reflevel_frame, text="Ref Level (dBm):").pack(side="left")
        self.reflevel_var = tk.DoubleVar(value=self.ref_level)
        reflevel_entry = ttk.Entry(reflevel_frame, textvariable=self.reflevel_var, width=8)
        reflevel_entry.pack(side="left", padx=(4,8))
        ttk.Button(reflevel_frame, text="设置", command=self.set_reflevel).pack(side="left")

        self.status_bar = ttk.Label(self.panel, text="系统就绪，监测中...", style="Status.TLabel", anchor="w")
        self.status_bar.pack(fill="x", pady=(20, 6), padx=3, side="bottom")

    def update_satellite_labels(self):
        sat = self.selected_sat
        band = sat['bands'][self.selected_band_idx]
        self.satellite_data = {
            "卫星名称": sat["name"],
            "卫星位置": sat["position"],
            "主频段": f"{band['name']} ({band['min']}-{band['max']} {band['unit']})",
            "覆盖区域": sat["cover"]
        }
        for key, label in self.satellite_labels.items():
            label.config(text=self.satellite_data.get(key, ""))

    def on_satellite_select(self, event):
        idx = self.sat_names.index(self.sat_var.get())
        self.selected_sat_idx = idx
        self.selected_sat = self.satellites[idx]
        self.selected_band_idx = 0
        self.current_band = self.selected_sat["bands"][self.selected_band_idx]
        self.noise_floor = self.current_band["noise_floor"]
        self.carrier_configs = self.selected_sat["carriers"]
        self.reset_zoom()
        self.status_bar.config(text=f"已切换至 {self.selected_sat['name']}")

    def create_display_area(self):
        self.fig = Figure(figsize=(11, 7), dpi=100, facecolor=self.colors["bg_light"])
        self.ax_spectrum = self.fig.add_subplot(111)
        self.style_axis(self.ax_spectrum)
        self.ax_spectrum.set_title('卫星频谱（现代化模拟）', color=self.colors["accent_blue"], fontsize=14, pad=20, fontproperties=zh_font)
        self.ax_spectrum.set_xlabel('频率 (MHz)', color=self.colors["fg_primary"], fontsize=12, labelpad=14, fontproperties=zh_font)
        self.ax_spectrum.set_ylabel('功率 (dBm)', color=self.colors["fg_primary"], fontsize=12, labelpad=14, fontproperties=zh_font)
        band_info = self.current_band
        freq_min = band_info["min"]
        freq_max = band_info["max"]
        x = np.linspace(freq_min, freq_max, 1000)
        y = np.zeros_like(x)
        self.spectrum_line, = self.ax_spectrum.plot(x, y, color=self.colors["spectrum"], linewidth=2.5, alpha=0.93, label='实时频谱')
        self.max_hold_line, = self.ax_spectrum.plot(x, y, color=self.colors["spectrum_max"], linewidth=1.5, alpha=0.8, linestyle='--', label='最大保持')
        self.min_hold_line, = self.ax_spectrum.plot(x, y, color=self.colors["accent_green"], linewidth=1.5, alpha=0.7, linestyle=':', label='最小保持')
        self.noise_floor_line, = self.ax_spectrum.plot([freq_min, freq_max], [self.noise_floor, self.noise_floor], color=self.colors["noise_floor"], linestyle='-.', linewidth=1.6, alpha=0.95, label='噪声底')
        self.trace_lines = []
        self.peak_marker = None
        self.avg_line = None

        self.set_ylim_by_scale()
        self.ax_spectrum.legend(loc='upper right', facecolor=self.colors["bg_panel"], edgecolor=self.colors["accent_blue"], labelcolor=self.colors["fg_primary"], fontsize=10, prop={'family': zh_font})
        self.rb_vb_text = self.ax_spectrum.text(0.02, 0.02, f"RB: {int(self.rb)} Hz | VB: {int(self.vb)} Hz", color=self.colors["fg_secondary"], fontsize=10, ha='left', va='bottom', transform=self.ax_spectrum.transAxes)
        self.cursor_text = self.ax_spectrum.text(0.98, 0.02, "", color=self.colors["fg_primary"], fontsize=10, ha='right', va='bottom', transform=self.ax_spectrum.transAxes, bbox=dict(boxstyle="round,pad=0.2", facecolor="#e3e9f0", edgecolor="#98c1fe"))
        self.fig.tight_layout(rect=(0, 0, 1, 1))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=0)
        self.canvas.draw()
        self.setup_mouse_interactions()

    def set_ylim_by_scale(self):
        # Y轴范围根据参考电平和刻度自动设置
        ref = self.ref_level
        scale = self.ylim_scale
        ndiv = 8
        self.ax_spectrum.set_ylim(ref - scale * ndiv, ref)

    def style_axis(self, ax):
        ax.set_facecolor(self.colors["bg_light"])
        ax.grid(True, color=self.colors["grid"], linestyle='--', alpha=0.5)
        ax.tick_params(axis='x', colors=self.colors["fg_secondary"], labelsize=11)
        ax.tick_params(axis='y', colors=self.colors["fg_secondary"], labelsize=11)
        for spine in ax.spines.values():
            spine.set_color(self.colors["panel_highlight"])
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.tick_params(which='minor', length=3, color=self.colors["grid"], width=1)

    def setup_mouse_interactions(self):
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)
        self.canvas.mpl_connect('button_press_event', self.on_marker_click)
        if self.rect_selector is not None:
            self.rect_selector.set_active(False)
        self.rect_selector = RectangleSelector(self.ax_spectrum, self.on_rect_select,
                                               useblit=True, button=[1], minspanx=5, spancoords='pixels', interactive=True,
                                               props=dict(facecolor=self.colors["accent_blue"], alpha=0.2, edgecolor=self.colors["accent_blue"], linestyle='-', linewidth=2))

    def on_mouse_move(self, event):
        if event.inaxes == self.ax_spectrum:
            cursor_freq = event.xdata
            cursor_power = event.ydata
            if cursor_freq is not None and cursor_power is not None:
                self.cursor_text.set_text(f"频率: {cursor_freq:.3f} MHz | 电平: {cursor_power:.2f} dBm")
                self.canvas.draw_idle()

    def on_mouse_click(self, event):
        if event.inaxes == self.ax_spectrum and event.button == 1 and event.dblclick:
            self.reset_zoom()

    def on_rect_select(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        if x1 is not None and x2 is not None:
            if x1 > x2:
                x1, x2 = x2, x1
            self.zoom_freq_min = x1
            self.zoom_freq_max = x2
            self.zoom_active = True
            self.ax_spectrum.set_xlim(x1, x2)
            self.status_bar.config(text=f"放大显示区域: {x1:.1f} MHz - {x2:.1f} MHz")
            self.canvas.draw_idle()

    def on_marker_click(self, event):
        if event.inaxes == self.ax_spectrum and event.button == 3:
            freq = event.xdata
            if freq is None:
                return
            for marker in self.markers:
                if abs(marker['freq'] - freq) < 0.5:
                    marker['line'].remove()
                    marker['label'].remove()
                    self.markers.remove(marker)
                    self.canvas.draw_idle()
                    self.status_bar.config(text=f"移除标点: {marker['freq']:.2f} MHz")
                    return
            ylim = self.ax_spectrum.get_ylim()
            line = self.ax_spectrum.axvline(freq, color=self.colors["marker"], linestyle='--', linewidth=2)
            label = self.ax_spectrum.text(freq, ylim[1], f"{freq:.2f} MHz", color=self.colors["marker"],
                                         fontsize=10, ha='center', va='bottom', backgroundcolor="#fff8e1", zorder=10)
            self.markers.append({'freq': freq, 'line': line, 'label': label})
            self.canvas.draw_idle()
            self.status_bar.config(text=f"添加标点: {freq:.2f} MHz")

    def clear_markers(self):
        for marker in self.markers:
            marker['line'].remove()
            marker['label'].remove()
        self.markers.clear()
        self.canvas.draw_idle()
        self.status_bar.config(text="已清除所有标点")

    def hold_trace(self):
        freq, psd = self.generate_spectrum()
        if len(self.traces) >= self.traces_max:
            old_line = self.traces.pop(0)
            old_line.remove()
        line, = self.ax_spectrum.plot(freq, psd, linestyle='-', alpha=0.5, linewidth=1.5, color=self.colors["trace"], label=f'Trace {len(self.traces)+1}')
        self.traces.append(line)
        self.ax_spectrum.legend(loc='upper right', facecolor=self.colors["bg_panel"], edgecolor=self.colors["accent_blue"], labelcolor=self.colors["fg_primary"], fontsize=10, prop={'family': zh_font})
        self.canvas.draw_idle()
        self.status_bar.config(text=f"已保持曲线（Trace Hold）")

    def clear_traces(self):
        for line in self.traces:
            line.remove()
        self.traces.clear()
        self.ax_spectrum.legend(loc='upper right', facecolor=self.colors["bg_panel"], edgecolor=self.colors["accent_blue"], labelcolor=self.colors["fg_primary"], fontsize=10, prop={'family': zh_font})
        self.canvas.draw_idle()
        self.status_bar.config(text="已清除所有曲线")

    def toggle_peak_search(self):
        self.peak_search_enabled = not self.peak_search_enabled
        self.status_bar.config(text=f"{'启用' if self.peak_search_enabled else '关闭'}峰值搜索（Peak Search）")

    def toggle_avg(self):
        self.avg_enabled = not self.avg_enabled
        self.status_bar.config(text=f"{'启用' if self.avg_enabled else '关闭'}平均（Average）")
        if not self.avg_enabled and self.avg_line:
            self.avg_line.remove()
            self.avg_line = None
            self.canvas.draw_idle()

    def update_rb(self, value):
        self.rb = float(value)
        self.rb_var.set(f"{int(self.rb)} Hz")
        self.rb_vb_text.set_text(f"RB: {int(self.rb)} Hz | VB: {int(self.vb)} Hz")

    def update_vb(self, value):
        self.vb = float(value)
        self.vb_var.set(f"{int(self.vb)} Hz")
        self.rb_vb_text.set_text(f"RB: {int(self.rb)} Hz | VB: {int(self.vb)} Hz")

    def reset_zoom(self):
        band_info = self.current_band
        freq_min = band_info["min"]
        freq_max = band_info["max"]
        self.ax_spectrum.set_xlim(freq_min, freq_max)
        self.zoom_active = False
        self.zoom_freq_min = None
        self.zoom_freq_max = None
        n = 1000
        self.max_hold = np.full(n, -1e9)
        self.min_hold = np.full(n, 1e9)
        self.set_ylim_by_scale()
        self.canvas.draw_idle()
        self.status_bar.config(text="最大/最小保持已重置")

    def reset_all(self):
        self.reset_zoom()
        self.clear_markers()
        self.clear_traces()
        self.peak_search_enabled = False
        self.avg_enabled = False
        self.avg_data.clear()
        self.ylim_scale = 10
        self.ref_level = -30
        self.scale_var.set(self.ylim_scale)
        self.reflevel_var.set(self.ref_level)
        self.set_ylim_by_scale()
        self.status_bar.config(text="全部参数已重置")

    def set_scale(self):
        try:
            value = float(self.scale_var.get())
            if value <= 0:
                raise ValueError("Scale必须为正数")
            self.ylim_scale = value
            self.set_ylim_by_scale()
            self.canvas.draw_idle()
            self.status_bar.config(text=f"Y轴刻度设为 {value} dB/div")
        except Exception as e:
            messagebox.showerror("输入错误", f"无效的Scale值: {e}")

    def set_reflevel(self):
        try:
            value = float(self.reflevel_var.get())
            self.ref_level = value
            self.set_ylim_by_scale()
            self.canvas.draw_idle()
            self.status_bar.config(text=f"参考电平设为 {value} dBm")
        except Exception as e:
            messagebox.showerror("输入错误", f"无效的Ref Level: {e}")

    def apply_rb_vb_filtering(self, psd_db):
        rb = np.clip(self.rb, 1, 40000)
        freq_span = self.current_band["max"] - self.current_band["min"]
        n_points = len(psd_db)
        rb_sigma_hz = rb / 2.355
        res_bw_per_point = (freq_span * 1e6) / n_points
        sigma_pts = rb_sigma_hz / res_bw_per_point
        kernel_len = int(sigma_pts * 12)
        if kernel_len < 5:
            kernel_len = 5
        if kernel_len % 2 == 0:
            kernel_len += 1
        x = np.arange(kernel_len) - kernel_len // 2
        kernel = np.exp(-0.5 * (x / sigma_pts) ** 2)
        kernel /= kernel.sum()
        rb_filtered = np.convolve(psd_db, kernel, mode='same')
        vb = np.clip(self.vb, 1, 400)
        dt = 0.01
        tau = 1.0 / (2 * np.pi * vb)
        alpha = dt / (tau + dt)
        vb_filtered = np.zeros_like(rb_filtered)
        vb_filtered[0] = rb_filtered[0]
        for i in range(1, len(rb_filtered)):
            vb_filtered[i] = alpha * rb_filtered[i] + (1 - alpha) * vb_filtered[i-1]
        return vb_filtered

    def modulation_spectrum(self, freq, center_freq, bandwidth, power, modulation):
        bw = bandwidth
        roll_off = 0.35 if "QAM" in modulation or "PSK" in modulation else 0.2
        symbol_bw = bw * (1 + roll_off)
        dist = freq - center_freq
        envelope = np.zeros_like(freq)
        inband = np.abs(dist) <= (bw/2)
        envelope[inband] = 1.0
        rolloff_band = (np.abs(dist) > (bw/2)) & (np.abs(dist) <= (symbol_bw/2))
        envelope[rolloff_band] = 0.5 * (1 + np.cos(np.pi * (np.abs(dist[rolloff_band]) - bw/2) / (symbol_bw/2 - bw/2)))
        envelope += 0.08 * np.exp(-0.5 * ((dist/(symbol_bw/2))**2))
        envelope = envelope.clip(0, 1)
        spectrum = envelope * (power - self.noise_floor) + self.noise_floor
        spectrum += np.random.uniform(-0.8, 0.8, size=spectrum.shape)
        return spectrum

    def generate_spectrum(self):
        band_info = self.current_band
        freq_min = band_info["min"]
        freq_max = band_info["max"]
        freq = np.linspace(freq_min, freq_max, 1000)
        noise_variation = np.random.normal(0, 1, len(freq))
        psd = self.noise_floor + noise_variation
        for carrier in self.carrier_configs:
            carrier_freq = carrier["freq"]
            bandwidth = carrier["bw"]
            power = carrier["power"]
            mod = carrier["modulation"]
            mod_curve = self.modulation_spectrum(freq, carrier_freq, bandwidth, power, mod)
            psd = np.maximum(psd, mod_curve)
        psd = self.apply_rb_vb_filtering(psd)
        return freq, psd

    def update_simulation(self):
        while self.running:
            try:
                freq, psd = self.generate_spectrum()
                if not hasattr(self, 'max_hold') or len(self.max_hold) != len(psd):
                    self.max_hold = psd.copy()
                else:
                    self.max_hold = np.maximum(self.max_hold, psd)
                if not hasattr(self, 'min_hold') or len(self.min_hold) != len(psd):
                    self.min_hold = psd.copy()
                else:
                    self.min_hold = np.minimum(self.min_hold, psd)

                # Average
                if self.avg_enabled:
                    self.avg_data.append(psd)
                    if len(self.avg_data) > self.avg_count:
                        self.avg_data.pop(0)
                    avg_curve = np.mean(self.avg_data, axis=0)
                else:
                    self.avg_data.clear()
                    avg_curve = None

                # Peak Search
                peak_freq = peak_val = None
                if self.peak_search_enabled:
                    idx = np.argmax(psd)
                    peak_freq = freq[idx]
                    peak_val = psd[idx]

                self.root.after(0, self.update_plots, freq, psd, avg_curve, peak_freq, peak_val)
                self.current_utc = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                self.time_label.config(text=f"UTC: {self.current_utc}")
                time.sleep(0.1)
            except Exception as e:
                print(f"更新错误: {e}")
                time.sleep(1.0)

    def update_plots(self, freq, psd, avg_curve, peak_freq, peak_val):
        self.spectrum_line.set_data(freq, psd)
        self.max_hold_line.set_data(freq, self.max_hold)
        self.min_hold_line.set_data(freq, self.min_hold)
        self.noise_floor_line.set_data([self.current_band["min"], self.current_band["max"]], [self.noise_floor, self.noise_floor])
        self.set_ylim_by_scale()

        # Draw traces
        for marker in self.markers:
            marker['line'].set_ydata([self.ax_spectrum.get_ylim()[0], self.ax_spectrum.get_ylim()[1]])
            marker['label'].set_y(self.ax_spectrum.get_ylim()[1])
        # Peak marker
        if hasattr(self, 'peak_marker') and self.peak_marker:
            self.peak_marker.remove()
            self.peak_marker = None
        if self.peak_search_enabled and peak_freq is not None and peak_val is not None:
            self.peak_marker = self.ax_spectrum.plot(peak_freq, peak_val, marker="o", color=self.colors["accent_red"],
                                                     markersize=12, markeredgecolor="white", zorder=20)[0]
            self.ax_spectrum.text(peak_freq, peak_val, f"峰值: {peak_freq:.2f} MHz\n{peak_val:.1f} dBm",
                                  color=self.colors["accent_red"], fontsize=10, ha='left', va='bottom', backgroundcolor="#fff8e1", zorder=21)
        # Average
        if hasattr(self, 'avg_line') and self.avg_line:
            self.avg_line.remove()
            self.avg_line = None
        if self.avg_enabled and avg_curve is not None:
            self.avg_line, = self.ax_spectrum.plot(freq, avg_curve, color=self.colors["accent_orange"], linestyle='-', linewidth=2, alpha=0.8, label='Average')
        self.ax_spectrum.legend(loc='upper right', facecolor=self.colors["bg_panel"], edgecolor=self.colors["accent_blue"], labelcolor=self.colors["fg_primary"], fontsize=10, prop={'family': zh_font})
        self.canvas.draw_idle()

    def export_spectrum(self):
        freq, psd = self.generate_spectrum()
        try:
            import pandas as pd
            file = f"spectrum_export_{self.selected_sat['name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame({'Frequency_MHz': freq, 'PSD_dBm': psd}).to_csv(file, index=False)
            messagebox.showinfo("导出成功", f"频谱数据已导出至: {file}")
            self.status_bar.config(text=f"频谱数据已导出: {file}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出失败: {e}")

    def on_closing(self):
        self.running = False
        time.sleep(0.2)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SatelliteSpectrumMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
