from pathlib import Path
import os
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
PROJECT_DIR=BASE_DIR.parent
load_dotenv(PROJECT_DIR/'.env')
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY','local-demo-key-yatrasense-do-not-use-for-deployment')
DEBUG=os.getenv('DJANGO_DEBUG','1')=='1'
ALLOWED_HOSTS=os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS=['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','corsheaders','rest_framework','rest_framework.authtoken','travel']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','corsheaders.middleware.CorsMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':os.getenv('DJANGO_DB_PATH',str(BASE_DIR/'db.sqlite3'))}}
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE='en-us'
TIME_ZONE='Asia/Kathmandu'
USE_I18N=True
USE_TZ=True
STATIC_URL='static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:4173','http://127.0.0.1:4173']
REST_FRAMEWORK={'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.TokenAuthentication'],'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.AllowAny'],'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.AnonRateThrottle','rest_framework.throttling.UserRateThrottle'],'DEFAULT_THROTTLE_RATES':{'anon':'120/min','user':'300/min'}}
ML_SERVICE_URL=os.getenv('ML_SERVICE_URL','http://127.0.0.1:8001')
DATA_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024
