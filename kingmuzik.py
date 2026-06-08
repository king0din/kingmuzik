import asyncio, logging, os, platform, random, re, socket
import aiohttp
import sys, time, textwrap, json
from os import getenv
from io import BytesIO
from time import strftime
from functools import partial
from dotenv import load_dotenv
from datetime import datetime
from typing import Union, List, Pattern
from logging.handlers import RotatingFileHandler

from pyrogram import Client, filters as pyrofl
from pytgcalls import PyTgCalls, filters as pytgfl
from pyrogram import idle, __version__ as pyro_version
from pytgcalls.__version__ import __version__ as pytgcalls_version

from ntgcalls import TelegramServerError
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    InviteRequestSent,
    UserAlreadyParticipant,
    UserNotParticipant,
    PeerIdInvalid,
    ChatForbidden,
    ChannelPrivate,
)
from pytgcalls.exceptions import NoActiveGroupCall
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPrivileges
from pytgcalls.types import ChatUpdate, Update, GroupCallConfig
from pytgcalls.types import Call, MediaStream, AudioQuality, VideoQuality

from PIL import Image, ImageDraw, ImageEnhance
from PIL import ImageFilter, ImageFont, Image, ImageOps
from youtubesearchpython.__future__ import VideosSearch
import numpy as np
import psutil  # RAM ve CPU kullanımı için

loop = asyncio.get_event_loop()

__version__ = {
    "ᴀᴘ": "1.0.0 Mini",
    "ᴘʏᴛʜᴏɴ": platform.python_version(),
    "ᴘʏʀᴏɢʀᴀᴍ": pyro_version,
    "ᴘʏᴛɢᴄᴀʟʟꜱ": pytgcalls_version,
}

logging.basicConfig(
    format="[%(name)s]:: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
    handlers=[
        RotatingFileHandler("logs.txt", maxBytes=(1024 * 1024 * 5), backupCount=10),
        logging.StreamHandler(),
    ],
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)

LOGGER = logging.getLogger("Sistem")

if os.path.exists(".env"):
    load_dotenv(".env")

# Telegram API bilgileri
API_ID = int(getenv("API_ID", ""))
API_HASH = getenv("API_HASH", "")
BOT_TOKEN = getenv("BOT_TOKEN", "")
STRING_SESSION = getenv("STRING_SESSION", "")
OWNER_ID = int(getenv("OWNER_ID", "1897795912"))
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", ""))

# Varsayılan resim URL
START_IMAGE_URL = "https://i.imgur.com/lOP9gt7.png"

# Bot adı
BOT_NAME = "King Muzik"  # Türkçe karakter sorununu önlemek için örneğin 'ü' yu 'u' yap
OWNER_USERNAME = "KingOdi"  # Sahip kullanıcı adı

# Dosya tabanlı veritabanı yolları
DB_PATH = "database"
os.makedirs(DB_PATH, exist_ok=True)
SERVED_CHATS_FILE = f"{DB_PATH}/served_chats.json"
SERVED_USERS_FILE = f"{DB_PATH}/served_users.json"
BANNED_CHATS_FILE = f"{DB_PATH}/banned_chats.json"

# Memory Database
ACTIVE_AUDIO_CHATS = []
ACTIVE_VIDEO_CHATS = []
ACTIVE_MEDIA_CHATS = []
BANNED_CHATS = set()  # Yasaklı grupları saklamak için

QUEUE = {}
PLAYER_MESSAGES = {}  # Oynatıcı mesajları için
STREAM_TIMES = {}     # Şarkı başlangıç zamanları için

# Komut filtreleri
def cdz(commands: Union[str, List[str]]):
    return pyrofl.command(commands, ["", "/", "!", "."]) & ~pyrofl.chat(list(BANNED_CHATS))

def rgx(pattern: Union[str, Pattern]):
    return pyrofl.regex(pattern)

# Bot sahibi kontrol
bot_owner_only = pyrofl.user(OWNER_ID)

# Yasaklı grup kontrolü

app = Client(
    name="App",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=STRING_SESSION,
)

