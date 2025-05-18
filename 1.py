import os
import requests
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class 百度语音识别器:
    def __init__(self, api密钥, secret密钥):
        self.api密钥 = api密钥
        self.secret密钥 = secret密钥
        self.token = None
        self._获取访问令牌()
        
    def _获取访问令牌(self):
        认证地址 = f"https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api密钥}&client_secret={self.secret密钥}"
        try:
            响应 = requests.get(认证地址)
            响应.raise_for_status()
            self.token = 响应.json().get("access_token")
            if not self.token:
                raise Exception("获取访问令牌失败：API凭证无效")
        except Exception as e:
            raise Exception(f"认证失败：{str(e)}")
    
    def 识别(self, 文件路径, 进度回调=None):
        if not os.path.exists(文件路径):
            raise ValueError("文件不存在")
            
        # 检查文件大小并选择合适API
        文件大小 = os.path.getsize(文件路径)
        if 文件大小 > 10 * 1024 * 1024:  # 大于10MB
            return self._识别长音频(文件路径, 进度回调)
        else:
            return self._识别短音频(文件路径, 进度回调)
    
    def _识别短音频(self, 文件路径, 进度回调=None):
        接口地址 = "http://vop.baidu.com/server_api"
        文件扩展名 = os.path.splitext(文件路径)[1][1:].lower()
        
        请求头 = {'Content-Type': f'audio/{文件扩展名}; rate=16000'}
        参数 = {
            "cuid": "python客户端",
            "token": self.token,
            "dev_pid": 1537  # 普通话
        }
        
        try:
            with open(文件路径, 'rb') as 音频文件:
                响应 = requests.post(接口地址, params=参数, headers=请求头, data=音频文件)
            
            结果 = 响应.json()
            if 结果.get("err_no") != 0:
                raise Exception(f"识别错误 {结果.get('err_no')}: {结果.get('err_msg')}")
            
            return 结果.get("result", "")
            
        except Exception as e:
            raise Exception(f"识别失败：{str(e)}")
    
    def _识别长音频(self, 文件路径, 进度回调=None):
        # 百度长语音识别需要先上传文件
        上传地址 = "https://openapi.baidu.com/robot/1.0/voice/audioprocess/upload"
        查询地址 = "https://openapi.baidu.com/robot/1.0/voice/audioprocess/query"
        
        # 第一步：上传文件
        try:
            with open(文件路径, 'rb') as 音频文件:
                响应 = requests.post(
                    上传地址,
                    files={'file': 音频文件},
                    data={'access_token': self.token}
                )
                上传结果 = 响应.json()
                
                if 上传结果.get('err_no') != 0:
                    raise Exception(f"上传失败：{上传结果.get('err_msg')}")
                
                任务ID = 上传结果['data']['task_id']
                
        except Exception as e:
            raise Exception(f"文件上传失败：{str(e)}")
        
        # 第二步：查询识别结果
        最大重试 = 30  # 最多等待3分钟(6秒*30)
        重试间隔 = 6
        
        for 尝试 in range(最大重试):
            try:
                if 进度回调:
                    进度 = int((尝试 / 最大重试) * 100)
                    进度回调(进度)
                
                响应 = requests.get(
                    查询地址,
                    params={
                        'access_token': self.token,
                        'task_id': 任务ID
                    }
                )
                查询结果 = 响应.json()
                
                if 查询结果.get('err_no') == 0:
                    if 查询结果['data']['status'] == 2:  # 完成
                        return 查询结果['data']['result']
                    elif 查询结果['data']['status'] == 3:  # 失败
                        raise Exception("服务器端识别失败")
                    # 否则继续等待
                
                elif 查询结果.get('err_no') != 26605:  # 26605表示"处理中"
                    raise Exception(f"查询错误：{查询结果.get('err_msg')}")
                
                if 尝试 < 最大重试 - 1:
                    threading.Event().wait(重试间隔)
                    
            except Exception as e:
                raise Exception(f"识别查询失败：{str(e)}")
        
        raise Exception("识别超时：处理时间过长")


