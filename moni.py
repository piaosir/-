import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.gridspec as gridspec
from scipy import signal
import datetime
import tkinter as tk
from tkinter import ttk, PhotoImage
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import threading
import time
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm
from matplotlib.widgets import RectangleSelector
import matplotlib.colors as mcolors
from matplotlib.ticker import AutoMinorLocator
import colorsys
from tkinter import filedialog
import os
import random
import platform

class SatelliteSpectrumMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("中星10号频谱监测系统")
        self.root.geometry("1400x800")
        self.root.configure(bg="#171A25")
        
        # 系统信息
        self.current_utc = "2025-05-18 04:25:54"
        self.user = "piaosir"
        
        # 设置字体
        self.setup_fonts()
        
        # 参数设置
        self.fs = 100e6 # 采样率100MHz
        self.rb = 100.0 # 分辨率带宽: 100 kHz
        self.vb = 50.0 # 视频带宽: 50 kHz
        
        # 定义频率范围 (频段简化为仅C波段)
        self.bands = {
            "C波段下行": {"min": 3700, "max": 4200, "center": 3950, "unit": "MHz", "noise_floor": -110}
        }
        
        self.current_band = "C波段下行"
        self.noise_floor = self.bands[self.current_band]["noise_floor"]
        
        # 简化载波配置
        self.carrier_configs = [
            {"freq": 3850, "bw": 36, "power": -45, "name": "电视传输", "type": "DVB-S2"},
            {"freq": 3950, "bw": 54, "power": -40, "name": "数据链路", "type": "8PSK"},
            {"freq": 4050, "bw": 27, "power": -50, "name": "通信系统", "type": "QPSK"}
        ]
        
        # 选定的信号参数（初始为第一个载波）
        self.selected_carrier = self.carrier_configs[0]
        
        # 载波测量数据
        self.carrier_data = {
            "中心频率": f"{self.selected_carrier['freq']} MHz",
            "带宽": f"{self.selected_carrier['bw']} MHz",
            "功率": f"{self.selected_carrier['power']} dBm",
            "载噪比": "28.5 dB",
            "调制类型": self.selected_carrier['type']
        }
        
        # 卫星数据
        self.satellite_data = {
            "卫星名称": "中星10号",
            "卫星位置": "110.5° E",
            "下行频段": "C波段 (3.7-4.2 GHz)",
            "覆盖区域": "中国全境"
        }
        
        # 缩放区域
        self.zoom_freq_min = None
        self.zoom_freq_max = None
        self.zoom_active = False
        
        # 创建颜色方案
        self.create_color_scheme()
        
        # 创建UI
        self.create_widgets()
        
        # 启动模拟
        self.running = True
        self.update_thread = threading.Thread(target=self.update_simulation)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def setup_fonts(self):
        """设置字体"""
        if platform.system() == "Windows":
            self.title_font = ("Microsoft YaHei UI", 12, "bold")
            self.text_font = ("Microsoft YaHei UI", 10)
            self.small_font = ("Microsoft YaHei UI", 9)
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        elif platform.system() == "Darwin": # macOS
            self.title_font = ("PingFang SC", 12, "bold")
            self.text_font = ("PingFang SC", 10)
            self.small_font = ("PingFang SC", 9)
            plt.rcParams['font.sans-serif'] = ['PingFang SC']
        else: # Linux 或其他
            self.title_font = ("Noto Sans CJK SC", 12, "bold")
            self.text_font = ("Noto Sans CJK SC", 10) 
            self.small_font = ("Noto Sans CJK SC", 9)
            plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC']
        
        plt.rcParams['axes.unicode_minus'] = False
    
    def create_color_scheme(self):
        """创建颜色方案"""
        self.colors = {
            # 背景和面板
            "bg_dark": "#171A25", # 主背景色（深蓝黑色）
            "bg_panel": "#1F2336", # 面板背景色（稍亮蓝黑色）
            "bg_highlight": "#252A40", # 高亮背景色
            
            # 前景色
            "fg_primary": "#E4F0FB", # 主文字颜色（浅蓝白色）
            "fg_secondary": "#8C9DB9", # 次要文字颜色（灰蓝色）
            "fg_muted": "#5D6B89", # 暗淡文字颜色
            
            # 强调色
            "accent_blue": "#4EADEB", # 主强调色（亮蓝色）
            "accent_cyan": "#2DE2E6", # 青色强调
            "accent_purple": "#6C5CE7", # 紫色强调
            "accent_red": "#F64E60", # 红色强调/警告
            "accent_green": "#0ECB81", # 绿色（成功色）
            "accent_orange": "#FF9931", # 橙色（警告色）
            
            # 图表和网格线
            "grid": "#2D3452", # 网格线颜色
            "spectrum": "#4EADEB", # 频谱线颜色
            "spectrum_max": "#F64E60", # 最大保持线
            "noise_floor": "#0ECB81", # 噪底线
            
            # 渐变
            "gradient_start": "#4EADEB",
            "gradient_end": "#6C5CE7"
        }
        
        # 创建频谱图渐变
        n_colors = 256
        colors = []
        for i in range(n_colors):
            # 从蓝到紫渐变
            r1, g1, b1 = self.hex_to_rgb(self.colors["gradient_start"])
            r2, g2, b2 = self.hex_to_rgb(self.colors["gradient_end"])
            
            r = r1 + (r2 - r1) * i / (n_colors-1)
            g = g1 + (g2 - g1) * i / (n_colors-1)
            b = b1 + (b2 - b1) * i / (n_colors-1)
            
            colors.append((r/255, g/255, b/255))
        
        self.spectrum_cmap = mcolors.LinearSegmentedColormap.from_list("spectrum", colors)
    
    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB元组"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def create_widgets(self):
        """创建主UI界面"""
        # 配置行列权重
        self.root.grid_columnconfigure(0, weight=0) # 控制面板
        self.root.grid_columnconfigure(1, weight=1) # 频谱显示区域
        self.root.grid_rowconfigure(0, weight=1) # 主区域
        
        # 创建左侧控制面板
        self.control_frame = ttk.Frame(self.root, style="Control.TFrame", width=250)
        self.control_frame.grid(row=0, column=0, sticky="ns", padx=(10, 0), pady=10)
        self.control_frame.grid_propagate(False) # 防止frame被内容压缩
        
        # 创建右侧频谱显示区域
        self.display_frame = ttk.Frame(self.root, style="Display.TFrame")
        self.display_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # 应用自定义样式
        self.apply_custom_style()
        
        # 创建控制面板内容
        self.create_control_panel()
        
        # 创建频谱显示区域
        self.create_display_area()
    
    def apply_custom_style(self):
        """应用自定义样式"""
        style = ttk.Style()
        
        # 配置背景色
        style.configure("TFrame", background=self.colors["bg_dark"])
        style.configure("Control.TFrame", background=self.colors["bg_panel"])
        style.configure("Display.TFrame", background=self.colors["bg_dark"])
        
        # 标签样式
        style.configure("TLabel", 
                       background=self.colors["bg_panel"], 
                       foreground=self.colors["fg_primary"],
                       font=self.text_font)
        
        style.configure("Title.TLabel", 
                       background=self.colors["bg_panel"], 
                       foreground=self.colors["accent_blue"],
                       font=self.title_font)
        
        style.configure("Subtitle.TLabel", 
                       background=self.colors["bg_panel"], 
                       foreground=self.colors["accent_cyan"],
                       font=self.text_font)
        
        style.configure("Data.TLabel", 
                       background=self.colors["bg_panel"], 
                       foreground=self.colors["accent_green"],
                       font=self.text_font)
        
        # 按钮样式
        style.configure("TButton", 
                       background=self.colors["accent_blue"], 
                       foreground=self.colors["bg_dark"],
                       font=self.text_font,
                       padding=5)
        
        style.map("TButton", 
                 background=[("active", self.colors["accent_blue"])],
                 foreground=[("active", self.colors["bg_dark"])])
        
        # 滑动条样式
        style.configure("TScale", 
                       background=self.colors["bg_panel"],
                       troughcolor=self.colors["bg_highlight"])
        
        # 下拉框样式
        style.configure("TCombobox", 
                       background=self.colors["bg_panel"],
                       fieldbackground=self.colors["bg_highlight"],
                       foreground=self.colors["fg_primary"])
        
        # LabelFrame样式
        style.configure("TLabelframe", 
                       background=self.colors["bg_panel"],
                       foreground=self.colors["fg_primary"],
                       padding=10)
        
        style.configure("TLabelframe.Label", 
                       background=self.colors["bg_panel"],
                       foreground=self.colors["accent_blue"],
                       font=self.text_font)
        
        # 状态栏样式
        style.configure("Status.TLabel", 
                       background=self.colors["bg_dark"], 
                       foreground=self.colors["accent_cyan"],
                       font=self.small_font)
    
    def create_control_panel(self):
        """创建左侧控制面板内容"""
        # 标题
        title_frame = ttk.Frame(self.control_frame, style="Control.TFrame")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ttk.Label(title_frame, text="卫星频谱监测系统", style="Title.TLabel")
        title_label.pack(side="left")
        
        # 时间和用户信息
        info_frame = ttk.Frame(self.control_frame, style="Control.TFrame")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.time_label = ttk.Label(info_frame, text=f"UTC: {self.current_utc}", style="TLabel")
        self.time_label.pack(anchor="w")
        
        user_label = ttk.Label(info_frame, text=f"用户: {self.user}", style="TLabel")
        user_label.pack(anchor="w")
        
        # 卫星信息面板
        sat_frame = ttk.LabelFrame(self.control_frame, text="卫星信息")
        sat_frame.pack(fill="x", padx=10, pady=10)
        
        for key, value in self.satellite_data.items():
            item_frame = ttk.Frame(sat_frame, style="Control.TFrame")
            item_frame.pack(fill="x", pady=2)
            
            key_label = ttk.Label(item_frame, text=f"{key}:", style="TLabel")
            key_label.pack(side="left", anchor="w")
            
            value_label = ttk.Label(item_frame, text=f"{value}", style="Data.TLabel")
            value_label.pack(side="right", anchor="e")
        
        # 载波控制面板
        control_panel = ttk.LabelFrame(self.control_frame, text="监测控制")
        control_panel.pack(fill="x", padx=10, pady=10)
        
        # 分辨率带宽 (RB) 控制
        rb_frame = ttk.Frame(control_panel, style="Control.TFrame")
        rb_frame.pack(fill="x", pady=5)
        
        ttk.Label(rb_frame, text="分辨率带宽 (RB):").pack(side="left")
        
        self.rb_var = tk.StringVar(value=f"{self.rb} kHz")
        rb_label = ttk.Label(rb_frame, textvariable=self.rb_var, style="Data.TLabel")
        rb_label.pack(side="right")
        
        rb_scale = ttk.Scale(control_panel, from_=10, to=500, orient="horizontal", 
                           command=self.update_rb)
        rb_scale.set(self.rb)
        rb_scale.pack(fill="x", pady=(0, 10))
        
        # 视频带宽 (VB) 控制
        vb_frame = ttk.Frame(control_panel, style="Control.TFrame")
        vb_frame.pack(fill="x", pady=5)
        
        ttk.Label(vb_frame, text="视频带宽 (VB):").pack(side="left")
        
        self.vb_var = tk.StringVar(value=f"{self.vb} kHz")
        vb_label = ttk.Label(vb_frame, textvariable=self.vb_var, style="Data.TLabel")
        vb_label.pack(side="right")
        
        vb_scale = ttk.Scale(control_panel, from_=10, to=300, orient="horizontal", 
                           command=self.update_vb)
        vb_scale.set(self.vb)
        vb_scale.pack(fill="x", pady=(0, 10))
        
        # 按钮区域
        button_frame = ttk.Frame(control_panel, style="Control.TFrame")
        button_frame.pack(fill="x", pady=10)
        
        measure_btn = ttk.Button(button_frame, text="测量载波", command=self.measure_carrier)
        measure_btn.pack(fill="x", pady=3)
        
        reset_zoom_btn = ttk.Button(button_frame, text="重置缩放", command=self.reset_zoom)
        reset_zoom_btn.pack(fill="x", pady=3)
        
        # 载波选择
        carrier_frame = ttk.LabelFrame(self.control_frame, text="载波选择")
        carrier_frame.pack(fill="x", padx=10, pady=10)
        
        # 创建载波按钮
        self.carrier_buttons = []
        for i, carrier in enumerate(self.carrier_configs):
            btn = ttk.Button(carrier_frame, 
                          text=f"{carrier['freq']} MHz - {carrier['name']}",
                          command=lambda idx=i: self.select_carrier(idx))
            btn.pack(fill="x", pady=3)
            self.carrier_buttons.append(btn)
        
        # 载波信息面板
        self.carrier_info_frame = ttk.LabelFrame(self.control_frame, text="载波信息")
        self.carrier_info_frame.pack(fill="x", padx=10, pady=10)
        
        # 载波数据表格
        self.carrier_labels = {}
        
        for key, value in self.carrier_data.items():
            item_frame = ttk.Frame(self.carrier_info_frame, style="Control.TFrame")
            item_frame.pack(fill="x", pady=2)
            
            key_label = ttk.Label(item_frame, text=f"{key}:", style="TLabel")
            key_label.pack(side="left", anchor="w")
            
            value_label = ttk.Label(item_frame, text=f"{value}", style="Data.TLabel")
            value_label.pack(side="right", anchor="e")
            self.carrier_labels[key] = value_label
        
        # 状态栏
        self.status_bar = ttk.Label(
            self.control_frame, 
            text="系统就绪，监测中...", 
            style="Status.TLabel",
            anchor="w"
        )
        self.status_bar.pack(fill="x", padx=10, pady=(20, 10), side="bottom")
    
    def create_display_area(self):
        """创建频谱显示区域"""
        # 创建频谱图
        self.fig = Figure(figsize=(10, 7), dpi=100, facecolor=self.colors["bg_dark"])
        
        # 创建子图
        self.ax_spectrum = self.fig.add_subplot(111)
        self.style_axis(self.ax_spectrum)
        
        # 设置标题和轴标签
        self.ax_spectrum.set_title('C波段卫星频谱', color=self.colors["accent_blue"], fontsize=14)
        self.ax_spectrum.set_xlabel('频率 (MHz)', color=self.colors["fg_primary"], fontsize=12)
        self.ax_spectrum.set_ylabel('功率 (dBm)', color=self.colors["fg_primary"], fontsize=12)
        
        # 初始化频谱数据
        band_info = self.bands[self.current_band]
        freq_min = band_info["min"]
        freq_max = band_info["max"]
        
        x = np.linspace(freq_min, freq_max, 1000)
        y = np.zeros_like(x)
        
        # 添加频谱线
        self.spectrum_line, = self.ax_spectrum.plot(
            x, y, 
            color=self.colors["spectrum"], 
            linewidth=1.5, 
            alpha=0.9,
            label='实时频谱'
        )
        
        # 添加最大值保持线
        self.max_hold_line, = self.ax_spectrum.plot(
            x, y, 
            color=self.colors["spectrum_max"], 
            linewidth=1, 
            alpha=0.7,
            linestyle='--',
            label='最大保持'
        )
        
        # 添加噪底线
        self.noise_floor_line, = self.ax_spectrum.plot(
            [freq_min, freq_max], 
            [self.noise_floor, self.noise_floor], 
            color=self.colors["noise_floor"], 
            linestyle=':', 
            linewidth=1.5, 
            alpha=0.8,
            label='噪底电平'
        )
        
        # 设置y轴范围
        self.ax_spectrum.set_ylim(self.noise_floor - 10, -20)
        
        # 添加图例
        self.ax_spectrum.legend(
            loc='upper right', 
            facecolor=self.colors["bg_highlight"], 
            edgecolor=self.colors["grid"],
            labelcolor=self.colors["fg_primary"]
        )
        
        # 添加RB/VB信息
        self.rb_vb_text = self.ax_spectrum.text(
            0.02, 0.02, 
            f"RB: {int(self.rb)} kHz | VB: {int(self.vb)} kHz",
            color=self.colors["fg_secondary"], 
            fontsize=9, 
            ha='left', 
            va='bottom',
            transform=self.ax_spectrum.transAxes,
            bbox=dict(
                boxstyle="round,pad=0.3", 
                facecolor=self.colors["bg_highlight"], 
                edgecolor=self.colors["grid"], 
                alpha=0.8
            )
        )
        
        # 添加光标信息文本
        self.cursor_text = self.ax_spectrum.text(
            0.98, 0.02, 
            "",
            color=self.colors["fg_primary"], 
            fontsize=9, 
            ha='right', 
            va='bottom',
            transform=self.ax_spectrum.transAxes,
            bbox=dict(
                boxstyle="round,pad=0.3", 
                facecolor=self.colors["bg_highlight"], 
                edgecolor=self.colors["grid"], 
                alpha=0.8
            )
        )
        
        self.fig.tight_layout()
        
        # 将图表放入Tkinter窗口
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 添加工具栏
        toolbar_frame = ttk.Frame(self.display_frame, style="Display.TFrame")
        toolbar_frame.pack(fill="x")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        # 设置鼠标交互
        self.setup_mouse_interactions()
    
    def style_axis(self, ax):
        """样式化图表轴"""
        ax.set_facecolor(self.colors["bg_dark"])
        ax.grid(True, color=self.colors["grid"], linestyle='--', alpha=0.6)
        
        # 设置刻度线和标签颜色
        ax.tick_params(axis='x', colors=self.colors["fg_primary"], labelsize=10)
        ax.tick_params(axis='y', colors=self.colors["fg_primary"], labelsize=10)
        
        # 设置边框颜色
        for spine in ax.spines.values():
            spine.set_color(self.colors["grid"])
        
        # 添加次要刻度
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.tick_params(which='minor', length=4, color=self.colors["grid"], width=1)
    
    def setup_mouse_interactions(self):
        """设置鼠标交互"""
        # 区域选择工具
        self.rect_selector = RectangleSelector(
            self.ax_spectrum, 
            self.on_select, 
            useblit=True,
            button=[1], # 左键
            minspanx=5,
            spancoords='pixels',
            interactive=True,
            props=dict(
                facecolor=self.colors["accent_cyan"], 
                edgecolor=self.colors["accent_blue"], 
                alpha=0.3
            )
        )
        
        # 鼠标移动事件
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        
        # 鼠标点击事件
        self.canvas.mpl_connect('button_press_event', self.on_mouse_click)
    
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
        if event.inaxes == self.ax_spectrum:
            # 更新光标信息
            cursor_freq = event.xdata
            cursor_power = event.ydata
            self.cursor_text.set_text(f"频率: {cursor_freq:.2f} MHz | 电平: {cursor_power:.2f} dBm")
            self.canvas.draw_idle()
    
    def on_mouse_click(self, event):
        """处理鼠标点击事件"""
        if event.inaxes == self.ax_spectrum and event.button == 3: # 右键点击
            # 找到最近的载波
            closest_carrier = None
            min_distance = float('inf')
            
            for i, carrier in enumerate(self.carrier_configs):
                distance = abs(carrier["freq"] - event.xdata)
                if distance < min_distance:
                    min_distance = distance
                    closest_carrier = i
            
            # 如果点击位置在合理范围内 (50MHz以内)，选择该载波
            if min_distance <= 50:
                self.select_carrier(closest_carrier)
                self.status_bar.config(text=f"已选择 {self.carrier_configs[closest_carrier]['freq']} MHz 载波")
    
    def on_select(self, eclick, erelease):
        """鼠标选区回调函数"""
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata
        
        # 确保x1小于x2
        if x1 > x2:
            x1, x2 = x2, x1
            
        # 更新频谱显示范围
        self.zoom_freq_min = x1
        self.zoom_freq_max = x2
        self.zoom_active = True
        
        # 更新显示
        self.ax_spectrum.set_xlim(x1, x2)
        self.canvas.draw_idle()
        
        # 更新状态
        self.status_bar.config(text=f"放大显示区域: {x1:.1f} MHz - {x2:.1f} MHz")
    
    def update_rb(self, value):
        """更新分辨率带宽"""
        self.rb = float(value)
        self.rb_var.set(f"{int(self.rb)} kHz")
        self.rb_vb_text.set_text(f"RB: {int(self.rb)} kHz | VB: {int(self.vb)} kHz")
    
    def update_vb(self, value):
        """更新视频带宽"""
        self.vb = float(value)
        self.vb_var.set(f"{int(self.vb)} kHz")
        self.rb_vb_text.set_text(f"RB: {int(self.rb)} kHz | VB: {int(self.vb)} kHz")
    
    def select_carrier(self, idx):
        """选择载波"""
        if 0 <= idx < len(self.carrier_configs):
            self.selected_carrier = self.carrier_configs[idx]
            
            # 更新载波数据
            freq = self.selected_carrier["freq"]
            bw = self.selected_carrier["bw"]
            power = self.selected_carrier["power"]
            carrier_type = self.selected_carrier["type"]
            
            # 计算载噪比
            cnr = abs(power - self.noise_floor - 5)
            
            self.carrier_data = {
                "中心频率": f"{freq} MHz",
                "带宽": f"{bw} MHz",
                "功率": f"{power} dBm",
                "载噪比": f"{cnr:.1f} dB",
                "调制类型": carrier_type
            }
            
            # 更新UI
            self.update_carrier_info()
            
            # 切换到相应频率
            self.ax_spectrum.set_xlim(freq - bw*3, freq + bw*3)
            
            # 更新缩放状态
            self.zoom_active = True
            self.zoom_freq_min = freq - bw*3
            self.zoom_freq_max = freq + bw*3
            
            # 强制刷新
            self.canvas.draw_idle()
    
    def update_carrier_info(self):
        """更新载波信息"""
        for key, label in self.carrier_labels.items():
            label.config(text=self.carrier_data[key])
    
    def reset_zoom(self):
        """重置缩放"""
        if self.zoom_active:
            band_info = self.bands[self.current_band]
            freq_min = band_info["min"]
            freq_max = band_info["max"]
            
            self.ax_spectrum.set_xlim(freq_min, freq_max)
            self.zoom_active = False
            self.zoom_freq_min = None
            self.zoom_freq_max = None
            
            self.canvas.draw_idle()
            self.status_bar.config(text="已重置缩放，显示全频段")
    
    def measure_carrier(self):
        """测量当前选中的载波"""
        # 添加随机波动以模拟测量
        power = float(self.carrier_data["功率"].split()[0]) + np.random.uniform(-0.5, 0.5)
        cnr = float(self.carrier_data["载噪比"].split()[0]) + np.random.uniform(-0.3, 0.3)
        
        # 更新值
        self.carrier_data["功率"] = f"{power:.1f} dBm"
        self.carrier_data["载噪比"] = f"{cnr:.1f} dB"
        
        # 更新UI
        self.update_carrier_info()
        
        # 更新状态
        freq = self.selected_carrier["freq"]
        self.status_bar.config(text=f"已测量 {freq} MHz 载波，功率: {power:.1f} dBm，CNR: {cnr:.1f} dB")
    
    def apply_rb_vb_filtering(self, psd_db):
        """模拟RB和VB滤波效果"""
        # RB滤波 (移动平均)
        rb_window = max(1, int(self.rb / 10))
        if rb_window > 1:
            if rb_window % 2 == 0:
                rb_window += 1
            
            kernel = np.ones(rb_window) / rb_window
            rb_filtered = np.convolve(psd_db, kernel, mode='same')
        else:
            rb_filtered = psd_db
        
        # VB滤波 (指数平滑)
        vb_factor = min(0.99, self.vb / 300.0)
        if vb_factor < 0.95:
            alpha = vb_factor
            vb_filtered = np.zeros_like(rb_filtered)
            vb_filtered[0] = rb_filtered[0]
            for i in range(1, len(rb_filtered)):
                vb_filtered[i] = alpha * rb_filtered[i] + (1 - alpha) * vb_filtered[i-1]
        else:
            vb_filtered = rb_filtered
        
        return vb_filtered
    
    def generate_spectrum(self):
        """生成频谱数据"""
        # 获取频率范围
        band_info = self.bands[self.current_band]
        freq_min = band_info["min"]
        freq_max = band_info["max"]
        
        # 创建频率数组
        freq = np.linspace(freq_min, freq_max, 1000)
        
        # 生成噪底
        noise_variation = np.random.normal(0, 1, len(freq))
        psd = self.noise_floor + noise_variation
        
        # 为每个载波添加频谱
        for carrier in self.carrier_configs:
            carrier_freq = carrier["freq"]
            bandwidth = carrier["bw"]
            power = carrier["power"]
            
            # 创建载波形状 (高斯加sinc)
            for i, f in enumerate(freq):
                # 到中心的距离
                dist = abs(f - carrier_freq)
                
                if dist <= bandwidth:
                    # 中心区域用高斯形状
                    shape = np.exp(-0.5 * (dist / (bandwidth/4))**2)
                    
                    # 载波功率
                    carrier_power = power * shape
                    
                    # 加入小幅波动
                    ripple = np.random.uniform(-1, 1)
                    carrier_power += ripple
                    
                    # 取较大值
                    psd[i] = max(psd[i], carrier_power)
        
        # 应用RB/VB滤波
        psd = self.apply_rb_vb_filtering(psd)
        
        return freq, psd
    
    def update_simulation(self):
        """更新模拟"""
        while self.running:
            try:
                # 生成频谱数据
                freq, psd = self.generate_spectrum()
                
                # 保存最大值
                if not hasattr(self, 'max_hold') or len(self.max_hold) != len(psd):
                    self.max_hold = psd.copy()
                else:
                    # 逐渐衰减最大值
                    self.max_hold = self.max_hold - 0.05
                    # 更新高于当前最大值的点
                    self.max_hold = np.maximum(self.max_hold, psd)
                
                # 更新UI
                self.root.after(0, self.update_plots, freq, psd)
                
                # 更新时间
                current_time = self.current_utc
                self.time_label.config(text=f"UTC: {current_time}")
                
                # 控制更新速率
                time.sleep(0.1)
                
            except Exception as e:
                print(f"更新错误: {e}")
                time.sleep(1.0)
    
    def update_plots(self, freq, psd):
        """更新图表"""
        # 更新频谱线
        self.spectrum_line.set_data(freq, psd)
        
        # 更新最大保持线
        self.max_hold_line.set_data(freq, self.max_hold)
        
        # 刷新画布
        self.canvas.draw_idle()
    
    def on_closing(self):
        """关闭窗口时清理"""
        self.running = False
        time.sleep(0.2)
        self.root.destroy()


# 启动应用
if __name__ == "__main__":
    root = tk.Tk()
    app = SatelliteSpectrumMonitor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
