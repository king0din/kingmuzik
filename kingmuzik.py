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
from PIL import ImageFilter, ImageFont, ImageOps
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

if os.path.exists("Config.env"):
    load_dotenv("Config.env")

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
ALLOWED_CHATS_FILE = f"{DB_PATH}/allowed_chats.json"
GROUP_AUTH_FILE = f"{DB_PATH}/group_auth.json"

# Memory Database
ACTIVE_AUDIO_CHATS = []
ACTIVE_VIDEO_CHATS = []
ACTIVE_MEDIA_CHATS = []
ALLOWED_CHATS = set()  # İzin verilen grupları saklamak için
GROUP_AUTH_ENABLED = True  # Varsayılan olarak grup yetkilendirme aktif

QUEUE = {}
PLAYER_MESSAGES = {}  # Oynatıcı mesajları için
STREAM_TIMES = {}     # Şarkı başlangıç zamanları için

# Komut filtreleri
def cdx(commands: Union[str, List[str]]):
    return pyrofl.command(commands, ["/", "!", "."])

def cdz(commands: Union[str, List[str]]):
    return pyrofl.command(commands, ["", "/", "!", "."])

def rgx(pattern: Union[str, Pattern]):
    return pyrofl.regex(pattern)

# Bot sahibi kontrol
bot_owner_only = pyrofl.user(OWNER_ID)

# İzin verilen gruplarda çalışma kontrol
def is_allowed_chat(_, __, m):
    if m.from_user and m.from_user.id == OWNER_ID:
        return True
    
    # Özel mesajlarda her zaman çalış
    if m.chat.type == ChatType.PRIVATE:
        return True
    
    # Grup yetkilendirme devre dışı ise, tüm gruplarda çalış
    if not GROUP_AUTH_ENABLED:
        return True
    
    # İzinli gruplarda çalış
    if m.chat.id in ALLOWED_CHATS:
        return True
    
    # Diğer tüm durumlarda hiçbir komuta yanıt verme
    return False

allowed_chat_filter = pyrofl.create(is_allowed_chat)

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

# Grup yetkilendirme durumu işlevleri
def save_group_auth_status():
    """Grup yetkilendirme durumunu kaydet"""
    try:
        data = {"enabled": GROUP_AUTH_ENABLED}
        save_json(GROUP_AUTH_FILE, data)
        LOGGER.info(f"Grup yetkilendirme durumu kaydedildi: {GROUP_AUTH_ENABLED}")
    except Exception as e:
        LOGGER.error(f"Grup yetkilendirme durumu kaydedilirken hata: {e}")

async def load_group_auth_status():
    """Grup yetkilendirme durumunu yükle"""
    global GROUP_AUTH_ENABLED
    try:
        if not os.path.exists(GROUP_AUTH_FILE):
            save_json(GROUP_AUTH_FILE, {"enabled": True})
            return
        
        data = load_json(GROUP_AUTH_FILE)
        GROUP_AUTH_ENABLED = data.get("enabled", True)
        LOGGER.info(f"Grup yetkilendirme durumu yüklendi: {GROUP_AUTH_ENABLED}")
    except Exception as e:
        LOGGER.error(f"Grup yetkilendirme durumu yüklenirken hata: {e}")

# Dosya tabanlı veritabanı işlevleri
async def load_allowed_chats():
    """Dosyadan izin verilen grupları yükle"""
    data = load_json(ALLOWED_CHATS_FILE)
    allowed_chat_ids = data.get("allowed_chats", [])
    ALLOWED_CHATS.update(allowed_chat_ids)
    LOGGER.info(f"Toplam {len(ALLOWED_CHATS)} izinli grup yüklendi.")

async def add_allowed_chat(chat_id: int):
    """Bir grubu izin verilen gruplara ekle"""
    # Eğer grup zaten izinli ise işlem yapma
    if chat_id in ALLOWED_CHATS:
        return

    # Belleğe ekle
    ALLOWED_CHATS.add(chat_id)
    
    # Dosyaya kaydet
    data = load_json(ALLOWED_CHATS_FILE)
    allowed_chats = data.get("allowed_chats", [])
    if chat_id not in allowed_chats:
        allowed_chats.append(chat_id)
        data["allowed_chats"] = allowed_chats
        save_json(ALLOWED_CHATS_FILE, data)

async def remove_allowed_chat(chat_id: int):
    """Bir grubu izin verilen gruplardan çıkar"""
    # Bellekten çıkar
    if chat_id in ALLOWED_CHATS:
        ALLOWED_CHATS.remove(chat_id)
    
    # Dosyadan çıkar
    data = load_json(ALLOWED_CHATS_FILE)
    allowed_chats = data.get("allowed_chats", [])
    if chat_id in allowed_chats:
        allowed_chats.remove(chat_id)
        data["allowed_chats"] = allowed_chats
        save_json(ALLOWED_CHATS_FILE, data)
        
    # Aktif bir yayın varsa sonlandır
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
        image = Image.new('RGB', (800, 600), color=(18, 19, 35))
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
    if not os.path.exists(ALLOWED_CHATS_FILE):
        save_json(ALLOWED_CHATS_FILE, {"allowed_chats": []})
    if not os.path.exists(GROUP_AUTH_FILE):
        save_json(GROUP_AUTH_FILE, {"enabled": True})
    
    # İzin verilen grupları yükle
    await load_allowed_chats()
    
    # Grup yetkilendirme durumunu yükle
    await load_group_auth_status()
    
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
        default_logo = Image.new('RGB', (128, 128), color=(18, 19, 35))
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
            await message.reply_text(f"❌ **Asistan yönetici yapma işlemi sırasında beklenmeyen hata:** `{str(e)}`")
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
            default_logo = Image.new('RGB', (128, 128), color=(18, 19, 35))
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
                default_logo = Image.new('RGB', (128, 128), color=(18, 19, 35))
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
                image_blurred = Image.new('RGB', (1280, 720), color=(18, 19, 35))
            
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
            image = Image.new('RGB', (1280, 720), color=(18, 19, 35))
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
        title = current_track.get("title", "").replace("[", "").replace("]", "")
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
            return
        except Exception as e:
            LOGGER.error(f"Oynatıcı güncelleme hatası: {str(e)}")
    except Exception as e:
        LOGGER.error(f"Oynatıcı güncelleme döngüsü hatası: {str(e)}")

# Oynatıcı güncelleme döngüsü
async def update_player_loop():
    while True:
        try:
            for chat_id in list(PLAYER_MESSAGES.keys()):
                await update_player_message(chat_id)
        except Exception as e:
            LOGGER.error(f"Oynatıcı güncelleme döngüsü hatası: {str(e)}")
        
        # Her 10 saniyede bir güncelle (Flood hatalarını azaltmak için)
        await asyncio.sleep(10)