bot = Client(
    name="Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

call = PyTgCalls(app)
call_config = GroupCallConfig(auto_start=False)


__start_time__ = time.time()

# Dosya tabanlı veritabanı işlevleri
def load_json(file_path):
    """JSON dosyasını yükle"""
    if not os.path.exists(file_path):
        return {}  # Dosya yoksa boş sözlük döndür
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        LOGGER.error(f"JSON dosyası yüklenirken hata oluştu: {file_path}")
        return {}

def save_json(file_path, data):
    """Veriyi JSON dosyasına kaydet"""
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Yasaklı grup işlevleri
async def load_banned_chats():
    """Dosyadan yasaklı grupları yükle"""
    data = load_json(BANNED_CHATS_FILE)
    banned_chat_ids = data.get("banned_chats", [])
    BANNED_CHATS.update(banned_chat_ids)
    LOGGER.info(f"Toplam {len(BANNED_CHATS)} yasaklı grup yüklendi.")

async def add_banned_chat(chat_id: int):
    """Bir grubu yasaklı gruplara ekle"""
    if chat_id in BANNED_CHATS:
        return

    BANNED_CHATS.add(chat_id)
    data = load_json(BANNED_CHATS_FILE)
    banned_chats = data.get("banned_chats", [])
    if chat_id not in banned_chats:
        banned_chats.append(chat_id)
        data["banned_chats"] = banned_chats
        save_json(BANNED_CHATS_FILE, data)

async def remove_banned_chat(chat_id: int):
    """Bir grubu yasaklı gruplardan çıkar"""
    if chat_id in BANNED_CHATS:
        BANNED_CHATS.remove(chat_id)
    
    data = load_json(BANNED_CHATS_FILE)
    banned_chats = data.get("banned_chats", [])
    if chat_id in banned_chats:
        banned_chats.remove(chat_id)
        data["banned_chats"] = banned_chats
        save_json(BANNED_CHATS_FILE, data)
        
    if chat_id in ACTIVE_MEDIA_CHATS:
        await close_stream(chat_id)

# Servis edilen sohbetler
async def is_served_chat(chat_id: int) -> bool:
    data = load_json(SERVED_CHATS_FILE)
    served_chats = data.get("served_chats", [])
    return chat_id in served_chats

async def get_served_chats() -> list:
    data = load_json(SERVED_CHATS_FILE)
    return data.get("served_chats", [])

async def add_served_chat(chat_id: int):
    is_served = await is_served_chat(chat_id)
    if is_served:
        return
    
    data = load_json(SERVED_CHATS_FILE)
    served_chats = data.get("served_chats", [])
    if chat_id not in served_chats:
        served_chats.append(chat_id)
        data["served_chats"] = served_chats
        save_json(SERVED_CHATS_FILE, data)

# Servis edilen kullanıcılar
async def is_served_user(user_id: int) -> bool:
    data = load_json(SERVED_USERS_FILE)
    served_users = data.get("served_users", [])
    return user_id in served_users

async def get_served_users() -> list:
    data = load_json(SERVED_USERS_FILE)
    return data.get("served_users", [])

async def add_served_user(user_id: int):
    is_served = await is_served_user(user_id)
    if is_served:
        return
    
    data = load_json(SERVED_USERS_FILE)
    served_users = data.get("served_users", [])
    if user_id not in served_users:
        served_users.append(user_id)
        data["served_users"] = served_users
        save_json(SERVED_USERS_FILE, data)

# Ping ölçüm fonksiyonu
async def measure_ping():
    start = time.time()
    try:
        msg = await bot.send_message(LOG_GROUP_ID, ".")
        await msg.delete()
        end = time.time()
        ping_time = (end - start) * 1000  # milisaniye cinsinden
        return round(ping_time, 2)
    except Exception as e:
        LOGGER.error(f"Ping ölçüm hatası: {e}")
        return 0

# Cache dizinini oluştur
os.makedirs("cache", exist_ok=True)

# Varsayılan resim olarak kullanacağımız bir logo oluştur
def create_default_thumbnail():
    try:
        image = Image.new("RGB", (800, 600), color=(18, 19, 35))
        draw = ImageDraw.Draw(image)
        draw.text((400, 300), f"{BOT_NAME}", fill=(255, 255, 255))
        output_path = f"cache/default_thumbnail.png"
        image.save(output_path)
        return output_path
    except Exception as e:
        LOGGER.error(f"Varsayılan thumbnail oluşturma hatası: {e}")
        return None

DEFAULT_THUMBNAIL = create_default_thumbnail()

# Botu başlat
async def main():
    LOGGER.info("🐬 Dizinler güncelleniyor ...")
    if "cache" not in os.listdir():
        os.mkdir("cache")
    if "cookies.txt" not in os.listdir():
        LOGGER.info("⚠️ 'cookies.txt' - Bulunamadı❗")
        with open("cookies.txt", "w") as f:
            f.write("")  # Boş bir cookies.txt dosyası oluştur
        LOGGER.info("✅ 'cookies.txt' - Oluşturuldu")
    if "downloads" not in os.listdir():
        os.mkdir("downloads")
    for file in os.listdir():
        if file.endswith(".session"):
            os.remove(file)
    for file in os.listdir():
        if file.endswith(".session-journal"):
            os.remove(file)
    LOGGER.info("Tüm dizinler güncellendi.")
    
    # JSON dosyalarını oluştur
    if not os.path.exists(SERVED_CHATS_FILE):
        save_json(SERVED_CHATS_FILE, {"served_chats": []})
    if not os.path.exists(SERVED_USERS_FILE):
        save_json(SERVED_USERS_FILE, {"served_users": []})
    if not os.path.exists(BANNED_CHATS_FILE):
        save_json(BANNED_CHATS_FILE, {"banned_chats": []})
    
    # Yasaklı grupları yükle
    await load_banned_chats()
    
    await asyncio.sleep(1)
    LOGGER.info("Gerekli değişkenler kontrol ediliyor . ..")
    if API_ID == 0:
        LOGGER.info("❌ 'API_ID' - Bulunamadı❗")
        sys.exit()
    if not API_HASH:
        LOGGER.info("❌ 'API_HASH' - Bulunamadı❗")
        sys.exit()
    if not BOT_TOKEN:
        LOGGER.info("❌ 'BOT_TOKEN' - Bulunamadı❗")
        sys.exit()
    if not STRING_SESSION:
        LOGGER.info("❌ 'STRING_SESSION' - Bulunamadı❗")
        sys.exit()
    
    LOGGER.info("✅ Gerekli değişkenler toplandı.")
    await asyncio.sleep(1)
    LOGGER.info("🌀 Tüm istemciler başlatılıyor. ...")
    try:
        await bot.start()
    except Exception as e:
        LOGGER.info(f"🚫 Bot Hatası: {e}")
        sys.exit()
    if LOG_GROUP_ID != 0:
        try:
            await bot.send_message(LOG_GROUP_ID, f"🤖 {BOT_NAME} başlatıldı.")
        except Exception as e:
            LOGGER.info(f"Log grubuna mesaj gönderilemedi: {e}")
            pass
    LOGGER.info(f"✅ {BOT_NAME} başlatıldı.")
    try:
        await app.start()
    except Exception as e:
        LOGGER.info(f"🚫 Asistan Hatası: {e}")
        sys.exit()
    try:
        await app.join_chat("kingduyurular")
        await app.join_chat("kingduyurular")
    except Exception:
        pass
    if LOG_GROUP_ID != 0:
        try:
            await app.send_message(LOG_GROUP_ID, "🦋 Asistan Başladı...")
        except Exception:
            pass
    LOGGER.info("Asistan Başladı.")
    try:
        await call.start()
    except Exception as e:
        LOGGER.info(f"🚫 Pytgcalls Hatası: {e}")
        sys.exit()
    LOGGER.info("Pytgcalls Başladı..")
    await asyncio.sleep(1)
    LOGGER.info(f"{BOT_NAME} başarıyla kuruldu! !!")
    LOGGER.info("@kingduyurular ziyaret edin.")
    
    # İlerleme çubuğu güncelleme döngüsünü başlat
    asyncio.create_task(update_player_loop())
    
    await idle()

# Thumbnail indirme işlevi - URL kontrolleri eklendi
async def download_thumbnail(vidid: str):
    async with aiohttp.ClientSession() as session:
        links = [
            f"https://i.ytimg.com/vi/{vidid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{vidid}/sddefault.jpg",
            f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg",
        ]
        thumbnail = f"cache/temp_{vidid}.png"
        for url in links:
            try:
                # URL kontrolü
                if not url or url.strip() == "":
                    continue
                    
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    else:
                        with open(thumbnail, "wb") as f:
                            f.write(await resp.read())
                        return thumbnail
            except Exception as e:
                LOGGER.info(f"Thumbnail indirme hatası: {e}")
                continue
        return DEFAULT_THUMBNAIL

# Kullanıcı logo indirme - Hata yönetimi
async def get_user_logo(user_id):
    try:
        user_chat = await bot.get_chat(user_id)
        if user_chat and user_chat.photo and user_chat.photo.big_file_id:
            user_logo = await bot.download_media(user_chat.photo.big_file_id, f"cache/{user_id}.png")
            return user_logo
    except Exception as e:
        LOGGER.info(f"Kullanıcı logo indirme hatası: {e}")
    
    try:
        bot_chat = await bot.get_me()
        if bot_chat and bot_chat.photo and bot_chat.photo.big_file_id:
            bot_logo = await bot.download_media(bot_chat.photo.big_file_id, f"cache/{bot.id}.png")
            return bot_logo
    except Exception as e:
        LOGGER.info(f"Bot logo indirme hatası: {e}")
    
    # Varsayılan logo oluştur
    try:
        default_logo = Image.new("RGB", (128, 128), color=(18, 19, 35))
        default_logo_path = f"cache/default_logo_{user_id}.png"
        default_logo.save(default_logo_path)
        return default_logo_path
    except Exception as e:
        LOGGER.info(f"Varsayılan logo oluşturma hatası: {e}")
        return None

async def fetch_and_save_image(url, save_path):
    # URL kontrolü
    if not url or url.strip() == "":
        return None
        
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    try:
                        # Dosyayı normal open ile kaydet
                        with open(save_path, "wb") as file:
                            file.write(await resp.read())
                        return save_path
                    except Exception as e:
                        LOGGER.error(f"Dosya kaydetme hatası: {e}")
                        return None
        except Exception as e:
            LOGGER.error(f"Resim indirme hatası: {e}")
    return None

# Asistanın yönetici olup olmadığını kontrol eden fonksiyon
async def is_assistant_admin(chat_id):
    try:
        member = await app.get_chat_member(chat_id, app.me.id)
        # Yönetici mi kontrol et
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            # Gerekli izinlere sahip mi baksın
            return (
                hasattr(member, "privileges") and 
                (member.privileges.can_manage_video_chats or 
                 member.privileges.can_invite_users)
            )
        else:
            return False
    except Exception as e:
        LOGGER.error(f"Admin kontrolü sırasında hata: {str(e)}")
        return False

# Asistanı gruba ekle ve yönetici yapma
async def add_assistant_to_chat(chat_id, message=None):
    # 1. Önce asistanın grupta olup olmadığını kontrol et
    try:
        # Eğer bot asistanın gruba üye olup olmadığını kontrol edemiyorsa, 
        # app client'ını kullanarak kontrol etmeyi dene
        try:
            is_member = False
            try:
                # Direkt olarak app client ile kontrol et
                chat_member = await app.get_chat_member(chat_id, app.me.id)
                is_member = True
            except UserNotParticipant:
                is_member = False
            except Exception as e:
                LOGGER.error(f"Asistan üyelik kontrolü hatası 1: {str(e)}")
                is_member = False
            
            # Eğer üye değilse, gruba katılmayı dene
            if not is_member:
                # 2. Gruba katılmayı dene
                success = await invite_assistant(chat_id, message)
                if not success:
                    if message:
                        await message.reply_text("**❌ Asistan gruba eklenemedi.** Lütfen asistanı manuel olarak ekleyin.")
                    return False
            
            # 3. Şimdi asistanın admin olup olmadığını kontrol et
            is_admin = await is_assistant_admin(chat_id)
            if not is_admin:
                # 4. Admin değilse, admin yapmayı dene
                success = await promote_assistant(chat_id, message)
                if not success and message:
                    await message.reply_text("**⚠️ Asistan gruba eklendi ancak yönetici yapılamadı.** Lütfen manuel olarak yönetici yapın.")
            
            return True
            
        except Exception as e:
            LOGGER.error(f"Asistan üyelik kontrolü hatası 2: {str(e)}")
            if message:
                await message.reply_text(f"**⚠️ Asistan durumu kontrol edilirken hata oluştu:** `{str(e)}`\nLütfen asistanı manuel olarak ekleyin ve yönetici yapın.")
            return False
    except Exception as e:
        LOGGER.error(f"add_assistant_to_chat genel hata: {str(e)}")
        if message:
            await message.reply_text(f"**❌ Beklenmeyen hata:** `{str(e)}`\nLütfen asistanı manuel olarak ekleyin.")
        return False
    
    # Asistanı gruba davet et - Tamamen yeniden yazıldı
async def invite_assistant(chat_id, message=None):
    try:
        # 1. Önce grubun bilgilerini al
        chat = None
        try:
            chat = await bot.get_chat(chat_id)
        except Exception as e:
            LOGGER.error(f"Sohbet bilgileri alınırken hata: {str(e)}")
            if message:
                await message.reply_text(f"**❌ Grup bilgileri alınamadı:** `{str(e)}`")
            return False
        
        # 2. Eğer grup bir kullanıcı adına sahipse, o kullanıcı adıyla katılmayı dene
        if chat and chat.username:
            try:
                LOGGER.info(f"Kullanıcı adı ile gruba katılma deneniyor: @{chat.username}")
                await app.join_chat(f"@{chat.username}")
                await asyncio.sleep(2)  # Katılma işleminin tamamlanması için bekle
                if message:
                    await message.reply_text("✅ **Asistan hesabı gruba katıldı.**")
                return True
            except Exception as e:
                LOGGER.error(f"Kullanıcı adı ile katılma hatası: {str(e)}")
                # Başarısız olursa davet bağlantısı kullanmaya geç
        
        # 3. Davet bağlantısı oluştur ve kullan
        try:
            # Davet bağlantısı oluştur
            try:
                LOGGER.info("Davet bağlantısı oluşturuluyor...")
                invite_link = await bot.export_chat_invite_link(chat_id)
                LOGGER.info(f"Oluşturulan davet bağlantısı: {invite_link}")
            except Exception as e:
                LOGGER.error(f"Davet bağlantısı oluşturma hatası: {str(e)}")
                if message:
                    await message.reply_text(f"**❌ Davet bağlantısı oluşturulamadı:** `{str(e)}`\nLütfen botu yönetici yapın ve 'Kullanıcı Ekleme' iznini verin.")
                return False
                
            # Davet bağlantısı kullanarak gruba katıl
            try:
                LOGGER.info(f"Asistan davet bağlantısı ile gruba katılmaya çalışıyor: {invite_link}")
                await app.join_chat(invite_link)
                await asyncio.sleep(2)  # Katılma işleminin tamamlanması için bekle
                
                # Bağlantıyı kullandıktan sonra iptal et
                try:
                    await bot.revoke_chat_invite_link(chat_id, invite_link)
                except:
                    pass  # Hatayı yok say
                
                if message:
                    await message.reply_text("✅ **Asistan hesabı davet bağlantısı ile gruba katıldı.**")
                return True
            except Exception as e:
                LOGGER.error(f"Davet bağlantısı ile katılma hatası: {str(e)}")
                if message:
                    await message.reply_text(f"**❌ Asistan gruba katılamadı:** `{str(e)}`\nLütfen bota ful yt verip tekrar deneyin.")
                return False
                
        except Exception as e:
            LOGGER.error(f"Davet bağlantısı genel hata: {str(e)}")
            if message:
                await message.reply_text(f"**❌ Davet işlemi sırasında hata:** `{str(e)}`\nLütfen bota ful yt verip tekrar deneyin.")
            return False
    except Exception as e:
        LOGGER.error(f"Asistan davet etme genel hatası: {str(e)}")
        if message:
            await message.reply_text(f"**❌ Asistan davet edilirken hata oluştu:** `{str(e)}`\nLütfen bota ful yt verip tekrar deneyin.")
        return False

# Asistanı yönetici yap
async def promote_assistant(chat_id, message=None):
    try:
        # 1. Bot'un yönetici yapma yetkisi var mı kontrol et
        try:
            bot_member = await bot.get_chat_member(chat_id, bot.me.id)
            if not bot_member.privileges or not bot_member.privileges.can_promote_members:
                if message:
                    await message.reply_text("❌ **Bot'un yönetici atama yetkisi yok.**\nLütfen botu yönetici yapın ve 'Yönetici Atama' iznini verin.\nDaha çok stabillik ve otomotikleştirme için ful yetki verin")
                return False
        except Exception as e:
            LOGGER.error(f"Bot yetki kontrolü hatası: {str(e)}")
            return False
        
        # 2. Asistanın ID'sini al
        assistant_id = app.me.id
        LOGGER.info(f"Asistan ID: {assistant_id} yönetici yapılıyor...")
        
        # 3. Asistanı yönetici yap
        try:
            privileges = ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_invite_users=True
            )
            
            await bot.promote_chat_member(
                chat_id=chat_id,
                user_id=assistant_id,
                privileges=privileges
            )
            
            if message:
                await message.reply_text("✅ **Asistan hesabı gruba yönetici olarak eklendi.**")
            return True
        except Exception as e:
            LOGGER.error(f"Asistanı yönetici yapma hatası: {str(e)}")
            if message:
                await message.reply_text(f"❌ **Asistan yönetici yapılamadı:** `{str(e)}`\nLütfen asistanı manuel olarak yönetici yapın.")
            return False
    except Exception as e:
        LOGGER.error(f"Asistanı yönetici yapma genel hatası: {str(e)}")
        if message:
            await message.reply_text(f"**❌ Asistan yönetici yapma işlemi sırasında beklenmeyen hata:** `{str(e)}`")
        return False