class 语音识别应用:
    def __init__(self, 主窗口):
        self.主窗口 = 主窗口
        self.主窗口.title("百度语音识别工具")
        self.主窗口.geometry("600x400")
        
        # API设置框架
        设置框架 = tk.LabelFrame(主窗口, text="API设置", padx=5, pady=5)
        设置框架.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(设置框架, text="API密钥:").grid(row=0, column=0, sticky=tk.W)
        self.api密钥输入 = tk.Entry(设置框架, width=50)
        self.api密钥输入.grid(row=0, column=1, padx=5, pady=2)
        self.api密钥输入.insert(0, "hvBbz00OqVPfUpv8eI3mShat")
        
        tk.Label(设置框架, text="Secret密钥:").grid(row=1, column=0, sticky=tk.W)
        self.secret密钥输入 = tk.Entry(设置框架, width=50, show="*")
        self.secret密钥输入.grid(row=1, column=1, padx=5, pady=2)
        self.secret密钥输入.insert(0, "oudveRqEdyqMk0Yle5LCG35sES6kO0xA")
        
        # 文件选择框架
        文件框架 = tk.LabelFrame(主窗口, text="音频文件", padx=5, pady=5)
        文件框架.pack(fill=tk.X, padx=10, pady=5)
        
        self.文件路径 = tk.StringVar()
        tk.Entry(文件框架, textvariable=self.文件路径, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(文件框架, text="浏览...", command=self.浏览文件).pack(side=tk.LEFT)
        
        # 进度条框架
        进度条框架 = tk.Frame(主窗口)
        进度条框架.pack(fill=tk.X, padx=10, pady=5)
        
        self.进度条 = ttk.Progressbar(进度条框架, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.进度条.pack()
        
        # 结果框架
        结果框架 = tk.LabelFrame(主窗口, text="识别结果", padx=5, pady=5)
        结果框架.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.结果文本 = tk.Text(结果框架, wrap=tk.WORD)
        滚动条 = tk.Scrollbar(结果框架, command=self.结果文本.yview)
        self.结果文本.configure(yscrollcommand=滚动条.set)
        
        滚动条.pack(side=tk.RIGHT, fill=tk.Y)
        self.结果文本.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        按钮框架 = tk.Frame(主窗口)
        按钮框架.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(按钮框架, text="开始识别", command=self.开始识别).pack(side=tk.LEFT)
        tk.Button(按钮框架, text="清空结果", command=self.清空结果).pack(side=tk.LEFT)
        tk.Button(按钮框架, text="保存结果", command=self.保存结果).pack(side=tk.LEFT)
        tk.Button(按钮框架, text="退出", command=主窗口.quit).pack(side=tk.RIGHT)
        
        self.识别器 = None
    
    def 浏览文件(self):
        文件类型 = (
            ('音频文件', '*.wav *.mp3 *.aac *.m4a *.amr *.wma *.flac'),
            ('所有文件', '*.*')
        )
        文件名 = filedialog.askopenfilename(title="选择音频文件", filetypes=文件类型)
        if 文件名:
            self.文件路径.set(文件名)
    
    def 更新进度(self, 值):
        self.进度条['value'] = 值
        self.主窗口.update_idletasks()
    
    def 开始识别(self):
        if not self.文件路径.get():
            messagebox.showerror("错误", "请先选择音频文件")
            return
            
        api密钥 = self.api密钥输入.get()
        secret密钥 = self.secret密钥输入.get()
        
        if not api密钥 or not secret密钥:
            messagebox.showerror("错误", "请输入API密钥和Secret密钥")
            return
            
        self.结果文本.delete(1.0, tk.END)
        self.结果文本.insert(tk.END, "处理中...请稍候...\n")
        self.进度条['value'] = 0
        
        def 识别线程():
            try:
                self.识别器 = 百度语音识别器(api密钥, secret密钥)
                结果 = self.识别器.识别(
                    self.文件路径.get(),
                    进度回调=self.更新进度
                )
                
                self.结果文本.delete(1.0, tk.END)
                self.结果文本.insert(tk.END, 结果)
                self.进度条['value'] = 100
                messagebox.showinfo("成功", "识别完成！")
                
            except Exception as e:
                self.结果文本.insert(tk.END, f"\n错误：{str(e)}")
                self.进度条['value'] = 0
                messagebox.showerror("错误", str(e))
        
        threading.Thread(target=识别线程, daemon=True).start()
    
    def 清空结果(self):
        self.结果文本.delete(1.0, tk.END)
        self.进度条['value'] = 0
    
    def 保存结果(self):
        if not self.结果文本.get(1.0, tk.END).strip():
            messagebox.showerror("错误", "没有可保存的结果")
            return
            
        文件名 = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*"))
        )
        if 文件名:
            with open(文件名, 'w', encoding='utf-8') as 文件:
                文件.write(self.结果文本.get(1.0, tk.END))


if __name__ == "__main__":
    主窗口 = tk.Tk()
    应用 = 语音识别应用(主窗口)
    主窗口.mainloop()