# Oynatıcı mesajını oluşturma/gönderme fonksiyonu
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
    # Grup izin kontrolü ekle - DÜZELTME YAPILDI
    if GROUP_AUTH_ENABLED and chat_id not in ALLOWED_CHATS:
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
            ytdlp_parameters="--cookies cookies.txt",
        )
    elif stream_type == "Video":
        stream_media = MediaStream(
            media_path=stream_file,
            audio_parameters=AudioQuality.STUDIO,
            video_parameters=VideoQuality.HD_720p,
            ytdlp_parameters="--cookies cookies.txt",
        )

    # Bildirim mesajı
    info_msg = await bot.send_message(chat_id, f"**🔄 Sonraki şarkıya geçiliyor...**")
    
    try:
        # Çağrıyı başlat
        await call.play(chat_id, stream_media, config=call_config)
        
        # Bilgilendirme mesajını sil
        await info_msg.delete()
        
        # İlerleme çubuklu yeni oynatıcı mesajını göster
        await send_player_message(chat_id, title, duration, stream_type, mention, thumbnail)
        
        # Aktif çalma durumunu güncelle
        await add_active_media_chat(chat_id, stream_type)
        
        # Log kaydı
        await stream_logger(chat_id, queued[0].get("user"), title, duration, stream_type, 0)
        
    except Exception as e:
        LOGGER.error(f"Akış değiştirme hatası: {e}")
        await info_msg.edit(f"**❌ Akış başlatılamadı: {str(e)}**")
        return await close_stream(chat_id)

async def close_stream(chat_id):
    try:
        # İlerleme mesajını temizle
        await reset_player_message(chat_id)
        
        # Çağrıdan ayrıl - hata yönetimini geliştirdim
        try:
            if chat_id in ACTIVE_MEDIA_CHATS:
                await call.leave_call(chat_id)
        except Exception as e:
            LOGGER.info(f"Görüntülü sohbetten ayrılırken hata: {e}")
            # Bu hata normal, userbot zaten çağrıda değilse gerçekleşir
            pass
            
        # Sırayı temizle
        await clear_queue(chat_id)
        
        # Aktif medya listesinden çıkar
        await remove_active_media_chat(chat_id)
        
        return True
    except Exception as e:
        LOGGER.error(f"Stream kapatma hatası: {e}")
        return False

# Start komutunu ekleyelim
@bot.on_message(cdz(["start"]))
async def start_command(client, message):
    user_id = message.from_user.id
    chat_type = message.chat.type
    
    # Kullanıcıyı veritabanına ekle
    await add_served_user(user_id)
    
    # Özel mesaj veya grup mesajı kontrolü
    if chat_type == ChatType.PRIVATE:
        # Özel mesaj için start komutu
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Beni Gruba Ekle", url=f"https://t.me/{bot.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📚 Komutlar", callback_data="help_command"),
                InlineKeyboardButton("👨‍💻 Sahip", url=f"https://t.me/{OWNER_USERNAME}")
            ]
        ])
        
        try:
            # Karşılama mesajı - Düzeltilmiş START_IMAGE_URL
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption=f"""**Merhaba {message.from_user.mention}!**

Ben **{BOT_NAME}**, gruplarda müzik ve video çalabilen bir botum. 
Beni grubunuza ekleyin ve sesli sohbetlerde müzik keyfi yaşayın!

Komutları görmek için aşağıdaki butonları kullanabilirsiniz.""",
                reply_markup=buttons
            )
        except Exception as e:
            LOGGER.error(f"Start resmi gönderme hatası: {e}")
            # Resim göndermede hata olursa metin mesajı gönder
            await message.reply_text(
                text=f"""**Merhaba {message.from_user.mention}!**

Ben **{BOT_NAME}**, gruplarda müzik ve video çalabilen bir botum. 
Beni grubunuza ekleyin ve sesli sohbetlerde müzik keyfi yaşayın!

Komutları görmek için aşağıdaki butonları kullanabilirsiniz.""",
                reply_markup=buttons
            )
    else:
        # Grup mesajı için start komutu
        await message.reply_text(
            f"""**Merhaba {message.from_user.mention}!**

Ben **{BOT_NAME}**, bu grupta aktifim. Müzik dinlemek için `/oynat` veya `/voynat` komutlarını kullanabilirsiniz.

Daha fazla bilgi için `/help` komutunu kullanın."""
        )
        # Grubu veritabanına ekle
        await add_served_chat(message.chat.id)
        
        # Asistan hesabını gruba ekle ve yönetici yap
        await check_and_join_chat(message.chat.id, message)

# /calis komutu - Bot sahibi için sohbeti etkinleştirme
@bot.on_message(cdx(["calis"]) & bot_owner_only)
async def enable_chat(client, message):
    chat_id = message.chat.id
    
    if message.chat.type in [ChatType.PRIVATE]:
        return await message.reply_text("**⚠️ Bu komut sadece gruplarda kullanılabilir.**")
    
    # Eğer grup zaten izinli ise bilgi ver
    if chat_id in ALLOWED_CHATS:
        return await message.reply_text("**✅ Bot zaten bu grupta çalışıyor.**")
    
    # Grubu izinli yapmak için
    await add_allowed_chat(chat_id)
    
    # Gruba servis etmek için
    await add_served_chat(chat_id)
    
    # Asistan hesabını gruba ekle ve yönetici yap
    await add_assistant_to_chat(chat_id, message)
    
    await message.reply_text("**✅ Bot bu grupta çalışmak için etkinleştirildi.**")
    
    # Log grubuna bilgi ver
    if LOG_GROUP_ID != 0:
        chat_info = await bot.get_chat(chat_id)
        chat_title = chat_info.title
        try:
            log_msg = f"""**✅ Yeni Grup Etkinleştirildi**

**❍ Grup:** {chat_title}
**❍ ID:** `{chat_id}`
**❍ Etkinleştiren:** {message.from_user.mention}"""
            
            await bot.send_message(LOG_GROUP_ID, log_msg)
        except Exception as e:
            LOGGER.error(f"Log mesajı gönderme hatası: {e}")

# /durdur_grup komutu - Grubu devre dışı bırakma
@bot.on_message(cdx(["durdur_grup"]) & bot_owner_only)
async def disable_chat(client, message):
    chat_id = message.chat.id
    
    if message.chat.type in [ChatType.PRIVATE]:
        return await message.reply_text("**⚠️ Bu komut sadece gruplarda kullanılabilir.**")
    
    # Eğer grup zaten izinli değilse bilgi ver
    if chat_id not in ALLOWED_CHATS:
        return await message.reply_text("**⚠️ Bot zaten bu grupta devre dışı.**")
    
    # Önce aktif sesli sohbeti kapat
    if chat_id in ACTIVE_MEDIA_CHATS:
        await close_stream(chat_id)
    
    # Sonra grubu izinli gruplardan çıkar
    await remove_allowed_chat(chat_id)
    
    # Değişiklikleri kaydet - gerekirse yeniden yükleme sırasında da hatırlamak için
    data = load_json(ALLOWED_CHATS_FILE)
    allowed_chats = data.get("allowed_chats", [])
    if chat_id in allowed_chats:
        allowed_chats.remove(chat_id)
        data["allowed_chats"] = allowed_chats
        save_json(ALLOWED_CHATS_FILE, data)
    
    await message.reply_text("**✅ Bot bu grupta devre dışı bırakıldı.**")
    
    # Log grubuna bilgi ver
    if LOG_GROUP_ID != 0:
        chat_info = await bot.get_chat(chat_id)
        chat_title = chat_info.title
        try:
            log_msg = f"""**❌ Grup Devre Dışı Bırakıldı**

**❍ Grup:** {chat_title}
**❍ ID:** `{chat_id}`
**❍ Devre Dışı Bırakan:** {message.from_user.mention}"""
            
            await bot.send_message(LOG_GROUP_ID, log_msg)
        except Exception as e:
            LOGGER.error(f"Log mesajı gönderme hatası: {e}")