# Grupları kontrol etmek ve katılmak için geliştirilmiş fonksiyon
async def check_and_join_chat(chat_id, message=None):
    try:
        # Asistan hesabını gruba ekle ve yönetici yap
        result = await add_assistant_to_chat(chat_id, message)
        return result
    except Exception as e:
        LOGGER.error(f"check_and_join_chat fonksiyonunda hata: {str(e)}")
        if message:
            await message.reply_text(f"❌ **Asistan kontrol edilirken hata:** `{str(e)}`")
        return False

# Video Chat başlatma işlevi - düzeltilmiş versiyon
async def create_group_video_chat(chat_id):
    try:
        # Önce gruba katıldığımızdan emin olalım
        await check_and_join_chat(chat_id)
        
        try:
            from pyrogram.raw.functions.phone import CreateGroupCall
            try:
                # PyTelegramApiServer versiyonuna göre parametreleri düzenliyoruz
                # start_date ve schedule_date parametre hatası için
                await app.invoke(
                    CreateGroupCall(
                        peer=await app.resolve_peer(chat_id),
                        random_id=random.randint(10000000, 999999999)
                    )
                )
                return True
            except Exception as e:
                LOGGER.error(f"Görüntülü sohbet başlatma hatası (invoke): {e}")
                try:
                    # create_video_chat methodu olmadığı için create_group_call kullanıyoruz
                    try:
                        await app.create_group_call(chat_id)
                    except AttributeError:
                        # Eski API kullanıyorsak
                        from pyrogram.raw.functions.channels import CreateChannelCall
                        await app.invoke(
                            CreateChannelCall(
                                channel=await app.resolve_peer(chat_id),
                                random_id=random.randint(10000000, 999999999)
                            )
                        )
                    return True
                except Exception as e:
                    LOGGER.error(f"Görüntülü sohbet başlatma hatası: {e}")
                    return False
        except Exception as e:
            LOGGER.error(f"Görüntülü sohbet başlatma modül hatası: {e}")
            return False
    except Exception as e:
        LOGGER.error(f"create_group_video_chat fonksiyonunda hata: {str(e)}")
        return False

