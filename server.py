from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import os
from typing import List, Dict
from PIL import Image
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

app = FastAPI()

# 挂载静态文件目录（包含index.html、music和images文件夹）
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

def get_music_info(num):
    pic_valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webm', '.jfif']
    music_valid_extensions = ['.wav', '.mp3']

    music_folder = f"music/{num}"
    if not os.path.exists(music_folder):
        raise HTTPException(status_code=404, detail="歌曲未找到")

    with open(f"{music_folder}/music.txt", "r", encoding="utf-8") as file:
        composer = file.readline().strip()
        song_name = file.readline().strip()

    return {
        "composer": composer,
        "song_name": song_name,
        "music_file": music_folder + "/" + [file for file in os.listdir(music_folder) if
                                           os.path.isfile(os.path.join(music_folder, file)) and any(
                                               file.lower().endswith(ext) for ext in music_valid_extensions)and "music" in file][0],
        "image_file": music_folder + "/" + [file for file in os.listdir(music_folder) if
                                           os.path.isfile(os.path.join(music_folder, file)) and any(
                                               file.lower().endswith(ext) for ext in pic_valid_extensions)and "music" in file][0],
    }


@app.get("/", response_class=HTMLResponse)
async def get_index():
    return FileResponse("static/index.html")

@app.get("/up", response_class=HTMLResponse)
async def get_index():
    return FileResponse("static/add.html")

@app.get("/list/", response_model=List[Dict[str, str]])
async def get_song_list():
    song_list = [
        {"name": await get_song_name(folder), "num": folder}
        for folder in os.listdir("music")
        if os.path.isdir(f"music/{folder}")
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


@app.post("/add_music")
async def add_music(
        music_file: UploadFile = File(...),
        image_file: UploadFile = File(...),
        song_name: str = Form(...),
        composer: str = Form(...)
):
    # 为新歌曲创建唯一标识符
    new_song_num = str(len(os.listdir("music")) + 1)

    # 为歌曲创建新文件夹
    new_song_folder = f"music/{new_song_num}"
    os.makedirs(new_song_folder, exist_ok=True)

    # 保存音乐文件
    yuan=new_song_folder+"/yuan_"+music_file.filename
    with open(yuan, "wb") as file:
        file.write(music_file.file.read())
    music_path = f"{new_song_folder}/music.wav"
    try:
        # 尝试解码上传的音频文件
        audio_streams = AudioSegment.from_file(yuan)
        if not audio_streams:
            raise HTTPException(status_code=400, detail="音频文件不包含有效的音频流")
        # 转换为wav格式
        audio_streams.export(music_path, format="wav")
    except CouldntDecodeError:
        raise HTTPException(status_code=400, detail="无法解码音频文件")

    # 保存图像文件
    image_path = f"{new_song_folder}/music.png"
    try:
        # 尝试打开上传的图片文件
        img = Image.open(image_file.file)
        # 转换为png格式
        img.save(image_path, "PNG")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法处理图像文件: {str(e)}")

    # 保存歌曲信息
    with open(f"{new_song_folder}/music.txt", "w", encoding="utf-8") as file:
        file.write(f"{composer}\n{song_name}")

    return {"num": new_song_num}

@app.put("/update_music/{num}")
async def update_music_info(
    num: str,
    music_file: UploadFile = File(...),
    image_file: UploadFile = File(...),
    song_name: str = Form(...),
    composer: str = Form(...),
):
    try:
        # 获取现有音乐信息
        existing_info = get_music_info(num)

        # 删除旧的音乐文件
        old_music_path = existing_info["music_file"]
        if os.path.exists(old_music_path):
            os.remove(old_music_path)

        # 删除旧的图像文件
        old_image_path = existing_info["image_file"]
        if os.path.exists(old_image_path):
            os.remove(old_image_path)

        # 更新音乐文件
        music_path = f"{existing_info['music_folder']}/music.wav"
        try:
            audio = AudioSegment.from_file(music_file.file)
            audio.export(music_path, format="wav")
        except CouldntDecodeError:
            raise HTTPException(status_code=400, detail="无法解码音频文件")

        # 更新图像文件
        image_path = f"{existing_info['music_folder']}/{image_file.filename}"
        try:
            img = Image.open(image_file.file)
            img.save(image_path, "PNG")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法处理图像文件: {str(e)}")

        # 更新歌曲信息
        with open(f"{existing_info['music_folder']}/music.txt", "w", encoding="utf-8") as file:
            file.write(f"{composer}\n{song_name}")

        return {"num": num, "message": "音乐信息已成功更新"}

    except HTTPException as e:
        raise e