# Grup yetkilerini devre dışı bırakma komutu - tüm gruplarda çalışır
@bot.on_message(cdx(["inaktif"]) & bot_owner_only)
async def disable_group_auth(client, message):
    global GROUP_AUTH_ENABLED
    
    # Zaten devre dışı ise bilgi ver
    if not GROUP_AUTH_ENABLED:
        return await message.reply_text("**ℹ️ Grup yetkilendirme sistemi zaten devre dışı.**\n\nBot tüm gruplarda çalışıyor.")
    
    # Grup yetkilerini devre dışı bırak
    GROUP_AUTH_ENABLED = False
    
    # Değişikliği kaydet
    save_group_auth_status()
    
    await message.reply_text("**✅ Grup yetkilendirme sistemi devre dışı bırakıldı.**\n\nBot artık tüm gruplarda çalışacak.")
    
    # Log kaydı
    if LOG_GROUP_ID != 0:
        try:
            log_msg = f"""**⚠️ Grup Yetkilendirme Devre Dışı**

**❍ Devre Dışı Bırakan:** {message.from_user.mention}
**❍ Durum:** Bot tüm gruplarda çalışıyor."""
            
            await bot.send_message(LOG_GROUP_ID, log_msg)
        except Exception as e:
            LOGGER.error(f"Log mesajı gönderme hatası: {e}")

# Grup yetkilerini aktifleştirme komutu
@bot.on_message(cdx(["aktif"]) & bot_owner_only)
async def enable_group_auth(client, message):
    global GROUP_AUTH_ENABLED
    
    # Zaten aktif ise bilgi ver
    if GROUP_AUTH_ENABLED:
        return await message.reply_text("**ℹ️ Grup yetkilendirme sistemi zaten aktif.**\n\nBot sadece yetkilendirilmiş gruplarda çalışıyor.")
    
    # Grup yetkilerini aktifleştir
    GROUP_AUTH_ENABLED = True
    
    # Değişikliği kaydet
    save_group_auth_status()
    
    await message.reply_text("**✅ Grup yetkilendirme sistemi aktifleştirildi.**\n\nBot sadece `/calis` komutunu kullandığınız gruplarda çalışacak.")
    
    # Log kaydı
    if LOG_GROUP_ID != 0:
        try:
            log_msg = f"""**✅ Grup Yetkilendirme Aktif**

**❍ Aktifleştiren:** {message.from_user.mention}
**❍ Durum:** Bot sadece yetkilendirilmiş gruplarda çalışıyor."""
            
            await bot.send_message(LOG_GROUP_ID, log_msg)
        except Exception as e:
            LOGGER.error(f"Log mesajı gönderme hatası: {e}")

# Grupları listele komutu 
@bot.on_message(cdx(["gruplar"]) & bot_owner_only)
async def list_allowed_groups(client, message):
    # İzinli grupları listele
    allowed_groups = list(ALLOWED_CHATS)
    
    if not allowed_groups:
        return await message.reply_text("**ℹ️ İzin verilen grup bulunmuyor.**")
    
    # Grup bilgilerini topla
    text = "**✅ İzin Verilen Gruplar:**\n\n"
    
    for i, chat_id in enumerate(allowed_groups, 1):
        try:
            chat_info = await bot.get_chat(chat_id)
            chat_title = chat_info.title
            chat_username = f"@{chat_info.username}" if chat_info.username else "Özel Grup"
            text += f"**{i}.** {chat_title} [`{chat_id}`]\n    └ {chat_username}\n\n"
        except Exception as e:
            text += f"**{i}.** Bilinmeyen Grup [`{chat_id}`] - Hata: {str(e)}\n\n"
    
    # Durum bilgisi ekle
    status = "**Aktif** ✅" if GROUP_AUTH_ENABLED else "**Devre Dışı** ❌"
    text += f"\n**Grup Yetkilendirme Durumu:** {status}"
    text += f"\n**Toplam İzinli Grup:** {len(allowed_groups)}"
    
    await message.reply_text(text)

# Help komutunu ekleyelim
@bot.on_message(cdz(["help"]))
async def help_command(client, message):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📚 Kullanıcı Komutları", callback_data="user_commands"),
            InlineKeyboardButton("👮‍♂️ Yönetici Komutları", callback_data="admin_commands")
        ],
        [
            InlineKeyboardButton("👨‍💻 Sahip", url=f"https://t.me/{OWNER_USERNAME}"),
            InlineKeyboardButton("🗑️ Kapat", callback_data="force_close")
        ]
    ])
    
    try:
        await message.reply_photo(
            photo=START_IMAGE_URL,
            caption=f"""**Yardım Menüsü - {BOT_NAME}**

Aşağıdaki butonları kullanarak komutlar hakkında bilgi alabilirsiniz.""",
            reply_markup=buttons
        )
    except Exception as e:
        LOGGER.error(f"Help resmi gönderme hatası: {e}")
        await message.reply_text(
            text=f"""**Yardım Menüsü - {BOT_NAME}**

Aşağıdaki butonları kullanarak komutlar hakkında bilgi alabilirsiniz.""",
            reply_markup=buttons
        )

# Stats komutunu düzeltelim - ping ekle
@bot.on_message(cdx(["stats"]))
async def check_bot_stats(client, message):
    try:
        await message.delete()
    except:
        pass
    
    # Loading mesajı göster
    loading_msg = await message.reply_text("📊 **İstatistikler alınıyor...**")
    
    try:
        # Ping ölçümü
        start_time = time.time()
        ping_msg = await bot.send_message(message.chat.id, "🏓")
        end_time = time.time()
        await ping_msg.delete()
        ping_time = round((end_time - start_time) * 1000, 2)  # ms cinsinden
        
        # Sistem bilgileri
        runtime = __start_time__
        boot_time = int(time.time() - runtime)
        uptime = get_readable_time((boot_time))
        
        # Kullanım istatistikleri
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # Bot istatistikleri
        served_chats = len(await get_served_chats())
        served_users = len(await get_served_users())
        activ_chats = len(ACTIVE_MEDIA_CHATS)
        audio_chats = len(ACTIVE_AUDIO_CHATS)
        video_chats = len(ACTIVE_VIDEO_CHATS)
        
        stats_text = f"""
**⚙️ Bot İstatistikleri**

**✦ Çalışma Süresi:** `{uptime}`
**✦ Ping:** `{ping_time} ms`
**✦ CPU Kullanımı:** `{cpu_usage}%`
**✦ RAM Kullanımı:** `{ram_usage}%`
**✦ Disk Kullanımı:** `{disk_usage}%`

**👥 Kullanıcılar:** `{served_users}`
**👨‍👩‍👧‍👦 Gruplar:** `{served_chats}`

**🎵 Aktif Müzik Çalınan:** `{audio_chats}`
**🎬 Aktif Video Çalınan:** `{video_chats}`
**🔊 Toplam Aktif Çalışan:** `{activ_chats}`

**🤖 Bot Versiyonu:** `{__version__["ᴀᴘ"]}`
**🐍 Python Sürümü:** `{__version__["ᴘʏᴛʜᴏɴ"]}`
**🔷 Pyrogram Sürümü:** `{__version__["ᴘʏʀᴏɢʀᴀᴍ"]}`
**🎧 PyTgCalls Sürümü:** `{__version__["ᴘʏᴛɢᴄᴀʟʟꜱ"]}`
"""
        
        # İstatistik mesajı gönder
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="refresh_stats")
            ],
            [
                InlineKeyboardButton(text="🗑️ Kapat", callback_data="force_close")
            ]
        ])
        
        try:
            await loading_msg.delete()
            await message.reply_photo(
                photo=START_IMAGE_URL,
                caption=stats_text,
                reply_markup=buttons
            )
        except Exception as e:
            LOGGER.error(f"Stats resmi gönderme hatası: {e}")
            await message.reply_text(
                text=stats_text,
                reply_markup=buttons
            )
    except Exception as e:
        LOGGER.error(f"Stats hatası: {e}")
        await loading_msg.edit_text(f"**❌ İstatistikler alınırken hata oluştu:** `{str(e)}`")