# Yeni süre hesaplama fonksiyonu
async def get_duration_in_seconds(duration_str):
    if not duration_str or duration_str == "Canlı Yayın":
        return 0
        
    # "Dakika" kelimesini kaldır
    if "Dakika" in duration_str:
        duration_str = duration_str.replace(" Dakika", "")
    
    total_seconds = 0
    if ":" in duration_str:
        time_parts = duration_str.split(":")
        if len(time_parts) == 2:  # mm:ss
            total_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
        elif len(time_parts) == 3:  # hh:mm:ss
            total_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
        elif len(time_parts) == 4:  # dd:hh:mm:ss
            total_seconds = int(time_parts[0]) * 86400 + int(time_parts[1]) * 3600 + int(time_parts[2]) * 60 + int(time_parts[3])
            
    return total_seconds

# Görsel işleme fonksiyonları
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage

def circle_image(image, size):
    size = (size, size)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    output = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    return output

def random_color_generator():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return (r, g, b)

def resize_image(image, max_width, max_height):
    return image.resize((int(max_width), int(max_height)))

def circle_crop(image, size):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    
    output = ImageOps.fit(image, (size, size), centering=(0.5, 0.5))
    output.putalpha(mask)
    return output

def random_color():
    return tuple(random.randint(0, 255) for _ in range(3))

