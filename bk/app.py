# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
import os
import speech_recognition as sr
from datetime import datetime
from pydub import AudioSegment
from time import sleep
import traceback
import random # Added for selecting random files
# Import MySQL connector
import mysql.connector
# Import werkzeug security for password hashing
from werkzeug.security import generate_password_hash, check_password_hash
import googletrans
from googletrans import Translator

# Initialize Flask app
app = Flask(__name__)
# Set a secret key for sessions (replace with a strong, random key)
# This is essential for session security. Generate a complex, random string.
app.secret_key = 'annavaram' # <--- CHANGE THIS IN PRODUCTION - Use a strong, random key

# --- Database Configuration ---
# Replace with your MySQL database credentials
DB_CONFIG = {
    'user': 'root', # <--- CHANGE THIS
    'password': 'root', # <--- CHANGE THIS
    'host': 'localhost', # <--- CHANGE THIS (e.g., 'localhost' or IP address)
    'database': 'speech' # <--- CHANGE THIS
}

# --- File Upload and Media Configuration ---
UPLOAD_FOLDER = 'uploads'
# Define the base directory for emotion-based media files
# UPDATED: Pointing to the 'files' folder INSIDE the 'static' folder
# This assumes a directory structure like:
# project_root/
# ├── app.py
# ├── templates/
# │   ├── index.html
# │   ├── signin.html
# │   └── signup.html
# └── static/
#     └── files/
#         ├── audio/
#         │   ├── Angry/
#         │   ├── Disgust/
#         │   ├── Happy/
#         │   ├── Sad/
#         │   └── Surprised/
#         ├── images/
#         │   ├── Angry/
#         │   ├── Disgust/
#         │   ├── Happy/
#         │   ├── Sad/
#         │   └── Surprised/
#         └── video/
#             ├── Angry/
#             ├── Disgust/
#             ├── Happy/
#             ├── Sad/
#             └── Surprised/
MEDIA_FOLDER = 'static/files' # <--- UPDATED PATH

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Ensure emotion and file type subfolders exist within the MEDIA_FOLDER
EMOTIONS = ['Angry', 'Disgust', 'Happy', 'Sad', 'Surprised', 'Neutral'] # Added Neutral
FILE_TYPES = ['images', 'audio', 'video'] # Subfolders within the MEDIA_FOLDER

# Create the directory structure: static/files/file_type/emotion/
# Use app.root_path to ensure directories are created relative to the app's root
for file_type in FILE_TYPES:
    for emotion in EMOTIONS:
        # Construct the full path including 'static' and app.root_path
        os.makedirs(os.path.join(app.root_path, MEDIA_FOLDER, file_type, emotion), exist_ok=True)


# --- Google Translate Initialization ---
# Added a more robust initialization check for googletrans
translator = None # Initialize translator as None
try:
    translator = Translator()
    # Attempt a simple translation to verify functionality
    # Use a try-except block specifically for this test translation
    try:
        test_result = translator.translate('hello', src='en', dest='fr')
        # Check if the result object has the expected 'text' attribute
        if hasattr(test_result, 'text'):
            print(f"Translator test: 'hello' (en) -> '{test_result.text}' (fr)", flush=True)
        else:
             print(f"Warning: Google Translate test translation result has unexpected structure. Translation features may not work as expected.", flush=True)
             translator = None # Set translator to None if test result is unexpected
    except Exception as test_err:
        print(f"Warning: Google Translate test translation failed: {test_err}. Translation features may not work.", flush=True)
        translator = None # Set translator to None if test translation fails

except Exception as init_err:
    print(f"Warning: Google Translate initialization failed: {init_err}. Translation features may not work.", flush=True)
    translator = None # Ensure translator is None if initialization itself fails