# İstatistik yenileme butonu
@bot.on_callback_query(rgx("refresh_stats"))
async def refresh_stats(client, query):
    try:
        # Ping ölçümü
        start_time = time.time()
        ping_msg = await bot.send_message(query.message.chat.id, "🏓")
        end_time = time.time()
        await ping_msg.delete()
        ping_time = round((end_time - start_time) * 1000, 2)  # ms cinsinden
        
        # Sistem bilgileri
        runtime = __start_time__
        boot_time = int(time.time() - runtime)
        uptime = get_readable_time((boot_time))
        
        # Kullanım istatistikleri
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # Bot istatistikleri
        served_chats = len(await get_served_chats())
        served_users = len(await get_served_users())
        activ_chats = len(ACTIVE_MEDIA_CHATS)
        audio_chats = len(ACTIVE_AUDIO_CHATS)
        video_chats = len(ACTIVE_VIDEO_CHATS)
        
        stats_text = f"""
**⚙️ Bot İstatistikleri**

**✦ Çalışma Süresi:** `{uptime}`
**✦ Ping:** `{ping_time} ms`
**✦ CPU Kullanımı:** `{cpu_usage}%`
**✦ RAM Kullanımı:** `{ram_usage}%`
**✦ Disk Kullanımı:** `{disk_usage}%`

**👥 Kullanıcılar:** `{served_users}`
**👨‍👩‍👧‍👦 Gruplar:** `{served_chats}`

**🎵 Aktif Müzik Çalınan:** `{audio_chats}`
**🎬 Aktif Video Çalınan:** `{video_chats}`
**🔊 Toplam Aktif Çalışan:** `{activ_chats}`

**🤖 Bot Versiyonu:** `{__version__["ᴀᴘ"]}`
**🐍 Python Sürümü:** `{__version__["ᴘʏᴛʜᴏɴ"]}`
**🔷 Pyrogram Sürümü:** `{__version__["ᴘʏʀᴏɢʀᴀᴍ"]}`
**🎧 PyTgCalls Sürümü:** `{__version__["ᴘʏᴛɢᴄᴀʟʟꜱ"]}`
"""
        
        # İstatistik mesajı güncelle
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="refresh_stats")
            ],
            [
                InlineKeyboardButton(text="🗑️ Kapat", callback_data="force_close")
            ]
        ])
        
        await query.edit_message_caption(
            caption=stats_text,
            reply_markup=buttons
        )
        
        await query.answer("📊 İstatistikler yenilendi")
    except Exception as e:
        LOGGER.error(f"Stats yenileme hatası: {e}")
        await query.answer(f"❌ Hata: {str(e)}", show_alert=True)

# Yeni grupları izle ve bot sahibine bildir
@bot.on_message(pyrofl.new_chat_members, group=1)
async def welcome_new_members(client, message):
    chat_id = message.chat.id
    
    # Bot grupta değil
    if message.chat.type not in [ChatType.PRIVATE]:
        # Sadece bot eklendiğinde grup izinlerini kontrol et
        for member in message.new_chat_members:
            if member.id == bot.me.id:
                # Bot sahibine bilgi ver
                try:
                    chat_info = await bot.get_chat(chat_id)
                    log_msg = f"""**ℹ️ Bot Yeni Bir Gruba Eklendi**

**❍ Grup:** {chat_info.title}
**❍ ID:** `{chat_id}`
**❍ Link:** {'@' + chat_info.username if chat_info.username else 'Özel Grup'}

**Durum:** {'Bot bu grupta çalışıyor ✅' if not GROUP_AUTH_ENABLED or chat_id in ALLOWED_CHATS else 'Bot bu grupta çalışmıyor ❌ - `/calis` komutu gerekli'}"""
                    
                    # Bot sahibine bilgi ver
                    await bot.send_message(OWNER_ID, log_msg)
                    
                    # Log grubuna bilgi ver
                    if LOG_GROUP_ID != 0:
                        await bot.send_message(LOG_GROUP_ID, log_msg)
                except Exception as e:
                    LOGGER.error(f"Log mesajı gönderme hatası: {e}")
                
                # Asistan hesabını gruba ekle 
                # Her grupta eklensin ama yetki isteyen komutlar çalışmasın
                try:
                    await add_assistant_to_chat(chat_id, message)
                except Exception as e:
                    LOGGER.error(f"Asistan eklenirken hata: {e}")
                
                # Grubu veritabanına ekle
                await add_served_chat(chat_id)
                
                # Eğer grup yetkilendirme aktifse ve izinli değilse bilgi ver
                if GROUP_AUTH_ENABLED and chat_id not in ALLOWED_CHATS:
                    # Karşılama mesajı
                    buttons = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("➕ Beni Gruba Ekle", url=f"https://t.me/{bot.me.username}?startgroup=true")
                        ],
                        [
                            InlineKeyboardButton("📚 Komutlar", callback_data="help_command"),
                            InlineKeyboardButton("👨‍💻 Sahip", url=f"https://t.me/{OWNER_USERNAME}")
                        ]
                    ])
                    
                    try:
                        welcome_msg = await message.reply_photo(
                            photo=START_IMAGE_URL,
                            caption=f"""**👋 Merhaba! Ben {BOT_NAME}!**

⚠️ Bu grubun henüz botumu kullanma izni yok. 
Bot sahibi `/calis` komutunu kullanmadan komutlarıma yanıt vermeyeceğim.""",
                            reply_markup=buttons
                        )
                    except Exception as e:
                        LOGGER.error(f"Karşılama mesajı resim hatası: {e}")
                        welcome_msg = await message.reply_text(
                            f"""**👋 Merhaba! Ben {BOT_NAME}!**

⚠️ Bu grubun henüz botumu kullanma izni yok.
Bot sahibi `/calis` komutunu kullanmadan komutlarıma yanıt vermeyeceğim.""",
                            reply_markup=buttons
                        )
                
                break