#Thumbnail Oluşturma Fonksiyonu
async def create_thumbnail(results, user_id):
    try:
        if not results:
            # Sonuç yoksa, varsayılan bir resim döndür
            return DEFAULT_THUMBNAIL
        
        vidid = results.get("id", "unknown")
        title = re.sub(r"\W+", " ", results.get("title", "Bilinmeyen")).title()
        # Türkçe karakterleri ASCII ile değiştir
        title = title.replace("ğ", "g").replace("Ğ", "G").replace("ü", "u").replace("Ü", "U").replace("ş", "s").replace("Ş", "S").replace("ı", "i").replace("İ", "I").replace("ö", "o").replace("Ö", "O").replace("ç", "c").replace("Ç", "C")
        
        # String olabilecek duration'ı kontrol etme
        duration_str = results.get("duration", "0")
        
        # Views değeri string ise int'e dönüştürme
        views_raw = results.get("views", 0)
        views = 0
        if isinstance(views_raw, int):
            views = views_raw
        elif isinstance(views_raw, str) and views_raw.isdigit():
            views = int(views_raw)
            
        channel = results.get("channel", "Unknown")
        thumbnail = results.get("thumbnail", START_IMAGE_URL)

        # Thumbnail indir
        image_path = await download_thumbnail(vidid)
        if not image_path:
            return DEFAULT_THUMBNAIL
        
        # Kullanıcı logosu indir
        logo_path = await get_user_logo(user_id)
        if not logo_path:
            # Varsayılan logo oluştur
            default_logo = Image.new("RGB", (128, 128), color=(18, 19, 35))
            logo_path = f"cache/default_logo_{user_id}.png"
            default_logo.save(logo_path)

        try:
            # Ana görsel işleme
            image_bg = resize_image(Image.open(image_path), 1280, 720)
            image_blurred = image_bg.filter(ImageFilter.GaussianBlur(15))
            image_blurred = ImageEnhance.Brightness(image_blurred).enhance(0.5)

            # Logo işleme
            try:
                image_logo = circle_crop(Image.open(logo_path), 90)
            except Exception as e:
                LOGGER.error(f"Logo işleme hatası: {e}")
                # Varsayılan logo oluştur
                default_logo = Image.new("RGB", (128, 128), color=(18, 19, 35))
                logo_path = f"cache/default_logo_{user_id}_2.png"
                default_logo.save(logo_path)
                image_logo = circle_crop(Image.open(logo_path), 90)

            # Kompozit oluşturma - Hata yönetimi eklenmiş
            try:
                image_blurred.paste(circle_crop(image_bg, 365), (140, 180), mask=circle_crop(image_bg, 365))
                image_blurred.paste(image_logo, (410, 450), mask=image_logo)
            except Exception as e:
                LOGGER.error(f"Kompozit oluşturma hatası: {e}")
                # Basit görsel oluştur
                image_blurred = Image.new("RGB", (1280, 720), color=(18, 19, 35))
            
            # Metin ekleme
            draw = ImageDraw.Draw(image_blurred)
            
            # Başlık 
            para = textwrap.wrap(title, width=28)
            title_pos = 230 if len(para) == 1 else 180

            for i, line in enumerate(para[:2]):
                draw.text((565, title_pos + i * 50), line, fill="white")
            
            # Kanal ve görüntülenme bilgisi 
            channel_views = f"{channel}  |  Views: {format_views(views)}"[:23]
            draw.text((565, 320), channel_views, fill="white")
            
            # İlerleme çubuğu
            line_length = 580
            line_color = random_color()

            if not "Canli" in str(duration_str) and not "Live" in str(duration_str):
                color_line_percentage = random.uniform(0.15, 0.85)
                color_line_length = int(line_length * color_line_percentage)
                draw.line([(565, 380), (565 + color_line_length, 380)], fill=line_color, width=9)
                draw.line([(565 + color_line_length, 380), (565 + line_length, 380)], fill="white", width=8)
                draw.ellipse([(565 + color_line_length - 10, 370), (565 + color_line_length + 10, 390)], fill=line_color)
            else:
                draw.line([(565, 380), (565 + line_length, 380)], fill=(255, 0, 0), width=9)
                draw.ellipse([(565 + line_length - 10, 370), (565 + line_length + 10, 390)], fill=(255, 0, 0))

            # Süre bilgisi
            draw.text((565, 400), "00:00", fill="white")
            # Pozisyon hesaplaması
            try:
                duration_pos_x = 1015 if len(str(duration_str)) == 8 else 1055 if len(str(duration_str)) == 5 else 1090
                draw.text((duration_pos_x, 400), str(duration_str), fill="white")
            except Exception as e:
                LOGGER.error(f"Süre pozisyonu hatası: {e}")
                draw.text((1090, 400), str(duration_str), fill="white")

            # Son dokunuşlar
            image_final = ImageOps.expand(image_blurred, border=10, fill=random_color())
            output_path = f"cache/{vidid}_{user_id}.png"
            image_final.save(output_path)

            return output_path
        except Exception as e:
            LOGGER.error(f"Thumbnail işleme hatası: {str(e)}")
            return thumbnail if thumbnail else DEFAULT_THUMBNAIL

    except Exception as e:
        LOGGER.error(f"Thumbnail oluşturma hatası: {str(e)}")
        try:
            # Basit varsayılan thumbnail
            image = Image.new("RGB", (1280, 720), color=(18, 19, 35))
            draw = ImageDraw.Draw(image)
            draw.text((640, 300), "Muzik", fill=(255, 255, 255))
            
            output_path = f"cache/error_{user_id}.png"
            image.save(output_path)
            return output_path
        except Exception as e:
            LOGGER.error(f"Varsayılan thumbnail oluşturma hatası: {str(e)}")
            return DEFAULT_THUMBNAIL

# Formatlama yardımcı fonksiyonları
def format_views(views: int) -> str:
    if not views:
        return "0"
    if views >= 1_000_000_000:
        return f"{views / 1_000_000_000:.1f}B"
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    if views >= 1_000:
        return f"{views / 1_000:.1f}K"
    return str(views)

def format_seconds(seconds):
    if seconds is None:
        return "N/A"
        
    # Eğer seconds bir string ise, int'e çevirmeye çalış
    if isinstance(seconds, str):
        try:
            if ":" in seconds:
                # Zaten formatted time olabilir
                return seconds
            seconds = int(seconds)
        except ValueError:
            return seconds  # Dönüştürülemezse olduğu gibi döndür
    
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
    except Exception as e:
        LOGGER.error(f"Format seconds hatası: {e}")
        return str(seconds)  # Hata durumunda string olarak döndür

# Gerekli bazı işlevler ...!!
def _netcat(host, port, content):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(content.encode())
    s.shutdown(socket.SHUT_WR)
    while True:
        data = s.recv(4096).decode("utf-8").strip("\n\x00")
        if not data:
            break
        return data
    s.close()

async def paste_queue(content):
    loop = asyncio.get_running_loop()
    link = await loop.run_in_executor(None, partial(_netcat, "ezup.dev", 9999, content))
    return link

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for i in range(len(time_list)):
        time_list[i] = str(time_list[i]) + time_suffix_list[i]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "
    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time

# VC Oyuncusu için işlevler
async def add_active_media_chat(chat_id, stream_type):
    if stream_type == "Ses":
        if chat_id in ACTIVE_VIDEO_CHATS:
            ACTIVE_VIDEO_CHATS.remove(chat_id)
        if chat_id not in ACTIVE_AUDIO_CHATS:
            ACTIVE_AUDIO_CHATS.append(chat_id)
    elif stream_type == "Video":
        if chat_id in ACTIVE_AUDIO_CHATS:
            ACTIVE_AUDIO_CHATS.remove(chat_id)
        if chat_id not in ACTIVE_VIDEO_CHATS:
            ACTIVE_VIDEO_CHATS.append(chat_id)
    if chat_id not in ACTIVE_MEDIA_CHATS:
        ACTIVE_MEDIA_CHATS.append(chat_id)

async def remove_active_media_chat(chat_id):
    if chat_id in ACTIVE_AUDIO_CHATS:
        ACTIVE_AUDIO_CHATS.remove(chat_id)
    if chat_id in ACTIVE_VIDEO_CHATS:
        ACTIVE_VIDEO_CHATS.remove(chat_id)
    if chat_id in ACTIVE_MEDIA_CHATS:
        ACTIVE_MEDIA_CHATS.remove(chat_id)

# VC Oynatıcı Sırası
async def add_to_queue(chat_id, user, title, duration, stream_file, stream_type, thumbnail):
    put = {
        "chat_id": chat_id,
        "user": user,
        "title": title,
        "duration": duration,
        "stream_file": stream_file,
        "stream_type": stream_type,
        "thumbnail": thumbnail,
        "mention": user.mention if hasattr(user, 'mention') else user.title
    }
    check = QUEUE.get(chat_id)
    if check:
        QUEUE[chat_id].append(put)
    else:
        QUEUE[chat_id] = []
        QUEUE[chat_id].append(put)

    return len(QUEUE[chat_id]) - 1

async def clear_queue(chat_id):
    check = QUEUE.get(chat_id)
    if check:
        QUEUE.pop(chat_id)
    await reset_player_message(chat_id)

# Stream kontrolleri
async def is_stream_off(chat_id: int) -> bool:
    active = ACTIVE_MEDIA_CHATS
    if chat_id not in active:
        return True
    try:
        call_status = await call.get_active_call(chat_id)
        if call_status.status == "paused":
            return True
        else:
            return False
    except Exception:
        return False

