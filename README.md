<h1 align="center">🎵 King Müzik Bot</h1

<p align="center">
  <img src="https://img.shields.io/github/stars/king0din/kingmuzik?style=social" alt="Stars">
  <img src="https://img.shields.io/github/forks/king0din/kingmuzik?style=social" alt="Forks">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="License">
</p>

 [![Telegram Badge](https://img.shields.io/badge/-Telegram-blue?style=flat-quare&labelColor=dark_blue&logo=Telegram&logoColor=dark_blue&link=t.me/kingduyurular)](https://t.me/kingduyurular)

<p align="center">
  Telegram grup ve kanallarınızda yüksek kaliteli ve akıcı ir şekilde müzik dinlemek için geliştirilmiş açık kaynaklı müzük botu! 🎧<br>
  YouTube de hem normal hemde canlı yayınları oynatma özeliği ve tamamen türkçe!.
</p>

---

## 🚀 Özellikler

- 🎵 YouTube'dan müzik arama ve oynatma
- 📺 YouTubede canlı yayınlarını oynatma
- 🧠 Akıllı sıra yönetimi ve otomatik geçiş
- 🔎 Anlık şarkı arama sadece şarkı adı girmek yerterlidir
- 🧑‍🤝‍🧑 Grup sohbetleriyle tam uyumlu
- 🛠️ Kolay kurulum ve yapılandırma

---

## 📦 Gereksinimler

- Python 3.9+
- FFmpeg
- Telegram Bot Token
- `api_id`, `api_hash` (my.telegram.org'dan alınır)

---

## ⚙️ Kurulum

``` bashh
apt update -y && apt install sudo -y && sudo apt install curl ffmpeg git nano python3-pip screen -y
```


# Repo'yu klonla
``` bash
git clone https://github.com/king0din/kingmuzik
```
``` bash
cd kingmuzik
```

# .env dosyasını bu komutu çalıştırıp düsenle
``` bash
nano config.env
```
**aşağıdaki gibi açılan bilgilerin karşısın doldurun**

`API_ID =` buraya asistan hesabının my.telegram.org dan api id alıp yanına ekleyin

`API_HASH =` buraya asistan hesabının my.telegram.org dan api has alıp yanına ekleyin

`BOT_TOKEN =` buraya telegramda bot fatherden aldığınız botun tokenini ekleyin

`STRING_SESSION =` buraya asistan hesabının string sensionunu ekleyin telegramda string alma botları mevut arama çubuğuna string session generator yazınca çıkar

`OWNER_ID =` botun sahibinin hesap id sini yazın rose botuna /id komutunu göndererek alabilirsiniz

`LOG_GROUP_ID =` müsik botunun logları göndereceği boş ir kanalın id sini ekleyin botlar aracılığıyla yine alınabilir

## ÖRNEK aşağıdaki gibi görünmeli:
`API_ID = 1234142`

`API_HASH = 324v234b245y2c34v54bbv2c`

`BOT_TOKEN = 2345234623:rthfdghsdfhserthsdhsdfghsdgfh`

`STRING_SESSION = rtyujgdfvnmö98nbvcxcv98m765ergnwedfiadsfbalkdfnşabşdlkfnabkdfbiadkfniakdfniabdfjiabdşkfngipearğq0e9...`

`OWNER_ID = 12345678`

`LOG_GROUP_ID = -123412345134`


**örnekteki gibi görünüyorsa aşağıdaki butonları kulanarak kaydedin ve çıkın**

```ctrl + o``` 

config.env nin başındaki config silip .env olacak şekilde entere basıp kaydedin

klavyeden ```y``` tıklayıp devam edin


```ctrl + x``` tıklayıp geri çıkın

# Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```
# Ve çalıştırma
```bash
python3 kingmuzik.py
```

---
 [![Telegram Badge](https://img.shields.io/badge/-Telegram-blue?style=flat-quare&labelColor=dark_blue&logo=Telegram&logoColor=dark_blue&link=t.me/kingduyurular)](https://t.me/kingduyurular) **👈güncellemeler için kanalımıza katılın takipte kalın..❗**
---