# Callback query komutları için help handler ekleyelim
@bot.on_callback_query(rgx("help_command"))
async def help_callback(client, query):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📚 Kullanıcı Komutları", callback_data="user_commands"),
            InlineKeyboardButton("👮‍♂️ Yönetici Komutları", callback_data="admin_commands")
        ],
        [
            InlineKeyboardButton("👨‍💻 Sahip", url=f"https://t.me/{OWNER_USERNAME}"),
            InlineKeyboardButton("🗑️ Kapat", callback_data="force_close")
        ]
    ])
    
    await query.edit_message_caption(
        caption=f"""**Yardım Menüsü - {BOT_NAME}**

Aşağıdaki butonları kullanarak komutlar hakkında bilgi alabilirsiniz.""",
        reply_markup=buttons
    )

@bot.on_callback_query(rgx("user_commands"))
async def user_commands_callback(client, query):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Geri", callback_data="help_command")
        ]
    ])
    
    await query.edit_message_caption(
        caption="""**📚 Kullanıcı Komutları**

- `/oynat [şarkı adı/YouTube URL]` - Sesli sohbette müzik çalar
- `/voynat [video adı/YouTube URL]` - Sesli sohbette video çalar
- `/stats` - Botun istatistiklerini gösterir
- `/help` - Yardım menüsünü gösterir

**Not:** Ayrıca bir ses veya video dosyasını yanıtlayarak da oynatabilirsiniz.""",
        reply_markup=buttons
    )

@bot.on_callback_query(rgx("admin_commands"))
async def admin_commands_callback(client, query):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔙 Geri", callback_data="help_command")
        ]
    ])
    
    await query.edit_message_caption(
        caption="""**👮‍♂️ Yönetici Komutları**

- `/durdur` - Çalan müziği duraklatır
- `/devam` - Duraklatılmış müziği devam ettirir
- `/atla` - Sıradaki parçaya geçer
- `/son` - Yayını sonlandırır ve sırayı temizler

**Not:** Bu komutlar sadece sesli sohbet yönetme yetkisi olan yöneticiler tarafından kullanılabilir.""",
        reply_markup=buttons
    )

@bot.on_callback_query(rgx("check_stats"))
async def check_total_stats(client, query):
    try:
        # Ping ölçümü
        start_time = time.time()
        ping_msg = await bot.send_message(query.message.chat.id, "🏓")
        end_time = time.time()
        await ping_msg.delete()
        ping_time = round((end_time - start_time) * 1000, 2)  # ms cinsinden
        
        # Bot istatistikleri
        runtime = __start_time__
        boot_time = int(time.time() - runtime)
        uptime = get_readable_time((boot_time))
        served_chats = len(await get_served_chats())
        served_users = len(await get_served_users())
        activ_chats = len(ACTIVE_MEDIA_CHATS)
        audio_chats = len(ACTIVE_AUDIO_CHATS)
        video_chats = len(ACTIVE_VIDEO_CHATS)
        
        stats_text = f"""
✨ **Bot İstatistikleri** ✨

⏱️ **Çalışma Süresi:** {uptime}
🏓 **Ping:** {ping_time} ms

👥 **Gruplar:** {served_chats}
👤 **Kullanıcılar:** {served_users}

🎵 **Aktif Müzik:** {audio_chats}
🎬 **Aktif Video:** {video_chats}
🔊 **Toplam Aktif:** {activ_chats}
"""
        await query.answer(stats_text, show_alert=True)
    except Exception as e:
        LOGGER.info(f"🚫 İstatistik hatası: {e}")
        await query.answer("İstatistikler alınırken bir hata oluştu.", show_alert=True)


@bot.on_message(cdx(["duyuru"]) & bot_owner_only)
async def broadcast_message(client, message):
    try:
        await message.delete()
    except:
        pass
    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
    else:
        if len(message.command) < 2:
            return await message.reply_text("**📢 Örnek:** `/duyuru [Mesaj veya Mesaja Yanıt]`")
        query = message.text.split(None, 1)[1]
        if "-pin" in query:
            query = query.replace("-pin", "")
        if "-nobot" in query:
            query = query.replace("-nobot", "")
        if "-pinloud" in query:
            query = query.replace("-pinloud", "")
        if "-user" in query:
            query = query.replace("-user", "")
        if query == "":
            return await message.reply_text("**📢 Lütfen bana yayınlamak için bir mesaj verin.**")
    
    # Geri bildirim mesajı
    status_msg = await message.reply_text("**📣 Duyuru gönderiliyor...**")
 
    if "-nobot" not in message.text:
        sent = 0
        pin = 0
        chats = []
        served_chats = await get_served_chats()
        for chat_id in served_chats:
            chats.append(int(chat_id))
        for i in chats:
            try:
                m = (
                    await bot.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await bot.send_message(i, text=query)
                )
                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        continue
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        continue
                sent += 1
                # Her 20 mesajda bir durum güncellemesi
                if sent % 20 == 0:
                    await status_msg.edit_text(f"**📣 Duyuru gönderiliyor... {sent}/{len(chats)} tamamlandı.**")
            except FloodWait as e:
                flood_time = int(e.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                continue
        try:
            await status_msg.edit_text(f"**✅ Duyuru Tamamlandı**\n\n**📢 {sent} gruba iletildi.**\n**📌 {pin} gruba sabitlendi.**")
        except:
            pass

    if "-user" in message.text:
        susr = 0
        served_users = []
        users_list = await get_served_users()
        for user_id in users_list:
            served_users.append(int(user_id))
        
        await status_msg.edit_text(f"**📣 Kullanıcılara duyuru gönderiliyor... (0/{len(served_users)})**")
        
        for i in served_users:
            try:
                m = (
                    await bot.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await bot.send_message(i, text=query)
                )
                susr += 1
                # Her 20 mesajda bir durum güncellemesi
                if susr % 20 == 0:
                    await status_msg.edit_text(f"**📣 Kullanıcılara duyuru gönderiliyor... ({susr}/{len(served_users)})**")
            except FloodWait as e:
                flood_time = int(e.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                pass
        try:
            await status_msg.edit_text(f"**✅ Kullanıcı Duyurusu Tamamlandı**\n\n**📢 {susr} kullanıcıya iletildi.**")
        except:
            pass


@bot.on_callback_query(rgx("usage_info"))
async def show_usage_info(client, query):
    caption = """
**📚 Komut Kullanımı**

**✓ Üye Komutları:**
- `/oynat [şarkı adı/YouTube URL]` - Sesli sohbette müzik çalar
- `/voynat [video adı/YouTube URL]` - Sesli sohbette video çalar

**✓ Yönetici Komutları:**
- `/durdur` - Çalan müziği duraklatır
- `/devam` - Duraklatılmış müziği devam ettirir
- `/atla` - Sıradaki parçaya geçer
- `/son` - Yayını sonlandırır ve sırayı temizler

**✓ Ekstra Özellikler:**
- Ses/video dosyasını yanıtlayarak da oynatabilirsiniz
- Oynatıcı mesajındaki butonları kullanarak kontrol edebilirsiniz
"""
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🔙 Geri",
                    callback_data="back_to_help",
                )
            ],
        ]
    )
    await query.edit_message_caption(caption, reply_markup=buttons)


