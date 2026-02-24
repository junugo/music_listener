#Python获取ffmepg进度: https://blog.csdn.net/qq_41730930/article/details/103815613

import os
import re
import json
import uuid
import requests
import subprocess
import shutil
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO

# 定义临时文件路径常量
temp_path = "temp"

# 确保temp文件夹存在
if not os.path.exists(temp_path):
    os.mkdir(temp_path)

# Bilibili API相关
class BilibiliParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.bilibili.com'
        }
    
    def extract_id_from_url(self, url: str) -> Optional[str]:
        """从Bilibili URL中提取视频ID"""
        # 处理BV号
        bv_pattern = r'(?:https?://)?(?:www\.)?bilibili\.com/video/([BbVv][Vv][0-9a-zA-Z]+)'
        bv_match = re.search(bv_pattern, url)
        if bv_match:
            return bv_match.group(1)
        
        # 处理av号
        av_pattern = r'(?:https?://)?(?:www\.)?bilibili\.com/video/[Aa][Vv](\d+)'
        av_match = re.search(av_pattern, url)
        if av_match:
            return f"av{av_match.group(1)}"
        
        # 处理短链接
        if 'b23.tv' in url:
            try:
                response = requests.head(url, headers=self.headers, allow_redirects=True)
                redirect_url = response.url
                return self.extract_id_from_url(redirect_url)
            except Exception:
                pass
        
        # 处理纯BV号
        if url.startswith('BV') or url.startswith('bv'):
            return url
        
        return None
    
    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """获取视频信息"""
        try:
            # 使用不需要登录的API
            if video_id.lower().startswith('av'):
                aid = video_id[2:]
                url = f"https://api.bilibili.com/x/web-interface/view?aid={aid}"
            else:
                url = f"https://api.bilibili.com/x/web-interface/view?bvid={video_id}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0 or not data.get('data'):
                raise ValueError(f"无法获取视频信息: {data}")
            
            video_data = data['data']
            return {
                'song_name': video_data['title'],
                'composer': video_data['owner']['name'],
                'cover_url': video_data['pic'],
                'video_id': video_id,
                'cid': video_data['cid']  # 获取cid用于下载视频
            }
        except Exception as e:
            raise Exception(f"获取Bilibili视频信息失败: {str(e)}")
    
    def download_video(self, video_id: str, cid: str, save_path: str, progress_callback=None) -> str:
        """下载视频文件"""
        try:
            # 获取视频下载链接
            if video_id.lower().startswith('av'):
                aid = video_id[2:]
                url = f"https://api.bilibili.com/x/player/playurl?avid={aid}&cid={cid}&qn=64&fnval=0"
            else:
                url = f"https://api.bilibili.com/x/player/playurl?bvid={video_id}&cid={cid}&qn=64&fnval=0"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0 or not data.get('data') or not data['data'].get('durl'):
                raise ValueError(f"无法获取视频下载链接: {data}")
            
            video_url = data['data']['durl'][0]['url']
            
            # 下载视频文件
            headers = self.headers.copy()
            headers['Referer'] = f"https://www.bilibili.com/video/{video_id}"
            
            # 获取文件大小用于进度计算
            with requests.get(video_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                
                download_temp_path = save_path + ".temp"
                with open(download_temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # 报告下载进度（0-40%）
                            if progress_callback and total_size > 0:
                                progress = int((downloaded_size / total_size) * 40)
                                progress_callback(progress, "正在下载音频...")
            
            # 报告转换开始（40%）
            if progress_callback:
                progress_callback(40, "正在转换音频格式...")
            
            try:
                # 使用subprocess调用ffmpeg，通过stderr获取进度信息
                cmd = ["ffmpeg", "-i", download_temp_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", save_path]
                
                # 启动ffmpeg进程，捕获stderr输出
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                # 实时解析进度
                last_progress = 0
                # 读取初始输入文件信息获取总时长
                total_duration = 0
                for line in process.stderr:
                    # 解析总时长
                    if 'Duration:' in line:
                        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', line)
                        if duration_match:
                            h, m, s = duration_match.groups()
                            total_duration = int(h) * 3600 + int(m) * 60 + float(s)
                    # 解析编码进度
                    elif 'time=' in line:
                        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                        if time_match and total_duration > 0:
                            h, m, s = time_match.groups()
                            current_time = int(h) * 3600 + int(m) * 60 + float(s)
                            # 计算当前进度比例（0-1）
                            progress_ratio = min(current_time / total_duration, 1.0)
                            # 转换为40%-70%范围
                            current_progress = 40 + int(progress_ratio * 30)
                            
                            # 确保进度只增不减，且在40%-70%范围内
                            if current_progress > last_progress and current_progress <= 70:
                                last_progress = current_progress
                                if progress_callback:
                                    progress_callback(current_progress, "正在转换音频格式...")
                    
                    # 检查进程是否结束
                    if process.poll() is not None:
                        break
                
                # 检查ffmpeg进程是否成功完成
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
            except Exception as e:
                # 处理异常
                raise
            
            # 报告转换完成（70%）
            if progress_callback:
                progress_callback(70, "音频格式转换完成")
            
            # 删除临时文件
            if os.path.exists(download_temp_path):
                os.remove(download_temp_path)
            
            return save_path
        except Exception as e:
            raise Exception(f"下载Bilibili视频失败: {str(e)}")
    
    def download_cover(self, cover_url: str, save_path: str) -> str:
        """下载封面图片"""
        try:
            response = requests.get(cover_url, headers=self.headers)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            img.save(save_path, "PNG")
            
            return save_path
        except Exception as e:
            raise Exception(f"下载Bilibili视频封面失败: {str(e)}")

# 内容解析器工厂
class ContentParserFactory:
    @staticmethod
    def create_parser(url: str):
        """根据URL创建相应的解析器"""
        if "bilibili.com" in url or "b23.tv" in url or url.startswith("BV") or url.startswith("bv") or url.startswith("AV") or url.startswith("av"):
            return BilibiliParser()
        else:
            raise ValueError("不支持的URL格式，请提供Bilibili的链接")

# 只解析URL信息而不下载的函数
def parse_url_info(url: str) -> Dict[str, Any]:
    """解析URL内容但不下载，返回解析结果"""
    try:
        # 创建解析器
        parser = ContentParserFactory.create_parser(url)
        
        # 提取ID
        content_id = parser.extract_id_from_url(url)
        if not content_id:
            raise ValueError("无法从URL中提取内容ID")
        
        # 获取内容信息
        info = parser.get_video_info(content_id)
        content_type = "bilibili_video"
        
        return {
            "song_name": info['song_name'],
            "composer": info['composer'],
            "cover_url": info['cover_url'],
            "content_id": content_id,
            "content_type": content_type,
            "additional_info": info
        }
    except Exception as e:
        raise Exception(f"解析内容失败: {str(e)}")

# 统一的内容处理函数
def process_content(url: str, music_path: str, override_title: str = None, override_author: str = None, progress_callback=None) -> Dict[str, Any]:
    """处理内容并保存到本地，可选择性地覆盖标题和作者"""
    # 创建临时文件标识符
    temp_id = str(uuid.uuid4())
    temp_folder = f"{temp_path}/temp_{temp_id}"
    
    try:
        # 创建解析器
        parser = ContentParserFactory.create_parser(url)
        
        # 提取ID
        content_id = parser.extract_id_from_url(url)
        if not content_id:
            raise ValueError("无法从URL中提取内容ID")
        
        # 获取内容信息
        info = parser.get_video_info(content_id)
        content_type = "bilibili_video"
        
        # 如果提供了覆盖值，则使用覆盖值
        song_name = override_title if override_title else info['song_name']
        composer = override_author if override_author else info['composer']
        
        # 创建唯一标识符
        new_song_num = str(uuid.uuid4())
        new_song_folder = f"{music_path}/{new_song_num}"
        
        # 先下载到temp文件夹下的临时位置
        os.makedirs(temp_folder, exist_ok=True)
        temp_music_path = f"{temp_folder}/temp_music.mp3"
        temp_cover_path = f"{temp_folder}/temp_cover.png"
        
        # 下载视频文件到临时位置，传递进度回调
        parser.download_video(content_id, info['cid'], temp_music_path, progress_callback)
        
        # 下载封面到临时位置（70%）
        if progress_callback:
            progress_callback(70, "正在下载封面图片...")
        parser.download_cover(info['cover_url'], temp_cover_path)
        
        # 音频音量均衡处理（75%）
        if progress_callback:
            progress_callback(75, "正在进行音频均衡处理...")
        normalized_music_path = f"{temp_folder}/normalized_music.mp3"
        try:
            # 使用ffmpeg进行音量均衡，通过stderr获取进度信息
            cmd = [
                "ffmpeg", "-i", temp_music_path, "-af", 
                "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=summary", 
                "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k",
                normalized_music_path
            ]
            
            # 启动ffmpeg进程，捕获stderr输出
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 实时解析进度
            last_progress = 75  # 起始进度
            # 读取初始输入文件信息获取总时长
            total_duration = 0
            for line in process.stderr:
                # 解析总时长
                if 'Duration:' in line:
                    duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', line)
                    if duration_match:
                        h, m, s = duration_match.groups()
                        total_duration = int(h) * 3600 + int(m) * 60 + float(s)
                # 解析编码进度
                elif 'time=' in line:
                    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                    if time_match and total_duration > 0:
                        h, m, s = time_match.groups()
                        current_time = int(h) * 3600 + int(m) * 60 + float(s)
                        # 计算当前进度比例（0-1）
                        progress_ratio = min(current_time / total_duration, 1.0)
                        # 转换为75%-95%范围
                        current_progress = 75 + int(progress_ratio * 20)
                        
                        # 确保进度只增不减，且在75%-95%范围内
                        if current_progress > last_progress and current_progress <= 95:
                            last_progress = current_progress
                            if progress_callback:
                                progress_callback(current_progress, "正在进行音频均衡处理...")
                
                # 检查进程是否结束
                if process.poll() is not None:
                    break
            
            # 检查ffmpeg进程是否成功完成
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
        except Exception as e:
            # 清理临时文件夹
            if os.path.exists(temp_folder):
                for file_name in os.listdir(temp_folder):
                    file_path = os.path.join(temp_folder, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(temp_folder)
            raise Exception(f"音频处理失败: {str(e)}")
        
        # 所有文件下载和处理成功后，创建最终目标文件夹（95%）
        if progress_callback:
            progress_callback(95, "正在保存文件...")
        os.makedirs(new_song_folder, exist_ok=True)
        
        # 复制处理好的文件到最终位置
        music_file_path = f"{new_song_folder}/music.mp3"
        cover_file_path = f"{new_song_folder}/music.png"
        
        shutil.copy2(normalized_music_path, music_file_path)
        shutil.copy2(temp_cover_path, cover_file_path)
        
        # 保存歌曲信息
        with open(f"{new_song_folder}/music.txt", "w", encoding="utf-8") as file:
            file.write(f"{composer}\n{song_name}")

        # 保存歌曲网址
        with open(f"{new_song_folder}/URL.txt", "w", encoding="utf-8") as file:
            file.write(url)
        
        # 清理临时文件夹
        if os.path.exists(temp_folder):
            for file_name in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(temp_folder)
        
        # 处理完成（100%）
        if progress_callback:
            progress_callback(100, "处理完成")
        
        return {
            "song_id": new_song_num,
            "song_name": song_name,
            "composer": composer,
            "content_type": content_type
        }
    except Exception as e:
        # 清理临时文件夹
        if os.path.exists(temp_folder):
            for file_name in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(temp_folder)
        
        # 如果文件夹已创建，则删除
        if 'new_song_folder' in locals() and os.path.exists(new_song_folder):
            for file_name in os.listdir(new_song_folder):
                file_path = os.path.join(new_song_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(new_song_folder)
        
        print(f"处理内容时出错: {str(e)}")
        raise Exception(f"处理内容失败: {str(e)}")