# --- Simple Keyword-based Emotion Detection ---
# This is a very basic implementation. For a real application, consider using NLP libraries or APIs.
# Added more keywords in English, Hindi, Kannada, Tamil, Telugu, French, Spanish, German, Japanese, and Russian
EMOTION_KEYWORDS = {
    'Happy': ['happy', 'joy', 'great', 'good', 'excited', 'yay', 'awesome', 'love', 'like', 'wonderful', 'fantastic', 'cheerful', 'pleased', 'glad', 'delighted', 'ecstatic', 'thrilled', 'blissful', 'upbeat', 'jovial',
              'khush' , 'anand', 'badhiya', 'achha', 'mazaa', 'prasanna', 'khushi', 'ullas', 'romanchit', 'utsaahit', 'mubarak', 'shubh', 'sukh', 'santusht', 'pramodit', # Hindi keywords
              'santosha', 'ananda', 'olleh', 'khushi', 'maja', 'ushara', 'santha', 'ullasa', 'romancha', 'utsaha', 'shubha', 'sukha', 'santrupti', 'pramoda', 'harsha', # Kannada keywords
              'magizhchi', 'anandham', 'nalla', 'sandhosam', 'sirappu', 'ullasam', 'romanjam', 'aarvam', 'vaazhthukkal', 'subam', 'sugam', 'thirupthi', 'perumai', 'pugazh', # Tamil keywords
              'santosham', 'anandam', 'bagundi', 'maha', 'ullasam', 'romancham', 'utsaham', 'subham', 'sukham', 'thrupti', 'garvam', 'pogadu', # Telugu keywords
              'heureux', 'joie', 'super', 'bon', 'excité', 'génial', 'amour', 'aimer', 'merveilleux', 'fantastique', 'joyeux', 'content', 'ravi', 'enchanté', 'euphorique', 'passionné', 'bienheureux', 'optimiste', 'jovial', # French keywords
              'feliz', 'alegría', 'genial', 'bueno', 'emocionado', 'increíble', 'amor', 'gustar', 'maravilloso', 'fantástico', 'alegre', 'contento', 'encantado', 'eufórico', 'apasionado', 'dichoso', 'optimista', 'jovial', # Spanish keywords
              'glücklich', 'freude', 'großartig', 'gut', 'aufgeregt', 'toll', 'liebe', 'mögen', 'wunderbar', 'fantastisch', 'fröhlich', 'zufrieden', 'entzückt', 'euphorisch', 'begeistert', 'selig', 'optimistisch', 'jovial', # German keywords
              '嬉しい' , '喜び' , '素晴らしい' , '良い' , '興奮している' , 'すごい' , '愛' , '好き' , '素晴らしい' , 'ファンタスティック' , '陽気な' , '満足している' , '喜んでいる' , '陶酔している' , 'ワクワクしている' , '至福の' , '楽観的' , '陽気', # Japanese keywords (Ureshii, Yorokobi, Subarashii, Yoi, Koufun shite iru, Sugoi, Ai, Suki, Subarashii, Fantasutikku, Youki na, Manzoku shite iru, Yorokonde iru, Tousui shite iru, Wakuwaku shite iru, Shifuku no, Rakkan-teki, Youki)
              'счастливый' , 'радость' , 'отлично' , 'хорошо' , 'взволнованный' , 'потрясающий' , 'любовь' , 'нравиться' , 'замечательный' , 'фантастический' , 'веселый' , 'довольный' , 'восхищенный' , 'эйфорический' , 'в восторге' , 'блаженный' , 'оптимистичный' , 'жизнерадостный', # Russian keywords (schastlivyy, radost', otlichno, khorosho, vzvolnovannyy, potryasayushchiy, lyubov', nravit'sya, zamechatel'nyy, fantasticheskiy, veselyy, dovol'nyy, voskhishchennyy, eyforicheskiy, v vostorge, blazhennyy, optimistischyy, zhizneradostnyy)
              ],
    'Sad': ['sad', 'unhappy', 'down', 'crying', 'depressed', 'lonely', 'bad', 'terrible', 'miserable', 'upset', 'sorrow', 'grief', 'heartbroken', 'tearful', 'gloomy', 'dejected', 'woeful', 'pessimistic', 'crestfallen', 'unfortunate',
            'dukh', 'udaas', 'rona', 'bura', 'nirash', 'aansu', 'dukhi', 'akela', 'kharaab', 'bhayanak', 'dukh bhara', 'mayus', 'shok', 'gham', 'dil tuta', 'aankhon mein aansu', 'udasi', 'niraasha', 'shokakul', 'badnaseeb', # Hindi keywords
            'duhkha', 'khedda', 'aluvudu', 'niraashe', 'kanneeru', 'sankata', 'ekangi', 'kettaddu', 'bhayanaka', 'duhkha bhara', 'manassu kedda', 'shoka', 'vyakulata', 'hrudaya bidda', 'kanneeru tumbida', 'udasa', 'niraasheya', 'shokagrasta', 'durbhagyavanta', # Kannada keywords
            'thukkam', 'varutham', 'ketta', 'sogham', 'kanneer', 'kavalai', 'thaniyaaga', 'mosamaana', 'payanagamana', 'thukkamana', 'manam uraindha', 'sokam', 'thuyaram', 'idhaiyam udaindha', 'kanneer niraindha', 'udasinam', 'niraasai', 'sokaththil', 'durbhagyasaali', # Tamil keywords
            'dukham', 'badhaga', 'ledu', 'nirasapadina', 'kanneeru', 'chinta', 'ekantham', 'chedina', 'bhayanakaramaina', 'dukhamaina', 'manasu bagaledu', 'sokam', 'vyakulam', 'hrudayam pagilindi', 'kanneeru nimmina', 'udasinam', 'niraasa', 'sokamlo', 'durbhagyavanthudu', # Telugu keywords
            'triste', 'malheureux', 'abattu', 'pleurer', 'déprimé', 'solitaire', 'mauvais', 'terrible', 'misérable', 'contrarié', 'chagrin', 'deuil', 'le cœur brisé', 'en larmes', 'sombre', 'abattu', 'affligé', 'pessimiste', 'découragé', 'malchanceux', # French keywords
            'triste', 'infeliz', 'abatido', 'llorando', 'deprimido', 'solitario', 'malo', 'terrible', 'miserable', 'molesto', 'dolor', 'duelo', 'con el corazón roto', 'lloroso', 'sombrío', 'abatido', 'afligido', 'pesimista', 'desanimado', 'desafortunado', # Spanish keywords
            'traurig', 'unglücklich', 'niedergeschlagen', 'weinend', 'deprimiert', 'einsam', 'schlecht', 'schrecklich', 'elend', 'verärgert', 'kummer', 'trauer', 'am Boden zerstört', 'tränenreich', 'düster', 'niedergeschlagen', 'bekümmert', 'pessimistisch', 'mutlos', 'unglücklich', # German keywords
            '悲しい' , '不幸な' , '落ち込んでいる' , '泣いている' , '憂鬱な' , '寂しい' , '悪い' , 'ひどい' , '惨めな' , '動揺している' , '悲しみ' , '悲嘆' , '心が折れた' , '涙ながらの' , '暗い' , '意気消沈した' , '悲嘆に暮れた' , '悲観的' , 'がっかりした' , '不運な', # Japanese keywords (Kanashii, Fukou na, Ochikonde iru, Naite iru, Yuuutsu na, Sabishii, Warui, Hidoi, Mijime na, Douyou shite iru, Kanashimi, Hitan, Kokoro ga oreta, Namida nagara no, Kurai, Ikishouchin shita, Hitan ni kureta, Hikanteki, Gakkari shita, Fūn na)
            'грустный' , 'несчастливый' , 'подавленный' , 'плачущий' , 'унылый' , 'одинокий' , 'плохой' , 'ужасный' , 'жалкий' , 'расстроенный' , 'печаль' , 'горе' , 'с разбитым сердцем' , 'слезливый' , 'мрачный' , 'удрученный' , 'огорченный' , 'пессимистичный' , 'унылый' , 'несчастный', # Russian keywords (grustnyy, neschastlivyy, podavlennyy, plachushchiy, unylyy, odinokiy, plokhoy, uzhasnyy, zhalkiy, rasstroennyy, pechal', gore, s razbitym serdtsem, slezlivyy, mrachnyy, udrachennyy, ogorchennyy, pessimistichnyy, unylyy, neschastnyy)
            ],
    'Angry': ['angry', 'mad', 'frustrated', 'annoyed', 'hate', 'furious', 'irritated', 'rage', 'pissed', 'resentful', 'infuriated', 'exasperated', 'hostile', 'indignant', 'wrathful', 'livid', 'savage', 'venomous', 'bitter', 'cross',
              'gussa', 'naraz', 'pareshan', 'krodh', 'chidh', 'aakrosh', 'gusse mein', 'naraazgi', 'pareshaani', 'ghrina', 'krodhit', 'vyakulta', 'shatru', 'rosh', 'krodhpoorn', 'laal peela', 'jangli', 'vishaila', 'kadva', 'gussewala', # Hindi keywords
              'kopishta', 'thika', 'kopa', 'iris', 'aakrosha', 'kopadalli', 'naaraajgi', 'pareshaani', 'dwesha', 'kopishtha', 'vyakulata', 'shatru', 'rosha', 'kopapurvaka', 'kempu-haladi', 'kaadu', 'visha', 'kahi', 'kopishta', # Kannada keywords
              'kobam', 'sinam', 'aathiram', 'murattu', 'kopaththil', 'sinaththil', 'aathiraththil', 'veruppu', 'kopaththaal', 'kalakkaththil', 'pagai', 'ragam', 'kopaththudan', 'sigappu-manjal', 'kaattu', 'visham', 'kasappu', 'kopaththaana', # Tamil keywords
              'kopam', 'chiraku', 'rodanam', 'manduthunna', 'kopamlo', 'chirakuluga', 'rodanamlo', 'dwesham', 'kopamtho', 'kalathanamlo', 'shatruvu', 'rosam', 'kopamgala', 'erupu-pasupu', 'adavi', 'vishamu', 'chedu', 'kopamaina', # Telugu keywords
              'en colère', 'fou', 'frustré', 'ennuyé', 'haine', 'furieux', 'irrit', 'rage', 'énervé', 'ressentiment', 'exaspéré', 'hostile', 'indigné', 'coléreux', 'livide', 'sauvage', 'venimeux', 'amer', 'mécontent', # French keywords
              'enojado', 'loco', 'frustrado', 'molesto', 'odio', 'furioso', 'irritado', 'rabia', 'cabreado', 'resentido', 'enfurecido', 'exasperado', 'hostil', 'indignado', 'iracundo', 'lívido', 'salvaje', 'venenoso', 'amargo', 'enojado', # Spanish keywords
              'wütend', 'verrückt', 'frustriert', 'genervt', 'hass', 'zornig', 'irritiert', 'wut', 'angefressen', 'verärgert', 'wutschnaubend', 'verärgert', 'feindselig', 'empört', 'zornig', 'blass vor Wut', 'wild', 'giftig', 'bitter', 'verärgert', # German keywords
              '怒っている' , '狂った' , 'イライラしている' , '迷惑している' , '憎しみ' , '激怒している' , 'いらいらしている' , '怒り' , 'むかついている' , '憤慨している' , '激怒した' , 'うんざりした' , '敵対的' , '憤慨した' , '激怒した' , '真っ青な' , '野生の' , '毒のある' , '苦い' , '不機嫌な', # Japanese keywords (Okotte iru, Kurutta, Iraira shite iru, Meiwaku shite iru, Nikushimi, Gekido shite iru, Iraira shite iru, Ikari, Mukatsuite iru, Fungai shite iru, Gekido shita, Unzari shita, Tekitai-teki, Fungai shita, Gekido shita, Massao na, Yasei no, Doku no aru, Nigai, Fukigen na)
              'сердитый' , 'сумасшедший' , 'расстроенный' , 'раздраженный' , 'ненависть' , 'яростный' , 'раздраженный' , 'гнев' , 'злой' , 'обиженный' , 'взбешенный' , 'раздраженный' , 'враждебный' , 'возмущенный' , 'гневный' , 'бледный от злости' , 'дикий' , 'ядовитый' , 'горький' , 'сердитый', # Russian keywords (serdityy, sumasshedshiy, rasstroennyy, razdrazhennyy, nenavist', yarostnyy, razdrazhennyy, gnev, zloy, obizhennyy, vzbeshennyy, razdrazhennyy, vrazhdebnyy, vozmushchennyy, gnevnyy, blednyy ot zlosti, dikiy, yadovityy, gor'kiy, serdityy)
              ],
    'Surprised': ['surprise', 'wow', 'unexpected', 'shocked', 'unbelievable', 'amazing', 'astonished', 'startled', '😳', '😲', '😮', 'gasp', 'stunned', 'bewildered', 'taken aback', 'flabbergasted', 'aghast', 'dumbfounded', 'speechless', 'awe',
                  'aश्चर्य', 'hairan', 'achanak', 'chaunkna', 'vishmay', 'hakka-bakka', 'dhang reh jana', 'aશ્ચર્યચકિત', 'hakka bakka reh gaya', 'dhang reh gaya', 'saans ruk gayi', 'achambha', 'chakrit', 'ghabrahat', 'hairat', 'dang', 'vichlit', 'bolti band', 'adbhut', # Hindi keywords
                  'ashcharya', 'achchanak', 'vismaya', 'dikku', 'hakka-bakka', 'dhang ulidaru', 'achcharikkitu', 'vismayachakita', 'hakka bakka aada', 'dhang ulidaru', 'usiru nintaru', 'ashcharya', 'chakita', 'ghabrahat', 'ashcharya', 'dang', 'vichalita', 'matu bandu', 'adbhuta', # Kannada keywords
                  'aacharyam', 'athisayam', 'viyappu', 'titukkittu', 'hakka-bakka', 'thangku nindranar', 'acharyappattaar', 'viyappadainthaar', 'hakka bakka aanaar', 'thangku nindranar', 'moochchu nindru vittathu', 'acharyam', 'chakitham', 'payam', 'aacharyam', 'dang', 'kuzhappam', 'pesa mudiyaamal', 'adhisayam', # Tamil keywords
                  'ascharyam', 'adbhutam', 'achchanak', 'kalavarapadina', 'hakka-bakka', 'dhanguliddaru', 'ascharyapoyaru', 'adbhutapoyaru', 'hakka bakka ayyaru', 'dhanguliddaru', 'swasam aagipoyindi', 'ascharyam', 'chakitham', 'bhayam', 'ascharyam', 'dang', 'kalaham', 'mataleka', 'adbhutamaina', # Telugu keywords
                  'surprise', 'wow', 'inattendu', 'choqué', 'incroyable', 'étonnant', 'stupéfait', 'surpris', 'haleter', 'abasourdi', 'perplexe', 'pris au dépourvu', 'sidéré', 'consterné', 'muet', 'admiration', # French keywords
                  'sorpresa', 'guau', 'inesperado', 'conmocionado', 'increíble', 'asombroso', 'asombrado', 'sobresaltado', 'jadear', 'atónito', 'perplejo', 'tomado por sorpresa', 'pasmado', 'consternado', 'mudo', 'asombro', # Spanish keywords
                  'überraschung', 'wow', 'unerwartet', 'schockiert', 'unglaublich', 'erstaunlich', 'erstaunt', 'erschrocken', 'keuchen', 'betäubt', 'verwirrt', 'überrumpelt', 'fassungslos', 'bestürzt', 'sprachlos', 'ehrfurcht', # German keywords
                  '驚き' , 'うわー' , '予期しない' , 'ショックを受けた' , '信じられない' , '素晴らしい' , '呆然とした' , 'びっくりした' , 'あえぎ' , '気絶した' , '当惑した' , '不意を突かれた' , 'あっけにとられた' , 'がく然とした' , '言葉を失った' , '畏敬の念', # Japanese keywords (Odoroki, Uwā, yoki shinai, Shokku o uketa, Shinji rarenai, Subarashii, Bōzen to shita, Bikkuri shita, Aegi, Kizetsu shita, Touwaku shita, Fui o tsukareta, Akke ni torareta, Gakuzen to shita, Kotoba o ushinatta, Ikeinou nen)
                  'сюрприз' , 'вау' , 'неожиданный' , 'шокированный' , 'невероятный' , 'удивительный' , 'изумленный' , 'вздрогнувший' , 'задыхаться' , 'ошеломленный' , 'сбитый с толку' , 'захваченный врасплох' , 'ошарашенный' , 'потрясенный' , 'безмолвный' , 'трепет', # Russian keywords (syurpriz, vau, neozhidannyy, shokirovannyy, neveroyatnyy, udvitel'nyy, izumlennyy, vzdragivshiy, zadykhat'sya, oshelomlennyy, sbityy s tolku, zakhvachennyy vrasplokh, osharachennyy, potryasennyy, bezmolvnyy, trepet)
                  ],
    'Disgust': ['disgust', 'gross', 'eww', 'nasty', 'horrible', 'sick', 'revolting', 'appalled', '🤢', '🤮', 'unpleasant', 'offensive', 'repugnant', 'loathsome', 'vile', 'foul', 'nauseating', 'distasteful', 'abominable', 'detestable',
                'ghin', 'ganda', 'beemar', 'nafrat', 'aruchi', 'ghinauna', 'apriya', 'apmaanajanak', 'ghrinaaspad', 'ghrina', 'bimaar', 'ghinauni', 'kharaab', 'nafrat karna', 'ghinaune', 'apriyakar', 'apmaanajanak', 'ghrinaaspad', 'ghrina', 'ghinaune', # Hindi keywords
                'aruchu', 'kedda', 'asahyavada', 'nindya', 'ghrina', 'aruchikara', 'apriya', 'avamana', 'ghrinaaspada', 'ghrina', 'rogi', 'aruchikara', 'kettaddu', 'dvesha', 'ghrinaaspada', 'apriyavada', 'avamana', 'ghrinaaspada', 'ghrina', 'ghrinaaspada', # Kannada keywords
                'veruppu', 'asingam', 'aruvaruppu', 'kadalikkira', 'ghrina', 'aruchikara', 'apriya', 'avamana', 'ghrinaaspada', 'ghrina', 'noyali', 'aruchikara', 'ketta', 'veruppu', 'ghrinaaspada', 'apriyamaana', 'avamana', 'ghrinaaspada', 'ghrina', 'ghrinaaspada', # Tamil keywords
                'grahanam', 'asahanam', 'ekkuva', 'vipareetamaina', 'ghrina', 'aruchikaramaina', 'apriyaramaina', 'avamana', 'ghrinaaspadamaina', 'ghrina', 'rogini', 'aruchikaramaina', 'chedina', 'dwesham', 'ghrinaaspadamaina', 'apriyaramaina', 'avamana', 'ghrinaaspadamaina', 'ghrina', 'ghrinaaspadamaina', # Telugu keywords
                'dégoût', 'brut', 'beurk', 'méchant', 'horrible', 'malade', 'répugnant', 'consterné', 'désagréable', 'offensant', 'répugnant', 'odieux', 'vil', 'immonde', 'nauséabond', 'désagréable', 'abominable', 'détestable', # French keywords
                'asco', 'bruto', 'puaj', 'desagradable', 'horrible', 'enfermo', 'repugnante', 'horrorizado', 'desagradable', 'ofensivo', 'repugnante', 'odioso', 'vil', 'inmundo', 'nauseabundo', 'desagradable', 'abominable', 'detestable', # Spanish keywords
                'ekel', 'brutto', 'igitt', 'böse', 'schrecklich', 'krank', 'widerlich', 'entsetzt', 'unangenehm', 'beleidigend', 'abstoßend', 'widerwärtig', 'gemein', 'scheußlich', 'übelkeitserregend', 'unangenehm', 'abscheulich', 'verabscheuungswürdig', # German keywords
                '嫌悪' , '総体的' , 'えー' , '嫌な' , '恐ろしい' , '病気' , '嫌悪感' , 'がく然とした' , '不快な' , '攻撃的な' , '嫌悪感を催す' , '忌まわしい' , '卑劣な' , '不潔な' , '吐き気を催す' , '不味い' , '忌まわしい' , '忌まわしい', # Japanese keywords (Ken'o, Sōtai-teki, Ē, Iya na, Osoroshii, Byōki, Ken'okan, Gakuzen to shita, Fukai na, Kōgeki-teki na, Ken'okan o moyōsu, Imawoshii, Hiretsu na, Fuketsu na, Hakike o moyōsu, Mazui, Imawoshii, Imawoshii)
                'отвращение' , 'грубый' , 'фу' , 'неприятный' , 'ужасный' , 'больной' , 'отвратительный' , 'испуганный' , 'неприятный' , 'оскорбительный' , 'отвратительный' , 'отвратительный' , 'мерзкий' , 'грязный' , 'тошнотворный' , 'неприятный' , 'отвратительный' , 'отвратительный', # Russian keywords (otvrashcheniye, grubyy, fu, nepriyatnyy, uzhasnyy, bol'noy, otvratitel'nyy, ispugannyy, nepriyatnyy, oskorbitel'nyy, otvratitel'nyy, otvratitel'nyy, merzkiy, gryaznyy, toshnotvornyy, nepriyatnyy, otvratitel'nyy, otvratitel'nyy)
                ]
}