@bot.on_callback_query(rgx("back_to_help"))
async def back_to_help_menu(client, query):
    caption = """**🔍 Nasıl Kullanılır:**

- `/oynat [Şarkı Adı]` - Şarkı çalar
- `/voynat [Video Adı]` - Video çalar
- Bir ses/video dosyasını yanıtlayarak da çalabilirsiniz"""
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🎯 Kullanım",
                    callback_data="usage_info",
                ),
                InlineKeyboardButton(
                    text="❌ Kapat",
                    callback_data="force_close",
                )
            ],
        ]
    )
    await query.edit_message_caption(caption, reply_markup=buttons)


@bot.on_callback_query(rgx("force_close"))
async def delete_cb_query(client, query):
    try:
        return await query.message.delete()
    except Exception:
        return

# Callback query işleyicileri için grup izin kontrolü ekle
@bot.on_callback_query(rgx("player_"))
async def player_controls(client, query):
    chat_id = query.message.chat.id
    
    # DÜZELTME - Callback query'lerde grup izin kontrolü
    if GROUP_AUTH_ENABLED and chat_id not in ALLOWED_CHATS:
        return await query.answer("⚠️ Bot bu grupta devre dışı bırakıldı.", show_alert=True)
    
    # Yönetici kontrolü
    if query.from_user.id != OWNER_ID:
        try:
            member = await bot.get_chat_member(chat_id, query.from_user.id)
            if not member.privileges or not member.privileges.can_manage_video_chats:
                return await query.answer("⚠️ **Bu işlem için sesli sohbet yönetme yetkisine sahip olmanız gerekir.**", show_alert=True)
        except Exception:
            return await query.answer("⚠️ **Yetki kontrol edilirken hata oluştu.**", show_alert=True)
            
    data = query.data.split("_")[1]
    
    if data == "pause":
        try:
            await call.pause(chat_id)
            await query.answer("⏸️ **Yayın duraklatıldı.**")
            
            # Yeni butonlar ile mesajı güncelle
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text=query.message.reply_markup.inline_keyboard[0][0].text, callback_data="dummy_progress")
                ],
                [
                    InlineKeyboardButton(text="▶️ Devam", callback_data="player_resume"),
                    InlineKeyboardButton(text="⏭️ Atla", callback_data="player_skip"),
                    InlineKeyboardButton(text="⏹️ Bitir", callback_data="player_end")
                ],
                [
                    InlineKeyboardButton(text="🗑️ Kapat", callback_data="force_close")
                ]
            ])
            
            await query.edit_message_reply_markup(reply_markup=buttons)
        except Exception as e:
            await query.answer(f"❌ **Hata:** {str(e)}", show_alert=True)
            
    elif data == "resume":
        try:
            await call.resume(chat_id)
            await query.answer("▶️ **Yayın devam ediyor.**")
            
            # Yeni butonlar ile mesajı güncelle
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(text=query.message.reply_markup.inline_keyboard[0][0].text, callback_data="dummy_progress")
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
            
            await query.edit_message_reply_markup(reply_markup=buttons)
        except Exception as e:
            await query.answer(f"❌ **Hata:** {str(e)}", show_alert=True)
            
    elif data == "skip":
        try:
            # Mesajı sil, yeni mesaj change_stream içinde gönderilecek
            await query.message.delete()
            await query.answer("⏭️ **Sonraki parçaya geçiliyor...**")
            await change_stream(chat_id)
        except Exception as e:
            await query.answer(f"❌ **Hata:** {str(e)}", show_alert=True)
            
    elif data == "end":
        try:
            # Yayını sonlandır ve mesajı sil
            await close_stream(chat_id)
            await query.message.delete()
            await bot.send_message(chat_id, "⏹️ **Yayın sonlandırıldı.**")
            await query.answer("⏹️ **Yayın sonlandırıldı.**")
        except Exception as e:
            await query.answer(f"❌ **Hata:** {str(e)}", show_alert=True)


@bot.on_callback_query(rgx("dummy_progress"))
async def handle_dummy_progress(client, query):
    # DÜZELTME - Callback query'lerde grup izin kontrolü
    chat_id = query.message.chat.id
    if GROUP_AUTH_ENABLED and chat_id not in ALLOWED_CHATS:
        return await query.answer("⚠️ Bot bu grupta devre dışı bırakıldı.", show_alert=True)
        
    await query.answer("⏱️ İlerleme çubuğu bilgisi", show_alert=False)