# Oynatıcı mesajını güncelleme fonksiyonu - Flood yönetimi eklendi
async def update_player_message(chat_id, force_update=False):
    try:
        if chat_id not in PLAYER_MESSAGES or chat_id not in STREAM_TIMES:
            return
            
        # Zaman bilgileri
        now = time.time()
        last_updated = STREAM_TIMES.get(chat_id, {}).get("last_update", 0)
        start_time = STREAM_TIMES.get(chat_id, {}).get("start_time", 0)
        
        # Flood wait sorunları için daha uzun bir güncelleme süresi (3 saniye yerine 10 saniye)
        if not force_update and (now - last_updated) < 10:
            return
            
        STREAM_TIMES[chat_id]["last_update"] = now
        
        if not QUEUE.get(chat_id):
            return
            
        current_track = QUEUE[chat_id][0]
        title = current_track.get("title", "").replace("[", "").replace("[", "").replace("]", "")
        duration_str = current_track.get("duration", "0")
        stream_type = current_track.get("stream_type", "Ses")
        mention = current_track.get("mention", "")
        thumbnail = current_track.get("thumbnail", DEFAULT_THUMBNAIL)

        # Süreyi saniyeye çevir
        total_seconds = 0
        if ":" in duration_str:
            parts = duration_str.split(":")
            if len(parts) == 2:  # MM:SS
                total_seconds = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif "Canlı" in duration_str:
            total_seconds = 0  # Canlı yayın
        
        elapsed_seconds = int(now - start_time)
        
        # Mesaj içeriğini oluştur
        caption = f"""
**✅ Sesli Sohbette Yayın Başladı**

**❍ Başlık:** {title}
**❍ Süre:** {duration_str}
**❍ Yayın Türü:** {stream_type}
**❍ İsteyen:** {mention}
"""
        
        # İlerleme çubuğunu oluştur
        if total_seconds <= 0 or "Canlı" in duration_str:
            # Canlı yayın veya bilinmeyen süre
            progress_line = "🔴 CANLI YAYIN"
        else:
            # İlerleme çubuğu
            progress = min(elapsed_seconds / total_seconds, 1.0)
            progress_bar_length = 10
            filled_length = int(progress_bar_length * progress)
            
            elapsed_formatted = format_seconds(elapsed_seconds)
            total_formatted = format_seconds(total_seconds)
            
            # Şık bir progress bar - Unicode karakterler yerine ASCII kullanarak
            progress_bar = ''.join(['■' for _ in range(filled_length)] + ['□' for _ in range(progress_bar_length - filled_length)])
            progress_line = f"{elapsed_formatted} {progress_bar} {total_formatted}"
        
        # Kontrol butonları
        is_paused = await is_stream_off(chat_id)
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text=progress_line, callback_data="dummy_progress")
            ],
            [
                InlineKeyboardButton(
                    text="⏸️ Duraklat" if not is_paused else "▶️ Devam", 
                    callback_data="player_pause" if not is_paused else "player_resume"
                ),
                InlineKeyboardButton(text="⏭️ Atla", callback_data="player_skip"),
                InlineKeyboardButton(text="⏹️ Bitir", callback_data="player_end")
            ],
            [
                InlineKeyboardButton(text="🗑️ Kapat", callback_data="force_close")
            ]
        ])
        
        # Mesajı güncelle - Flood hatası için try-except ekledik
        try:
            player_msg = PLAYER_MESSAGES[chat_id]
            await player_msg.edit_caption(caption=caption, reply_markup=buttons)
        except FloodWait as e:
            # Flood bekleme süresi
            wait_time = e.value
            LOGGER.info(f"Mesaj güncellemesi için bekleme: {wait_time} saniye")
            # Belirtilen süre kadar bekle ve bu güncellemeyi atla
            await asyncio.sleep(wait_time)
        except Exception as e:
            LOGGER.error(f"Oynatıcı mesajı güncelleme hatası: {str(e)}")
    except Exception as e:
        LOGGER.error(f"update_player_message genel hatası: {str(e)}")
    
    # Her 10 saniyede bir güncelle (Flood hatalarını azaltmak için)
    await asyncio.sleep(10)

async def send_player_message(chat_id, title, duration, stream_type, mention, thumbnail):
    # İlk oynatıcı mesajını gönder
    caption = f"""
**✅ Sesli Sohbette Yayın Başladı**

**❍ Başlık:** {title}
**❍ Süre:** {duration}
**❍ Yayın Türü:** {stream_type}
**❍ İsteyen:** {mention}"""
    
    
    # İlerleme çubuğunu buton olarak ekle
    progress_line = "00:00 □□□□□□□□□□ " + duration if duration not in ["Canlı", "Canlı Yayın"] else "🔴 CANLI YAYIN"
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=progress_line, callback_data="dummy_progress")
        ],
        [
            InlineKeyboardButton(text="⏸️ Duraklat", callback_data="player_pause"),
            InlineKeyboardButton(text="⏭️ Atla", callback_data="player_skip"),
            InlineKeyboardButton(text="⏹️ Bitir", callback_data="player_end")
        ],
        [
            InlineKeyboardButton(text="🗑️ Kapat", callback_data="force_close")
        ]
    ])
    
    try:
        # Önceki oynatıcı mesajını temizle
        await reset_player_message(chat_id)
        
        # URL kontrolü ekliyoruz
        if not thumbnail:
            thumbnail = DEFAULT_THUMBNAIL
        
        try:
            # Flood wait hatası yönetimi
            # Yeni oynatıcı mesajını gönder
            player_msg = await bot.send_photo(
                chat_id, 
                photo=thumbnail, 
                caption=caption, 
                reply_markup=buttons
            )
        except FloodWait as e:
            # Belirtilen süre kadar bekle ve tekrar dene
            LOGGER.info(f"Mesaj gönderme için bekleme: {e.value} saniye")
            await asyncio.sleep(e.value)
            player_msg = await bot.send_photo(
                chat_id, 
                photo=thumbnail, 
                caption=caption, 
                reply_markup=buttons
            )
        
        # Oynatıcı bilgisini ve zamanını kaydet
        PLAYER_MESSAGES[chat_id] = player_msg
        STREAM_TIMES[chat_id] = {"start_time": time.time(), "last_update": 0}
        
        # Hemen ilk güncellemeyi yap
        await update_player_message(chat_id, force_update=True)
    except Exception as e:
        LOGGER.error(f"Oynatıcı mesajı gönderme hatası: {str(e)}")
        try:
            # Thumbnail ile gönderme başarısız olursa, sadece metin mesajı gönder
            player_msg = await bot.send_message(
                chat_id, 
                text=caption, 
                reply_markup=buttons
            )
            PLAYER_MESSAGES[chat_id] = player_msg
            STREAM_TIMES[chat_id] = {"start_time": time.time(), "last_update": 0}
        except Exception as e2:
            LOGGER.error(f"Yedek mesaj gönderme hatası: {str(e2)}")

# Oynatıcı mesajını sil
async def reset_player_message(chat_id):
    if chat_id in PLAYER_MESSAGES:
        try:
            # Mesajı silme
            await PLAYER_MESSAGES[chat_id].delete()
        except Exception as e:
            LOGGER.error(f"Oynatıcı mesajı silme hatası: {str(e)}")
        finally:
            # Mesaj referansını temizle
            PLAYER_MESSAGES.pop(chat_id, None)
            STREAM_TIMES.pop(chat_id, None)
