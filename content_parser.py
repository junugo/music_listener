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
    
    def download_video(self, video_id: str, cid: str, save_path: str) -> str:
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
            response = requests.get(video_url, headers=headers, stream=True)
            response.raise_for_status()
            
            temp_path = save_path + ".temp"
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 使用ffmpeg转换为mp3格式
            cmd = ["ffmpeg", "-i", temp_path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", save_path]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 删除临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
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
def process_content(url: str, music_path: str, override_title: str = None, override_author: str = None) -> Dict[str, Any]:
    """处理内容并保存到本地，可选择性地覆盖标题和作者"""
    # 创建临时文件标识符
    temp_id = str(uuid.uuid4())
    temp_folder = f"temp_{temp_id}"
    
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
        
        # 先下载到临时位置
        os.makedirs(temp_folder, exist_ok=True)
        temp_music_path = f"{temp_folder}/temp_music.mp3"
        temp_cover_path = f"{temp_folder}/temp_cover.png"
        
        # 下载视频文件到临时位置
        parser.download_video(content_id, info['cid'], temp_music_path)
        
        # 下载封面到临时位置
        parser.download_cover(info['cover_url'], temp_cover_path)
        
        # 音频音量均衡处理
        normalized_music_path = f"{temp_folder}/normalized_music.mp3"
        try:
            # 使用ffmpeg进行音量均衡
            cmd = [
                "ffmpeg", "-i", temp_music_path, "-af", 
                "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=summary", 
                "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", 
                normalized_music_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            # 清理临时文件夹
            if os.path.exists(temp_folder):
                for file_name in os.listdir(temp_folder):
                    file_path = os.path.join(temp_folder, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(temp_folder)
            raise Exception(f"音频处理失败: {str(e)}")
        
        # 所有文件下载和处理成功后，创建最终目标文件夹
        os.makedirs(new_song_folder, exist_ok=True)
        
        # 复制处理好的文件到最终位置
        music_file_path = f"{new_song_folder}/music.mp3"
        cover_file_path = f"{new_song_folder}/music.png"
        
        shutil.copy2(normalized_music_path, music_file_path)
        shutil.copy2(temp_cover_path, cover_file_path)
        
        # 保存歌曲信息
        with open(f"{new_song_folder}/music.txt", "w", encoding="utf-8") as file:
            file.write(f"{composer}\n{song_name}")
        
        # 清理临时文件夹
        if os.path.exists(temp_folder):
            for file_name in os.listdir(temp_folder):
                file_path = os.path.join(temp_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(temp_folder)
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
        if os.path.exists(new_song_folder):
            for file_name in os.listdir(new_song_folder):
                file_path = os.path.join(new_song_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(new_song_folder)
        
        print(f"处理内容时出错: {str(e)}")
        raise Exception(f"处理内容失败: {str(e)}")