def detect_emotion(text):
    """
    Detects emotion based on keywords in the provided text.
    Returns the detected emotion (e.g., 'Happy', 'Sad') or 'Neutral' if no keywords match.
    """
    if not text:
        return 'Neutral'

    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()

    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return emotion

    return 'Neutral' # Default if no emotion keywords are found

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def get_db_connection():
    """Establishes and returns a new database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}", flush=True)
        return None

def is_logged_in():
    """Checks if a user is logged in based on session data."""
    return 'loggedin' in session and session['loggedin']

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.route('/')
def home():
    """Redirects to login page if not logged in, otherwise to index."""
    if is_logged_in():
        # Render the speech-to-text page if logged in
        return render_template('index.html')
    else:
        # Redirect to the login page if not logged in
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login and displays the login form."""
    msg = ''
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
             msg = 'Please enter both email and password!'
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                # Retrieve user by email
                cursor.execute('SELECT * FROM users WHERE EMAIL = %s', (email,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()

                if user and check_password_hash(user['PASSWORD'], password):
                    # Password is correct, create session
                    session['loggedin'] = True
                    session['id'] = user['id']
                    session['email'] = user['EMAIL']
                    session['fname'] = user['FNAME'] # Store first name in session
                    msg = 'Logged in successfully!'
                    print(f"User logged in: {email}", flush=True)
                    # Redirect to the home page (which will render index.html)
                    return redirect(url_for('home'))
                elif user:
                     msg = 'Incorrect password!'
                     print(f"Failed login attempt for {email}: Incorrect password", flush=True)
                else:
                    msg = 'Email not found!'
                    print(f"Failed login attempt: Email '{email}' not found", flush=True)
            else:
                msg = 'Database connection failed.'
                print("Login failed: Database connection error.", flush=True)

    # Render the signin template for GET requests or failed POST attempts
    # Pass the message to the template
    return render_template('signin.html', msg=msg)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user registration and displays the signup form."""
    msg = ''
    if request.method == 'POST':
        # Get form data
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        # Optional fields
        age = request.form.get('age')
        dob_str = request.form.get('dob')
        dob = None

        if not fname or not lname or not email or not password:
            msg = 'Please fill out all required fields (First Name, Last Name, Email, Password)!'
        else:
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    msg = 'Invalid date format for Date of Birth. UseYYYY-MM-DD.'
                    # Render signup template with error message
                    return render_template('signup.html', msg=msg)

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                # Check if account already exists with this email
                cursor.execute('SELECT * FROM users WHERE EMAIL = %s', (email,))
                account = cursor.fetchone()

                if account:
                    msg = 'Account already exists with this email!'
                    print(f"Signup failed: Account already exists for {email}", flush=True)
                else:
                    # Hash the password before storing
                    hashed_password = generate_password_hash(password)

                    # Insert new user into the database
                    cursor.execute('INSERT INTO users (FNAME, LNAME, AGE, DOB, EMAIL, PASSWORD) VALUES (%s, %s, %s, %s, %s, %s)',
                                   (fname, lname, age, dob, email, hashed_password))
                    conn.commit()
                    msg = 'You have successfully signed up! Please log in.'
                    print(f"New user signed up: {email}", flush=True)
                    # After successful signup, redirect to the login page with a success message
                    return redirect(url_for('login', msg=msg))

                cursor.close()
                conn.close()
            else:
                msg = 'Database connection failed during signup.'
                print("Signup failed: Database connection error.", flush=True)

    # Render the signup template for GET requests or failed POST attempts
    # Pass the message to the template
    return render_template('signup.html', msg=msg)


@app.route('/logout')
def logout():
    """Logs out the user by clearing the session."""
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    session.pop('fname', None)
    msg = 'You have been logged out.'
    print("User logged out.", flush=True)
    # Redirect to the login page with a logout message
    return redirect(url_for('login', msg=msg))


@app.route('/upload', methods=['POST'])
def upload():
    """
    Handles audio file uploads, converts to WAV (if needed), performs
    speech-to-text transcription using the specified language, performs
    emotion detection, saves files and transcript details, and returns
    transcription, translation, and detected emotion.

    This route is now protected and requires the user to be logged in.
    """
    # --- Check if user is logged in ---
    if not is_logged_in():
        print("Access denied to /upload: User not logged in.", flush=True)
        # Return a JSON response indicating unauthorized access
        return jsonify({"message": "Access denied. Please log in to use this feature."}), 401 # Unauthorized

    # Initialize variables
    server_transcript = "[Transcription not attempted]"
    wav_path = None
    original_audio_path = None
    user_transcript = request.form.get('transcript', '[User transcript not provided]') # Browser transcript
    language_code = request.form.get('language', 'en-IN') # Default language if not provided by frontend
    language_used = language_code # Track the language code actually used for transcription
    detected_emotion = 'Neutral' # Default emotion
    translated_response = "Translation not available."

    try:
        # --- 1. Get Uploaded Data (Audio File and Form Data) ---
        audio_file = request.files.get('audio')

        # --- Basic Validation ---
        if not audio_file or not audio_file.filename:
            return jsonify({"message": "No audio file received or file has no filename."}), 400

        # --- 2. Prepare File Paths (using timestamp and user ID for uniqueness) ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = audio_file.filename
        original_extension = os.path.splitext(original_filename)[1]

        # Handle cases where the browser might not send an extension but sends mime type
        if not original_extension:
            mime_type = audio_file.content_type
            if mime_type == 'audio/webm': original_extension = '.webm'
            elif mime_type == 'audio/ogg': original_extension = '.ogg'
            elif mime_type == 'audio/wav': original_extension = '.wav'
            elif mime_type == 'audio/mp4': original_extension = '.mp4'
            elif mime_type == 'audio/aac': original_extension = '.aac'
            elif mime_type == 'audio/mpeg': original_extension = '.mp3'
            else: original_extension = '.bin'

        # Construct full paths for saving files
        original_audio_path = os.path.join(UPLOAD_FOLDER, f"audio_{timestamp}{original_extension}")
        user_id = session.get('id', 'unknown_user') # Get user ID from session
        wav_filename = f"audio_{user_id}_{timestamp}.wav"
        wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)
        transcript_filename = f"transcript_{user_id}_{timestamp}_{language_code}.txt"
        transcript_path = os.path.join(UPLOAD_FOLDER, transcript_filename)


        # --- 3. Save Original Uploaded Audio File ---
        audio_file.save(original_audio_path)

        # --- 4. Convert Audio to WAV using pydub (if not already WAV) ---
        if original_extension.lower() != '.wav':
            try:
                audio_segment = AudioSegment.from_file(original_audio_path)
                audio_segment.export(wav_path, format="wav")
            except Exception as convert_err:
                print(f"Error during audio conversion: {convert_err}", flush=True)
                print(traceback.format_exc(), flush=True)
                server_transcript = "[Audio conversion failed, transcription skipped]"
                print(f"--> FINAL STATUS ({language_used}): {server_transcript}", flush=True)
                # Optionally clean up the failed original file if needed
                # if os.path.exists(original_audio_path): os.remove(original_audio_path)
                return jsonify({
                    "message": "Error converting audio file to WAV.",
                    "error": str(convert_err),
                    "user_transcript": user_transcript,
                    "server_transcript": server_transcript,
                    "language_used": language_used,
                    "detected_emotion": "Error",
                    "translated_response": "Translation not available."
                }), 500
        else:
             # If the uploaded file is already WAV, copy it to the user-specific WAV path
             import shutil
             shutil.copy(original_audio_path, wav_path)
             # Clean up the original file if it's not the one we are keeping
             if original_audio_path != wav_path:
                 os.remove(original_audio_path)


        # --- 5. Transcribe the Converted WAV File using SpeechRecognition ---
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)

            server_transcript = recognizer.recognize_google(audio_data, language=language_code)

        # Handle common SpeechRecognition errors
        except sr.UnknownValueError:
            server_transcript = f"[Could not understand audio ({language_code})]"
        except sr.RequestError as e:
            server_transcript = f"[Speech Recognition request failed ({language_code}): {e}]"
        except ValueError as ve:
             server_transcript = f"[Error during transcription, possibly invalid language code: {language_code}]"
             language_used = "Error"
        except Exception as sr_err:
             print(f"An unexpected error occurred during speech recognition: {sr_err}", flush=True)
             print(traceback.format_exc(), flush=True)
             server_transcript = f"[Unexpected error during transcription ({language_code})]"

        # *** Print the final transcription result or status message to the console ***
        print(f"--> TRANSCRIPT ({language_used}): {server_transcript}", flush=True)

        # --- 6. Perform Emotion Detection ---
        if server_transcript and not server_transcript.startswith('['): # Only detect emotion if transcription was successful
            f=open('D:/code/1/task.txt','w')
            f.write(server_transcript)
            f.close()
            sleep(3)
            f=open('D:/code/1/output.txt','r')
            res=f.read()
            f.close()

            detected_emotion = res#detect_emotion(server_transcript)
            print(f"Detected emotion: {detected_emotion}", flush=True)
        else:
             detected_emotion = 'Neutral' # Default to Neutral if transcription failed or was not attempted
             print(f"Emotion detection skipped due to transcription status. Defaulting to: {detected_emotion}", flush=True)


        # --- 7. Perform Translation (if translator is available) ---
        if translator and server_transcript and not server_transcript.startswith('['): # Only translate if transcription was attempted and not an error message
            try:
                # Detect language of the server transcript
                detected_lang_result = translator.detect(server_transcript) # <-- Language Detection happens here
                detected_lang_code = detected_lang_result.lang
                print(f"Detected language for translation: {detected_lang_code}, Confidence: {detected_lang_result.confidence}", flush=True)

                # Translate the server transcript to English (or another target language)
                english_translation_obj = translator.translate(server_transcript, src=detected_lang_code, dest='en')
                english_translation = english_translation_obj.text
                print(f"Translated to English: {english_translation}", flush=True)

                # Example: Translate a predefined response back to the detected language
                predefined_response_en = f"Okay, I heard you say: '{english_translation}'. Based on that, I detected the emotion: '{detected_emotion}'. How can I help further?"
                translated_response_obj = translator.translate(predefined_response_en, src='en', dest=detected_lang_code)
                translated_response = translated_response_obj.text
                print(f"Translated response to {detected_lang_code}: {translated_response}", flush=True)

            except Exception as translate_err:
                print(f"Error during translation: {translate_err}", flush=True)
                translated_response = f"[Translation failed: {translate_err}]"
        elif not translator:
             print("Translator not initialized, skipping translation.", flush=True)


        # --- 8. Save Transcript Details to a Text File ---
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"User ID: {user_id}\n")
                f.write(f"Requested Language: {language_code}\n")
                f.write(f"Original File: {os.path.basename(original_audio_path)}\n")
                f.write(f"Processed WAV File: {os.path.basename(wav_path)}\n")
                f.write(f"User transcript (from frontend): {user_transcript}\n")
                f.write(f"Server transcript ({language_used}): {server_transcript}\n")
                f.write(f"Detected Emotion: {detected_emotion}\n")
                if translator:
                    f.write(f"Translated Response: {translated_response}\n")

        except Exception as write_err:
            print(f"Error saving transcript file '{transcript_path}': {write_err}", flush=True)


        # --- 9. Return JSON Response to Frontend ---
        return jsonify({
            "message": "Audio processed, transcription and emotion detection attempted.",
            "user_transcript": user_transcript, # Browser's transcript
            "server_transcript": server_transcript, # Server's transcript
            "detected_emotion": detected_emotion, # Send detected emotion
            "translated_response": translated_response, # Translated response
            "language_used": language_used, # Send back language actually used
            "original_filename": original_filename,
            # Note: Not returning internal file paths for security
        }), 200

    except Exception as e:
        # --- Global Error Handling for the entire route ---
        print(f"--> UNEXPECTED ERROR in /upload: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({
            "message": "An internal server error occurred during processing.",
            "error": str(e),
            "user_transcript": user_transcript,
            "server_transcript": server_transcript,
            "language_used": language_used,
            "detected_emotion": "Error", # Indicate error in emotion detection
            "translated_response": "Translation not available due to error."
        }), 500

@app.route('/get_emotion_file/<emotion_name>/<file_type>')
def get_emotion_file(emotion_name, file_type):
    """
    Serves a random file from the specified emotion and file type subfolder.
    Requires the user to be logged in.
    """
    # --- Check if user is logged in ---
    if not is_logged_in():
        print(f"Access denied to /get_emotion_file: User not logged in.", flush=True)
        return jsonify({"message": "Access denied. Please log in."}), 401 # Unauthorized

    # Validate emotion and file type
    if emotion_name not in EMOTIONS or file_type not in FILE_TYPES:
        print(f"Invalid request for emotion file: emotion={emotion_name}, file_type={file_type}", flush=True)
        return jsonify({"message": "Invalid emotion or file type."}), 400 # Bad Request

    # Construct the directory path based on the corrected structure: static/files/file_type/emotion/
    # Use app.root_path to get the absolute path of the application root
    directory = os.path.join(app.root_path, MEDIA_FOLDER, file_type, emotion_name)

    # --- Debugging Prints ---
    print(f"Attempting to list files in directory: {directory}", flush=True)
    # --- End Debugging Prints ---

    try:
        # List all files in the directory
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

        # --- Debugging Prints ---
        print(f"Files found in {directory}: {files}", flush=True)
        # --- End Debugging Prints ---


        if not files:
            print(f"No files found in directory: {directory}", flush=True)
            return jsonify({"message": f"No {file_type} files found for emotion '{emotion_name}'."}), 404 # Not Found

        # Select a random file
        random_file = random.choice(files)
        print(f"Serving random file: {random_file} from {directory}", flush=True)

        # Serve the file
        # send_from_directory requires the directory path and the filename
        # The directory path should be relative to the application root or an absolute path
        # We are already constructing an absolute path using app.root_path
        return send_from_directory(directory, random_file)

    except FileNotFoundError:
        print(f"Directory not found: {directory}", flush=True)
        return jsonify({"message": "Resource directory not found."}), 404 # Not Found
    except Exception as e:
        print(f"Error serving emotion file: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        return jsonify({"message": "An internal server error occurred while fetching the file."}), 500 # Internal Server Error


# -----------------------------------------------------------------------------
# Main Execution Block
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    print(f"--- Flask server starting ---", flush=True)
    print(f"--- Uploads will be saved to: {os.path.abspath(UPLOAD_FOLDER)} ---", flush=True)
    # Corrected print to show the absolute path of the MEDIA_FOLDER
    print(f"--- Media files will be served from: {os.path.abspath(MEDIA_FOLDER)} ---", flush=True)
    print(f"--- Access the application at http://127.0.0.1:5000/ ---", flush=True)
    # Run the Flask development server
    app.run(debug=True, port=5000)