# Tüm Akışları Günlüğe Kaydet
async def stream_logger(chat_id, user, title, duration, stream_type, position=None):
    if LOG_GROUP_ID != 0:
        if chat_id != LOG_GROUP_ID:
            try:
                chat = await bot.get_chat(chat_id)
                chat_name = chat.title
                if chat.username:
                    chat_link = f"@{chat.username}"
                else:
                    chat_link = "Gizli Grup"
                try:
                    if user.username:
                        requested_by = f"@{user.username}"
                    else:
                        requested_by = user.mention
                except Exception:
                    requested_by = user.title
                if position:
                    mesaj = f"""**#{position} ✅ Kuyruğa Eklendi**

**❍ Başlık:** {title}
**❍ Süre:** {duration}
**❍ Yayın Türü:** {stream_type}
**❍ Grup:** {chat_name}
**❍ Grup Linki:** {chat_link}
**❍ Talep Eden:** {requested_by}"""
                else:
                    mesaj = f"""**✅ Yayın Başlatıldı**

**❍ Başlık:** {title}
**❍ Süre:** {duration}
**❍ Yayın Türü:** {stream_type}
**❍ Grup:** {chat_name}
**❍ Grup Linki:** {chat_link}
**❍ Talep Eden:** {requested_by}"""
                try:
                    # Thumbnail ile gönder
                    if isinstance(title, str) and '[' in title and ']' in title:
                        # Title bir bağlantı içeriyorsa, temizlenmiş başlık kullan
                        clean_title = re.sub(r'\[|\]|\(|\)|https?://\S+', '', title).strip()
                        if not clean_title:
                            clean_title = "Müzik"
                    else:
                        clean_title = title
                    
                    # Log mesajını gönder (varsayılan thumbnail ile)
                    await bot.send_photo(LOG_GROUP_ID, photo=DEFAULT_THUMBNAIL, caption=mesaj)
                except Exception as e:
                    LOGGER.error(f"Log grubuna mesaj gönderilemedi: {e}")
                    try:
                        await bot.send_message(LOG_GROUP_ID, text=mesaj)
                    except Exception:
                        pass
            except Exception as e:
                LOGGER.error(f"Log oluşturma hatası: {e}")

# Çağrı Durumunu Al - Hata yönetimi geliştirildi
async def get_call_status(chat_id):
    try:
        calls = await call.calls
        chat_call = calls.get(chat_id)
        if chat_call:
            # PyTGCalls versiyonuna göre Status atributı farklı olabilir
            try:
                status = chat_call.status
                if status == Call.Status.IDLE:
                    call_status = "IDLE"
                elif status == Call.Status.ACTIVE:
                    call_status = "PLAYING"
                elif status == Call.Status.PAUSED:
                    call_status = "PAUSED"
                else:
                    call_status = "NOTHING"
            except AttributeError:
                # Status atributu yoksa
                if chat_id in ACTIVE_MEDIA_CHATS:
                    call_status = "PLAYING"
                else:
                    call_status = "NOTHING"
        else:
            call_status = "NOTHING"
    except Exception as e:
        LOGGER.info(f"Çağrı durumunu alma hatası: {e}")
        # Hata durumunda bellek değişkenlerine bakarak karar ver
        if chat_id in ACTIVE_MEDIA_CHATS:
            call_status = "PLAYING"
        else:
            call_status = "NOTHING"
    
    return call_status

