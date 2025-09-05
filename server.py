import os
from typing import List, Dict

import uvicorn
from PIL import Image
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse

import subprocess
# 抛弃了 pydub，因为 python 3.13 开始，pydub 出现问题
import uuid
import json

# 导入内容解析模块
from content_parser import process_content

music_path = "music"
if not os.path.exists(music_path):
    os.mkdir(music_path)
album_path = "album"
if not os.path.exists(album_path):
    os.mkdir(album_path)

app = FastAPI()


# 挂载静态文件目录（包含index.html、music和images文件夹）
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

def get_music_info(num):
    pic_valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webm', '.jfif']
    music_valid_extensions = ['.wav', '.mp3']

    music_folder = f"{music_path}/{num}"
    if not os.path.exists(music_folder):
        raise HTTPException(status_code=404, detail="歌曲未找到")

    with open(f"{music_folder}/music.txt", "r", encoding="utf-8") as file:
        composer = file.readline().strip()
        song_name = file.readline().strip()

    music_file = os.path.join(music_folder, "music.mp3")
    if not os.path.exists(music_file):
        music_file = os.path.join(music_folder, [file for file in os.listdir(music_folder) if
                                                 os.path.isfile(os.path.join(music_folder, file)) and any(
                                                     file.lower().endswith(ext) for ext in
                                                     music_valid_extensions) and "music." in file][0])
    image_file = os.path.join(music_folder, "music.png")
    if not os.path.exists(image_file):
        image_file = os.path.join(music_folder, [file for file in os.listdir(music_folder) if
                                                 os.path.isfile(os.path.join(music_folder, file)) and any(
                                                     file.lower().endswith(ext) for ext in
                                                     pic_valid_extensions) and "music." in file][0])

    return {
        "composer": composer,
        "song_name": song_name,
        "music_file": music_file,
        "image_file": image_file,
    }


time = 0


@app.get("/", response_class=HTMLResponse)
async def get_index():
    global time
    time += 1
    print(f"访问次数：{time}")
    return FileResponse("static/index.html")

@app.get("/add_content", response_class=HTMLResponse)
async def add_content():
    return FileResponse("static/add_content.html")


@app.get("/file/{page_name}", response_class=HTMLResponse)
async def find_page(page_name: str):
    # 通过路径参数指定页面名称，读取对应的 HTML 文件内容并返回
    if "." not in page_name:
        page_name += ".html"
    file_path = f"static/{page_name}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        # 如果文件不存在，跳转至欢迎页面
        return HTTPException(status_code=404, detail="页面在哪里？")


@app.get("/icon/{page_name}")
async def find_page(page_name: str):
    if "." not in page_name:
        page_name += ".svg"
    file_path = f"static/icon/{page_name}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/svg+xml")
    else:
        # 如果文件不存在，跳转至欢迎页面
        return HTTPException(status_code=404, detail="页面在哪里？")


@app.get("/list/", response_model=List[Dict[str, str]])  # 废弃 API
async def get_song_list():
    song_list = [
        {"name": await get_song_name(folder), "num": folder}
        for folder in os.listdir("music")
        if os.path.isdir(f"{music_path}/{folder}")
    ]
    return song_list


@app.get("/name/{num}", response_model=str)
async def get_song_name(num: str):
    try:
        info = get_music_info(num)
        return info["song_name"]
    except HTTPException as e:
        raise e


@app.get("/music/{num}")
async def get_music_file(num: str):
    try:
        info = get_music_info(num)
        return FileResponse(info["music_file"], media_type="audio/wav")
    except HTTPException as e:
        raise e


@app.get("/musician/{num}", response_model=str)
async def get_musician(num: str):
    try:
        info = get_music_info(num)
        return info["composer"]
    except HTTPException as e:
        raise e


@app.get("/photo/{num}")
async def get_photo(num: str):
    try:
        info = get_music_info(num)
        return FileResponse(info["image_file"], media_type="image/png")
    except HTTPException as e:
        raise e


@app.get("/all_information_of_music")  # 废弃API
async def information():
    song_list = [
        {"num": folder, "name": await get_song_name(folder), "musician": await get_musician(folder)}
        for folder in os.listdir(music_path)
        if os.path.isdir(f"{music_path}/{folder}")
    ]
    song_list = sorted(song_list, key=lambda x: int(x['num']))
    return song_list


