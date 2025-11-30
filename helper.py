import logging
import subprocess
import datetime
import asyncio
import os
import requests
import time
import json
from p_bar import progress_bar
import aiohttp
import tgcrypto
import aiofiles
from pyrogram.types import Message
from pyrogram import Client, filters

async def generate_thumbnail(filename, width=1280, height=720, time="0.0"):
    try:
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")

        subprocess.run(
            [
                "ffmpeg",
                "-ss",
                time,
                "-i",
                filename,
                "-vframes",
                "1",
                "-s",
                f"{width}x{height}",
                f"{filename}.jpg",
            ],
            check=True,
        )
        return f"{filename}.jpg"
    except subprocess.CalledProcessError as e:
        return None

def get_video_duration(filename, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                filename
            ]

            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            duration_str = result.stdout.strip()
            
            if duration_str:
                try:
                    duration = float(duration_str)
                    return int(duration)
                except (ValueError, TypeError):
                    print(f"Attempt {attempt+1}: Invalid duration format: {duration_str}")
                    continue
                    
            print(f"Attempt {attempt+1}: Duration not found. Retrying...")
            continue
            
        except Exception as e:
            print(f"Attempt {attempt+1}: An unexpected error occurred: {e}. Retrying...")

    print(f"Failed to get duration after {max_attempts} attempts. Returning 0")
    return 0

def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    try:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    except:
        return "00:00"

async def download(url, name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

def old_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"

async def download_video(url, name, raw_text2):
    try:
        output_file = f"{name}.mp4"
        
        command = [
            "yt-dlp",
            "-k", 
            "--allow-unplayable-formats", 
            "--geo-bypass",
            "--cookies", "cookies.txt",
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            "-S", f"res~{raw_text2},+size,+br",
            "--fixup", "never",
            url,
            "--external-downloader", "aria2c",
            "--external-downloader-args", "-x 16 -s 16 -k 1M", 
            "--output", output_file,
            "--merge-output-format", "mp4",
        ]
            
        result = subprocess.run(command, check=True, text=True, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            print(f"Successfully downloaded: {output_file}")
                                
            if os.path.isfile(output_file):
                return output_file

        else:
            print(f"yt-dlp command failed: {result.stderr.strip()}")
            return None

    except FileNotFoundError as exc:
        print(f"File not found: {exc}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr.strip()}")
        return None
        
async def send_vid(bot: Client, m: Message, cc, filename, name, thumb):
    reply = await m.reply_text(f"**UPLOADING » {name}**")

    # Use the provided thumbnail
    thumbnail = thumb

    # Get duration and format it
    duration_seconds = get_video_duration(filename)
    duration_formatted = format_duration(duration_seconds)
    
    # Get file size
    file_size = os.path.getsize(filename)
    size_mb = file_size / (1024 * 1024)
    
    # Modified caption with duration and size
    modified_caption = f"{cc}\n\n⏰ **Duration:** {duration_formatted}\n💾 **Size:** {size_mb:.1f} MB"

    start_time = time.time()

    try:        
        await m.reply_video(
            video=filename, 
            caption=modified_caption, 
            supports_streaming=True, 
            height=720, 
            width=1280, 
            thumb=thumbnail, 
            duration=duration_seconds, 
            progress=progress_bar, 
            progress_args=(reply, start_time)
        )
                
    except Exception as e:
        await m.reply_text(f"Upload error: {str(e)}")
                
    # Cleanup
    if os.path.exists(filename):
        os.remove(filename)
    if thumbnail and os.path.exists(thumbnail) and thumbnail != "No":
        os.remove(thumbnail)
    
    await reply.delete(True)