@bot.on_message(cdx(["durdur"]) & ~pyrofl.private & allowed_chat_filter)
async def pause_running_stream_on_vc(client, message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    try:
        call_status = await get_call_status(chat_id)
        if call_status == "IDLE" or call_status == "NOTHING":
            return await message.reply_text("**❌ Şuan aktif yayın yok.**")

        elif call_status == "PAUSED":
            return await message.reply_text("**⏸️ Yayın zaten duraklatılmış.**")
        elif call_status == "PLAYING":
            await call.pause(chat_id)
            
            # Oynatıcı mesajını güncelle
            if chat_id in PLAYER_MESSAGES:
                await update_player_message(chat_id, force_update=True)
                
            return await message.reply_text("**⏸️ Yayın duraklatıldı.**")
        else:
            return
    except Exception as e:
        try:
            await bot.send_message(chat_id, f"**❌ Hata:** `{e}`")
        except Exception:
            LOGGER.info(f"🚫 Hata: {e}")
            return


@bot.on_message(cdx(["devam"]) & ~pyrofl.private & allowed_chat_filter)
async def resume_paused_stream_on_vc(client, message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    try:
        call_status = await get_call_status(chat_id)
        if call_status == "IDLE" or call_status == "NOTHING":
            return await message.reply_text("**❌ Şuan aktif yayın yok.**")

        elif call_status == "PLAYING":
            return await message.reply_text("**▶️ Yayın zaten devam ediyor.**")
        elif call_status == "PAUSED":
            await call.resume(chat_id)
            
            # Oynatıcı mesajını güncelle
            if chat_id in PLAYER_MESSAGES:
                await update_player_message(chat_id, force_update=True)
                
            return await message.reply_text("**▶️ Yayın devam ettiriliyor.**")
        else:
            return
    except Exception as e:
        try:
            await bot.send_message(chat_id, f"**❌ Hata:** `{e}`")
        except Exception:
            LOGGER.info(f"🚫 Hata: {e}")
            return


@bot.on_message(cdx(["atla"]) & ~pyrofl.private & allowed_chat_filter)
async def skip_and_change_stream(client, message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    try:
        call_status = await get_call_status(chat_id)
        if call_status == "IDLE" or call_status == "NOTHING":
            return await bot.send_message(chat_id, "**❌ Şuan aktif yayın yok.**")
        elif call_status == "PLAYING" or call_status == "PAUSED":
            # Hazırlık mesajı
            info_msg = await message.reply_text("**🔄 Sonraki parçaya geçiliyor...**")
            # Yayını değiştir
            await change_stream(chat_id)
            # Bildirim mesajını sil
            try:
                await info_msg.delete()
            except Exception:
                pass
    except Exception as e:
        try:
            await bot.send_message(chat_id, f"**❌ Hata:** `{e}`")
        except Exception:
            LOGGER.info(f"🚫 Hata: {e}")
            return


@bot.on_message(cdx(["son"]) & ~pyrofl.private & allowed_chat_filter)
async def stop_stream_and_leave_vc(client, message):
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    try:
        call_status = await get_call_status(chat_id)
        if call_status == "NOTHING":
            return await message.reply_text("**❌ Şuan aktif yayın yok.**")
        elif call_status == "IDLE":
            return await message.reply_text("**✅ Yayın zaten sonlandırılmış.**")
        elif call_status == "PLAYING" or call_status == "PAUSED":
            await close_stream(chat_id)
            return await message.reply_text("**⏹️ Yayın sonlandırıldı.**")
        else:
            return
    except Exception as e:
        try:
            await bot.send_message(chat_id, f"**❌ Hata:** `{e}`")
        except Exception:
            LOGGER.info(f"🚫 Hata: {e}")
            return


@call.on_update(pytgfl.chat_update(ChatUpdate.Status.CLOSED_VOICE_CHAT))
@call.on_update(pytgfl.chat_update(ChatUpdate.Status.KICKED))
@call.on_update(pytgfl.chat_update(ChatUpdate.Status.LEFT_GROUP))
async def stream_services_handler(_, update: Update):
    chat_id = update.chat_id
    return await close_stream(chat_id)


@call.on_update(pytgfl.stream_end())
async def stream_end_handler(_, update: Update):
    chat_id = update.chat_id
    
    # DÜZELTME - Stream sonu işleyicisine grup izin kontrolü ekle
    if GROUP_AUTH_ENABLED and chat_id not in ALLOWED_CHATS:
        return await close_stream(chat_id)
        
    return await change_stream(chat_id)


@bot.on_message(cdz(["oynat", "voynat"]) & ~pyrofl.private & allowed_chat_filter)
async def stream_audio_or_video(client, message):
    try:
        # Komutu sil
        await message.delete()
    except Exception:
        pass
        
    chat_id = message.chat.id
    await add_served_chat(chat_id)
    user = message.from_user if message.from_user else message.sender_chat
    replied = message.reply_to_message
    audio = (replied.audio or replied.voice) if replied else None
    video = (replied.video or replied.document) if replied else None
    
    # Asistan hesabı gruba ekli mi ve yönetici mi kontrol et
    assistant_check = await check_and_join_chat(chat_id, message)
    if not assistant_check:
        return await message.reply_text("**❌ Asistan hesabı gruba katılamadı veya yönetici yapılamadı.**\nLütfen manuel olarak ekleyip yönetici yapın.")
        
    # Yükleniyor mesajı için daha şık emojiler
    loading_emojis = ["🎵", "🎧", "🎼", "🎹", "🎸", "🎻", "🎺"]
    # Yükleniyor mesajını göster
    aux = await message.reply_text(f"{random.choice(loading_emojis)} **Yükleniyor...**")
    
    if audio:
        # Başlık ve süre bilgilerini daha doğru şekilde al
        if replied.audio:
            try:
                title = replied.audio.title or "Bilinmeyen Parça"
                if replied.audio.performer:
                    title = f"{replied.audio.performer} - {title}"
                duration = format_seconds(replied.audio.duration)
            except:
                title = "Desteklenmeyen Başlık"
                duration = "Bilinmeyen"
        else:
            title = "Ses Dosyası"
            duration = "Bilinmeyen"
        
        try:
            # Dosyayı indir ve geri bildirim ver
            await aux.edit_text(f"🎵 **Ses dosyası indiriliyor...**")
            stream_file = await replied.download()
        except Exception as e:
            LOGGER.info(f"Ses dosyası indirme hatası: {e}")
            await aux.edit_text("❌ **Ses dosyası indirilemedi.**")
            return
            
        stream_type = "Ses"
        result_x = {"title": title, "id": f"local_{chat_id}_{user.id}", "duration": duration}
        
    elif video:
            # Video bilgilerini al
            if replied.video:
                try:
                    title = replied.video.file_name or "Video Dosyası"
                    duration = format_seconds(replied.video.duration)
                except:
                    title = "Video Dosyası"
                    duration = "Bilinmeyen"
            else:
                title = "Video Dosyası"
                duration = "Bilinmeyen"
                
            try:
                # Dosyayı indir ve geri bildirim ver
                await aux.edit_text(f"🎬 **Video dosyası indiriliyor...**")
                stream_file = await replied.download()
            except Exception as e:
                LOGGER.info(f"Video dosyası indirme hatası: {e}")
                await aux.edit_text("❌ **Video dosyası indirilemedi.**")
                return
                
            result_x = {"title": title, "id": f"local_{chat_id}_{user.id}", "duration": duration}
            stream_type = "Video"
            
    else:
        if len(message.command) < 2:
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🎯 Kullanım",
                            callback_data="usage_info",
                        ),
                        InlineKeyboardButton(
                            text="❌ Kapat",
                            callback_data="force_close",
                        )
                    ],
                ]
            )
            return await aux.edit_text(
                "**🔍 Nasıl Kullanılır:**\n\n"
                "• `/oynat [Şarkı Adı]` - Şarkı çalar\n"
                "• `/voynat [Video Adı]` - Video çalar\n"
                "• Bir ses/video dosyasını yanıtlayarak da çalabilirsiniz",
                reply_markup=buttons,
            )
            
        query = message.text.split(None, 1)[1]
        stream_type = "Video" if message.command[0].startswith("v") else "Ses"
        
        # Arama kısmını güncelle
        await aux.edit_text(f"**🔍 Arıyorum:** `{query}`")
        
        # URL kontrolü
        if "https://" in query:
            base = r"(?:https?:)?(?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube(?:\-nocookie)?\.(?:[A-Za-z]{2,4}|[A-Za-z]{2,3}\.[A-Za-z]{2})\/)?(?:shorts\/|live\/)?(?:watch|embed\/|vi?\/)*(?:\?[\w=&]*vi?=)?([^#&\?\/]{11}).*$"
            resu = re.findall(base, query)
            vidid = resu[0] if resu and resu[0] else None
            url = f"https://www.youtube.com/watch?v={vidid}" if vidid else None
            search_query = url if url else query
        else:
            vidid = None
            url = None
            search_query = query
            
        try:
            # YouTube'da ara
            await aux.edit_text(f"**🔍 YouTube'da arıyorum:** `{search_query}`")
            results = VideosSearch(search_query, limit=1)
            result_list = await results.next()
            if not result_list or not result_list.get("result"):
                await aux.edit_text("❌ **Video bulunamadı.**")
                return
                
            result = result_list["result"][0]
            vid_id = vidid if vidid else result["id"]
            vid_url = url if url else result["link"]
            try:
                title = result["title"]
                title_link = f"[{title}]({vid_url})"
                title_x = title
            except Exception:
                title = "Desteklenmeyen Başlık"
                title_link = title
                title_x = title
                
            try:
                durationx = result.get("duration")
                if not durationx:
                    duration = "🔴 CANLI YAYIN"
                    duration_x = "Canlı"
                else:
                    duration = f"{durationx}"
                    duration_x = f"{durationx}"
            except Exception:
                duration = "Bilinmeyen"
                duration_x = "Bilinmeyen"
                
            try:
                views = result["viewCount"]["short"]
            except Exception:
                views = "Bilinmeyen"
                
            try:
                channel = result["channel"]["name"]
            except Exception:
                channel = "Bilinmeyen"
                
            stream_file = url if url else result["link"]
            result_x = {
                "title": title_x,
                "id": vid_id,
                "link": vid_url,
                "duration": duration_x,
                "views": views,
                "channel": channel,
            }
            
            # Bulundu bilgisi
            await aux.edit_text(f"**✅ Bulundu:** `{title_x}`\n**⏱️ Süre:** `{duration_x}`\n**🎬 İndiriliyor...**")
            
        except Exception as e:
            LOGGER.info(f"Video arama hatası: {e}")
            await aux.edit_text("❌ **Video aranırken hata oluştu.**")
            return

    # Thumbnail oluştur
    thumbnail = await create_thumbnail(result_x, user.id)
    
    # Kullanıcı bilgisi
    try:
        requested_by = user.mention
    except Exception:
        if user.username:
            requested_by = "[" + user.title + "](https://t.me/" + user.username + ")"
        else:
            requested_by = user.title
            
    # Media Stream oluştur
    if stream_type == "Ses":
        stream_media = MediaStream(
            media_path=stream_file,
            video_flags=MediaStream.Flags.IGNORE,
            audio_parameters=AudioQuality.STUDIO,
            ytdlp_parameters="--cookies cookies.txt",
        )
    elif stream_type == "Video":
        stream_media = MediaStream(
            media_path=stream_file,
            audio_parameters=AudioQuality.STUDIO,
            video_parameters=VideoQuality.HD_720p,
            ytdlp_parameters="--cookies cookies.txt",
        )
    
    # Çağrı durumunu kontrol et
    call_status = await get_call_status(chat_id)
    try:
        if call_status == "PLAYING" or call_status == "PAUSED":
            try:
                # Sıraya ekle
                position = await add_to_queue(
                    chat_id, user, title_link if 'title_link' in locals() else title, 
                    duration, stream_file, stream_type, thumbnail
                )
                
                # Hazırlık mesajını sil
                await aux.delete()
                
                # Kuyruk mesajı gönder
                mesaj = f"""
**#️⃣ Sıraya Eklendi ({position+1})**

**❍ Başlık:** {title_link if 'title_link' in locals() else title}
**❍ Süre:** {duration}
**❍ Yayın Türü:** {stream_type}
**❍ İsteyen:** {requested_by}"""
                
                if 'views' in locals() and 'channel' in locals():
                    mesaj += f"\n**❍ İzlenme:** {views}\n**❍ Kanal:** {channel}"
                
                # Kuyruk mesajı için butonlar
                buttons = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="🗑️ Kapat",
                                callback_data="force_close",
                            )
                        ],
                    ]
                )
                
                try:
                    # FloodWait için try-except ekledik
                    await bot.send_photo(chat_id, thumbnail, mesaj, reply_markup=buttons)
                except FloodWait as e:
                    # Bekle ve tekrar dene
                    await asyncio.sleep(e.value)
                    await bot.send_photo(chat_id, thumbnail, mesaj, reply_markup=buttons)
                except Exception as e:
                    LOGGER.error(f"Kuyruk mesajı gönderme hatası: {e}")
                    await bot.send_message(chat_id, mesaj, reply_markup=buttons)
                
                # Log kaydet
                await stream_logger(
                    chat_id, user, title, duration, stream_type, position+1
                )
            except Exception as e:
                try:
                    return await aux.edit(f"**❌ Hata:** `{e}`")
                except Exception:
                    LOGGER.info(f"Hata: {e}")
                    return
        elif call_status == "IDLE" or call_status == "NOTHING":
            try:
                # Hazırlık mesajını güncelle
                await aux.edit_text(f"**🔄 Yayın başlatılıyor...**")
                
                # PEER_ID_INVALID hatasını önlemek için gruba katılma işlemi
                joined = await check_and_join_chat(chat_id, message)
                if not joined:
                    return await aux.edit_text("**❌ Asistan gruba katılamadı. Lütfen yönetici izinlerini kontrol edin.**")
                
                # Çağrı başlat
                try:
                    await call.play(chat_id, stream_media, config=call_config)
                except NoActiveGroupCall:
                    try:
                        # Sesli sohbet başlatma girişimi
                        await aux.edit_text("**⏳ Sesli sohbet başlatılıyor...**")
                        started = await create_group_video_chat(chat_id)
                        if not started:
                            return await aux.edit_text("**❌ Sesli sohbet başlatılamadı. Lütfen yönetici izinlerini kontrol edin.**")
                        
                        # Biraz bekle ve tekrar dene
                        await asyncio.sleep(2)
                        await call.play(chat_id, stream_media, config=call_config)
                    except Exception as e:
                        return await aux.edit_text(f"**❌ Sesli sohbet hatası: {str(e)}**")
                except TelegramServerError:
                    return await aux.edit_text("**⚠️ Telegram sunucu sorunu.** Lütfen daha sonra deneyin.")
                except PeerIdInvalid:
                    # PeerIdInvalid hatası - yeniden katılmayı dene
                    await aux.edit_text("**⏳ Bağlantı hatası. Yeniden bağlanılıyor...**")
                    # Asistanı gruba yeniden katılmaya zorla
                    if message.chat.username:
                        try:
                            await app.leave_chat(message.chat.id)
                        except:
                            pass
                        await asyncio.sleep(1)
                        await app.join_chat(message.chat.username)
                    else:
                        try:
                            await app.leave_chat(message.chat.id)
                        except:
                            pass
                        await asyncio.sleep(1)
                        invite_link = await bot.export_chat_invite_link(chat_id)
                        await app.join_chat(invite_link)
                    
                    # Biraz bekleyip tekrar dene
                    await asyncio.sleep(3)
                    try:
                        await call.play(chat_id, stream_media, config=call_config)
                    except Exception as e:
                        return await aux.edit_text(f"**❌ Bağlantı hatası: {str(e)}**")
                except Exception as e:
                    return await aux.edit_text(f"**❌ Yayın başlatma hatası: {str(e)}**")
                
                # Sıraya ekle ve oynatıcı mesajını göster
                try:
                    position = await add_to_queue(
                        chat_id, user, title_link if 'title_link' in locals() else title, 
                        duration, stream_file, stream_type, thumbnail
                    )
                    
                    # Hazırlık mesajını sil
                    await aux.delete()
                    
                    # İlerleme çubuklu oynatıcı mesajını gönder
                    await send_player_message(
                        chat_id, 
                        title_link if 'title_link' in locals() else title, 
                        duration, stream_type, requested_by, thumbnail
                    )
                    
                    # Log kaydet
                    await stream_logger(
                        chat_id, user, title, duration, stream_type
                    )
                    
                    # Aktif çalma durumunu güncelle
                    await add_active_media_chat(chat_id, stream_type)
                except Exception as e:
                    try:
                        return await aux.edit(f"**❌ Hata:** `{e}`")
                    except Exception:
                        LOGGER.info(f"Hata: {e}")
                        return
            except Exception as e:
                try:
                    return await aux.edit_text(f"**❌ Hata:** `{e}`")
                except Exception:
                    LOGGER.info(f"🚫 Hata: {e}")
                    return
        else:
            return
            
        try:
            await aux.delete()
        except Exception:
            pass
            
        return
    except Exception as e:
        try:
            return await aux.edit_text(f"**❌ Hata:** `{e}`")
        except Exception:
            LOGGER.info(f"🚫 Hata: {e}")
            return


if __name__ == "__main__":
    loop.run_until_complete(main())
