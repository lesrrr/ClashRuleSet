
根据 https://github.com/doge-8/kuzco-monitor/delete/main/kz.py 进行修改

解决了实例异常时无法完全杀死实例进程导致实例数量不断增加的问题，

每300秒没有完成推理请求会自动重启，内界面美化


![image](https://github.com/user-attachments/assets/3326c406-1219-4322-8e1e-1eda649c6b88)


点击右边【Releases】下载

下载后需要配置的几个参数：

check_interval = 300  # 检测时间间隔，单位：秒  可自由调整，如果网络较差可适当延长检测时间

workers = 12  # 根据自己的设备设置进程数量

code = ""  # 粘贴code

只需粘贴--code后面的代码

![image](https://github.com/user-attachments/assets/caf636bd-7315-4f7f-b529-47b6a06dd342)