@app.get("/all_albums", response_model=Dict[str, str])
async def all_albums():
    albums = {"all": "全部"}
    for file in os.listdir(album_path):
        if file.lower().endswith(".json") and os.path.isfile(os.path.join(album_path, file)):
            # 提取album编号（去掉.json后缀）
            album_num = file[:-5]  # 去掉最后的.json
            
            # 读取album文件内容
            path = os.path.join(album_path, file)
            with open(path, "r", encoding="utf-8") as f:
                album_data = json.load(f)
            try:
                # 提取album名称
                if isinstance(album_data, dict) and "name" in album_data:
                    album_name = album_data["name"]
                else:
                    # 对于旧格式的album文件，使用默认名称
                    album_name = "未命名专辑"
            except json.JSONDecodeError:
                album_name = "无效的专辑文件"
            
            # 以num为键，name为值
            albums[album_num] = album_name
    return albums

def get_song(songList):
    song_list=[]
    for song in songList:
        if os.path.isdir(f"{music_path}/{song}"):
            try:
                info = get_music_info(song)
                song_list.append(
                    {"num": song, "name": info["song_name"], "musician": info["composer"]})
            except HTTPException as e:
                raise e
    return song_list

@app.get("/album/{num}", response_model=Dict[str, object])
async def get_album(num: str):
    if num == "all":
        return {
            "name": "全部",
            "songs": get_song(os.listdir(music_path))
        }
    path = os.path.join(album_path, f"{num}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="专辑未找到")
    with open(path, "r", encoding="utf-8") as file:
        album = json.load(file)
    album["songs"] = get_song(album.get("songs", []))
    return album

@app.post("/modify_album/{num}", response_model=Dict[str, str])
async def modify_album(num: str, album: dict):
    name = album["name"]
    songs = album["songs"]

    path = os.path.join(album_path, f"{num}.json")
    
    # 检查专辑是否存在
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="专辑不存在")
    
    # 检查所有歌曲是否存在
    for song_num in songs:
        if not os.path.isdir(os.path.join(music_path, song_num)):
            raise HTTPException(status_code=404, detail=f"歌曲 {song_num} 不存在")
    
    # 更新专辑文件
    with open(path, "w", encoding="utf-8") as file:
        json.dump({"name": name, "songs": songs}, file, ensure_ascii=False, indent=4)
    
    return {"message": "SUCCESS", "num": num}

@app.get("/create_album/{album_name}", response_model=Dict[str, str])
async def create_album(album_name: str):
    new_album_num = str(uuid.uuid4())[:8]  # 使用UUID的前8个字符作为编号
    
    # 检查是否有重复的编号
    while os.path.exists(os.path.join(album_path, f"{new_album_num}.json")):
        new_album_num = str(uuid.uuid4())[:8]

    # 创建album文件
    path = os.path.join(album_path, f"{new_album_num}.json")
    with open(path, "w", encoding="utf-8") as file:
        # 存储专辑名称和歌曲列表
        album_data = {
            "name": album_name,
            "songs": []
        }
        json.dump(album_data, file, ensure_ascii=False, indent=4)
    
    return {
        "message": "SUCCESS", 
        "num": new_album_num, 
        "name": album_name
    }

@app.get("/delete_album/{num}", response_model=Dict[str, str])
async def delete_album(num: str):
    # 构建专辑文件路径
    path = os.path.join(album_path, f"{num}.json")
    
    # 检查专辑是否存在
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="专辑不存在")
    
    # 删除专辑文件
    try:
        os.remove(path)
        return {"message": "SUCCESS", "num": num}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除专辑时出错: {str(e)}")