# Yayını Değiştir ve Yayını Kapat
async def change_stream(chat_id):
    # Yasaklı grup kontrolü ekle
    if chat_id in BANNED_CHATS:
        return await close_stream(chat_id)
        
    queued = QUEUE.get(chat_id)
    if queued:
        queued.pop(0)
    if not queued:
        await bot.send_message(chat_id, "**❌ Sırada başka şarkı yok.**\n**🔇 Sesli sohbetten ayrılıyorum...**")
        return await close_stream(chat_id)

    title = queued[0].get("title")
    duration = queued[0].get("duration")
    stream_file = queued[0].get("stream_file")
    stream_type = queued[0].get("stream_type")
    thumbnail = queued[0].get("thumbnail")
    mention = queued[0].get("mention")
    try:
        if hasattr(queued[0].get("user"), 'mention'):
            requested_by = queued[0].get("user").mention
        else:
            if hasattr(queued[0].get("user"), 'username') and queued[0].get("user").username:
                requested_by = (
                    "["
                    + queued[0].get("user").title
                    + "](https://t.me/"
                    + queued[0].get("user").username
                    + ")"
                )
            else:
                requested_by = queued[0].get("user").title
    except Exception:
        requested_by = "Bilinmeyen"

    if stream_type == "Ses":
        stream_media = MediaStream(
            media_path=stream_file,
            video_flags=MediaStream.Flags.IGNORE,
            audio_parameters=AudioQuality.STUDIO,
            ytdlp_parameters="--cookies cookies.txt -f bestaudio[ext=m4a]/bestaudio",
        )
    elif stream_type == "Video":
        stream_media = MediaStream(
            media_path=stream_file,
            video_flags=MediaStream.Flags.IGNORE,
            audio_parameters=AudioQuality.STUDIO,
            ytdlp_parameters="--cookies cookies.txt -f bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        )

    # Bilgilendirme mesajı
    info_msg = await bot.send_message(chat_id, f"**🔄 Sonraki şarkıya geçiliyor...**")

    try:
        # Çağrıyı başlat
        await call.play(chat_id, stream_media, config=call_config)
        
        # await info_msg.delete()
        await send_player_message(chat_id, title, duration, stream_type, mention, thumbnail)
        
        # Aktif çalma durumunu güncelle
        await add_active_media_chat(chat_id, stream_type)
        
        # Log kaydı
        await stream_logger(chat_id, queued[0].get("user"), title, duration, stream_type, 0)
        
    except Exception as e:
        LOGGER.error(f"Akış başlatma hatası: {e}")
        await info_msg.edit(f"**❌ Akış başlatılamadı: {str(e)}**")
        return await close_stream(chat_id)



async def ban_group_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("**Kullanım:** `/ban_group <grup_id>` veya `/yasakla <grup_id>`")
        return
    
    try:
        chat_id = int(message.command[1])
    except ValueError:
        await message.reply_text("**Geçersiz grup ID.** Lütfen sayısal bir ID girin.")
        return

    await add_banned_chat(chat_id)
    await message.reply_text(f"**✅ Grup yasaklandı:** `{chat_id}`")

@bot.on_message(cdz(["unban_group", "yasakkaldir"]) & bot_owner_only)
async def unban_group_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("**Kullanım:** `/unban_group <grup_id>` veya `/yasakkaldir <grup_id>`")
        return
    
    try:
        chat_id = int(message.command[1])
    except ValueError:
        await message.reply_text("**Geçersiz grup ID.** Lütfen sayısal bir ID girin.")
        return

    await remove_banned_chat(chat_id)
    await message.reply_text(f"**✅ Grup yasağı kaldırıldı:** `{chat_id}`")




@bot.on_message(cdz(["oynat", "play"]))
async def play_command(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    query = " ".join(message.command[1:])

    if not query:
        await message.reply_text("**Lütfen bir şarkı adı veya YouTube linki girin.**")
        return

    # Asistanın gruba ekli ve yönetici olduğundan emin ol
    if not await check_and_join_chat(chat_id, message):
        return

    # Sesli sohbete katıl
    try:
        await call.join(chat_id)
    except Exception as e:
        await message.reply_text(f"**❌ Sesli sohbete katılamadım:** `{str(e)}`")
        return

    # Arama yap
    try:
        search = VideosSearch(query, limit=1)
        result = (await search.next())["result"][0]
        title = result["title"]
        duration = result["duration"]
        thumbnail = result["thumbnails"][0]["url"]
        link = result["link"]
        vidid = result["id"]
    except Exception as e:
        await message.reply_text(f"**❌ Şarkı bulunamadı:** `{str(e)}`")
        return

    # Kuyruğa ekle
    position = await add_to_queue(chat_id, message.from_user, title, duration, link, "Ses", thumbnail)

    if position == 0:
        # İlk şarkıysa hemen çal
        await change_stream(chat_id)
    else:
        # Kuyruğa eklendi mesajı
        await message.reply_text(f"**✅ Kuyruğa eklendi:** `{title}`\n**Sıra:** `{position + 1}`")

    # Log kaydı
    await stream_logger(chat_id, message.from_user, title, duration, "Ses", position)


@bot.on_message(cdz(["durdur", "pause"])) 
async def pause_command(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_MEDIA_CHATS:
        await message.reply_text("**❌ Sesli sohbette çalan bir şey yok.**")
        return
    try:
        await call.pause_stream(chat_id)
        await message.reply_text("**⏸️ Yayın duraklatıldı.**")
        await update_player_message(chat_id, force_update=True)
    except Exception as e:
        await message.reply_text(f"**❌ Yayını duraklatırken hata oluştu:** `{str(e)}`")

@bot.on_message(cdz(["devam", "resume"])) 
async def resume_command(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_MEDIA_CHATS:
        await message.reply_text("**❌ Sesli sohbette çalan bir şey yok.**")
        return
    try:
        await call.resume_stream(chat_id)
        await message.reply_text("**▶️ Yayın devam ettirildi.**")
        await update_player_message(chat_id, force_update=True)
    except Exception as e:
        await message.reply_text(f"**❌ Yayını devam ettirirken hata oluştu:** `{str(e)}`")

@bot.on_message(cdz(["atla", "skip"])) 
async def skip_command(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_MEDIA_CHATS:
        await message.reply_text("**❌ Sesli sohbette çalan bir şey yok.**")
        return
    try:
        await change_stream(chat_id)
        await message.reply_text("**⏭️ Şarkı atlandı.**")
    except Exception as e:
        await message.reply_text(f"**❌ Şarkıyı atlarken hata oluştu:** `{str(e)}`")

@bot.on_message(cdz(["bitir", "end"])) 
async def end_command(client, message):
    chat_id = message.chat.id
    if chat_id not in ACTIVE_MEDIA_CHATS:
        await message.reply_text("**❌ Sesli sohbette çalan bir şey yok.**")
        return
    try:
        await close_stream(chat_id)
        await message.reply_text("**⏹️ Yayın sona erdi.**")
    except Exception as e:
        await message.reply_text(f"**❌ Yayını sona erdirirken hata oluştu:** `{str(e)}`")

async def close_stream(chat_id):
    try:
        await call.leave_call(chat_id)
    except Exception as e:
        LOGGER.error(f"Sesli sohbetten ayrılırken hata: {e}")
    finally:
        await remove_active_media_chat(chat_id)
        await clear_queue(chat_id)
        await reset_player_message(chat_id)


@bot.on_message(cdz(["kuyruk", "queue"])) 
async def queue_command(client, message):
    chat_id = message.chat.id
    if chat_id not in QUEUE or not QUEUE[chat_id]:
        await message.reply_text("**❌ Kuyruk boş.**")
        return
    
    queue_list = "**🎵 Kuyruk:**\n\n"
    for i, track in enumerate(QUEUE[chat_id]):
        queue_list += f"**{i+1}.** `{track.get('title', '')}` - `{track.get('duration', '')}` (İsteyen: {track.get('mention', '')})\n"
    
    if len(queue_list) > 4096:
        # Eğer mesaj çok uzunsa, pastebin gibi bir yere yükle
        link = await paste_queue(queue_list)
        await message.reply_text(f"**🎵 Kuyruk çok uzun, buradan erişebilirsiniz:** {link}")
    else:
        await message.reply_text(queue_list)

@bot.on_message(cdz(["baslat", "start"])) 
async def start_command(client, message):
    await message.reply_text("**Merhaba! Ben King Müzik Botu.**\n\nSesli sohbetlerde müzik çalmak için beni kullanabilirsiniz.\n\n**Komutlar:**\n`/oynat <şarkı adı/linki>` - Müzik çalmaya başlar veya kuyruğa ekler\n`/durdur` - Çalan müziği duraklatır\n`/devam` - Duraklatılan müziği devam ettirir\n`/atla` - Sıradaki şarkıya geçer\n`/bitir` - Yayını sona erdirir\n`/kuyruk` - Kuyruktaki şarkıları gösterir\n`/ping` - Botun gecikmesini gösterir\n`/yardim` - Bu mesajı gösterir\n\n**Sahip Komutları:**\n`/ban_group <grup_id>` - Belirtilen grubu yasaklar\n`/unban_group <grup_id>` - Belirtilen grubun yasağını kaldırır\n\n**Daha fazla bilgi için:** @kingduyurular")

@bot.on_message(cdz(["ping"])) 
async def ping_command(client, message):
    ping_time = await measure_ping()
    await message.reply_text(f"**🏓 Pong!** `{ping_time}ms`")

@bot.on_message(cdz(["yardim", "help"])) 
async def help_command(client, message):
    await message.reply_text("**Merhaba! Ben King Müzik Botu.**\n\nSesli sohbetlerde müzik çalmak için beni kullanabilirsiniz.\n\n**Komutlar:**\n`/oynat <şarkı adı/linki>` - Müzik çalmaya başlar veya kuyruğa ekler\n`/durdur` - Çalan müziği duraklatır\n`/devam` - Duraklatılan müziği devam ettirir\n`/atla` - Sıradaki şarkıya geçer\n`/bitir` - Yayını sona erdirir\n`/kuyruk` - Kuyruktaki şarkıları gösterir\n`/ping` - Botun gecikmesini gösterir\n`/yardim` - Bu mesajı gösterir\n\n**Sahip Komutları:**\n`/ban_group <grup_id>` - Belirtilen grubu yasaklar\n`/unban_group <grup_id>` - Belirtilen grubun yasağını kaldırır\n\n**Daha fazla bilgi için:** @kingduyurular")




if __name__ == "__main__":
    loop.run_until_complete(main())
