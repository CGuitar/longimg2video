# longimg2video

windows长图转视频

### 简介

实现单张图片在固定分辨率画框下的滚动效果

> 使用场景：项目产品展示；餐厅菜单展示；图文滚动展示；简历展示···

![demo演示](/example/demo.gif)

### 使用方法

#### 一、压缩包下载解压（推荐）

1. 下载longimg2video.zip并解压
2. 右键longimg2video.exe创建快捷方式（可选）
3. 双击图标即可进入配置弹窗，可修改分辨率、帧率、画质、播放速度等参数
4. 拖动图片到图标即可转换为视频到原文件夹

#### 二、源码配置

1. 克隆仓库到本地

```powershell
git clone https://github.com/CGuitar/longimg2video.git
```

2. 安装依赖

```powershell
pip install -r requirements.txt
```

3. 将脚本打包为exe文件

```powershell
pyinstaller --onefile --icon=icon.ico longimg2video.py
```

4. 下载 `ffmpeg.exe` 并放在exe文件同目录下，或者确保系统PATH中有ffmpeg（下载地址：https://ffmpeg.org/download.html）

5. 右键longimg2video.exe创建快捷方式（可选）

---

> 默认参数：
>
> 分辨率：720p
>
> 帧率：30帧
>
> 画质：低
>
> 速度：极快