@app.post("/add_music")
async def add_music(
        music_file: UploadFile = File(...),
        image_file: UploadFile = File(...),
        song_name: str = Form(...),
        composer: str = Form(...)
):
    """传统方式添加音乐文件，包含音量均衡处理"""
    # 为新歌曲创建唯一标识符
    new_song_num = uuid.uuid4()  # str(len(os.listdir(music_path)) + 1)

    # 为歌曲创建新文件夹
    new_song_folder = f"{music_path}/{new_song_num}"
    
    # 保存音乐文件到临时位置
    temp_file = f"temp_{uuid.uuid4()}_{music_file.filename}"
    try:
        with open(temp_file, "wb") as file:
            file.write(music_file.file.read())
            
        # 创建目标文件夹
        os.makedirs(new_song_folder, exist_ok=True)
        
        # 临时原始文件路径
        yuan = new_song_folder + "/original_" + music_file.filename
        # 最终音乐文件路径
        original_music_path = f"{new_song_folder}/music.mp3"
        
        # 复制临时文件到原始文件位置
        with open(yuan, "wb") as dest_file:
            with open(temp_file, "rb") as src_file:
                dest_file.write(src_file.read())
        
        # 调用 ffmpeg 尝试解码并转换上传的音频文件，添加音量均衡处理
        # 使用loudnorm滤镜实现音量均衡，目标响度为-16 LUFS
        cmd = [
            "ffmpeg", "-i", yuan, "-af", 
            "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=summary", 
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", 
            original_music_path
        ]
        # 执行命令
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 保存图像文件
        image_path = f"{new_song_folder}/music.png"
        try:
            # 尝试打开上传的图片文件
            img = Image.open(image_file.file)
            # 转换为png格式
            img.save(image_path, "PNG")
        except Exception as e:
            # 如果图像处理失败，清理已创建的文件夹和文件
            if os.path.exists(new_song_folder):
                for file_name in os.listdir(new_song_folder):
                    file_path = os.path.join(new_song_folder, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(new_song_folder)
            raise HTTPException(status_code=400, detail=f"无法处理图像文件: {str(e)}")

        # 保存歌曲信息
        with open(f"{new_song_folder}/music.txt", "w", encoding="utf-8") as file:
            file.write(f"{composer}\n{song_name}")
            
        # 处理完成后删除临时原始文件
        if os.path.exists(yuan):
            os.remove(yuan)
            
        return {"num": new_song_num}
        
    except subprocess.CalledProcessError as e:
        # 如果 ffmpeg 返回非零退出码，表示命令执行失败
        # 获取错误信息
        error_info = e.stderr.decode("utf-8").strip()
        # 清理已创建的文件夹和文件
        if os.path.exists(new_song_folder):
            for file_name in os.listdir(new_song_folder):
                file_path = os.path.join(new_song_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(new_song_folder)
        # 根据错误信息判断是否是无法解码的情况
        raise HTTPException(status_code=500, detail=f"处理音频文件时出错: {error_info}")
    except FileNotFoundError:
        # 如果 ffmpeg 命令未找到
        # 清理已创建的文件夹和文件
        if os.path.exists(new_song_folder):
            for file_name in os.listdir(new_song_folder):
                file_path = os.path.join(new_song_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(new_song_folder)
        raise HTTPException(status_code=500, detail="系统未安装 ffmpeg 或音频传输异常")
    except Exception as e:
        # 处理其他异常
        # 清理已创建的文件夹和文件
        if os.path.exists(new_song_folder):
            for file_name in os.listdir(new_song_folder):
                file_path = os.path.join(new_song_folder, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(new_song_folder)
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")
    finally:
        # 确保临时文件被删除
        if os.path.exists(temp_file):
            os.remove(temp_file)


@app.post("/parse_content")
async def parse_content(url: str = Form(...)):
    """解析URL内容但不保存，返回解析结果供前端显示"""
    try:
        # 使用内容解析模块解析URL，但不下载和保存文件
        from content_parser import parse_url_info
        result = parse_url_info(url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add_content_by_url")
async def add_content_by_url(url: str = Form(...), song_name: str = Form(None), composer: str = Form(None)):
    """通过URL添加Bilibili内容，可选择性地覆盖解析出的标题和作者"""
    try:
        # 使用内容解析模块处理URL
        result = process_content(url, music_path, override_title=song_name, override_author=composer)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @app.put("/update_music/{num}")
# async def update_music_info(
#         num: str,
#         music_file: UploadFile = File(...),
#         image_file: UploadFile = File(...),
#         song_name: str = Form(...),
#         composer: str = Form(...),
# ):
#     try:
#         # 获取现有音乐信息
#         existing_info = get_music_info(num)
#
#         # 删除旧的音乐文件
#         old_music_path = existing_info["music_file"]
#         if os.path.exists(old_music_path):
#             os.remove(old_music_path)
#
#         # 删除旧的图像文件
#         old_image_path = existing_info["image_file"]
#         if os.path.exists(old_image_path):
#             os.remove(old_image_path)
#
#         # 更新音乐文件
#         music_path = f"{existing_info['music_folder']}/music.wav"
#         try:
#             audio = AudioSegment.from_file(music_file.file)
#             audio.export(music_path, format="wav")
#         except CouldntDecodeError:
#             raise HTTPException(status_code=400, detail="无法解码音频文件")
#
#         # 更新图像文件
#         image_path = f"{existing_info['music_folder']}/{image_file.filename}"
#         try:
#             img = Image.open(image_file.file)
#             img.save(image_path, "PNG")
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"无法处理图像文件: {str(e)}")
#
#         # 更新歌曲信息
#         with open(f"{existing_info['music_folder']}/music.txt", "w", encoding="utf-8") as file:
#             file.write(f"{composer}\n{song_name}")
#
#         return {"num": num, "message": "音乐信息已成功更新"}
#
#     except HTTPException as e:
#         raise e


if __name__ == "__main__":
    uvicorn.run(app="server:app", host="127.0.0.1", port=88, reload=True)
    # uvicorn.run(app="server:app", host="192.168.31.104", port=88, reload=True)
