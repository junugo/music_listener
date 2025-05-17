music_listener
-
只是一个音乐软件，python 作为后端，前端使用 HTML CSS JS

名字是一个明显的翻译错误，不过还挺不错的对吧 awa

# 功能
> [!TIP]
> 以下展示中出现的乐曲、图片皆属于他人作品，版权归原作者所有，如有侵权请与我联系。（图中正在播放的音乐为 [周一能不能放过我一次😭👊🏻 - bilibili](https://www.bilibili.com/video/BV17wogYrEME/)）

> 网站效果（打开菜单）

![image](https://github.com/user-attachments/assets/b297bac8-a8af-4058-904d-80dba35d6859 "网站效果（打开菜单）")
> 网站效果（关闭菜单）

![image](https://github.com/user-attachments/assets/60ec1c3f-2822-4aec-bb81-bc92aa611516 "网站效果（关闭菜单）")
> 小窗播放效果

![image](https://github.com/user-attachments/assets/78b17b56-32b7-42d2-9624-354647b13ef2 "小窗播放效果")

这是一个在线音乐播放器，可以本地播放音乐，也可以部署至服务器和他人共享音乐。仅需打开网站即可享受音乐。CSS样式可以自动适应大部分尺寸的设备。

网站界面使用了简约的设计风格，减少文字的出现。如果您需要操作指南，请在左上角打开菜单并将鼠标移至“指南针”上查看提示。（感谢 [feathericons](https://feathericons.com) 优美的图标）

不得不说，这个界面听音乐挺舒服的，特别是一些有节奏的音乐，可以触发自带的界面特效。（自豪）

> [!warning]
> 此项目为本人新手作品，如有改进建议或 BUG，请提交 ISSUE
> 
> **代码中存在大量屎山，包括但不限于在 Python 中使用大量语法糖、把 CSS\HTML\JS 写在一个 html 文件中、玄学变量名等行为，二次开发需注意安全**

# 安装

```
git clone https://github.com/junugo/music_listener.git
cd music_listener
pip install -r requirements.txt
```

如果你需要上传音乐功能，务必配置 [ffmpeg](https://ffmpeg.org/) ，否则服务器会 **爆掉** 哦

# 运行

你只需要打开 server.py ，然后访问 `127.0.0.1:88` 如果你使用 Windows 系统，可以直接运行 start.bat

# 感谢

代码中使用了一些其它人的作品，感谢他们的贡献，如果你想知道来源，代码中注释均有标注