import tkinter as tk
from tkinter import *
from tkinter import Text
from tkinter.messagebox import showinfo, askokcancel
import cv2
import os
import numpy as np
from PIL import Image, ImageTk
import pandas as pd
import datetime
from time import strftime
import time
import tkinter.ttk as ttk
import pickle
import sqlite3
import face_recognition
from imutils import paths
import subprocess
from threading import Thread
import threading
import psutil
import re
from tkinter import messagebox
from configparser import ConfigParser
from tkinter import filedialog
import shutil
from os import listdir
from os.path import isfile, join
import glob
import tkinter.scrolledtext as scrolledtext
from apscheduler.schedulers.background import BlockingScheduler
import webbrowser
from tkVideoPlayer import TkinterVideo
import platform

# Импорт модулей логирования и обработки ошибок
try:
    from logger_config import (
        main_logger, auth_logger, camera_logger, recognition_logger,
        database_logger, ui_logger, stream_logger,
        DatabaseError, CameraError, AuthenticationError, RecognitionError,
        StreamError, ConfigurationError, log_exception, safe_execute
    )
    from db_manager import (
        DatabaseManager, get_settings_db, get_auth_db, 
        get_objects_db, get_camera_db
    )
    LOGGING_ENABLED = True
    main_logger.info("Модули логирования и обработки ошибок загружены успешно")
except ImportError as e:
    LOGGING_ENABLED = False
    print(f"ПРЕДУПРЕЖДЕНИЕ: Модули логирования не найдены: {e}")
    print("Приложение будет работать с базовым выводом в консоль")

# Импорт модуля безопасности паролей
try:
    from password_security import (
        hash_password as secure_hash_password,
        check_password as secure_check_password,
        verify_and_check_migration,
        validate_password,
        get_password_strength,
        login_tracker,
        PasswordConfig
    )
    PASSWORD_SECURITY_ENABLED = True
    if LOGGING_ENABLED:
        main_logger.info("Модуль безопасности паролей загружен успешно")
except ImportError as e:
    PASSWORD_SECURITY_ENABLED = False
    if LOGGING_ENABLED:
        main_logger.warning(f"Модуль безопасности паролей не найден: {e}")
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: Модуль безопасности паролей не найден: {e}")

if platform.system() == 'Windows':
    run_system = "Windows"
elif platform.system() == 'Linux':
    run_system = "Linux"
else:
	run_system = "Others"

abc = os.path.isfile(os.path.join(os.getcwd(), 'data/setting.db'))
if abc == False:
	file_path = "data/setting.db"
	try:
		connection = sqlite3.connect(os.path.join(os.getcwd(), file_path))
		cursor = connection.cursor()
		cursor.execute('''
							CREATE TABLE IF NOT EXISTS setting (
							parametr_name TEXT,
							set01 TEXT,
							set02 TEXT,
							set03 TEXT,
							set04 TEXT,
							set05 TEXT,
							set06 TEXT,
							set07 TEXT,
							set08 TEXT,
							set09 TEXT,
							set10 TEXT
							)
							''')
		# Добавляем начальные настройки
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02, set03, set04) VALUES (?, ?, ?, ?, ?)',
					   ('model_forone', '0', '0', '0', '0'))  # время на одну. объектов. файлов. размер
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('numberreestr', '10000'))
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('model_algoritm', 'cnn'))
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('objects_pic', 'circle'))
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('enabled_sec', '1'))
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02) VALUES (?, ?, ?)',
					   ('stream', '127.0.0.1', '8000'))
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02) VALUES (?, ?, ?)',
					   ('stream_res_qua', '704', '90')) # разрешение. качество
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('resolut_video_model', '60')) #  резрешение для модели
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02, set03) VALUES (?, ?, ?, ?)',
					   ('facerecog_granici1_face', '2', '4', '6'))
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02, set03) VALUES (?, ?, ?, ?)',
					   ('video_save', '10', 'XVID', '15')) # продолжит. кодек. кадров
		cursor.execute('INSERT INTO setting (parametr_name, set01) VALUES (?, ?)',
					   ('foto_save', '10')) #  охранение кадров для известных
		cursor.execute('INSERT INTO setting (parametr_name, set01, set02) VALUES (?, ?, ?)',
					   ('oper_jurnal', '5', '60')) # групировка строк в оперативном журнале
		connection.commit()
		connection.close()
		if LOGGING_ENABLED:
			main_logger.info("База данных настроек создана и инициализирована успешно")
	except sqlite3.Error as e:
		if LOGGING_ENABLED:
			main_logger.error(f"Ошибка при создании базы данных настроек: {e}")
			log_exception(main_logger, e, "Инициализация setting.db")
		else:
			print(f"ОШИБКА: Не удалось создать базу данных настроек: {e}")
else:
	if LOGGING_ENABLED:
		main_logger.info("Файл data/setting.db существует")
	else:
		print("файл data\\setting.db существует")


ti = time.time()
print(ti)
dt_object = datetime.datetime.fromtimestamp(ti)
print(dt_object)
rv1 = None
TrainImageRunStatus = False
TrackIm = False
stop_thread_rv1: bool = False
rv = None
WS1 = None
WS = None
WS_spot: bool = False
imshowwindows = False
canvaswindows = True
TrackImwindows = True
trakingdef1st = False
activeuserlogin = None
activeusergroupe = None
activatmainprogram = False
stream = None
timesec = "1"
pid = None
camera01link = None
imgtk = None
ct1 = False
height = 0
width = 0
fps = 0
cam_set_a = 0
cam_set_b = 0
cam_set_c = 0
cam_set_d = 0
set02_user = 0
set03_user = 0
object_name = None
objeck_family  = None
categor = None
objeck_homenumb = None
objeck_apartmentnumb  = None
objeck_floornumb  = None
objeck_tel = None
formodel_var = None
formodel_first_name = None
spisok_ob_vivod = []
enabled_checkbutton_view_scr_state = True
enabled_checkbutton_view_scr_state_last = True
enabled_checkbutton_video_close_state = True
img_text_lab = None
img_text_lab01 = None
img_text_lab02 = None
img_text_lab03 = None
img_text_lab04 = None
img_text_lab_csv = None
img_text_lab_kard = None
ch01 = 0
text_lab = ""
text_lab02 = ""
text_lab03 = ""
text_lab04 = ""
text_lab05 = ""
text_lab_kard = ""
catalog_foto_ob = None
razmer_icon_temp = None
checkboxes_cat = {}
checklist_cat = ""
fileList2 = None
icon_size_width = None
icon_size_height = None
data_view = None
checklist = ""
checkboxes = {}
obect_view01 = None
imgs_csv = []
checkboxes_csv = {}
imgs_csv_m = []
checkboxes_csv_m = {}
window001 = None
model_algoritm_var = "cnn"
v_record_dlit_var = 30
v_record_frames_var = 15
v_record_codec_var = 'XVID'
object_pic_var = 'circle'
facerecog_granici1_face_var = 2
facerecog_granici2_face_var = 4
facerecog_granici3_face_var = 6
resolut_video_model_var = '100'
foto_save_kadr_var = 10
for_start_model_mess = False
window_csv = None
win_katalog02 = None
objekt_list = None
win_katalog = None
label_locallink = None
label_locallink_vlc = None
imgs_csv_m_v = []
checkboxes_csv_m_v = {}
imgs_csv_m_v_d = []
checkboxes_csv_m_v_d = {}
data_file_csv_for_search = None

timesecset = None
def timesec_d():
	global timesec
	global timesecset
	if timesec == "1":
		timesecset = str('%d %B  %H:%M:%S')
	else:
		timesecset = str('%d %B  %H:%M')

def openFolder(folder_path):
    command = 'explorer.exe "' + folder_path + '"'
	#command = f'explorer.exe "{folder_path}"'
    os.system(command)

def bdauthencontrol():
	"""
	Проверяет наличие учётной записи администратора в базе данных.
	Если администратор не найден - вызывает функцию создания.
	"""
	file_path = "data/avtorizachiy.db"
	
	if os.path.isfile(os.path.join(os.getcwd(), file_path)) is True:
		try:
			conn = sqlite3.connect(file_path)
			c = conn.cursor()
			c.execute('SELECT groupe FROM logins')
			groupes = c.fetchall()
			adminrezult = False
			
			for groupe in groupes:
				if groupe[0] == "admin":
					if LOGGING_ENABLED:
						auth_logger.info(f"Найден администратор: {groupe}")
					else:
						print(groupe)
					conn.close()
					adminrezult = True
					break
				else:
					adminrezult = False
			
			if adminrezult:
				if LOGGING_ENABLED:
					auth_logger.info("Администратор системы найден в базе данных")
				else:
					print("adminrezult " + str(adminrezult))
			else:
				if LOGGING_ENABLED:
					auth_logger.warning("Администратор не найден, запуск мастера создания")
				creatadmin()
				
		except sqlite3.Error as e:
			if LOGGING_ENABLED:
				auth_logger.error(f"Ошибка при проверке администратора: {e}")
				log_exception(auth_logger, e, "bdauthencontrol")
			else:
				print(f"ОШИБКА БД при проверке администратора: {e}")
			creatadmin()
		finally:
			try:
				conn.close()
			except:
				pass
	else:
		if LOGGING_ENABLED:
			auth_logger.info("База авторизации не найдена, создание нового администратора")
		creatadmin()

def creatadmin():
	"""
	Создаёт учётную запись администратора системы.
	Если база данных авторизации не существует - создаёт её.
	"""
	import sqlite3
	import re
	import hashlib
	
	file_path = "data/avtorizachiy.db"
	
	try:
		connection = sqlite3.connect(os.path.join(os.getcwd(), file_path))
		cursor = connection.cursor()
		cursor.execute('''
			    CREATE TABLE IF NOT EXISTS logins (
			    id INTEGER PRIMARY KEY,
			    logins TEXT NOT NULL,
			    passwordtab TEXT NOT NULL,
			    groupe TEXT NOT NULL,
			    email TEXT,
			    set01 TEXT,
			    set02 TEXT,
			    set03 TEXT,
			    set04 TEXT,
			    set05 TEXT,
			    set06 TEXT,
			    set07 TEXT,
			    set08 TEXT,
			    set09 TEXT,
			    set10 TEXT
			    )
			    ''')
		connection.commit()
		connection.close()
		
		if LOGGING_ENABLED:
			auth_logger.info("Таблица авторизации создана/проверена успешно")
			
	except sqlite3.Error as e:
		if LOGGING_ENABLED:
			auth_logger.error(f"Ошибка при создании таблицы авторизации: {e}")
			log_exception(auth_logger, e, "creatadmin - создание БД")
		else:
			print(f"ОШИБКА: Не удалось создать таблицу авторизации: {e}")
		return  # Прерываем выполнение, если БД недоступна


	window = tk.Tk()
	# window = Toplevel()
	window.attributes('-topmost', 'true')
	# заголовок окна
	window.title('Дозор')
	window.iconbitmap(os.path.join(os.getcwd(), 'data/dozor.ico'))
	# размер окна
	window.geometry('500x450+600+100')
	window.configure(bg="lightgrey")
	# можно ли изменять размер окна - нет
	window.resizable(False, False)

	# кортежи и словари, содержащие настройки шрифтов и отступов
	font_header = ('Helvetica', 12)
	font_entry = ('Helvetica', 10)
	label_font = ('Helvetica', 10)
	base_padding = {'padx': 10, 'pady': 8}
	header_padding = {'padx': 10, 'pady': 12}
	s = ttk.Style()
	s.configure('my.TButton', font=('Helvetica', 10), background='lightgrey')

	userid = None
	username = None
	password = None
	email = None
	statustext = None

	#main_status = Label(window, text="", font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	#main_status.pack()

	def clickedtest():
		global userid, username, password, email
		userid = username_entry.get()
		password = password_entry.get()
		password02 = password_entry02.get()
		email = email_entry.get()
		userid = userid.strip()  # удаляем пробелы в начале и в конце строки
		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()
		cursor.execute('SELECT logins FROM logins')
		logins = cursor.fetchall()
		loginfound = False
		for login in logins:
			print(login)
			if login[0] == userid:
				print("Login found " + str(userid))
				loginfound = True
				connection.close()
				break
			else:
				loginfound = False
				print("Login not found")
		connection.close()
		if loginfound == False:
			if len(userid) < 21:
				if re.match(r'^[a-zA-Z0-9]+$', userid):
					if len(password) < 30:
						if password == password02:
							print("ok")
							clickedad()
						else:
							print("пароли не совпадают")
							res = str("Пароли не совпадают")
							main_status.configure(text=res, fg="red")
					else:
						print("длинный пароль")
						res = str("Пароль до 30 символов")
						main_status.configure(text=res, fg="red")
				else:
					print("nevernet simvoli")
					res = str("Недопустимые символы в имени пользователя")
					main_status.configure(text=res, fg="red")
			else:
				res = str("Имя пользователя до 20 символов")
				main_status.configure(text=res, fg="red")
				print("ukorotit")
		else:
			res = str("Имя пользователя уже существует")
			main_status.configure(text=res, fg="red")
			print("uje est login")

	def clickedad():
		global userid, username, password, email
		passwordh = password

		def hash_password(passwordh):
			return hashlib.sha256(passwordh.encode()).hexdigest()

		def check_password(stored_password, provided_password):
			return stored_password == hashlib.sha256(provided_password.encode()).hexdigest()

		stored_password = hash_password(passwordh)
		print(stored_password)
		# print(check_password(stored_password, '123456'))  # True
		# print(check_password(stored_password, 'wrong_password'))  # False

		print("Add")
		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()

		# Добавляем нового пользователя
		cursor.execute('INSERT INTO logins (logins, passwordtab, groupe, email) VALUES (?, ?, ?, ?)',
					   (userid, stored_password, 'admin', email))
		# Сохраняем изменения и закрываем соединение
		connection.commit()
		connection.close()
		window.destroy()


	#main_label = Label(window, text='Дозорный', font=font_header, justify=CENTER,
	#				   **header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	#main_label.pack()
	main_label1 = Label(window, text='Создать учетную запись администратора', font=font_header, justify=CENTER,
						**header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	main_label1.pack()

	# метка для поля ввода имени
	username_label1 = Label(window, text='Имя (login)', font=label_font, **base_padding, bg="lightgrey")
	username_label1.pack()
	username_label2 = Label(window, text='(англйиские буквы, цифры, до 20 символов):', font=label_font,
							**base_padding, bg="lightgrey")
	username_label2.pack()
	# поле ввода имени
	username_entry = Entry(window, bg='#fff', fg='#444', font=font_entry)
	username_entry.pack()

	# метка для поля ввода пароля
	password_label = Label(window, text='Пароль (до 30 символов):', font=label_font, **base_padding, bg="lightgrey")
	password_label.pack()

	# поле ввода пароля
	password_entry = Entry(window, bg='#fff', fg='#444', font=font_entry)
	password_entry.pack()

	# метка для поля ввода пароля
	password_label = Label(window, text='Повтор ввода пароля:', font=label_font, **base_padding, bg="lightgrey")
	password_label.pack()

	# поле ввода пароля
	password_entry02 = Entry(window, bg='#fff', fg='#444', font=font_entry)
	password_entry02.pack()

	# метка для поля ввода пароля
	email_label = Label(window, text='E-mail, телефон, комментарий:', font=label_font, **base_padding, bg="lightgrey")
	email_label.pack()

	# поле ввода пароля
	email_entry = Entry(window, bg='#fff', fg='#444', width=50, font=font_entry)
	email_entry.pack()

	# кнопка отправки формы
	send_btn = ttk.Button(window, text='Создать', style='my.TButton',command=clickedtest)
	send_btn.pack(**base_padding)

	send_btn = ttk.Button(window, text='Отмена', style='my.TButton',command=window.destroy)
	send_btn.pack(**base_padding)

	main_status = Label(window, text="", font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	main_status.pack()

	# запускаем главный цикл окна
	window.mainloop()

bdauthencontrol()

def Authentication(): #авторизация при запуске программы
	import tkinter as tk
	import sqlite3
	import hashlib
	global activeuserlogin, activeusergroupe, activatmainprogram
	activeuserlogin = None
	activeusergroupe = None
	activatmainprogram = False
	global window001


	window001 = tk.Tk()
	# window = Toplevel()
    # заголовок окна
	window001.title('Дозор')
	window001.attributes('-topmost', 'true')
	# размер окна
	win_color = 'lightskyblue'  #azure3
	window001.geometry('760x510+600+100')
	# можно ли изменять размер окна - нет
	window001.resizable(False, False)
	window001.configure(bg=win_color)
	s = ttk.Style()
	s.configure('my.TButton', font=('Helvetica', 10), background='lightgrey')

	# кортежи и словари, содержащие настройки шрифтов и отступов
	font_header = ('Helvetica', 12)
	font_entry = ('Helvetica', 12)
	label_font = ('Helvetica', 12)
	base_padding = {'padx': 5, 'pady': 5}
	header_padding = {'padx': 5, 'pady': 5}

	username = None
	password = None
	statustext = None

	# обработчик нажатия на клавишу 'Войти'
	def clicked():
		def hash_password(password):
			return hashlib.sha256(password.encode()).hexdigest()

		def check_password(stored_password, provided_password):
			return stored_password == hashlib.sha256(provided_password.encode()).hexdigest()

		userid = username_entry.get()
		password = password_entry.get()
		userid = userid.strip()  # удаляем пробелы в начале и в конце строки
		# password = password.strip() #удаляем пробелы в начале и в конце строки - для пароля не применяем
		stored_password = hash_password(password)
		print(stored_password)

		loginfound = False
		passfound = False
		global activeuserlogin, activeusergroupe, activatmainprogram

		connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
		cursor = connection.cursor()
		# Выбираем всех пользователей
		cursor.execute('SELECT logins FROM logins')
		logins = cursor.fetchall()

		# Выводим результаты
		for login in logins:
			print(login)
			if login[0] == userid:
				print("Login found " + str(userid))
				loginfound = True
				connection.close()
				break
			else:
				loginfound = False
				print("Login not found")
		connection.close()

		if loginfound:
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			# Выбираем всех пользователей
			cursor.execute('SELECT passwordtab FROM logins WHERE logins = ?', (userid,))
			passwords = cursor.fetchall()
			for passworda in passwords:
				print(passworda)
				if passworda[0] == stored_password:
					print("Pass Successful " + str(passworda[0]))
					passfound = True
					connection.close()
					break
				else:
					passfound = False
					print("Pass Failed")
			connection.close()

		# You can add your own validation logic here
		if loginfound is True and passfound is True:
			activeuserlogin = userid
			print(activeuserlogin)
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			cursor.execute('SELECT groupe FROM logins WHERE logins = ?', (userid,))
			groupes = cursor.fetchall()
			for groupe in groupes:
				print(groupe)
				if groupe[0] == "admin":
					print("admin Successful ")
					activeusergroupe = "admin"
					connection.close()
					break
				if groupe[0] == "operator":
					print("operator Successful ")
					activeusergroupe = "operator"
					connection.close()
					break
			connection.close()
			print(activeusergroupe)
			res = str("Login Successful.")
			main_status.configure(text=res)
			#messagebox.showinfo("Login Successful", "Welcome, Admin!")
			if activeusergroupe == "admin":
				pass
			activatmainprogram = True
			window001.destroy()
		else:
			res = str("Неправильное имя \nили пароль!")
			main_status.configure(text=res, fg="red", bg=win_color)
			#messagebox.showerror("Ошибка авторизации", "Неправильное имя пользователя или пароль")

	main_label2 = Label(window001, text='Авторизация', font=font_header, bg=win_color, justify=CENTER, **header_padding)
	# помещаем виджет в окно по принципу один виджет под другим
	#main_label2.pack()
	main_label2.place(x=80, y=10)

	# метка для поля ввода имени
	username_label = Label(window001, text='Имя пользователя:', font=label_font,  bg=win_color, **base_padding)
	#username_label.pack()
	username_label.place(x=40, y=45)

	# поле ввода имени
	username_entry = Entry(window001, bg='#fff', fg='#444', font=font_entry)
	#username_entry.pack()
	username_entry.place(x=50, y=80)

	# метка для поля ввода пароля
	password_label = Label(window001, text='Пароль:', font=label_font,  bg=win_color, **base_padding)
	#password_label.pack()
	password_label.place(x=40, y=115)

	# поле ввода пароля
	password_entry = Entry(window001, bg='#fff', fg='#444', show="*", font=font_entry)
	#password_entry.pack()
	password_entry.place(x=50, y=150)

	# кнопка отправки формы
	send_btn = ttk.Button(window001, text='Войти', style='my.TButton', command=clicked)  # clicked
	#send_btn.pack(**base_padding)
	send_btn.place(x=150, y=200)

	main_status = Label(window001, text="", font=font_header, bg=win_color, justify=CENTER, **header_padding)
	# помещаем виджет в окно по принципу один виджет под другим
	#main_status.pack()
	main_status.place(x=40, y=235)

	path111 = os.path.join(os.getcwd(),"data/photo/style/circle_p_001.png")
	img_text_lab = ImageTk.PhotoImage(Image.open(path111).resize((500, 500)))
	panel = Label(window001, image=img_text_lab)
	panel.place(x=250, y=3)

	# запускаем главный цикл окна
	window001.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
	window001.mainloop()

#Чтение настроек пользователя
def user_setting_read():
	global set02_user, set03_user
	# set01 - размер иконок в форме модели
	# set02 - автостарт трансляции
	# set03 - автостарт распознования
	# set04 - цвет интефейса
	# set05 - размер шрифта, цветы шрифта и фона протокола событий
	# set06 -
	# set07 -
	# set08 -
	# set09 -
	# set10 -
	connection = sqlite3.connect('data/avtorizachiy.db')
	cursor = connection.cursor()
	cursor.execute('SELECT set02, set03 FROM logins WHERE logins = ?', (activeuserlogin,))
	sets_user = cursor.fetchall()
	for row in sets_user:
		set02_user = row[0]
		set03_user = row[1]
		print("Чтение настроек для " + activeuserlogin + ":, set02 :", set02_user, ", set03 :", set03_user)
	connection.close()

def main_setting_read():
	global model_algoritm_var
	global resolut_video_model_var
	global foto_save_kadr_var
	global v_record_dlit_var
	global v_record_codec_var
	global v_record_frames_var
	global objects_pic_var
	global timesec
	global oper_jurnal_laststroki_var
	global oper_jurnal_laststrokitime_var
	global camera01link
	model_algoritm_var1 = "model_algoritm"
	v_record_codec_var1 = 'video_save'
	object_pic_var1 = "objects_pic"
	enabled_sec_var1 = "enabled_sec"
	resolut_video_model_var1 = 'resolut_video_model'
	facerecog_granici1_face_var1 = 'facerecog_granici1_face'
	foto_save_kadr_var1 = 'foto_save'
	oper_jurnal_var1 = 'oper_jurnal'
	parametr_stream_var1 = 'stream'
	connection = sqlite3.connect('data\setting.db')
	cursor = connection.cursor()
	cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr_stream_var1,))
	parametr_stream_var11 = cursor.fetchall()
	for row in parametr_stream_var11:
		host_acc = row[0]
		stream_port_var = row[1]
	camera01link =  "http://127.0.0.1:" + str(stream_port_var) + "/video_feed"
	print("назначение порта", camera01link)
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (model_algoritm_var1,))
	model_algoritm_var11 = cursor.fetchall()
	for row in model_algoritm_var11:
		model_algoritm_var = row[0]
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (foto_save_kadr_var1,))
	foto_save_kadr_var11 = cursor.fetchall()
	for row in foto_save_kadr_var11:
		foto_save_kadr_var = row[0]
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (resolut_video_model_var1,))
	resolut_video_model_var11 = cursor.fetchall()
	for row in resolut_video_model_var11:
		resolut_video_model_var = row[0]
	cursor.execute('SELECT set01, set02, set03 FROM setting WHERE parametr_name = ?', (facerecog_granici1_face_var1,))
	facerecog_granici1_face_var11 = cursor.fetchall()
	for row in facerecog_granici1_face_var11:
		facerecog_granici1_face_var = row[0]
		facerecog_granici2_face_var = row[1]
		facerecog_granici3_face_var = row[2]
	cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (oper_jurnal_var1,))
	oper_jurnal_var11 = cursor.fetchall()
	for row in oper_jurnal_var11:
		oper_jurnal_laststroki_var = row[0]
		oper_jurnal_laststrokitime_var = row[1]
	cursor.execute('SELECT set01, set02, set03 FROM setting WHERE parametr_name = ?', (v_record_codec_var1,))
	v_record_codec_var11 = cursor.fetchall()
	for row in v_record_codec_var11:
		v_record_dlit_var = row[0]
		v_record_codec_var = row[1]
		v_record_frames_var = row[2]
		#print(v_record_codec_var)
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (object_pic_var1,))
	object_pic_var11 = cursor.fetchall()
	for row in object_pic_var11:
		object_pic_var = row[0]
		#print(object_pic_var)
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (enabled_sec_var1,))
	enabled_sec_var11 = cursor.fetchall()
	for row in enabled_sec_var11:
		timesec = row[0]
	connection.close()

def reload_stream_setting():
	global camera01link
	parametr_stream_var1 = 'stream'
	connection = sqlite3.connect('data\setting.db')
	cursor = connection.cursor()
	cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr_stream_var1,))
	parametr_stream_var11 = cursor.fetchall()
	for row in parametr_stream_var11:
		host_acc = row[0]
		stream_port_var = row[1]
	camera01link = "http://127.0.0.1:" + str(stream_port_var) + "/video_feed"
	connection.close()



Authentication()
user_setting_read()
main_setting_read()

def on_closing():
	#print(str(3333))
	exitmainprogramm()
	#if messagebox.askokcancel("Quit", "Do you want to quit?"):
        #window.destroy()


def on_closing_model_status():
	global window_csv
	TranImage_control_button()
	window_csv.destroy()

def on_closing_model_status_2():
	global win_katalog02
	TranImage_control_button()
	win_katalog02.destroy()

def on_closing_model_status_3():
	global objekt_list
	TranImage_control_button()
	objekt_list.destroy()

def on_closing_model_status_4():
	global win_katalog
	TranImage_control_button()
	win_katalog.destroy()

# Основное окно программы
root1 = tk.Tk()
root1.title('Дозор')
root1.configure(background='lightgrey')
root1.geometry('1820x950+50+50')
root1.state('zoomed')
#root1.resizable(False, False)
root1.grid_rowconfigure(0, weight=5)
root1.grid_columnconfigure(0, weight=5)
root1.protocol("WM_DELETE_WINDOW", on_closing)

style = ttk.Style()
style.configure('TFrame', background='lightgrey') #gray87
style.configure("TNotebook.Tab", background="red", foreground="black", font=('Helvetica', 10))
style.map('TNotebook.Tab', foreground=[('selected', 'blue'), ('active', 'black')], background=[('selected', 'black')])
#style.configure('my.TButton', background='blue', font=('Helvetica', 10))
style.configure("My.TLabel",  # имя стиля
			font="helvetica 10",  # шрифт
			foreground="#000000",  # цвет текста
			#padding=0,  # отступы
			background="lightgrey")  # фоновый цвет
style.configure('TCheckbutton', background='lightgrey', font="helvetica 10")

window = ttk.Notebook(root1)
window.pack(expand=True, fill=BOTH)
frame1 = ttk.Frame(window)
frame2 = ttk.Frame(window)
frame3 = ttk.Frame(window)
frame4 = ttk.Frame(window)
frame5 = ttk.Frame(window)

frame3.pack(fill=BOTH, expand=True)
frame1.pack(fill=BOTH, expand=True)
frame2.pack(fill=BOTH, expand=True)
frame4.pack(fill=BOTH, expand=True)
frame5.pack(fill=BOTH, expand=True)


# добавляем фреймы в качестве вкладок
window.add(frame3, text="   Управление   ")
window.add(frame1, text="   События   ")
window.add(frame2, text="   Объекты   ")
window.add(frame4, text="   Настройки   ")
window.add(frame5, text="   Выход   ")

labletime = tk.Label(window, font=('Helvetica', 13, 'bold'), background='darkslateblue', foreground='white', width=22, height=1)
labletime.place(x=3, y=30)

timesec_d()
def timestroka():
	global timesecset
	string = strftime(timesecset)
	labletime.config(text=string)
	labletime.after(1000, timestroka)
timestroka()

def open_link(event):
	webbrowser.open_new(camera01link)

def open_link_vlc(event):
	os.system(f'start vlc "{camera01link}"')

#lbl = tk.Label(window, text="No.",
			#width=20, height=2, fg="green",
			#bg="white", font=('times', 15, ' bold '))
#lbl.place(x=400, y=200)

#txt = tk.Entry(window,
			#width=20, bg="white",
			#fg="green", font=('times', 15, ' bold '))
#txt.place(x=700, y=215)

#lbl2 = tk.Label(window, text="Name",
				#width=20, fg="green", bg="white",
				#height=2, font=('times', 15, ' bold '))
#lbl2.place(x=400, y=300)

#txt2 = tk.Entry(window, width=20,
				#bg="white", fg="green",
				#font=('times', 15, ' bold '))
#txt2.place(x=700, y=315)


# The function below is used for checking
# whether the text below is number or not ?

def Authenticationinside():
	import hashlib
	global activeuserlogin, activeusergroupe

	def bez_avtoriz():
		global activeuserlogin, activeusergroupe
		activeuserlogin = None
		activeusergroupe = None
		lableuser.config(text="Не авториз.", fg="red")
		message.configure(text="Пользователь не авторизован!")
		windowinside.destroy()

	windowinside = tk.Toplevel()
	windowinside.attributes('-topmost', 'true')
	# заголовок окна
	windowinside.title('Авторизация / Смена пользователя "Дозор"')
	# размер окна
	windowinside.geometry('460x310+650+220')
	windowinside.configure(bg="lightgrey")
	# можно ли изменять размер окна - нет
	windowinside.resizable(False, False)
	s = ttk.Style()
	s.configure('my.TButton', font=('Helvetica', 10), background='lightgrey')

	# кортежи и словари, содержащие настройки шрифтов и отступов
	font_header = ('Helvetica', 12)
	font_entry = ('Helvetica', 10)
	label_font = ('Helvetica', 10)
	base_padding = {'padx': 10, 'pady': 12}
	header_padding = {'padx': 10, 'pady': 5}

	username = None
	password = None
	statustext = None

	#main_status = Label(windowinside, text="", font=font_header, justify=CENTER, **header_padding)
	# помещаем виджет в окно по принципу один виджет под другим
	#main_status.pack()

	# обработчик нажатия на клавишу 'Войти'
	def clicked():
		def hash_password(password):
			return hashlib.sha256(password.encode()).hexdigest()

		def check_password(stored_password, provided_password):
			return stored_password == hashlib.sha256(provided_password.encode()).hexdigest()

		userid = username_entry.get()
		password = password_entry.get()
		userid = userid.strip()  # удаляем пробелы в начале и в конце строки
		# password = password.strip() #удаляем пробелы в начале и в конце строки
		stored_password = hash_password(password)
		print(stored_password)
		#print(check_password(stored_password, '123456'))  # True
		#print(check_password(stored_password, 'wrong_password'))  # False

		loginfound = False
		passfound = False
		global activeuserlogin, activeusergroupe

		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()
		# Выбираем всех пользователей
		cursor.execute('SELECT logins FROM logins')
		logins = cursor.fetchall()

		# Выводим результаты
		for login in logins:
			print(login)
			if login[0] == userid:
				#print("Login found " + str(userid))
				loginfound = True
				connection.close()
				break
			else:
				loginfound = False
				#print("Login not found")
		connection.close()

		if loginfound:
			connection = sqlite3.connect('data/avtorizachiy.db')
			cursor = connection.cursor()
			# Выбираем всех пользователей
			cursor.execute('SELECT passwordtab FROM logins WHERE logins = ?', (userid,))
			passwords = cursor.fetchall()
			for passworda in passwords:
				print(passworda)
				if passworda[0] == stored_password:
					print("Pass Successful " + str(passworda[0]))
					passfound = True
					connection.close()
					break
				else:
					passfound = False
					print("Pass Failed")
			connection.close()

		# You can add your own validation logic here
		if loginfound is True and passfound is True:
			activeuserlogin = userid
			print(activeuserlogin)
			connection = sqlite3.connect('data/avtorizachiy.db')
			cursor = connection.cursor()
			cursor.execute('SELECT groupe FROM logins WHERE logins = ?', (userid,))
			groupes = cursor.fetchall()
			for groupe in groupes:
				print(groupe)
				if groupe[0] == "admin":
					#print("admin Successful ")
					activeusergroupe = "admin"
					connection.close()
					break
				if groupe[0] == "operator":
					#print("operator Successful ")
					activeusergroupe = "operator"
					connection.close()
					break
			connection.close()
			#print(activeusergroupe)
			#res2 = str("Login Successful.")
			#main_status.configure(text=res2)
			res = "Режим: " + activeusergroupe + ", модель распозн.: " + model_algoritm_var + ", видео кодек: " + v_record_codec_var + ")."
			message.configure(text=res)
			lableuser.config(text="Логин: " + str(activeuserlogin), fg="black")
			#messagebox.showinfo("Login Successful", "Welcome, Admin!")
			if activeusergroupe == "admin":
				#print("ок")
				pass
			user_setting_read()
			time.sleep(0.3)
			if set02_user == "1":
				canvas_checkbutton.state(["selected"])
			else:
				canvas_checkbutton.state(['!selected'])
			if set03_user == "1":
				canvas_checkbutton03.state(["selected"])
			else:
				canvas_checkbutton03.state(['!selected'])
			windowinside.destroy()
		else:
			res = str("Неправильное имя пользователя или пароль")
			main_status.configure(text=res, fg="red")
			#messagebox.showerror("Ошибка авторизации", "Неправильное имя пользователя или пароль")

	# заголовок формы: настроены шрифт (font), отцентрирован (justify), добавлены отступы для заголовка
	# для всех остальных виджетов настройки делаются также
	main_label = Label(windowinside, text='Авторизация / Смена пользователя', font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	main_label.pack()

	# метка для поля ввода имени
	username_label = Label(windowinside, text='Имя пользователя', font=label_font, **base_padding, bg="lightgrey")
	username_label.pack()

	# поле ввода имени
	username_entry = Entry(windowinside, bg='#fff', fg='#444', font=font_entry)
	username_entry.pack()

	# метка для поля ввода пароля
	password_label = Label(windowinside, text='Пароль', font=label_font, **base_padding, bg="lightgrey")
	password_label.pack()

	# поле ввода пароля
	password_entry = Entry(windowinside, bg='#fff', fg='#444', show="*", font=font_entry)
	password_entry.pack()

	# кнопка отправки формы
	send_btn = ttk.Button(windowinside, text='Войти', style='my.TButton', command=clicked)
	send_btn.pack(**base_padding)

	send_btn = ttk.Button(windowinside, text='Продолжить без авторизации', style='my.TButton', command=bez_avtoriz)
	send_btn.pack(**base_padding)

	main_status = Label(windowinside, text="", font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
	# помещаем виджет в окно по принципу один виджет под другим
	main_status.pack()

	windowinside.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
	windowinside.grab_set()

	# запускаем главный цикл окна
	#windowinside.mainloop()




def combine_funcs(*funcs):
	def combined_func(*args, **kwargs):
		for f in funcs:
			f(*args, **kwargs)
	return combined_func





def ModelControl():
	try:
		data = pickle.loads(open(os.path.join(os.getcwd(),'encodings.pickle', 'rb')).read())  # encodings here
	except FileNotFoundError:
		res = str("Файл encodings.pickle не обнаружен. Выполните обучение или восстановите файл из архива")
		message.configure(text=res)

def objekt_list_edit():
	global activeusergroupe
	global object_pic_var
	global objekt_list
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		objekt_list = tk.Toplevel(window)
		objekt_list.title('Список объектов')
		objekt_list.configure(bg='lightgrey')
		objekt_list.geometry("1400x700+300+100")
		objekt_list.protocol("WM_DELETE_WINDOW", on_closing_model_status_3)
		object_pic_var1 = "objects_pic"
		connection = sqlite3.connect('data\setting.db')
		cursor = connection.cursor()
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (object_pic_var1,))
		object_pic_var11 = cursor.fetchall()
		for row in object_pic_var11:
			object_pic_var = row[0]
			print(object_pic_var)
		connection.close()
		# Read our config file and get colors
		parser = ConfigParser()
		parser.read(os.path.join(os.getcwd(),"data/treebase.ini"))
		saved_primary_color = parser.get('colors', 'primary_color')
		saved_secondary_color = parser.get('colors', 'secondary_color')
		saved_highlight_color = parser.get('colors', 'highlight_color')

		def query_database():
			# Clear the Treeview
			for record in my_tree.get_children():
				my_tree.delete(record)

			# Create a database or connect to one that exists
			conn = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))

			# Create a cursor instance
			c = conn.cursor()

			c.execute("SELECT rowid, * FROM People")
			records = c.fetchall()

			# Add our data to the screen
			global count
			count = 0

			# for record in records:
			#	print(record)

			for record in records:
				if count % 2 == 0:
					if record[4] == '1':
						categoriy_s = 'Жилец'
					if record[4] == '2':
						categoriy_s = 'Гость'
					if record[4] == '3':
						categoriy_s = 'Специальный'
					if record[4] == '4':
						categoriy_s = 'Внимание!'
					# print(categoriy_s)
					my_tree.insert(parent='', index='end', iid=count, text='',
								   values=(
								   record[1], record[2], categoriy_s, record[3], record[6], record[7], record[9],
								   record[8], record[10], record[11]),
								   tags=('evenrow',))
				else:
					if record[4] == '1':
						categoriy_s = 'Жилец'
					if record[4] == '2':
						categoriy_s = 'Гость'
					if record[4] == '3':
						categoriy_s = 'Специальный'
					if record[4] == '4':
						categoriy_s = 'Внимание!'
					# print(categoriy_s)
					my_tree.insert(parent='', index='end', iid=count, text='',
								   values=(
								   record[1], record[2], categoriy_s, record[3], record[6], record[7], record[9],
								   record[8], record[10], record[11]),
								   tags=('oddrow',))
				# increment counter
				count += 1

			# Commit changes
			conn.commit()

			# Close our connection
			conn.close()

		def search_records():
			lookup_record = search_entry.get()
			lookup_record_kv = search_kv.get()
			lookup_record_name = search_name.get()
			lookup_record_fal = search_fal.get()
			lookup_record_kateg = search_kateg.get()
			# close the search box
			search.destroy()
			print(lookup_record, lookup_record_kv, lookup_record_name, lookup_record_fal, lookup_record_kateg)
			lookup_record = lookup_record.strip()
			lookup_record_kv = lookup_record_kv.strip()
			lookup_record_name = lookup_record_name.strip()
			lookup_record_fal = lookup_record_fal.strip()
			lookup_record_kateg = lookup_record_kateg.strip()
			lookup_record_kateg_bd = None
			print(lookup_record, lookup_record_kv, lookup_record_name, lookup_record_fal, lookup_record_kateg)
			if lookup_record_kateg == 'Жилец':
				lookup_record_kateg_bd = '1'
			if lookup_record_kateg == 'Гость':
				lookup_record_kateg_bd = '2'
			if lookup_record_kateg == 'Специальный':
				lookup_record_kateg_bd = '3'
			if lookup_record_kateg == 'Внимание!':
				lookup_record_kateg_bd = '4'
			conditions_ob = []
			params_ob = []

			if lookup_record:
				conditions_ob.append("floornumb LIKE ?")
				params_ob.append(lookup_record)

			if lookup_record_kv:
				conditions_ob.append("apartmentnumb LIKE ?")
				params_ob.append(lookup_record_kv)

			if lookup_record_name:
				conditions_ob.append("first_name LIKE ?")
				params_ob.append(lookup_record_name)

			if lookup_record_fal:
				conditions_ob.append("last_name LIKE ?")
				params_ob.append(lookup_record_fal)

			if lookup_record_kateg_bd:
				conditions_ob.append("category LIKE ?")
				params_ob.append(lookup_record_kateg_bd)

			# Clear the Treeview
			for record in my_tree.get_children():
				my_tree.delete(record)

			# Create a database or connect to one that exists
			conn = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))

			# Create a cursor instance
			c = conn.cursor()

			base_query = "SELECT rowid, * FROM People"
			if conditions_ob:
				query = f"{base_query} WHERE " + " AND ".join(conditions_ob)
			else:
				query = base_query  # Если нет условий, выбираем все

			c.execute(query, params_ob)

			#c.execute("SELECT rowid, * FROM People WHERE floornumb LIKE ? AND apartmentnumb LIKE ?",
			#		  (lookup_record, lookup_record_kv))

			records = c.fetchall()

			# Add our data to the screen
			global count
			count = 0

			# for record in records:
			#	print(record)

			for record in records:
				if count % 2 == 0:
					if record[4] == '1':
						categoriy_s = 'Жилец'
					if record[4] == '2':
						categoriy_s = 'Гость'
					if record[4] == '3':
						categoriy_s = 'Специальный'
					if record[4] == '4':
						categoriy_s = 'Внимание!'
					my_tree.insert(parent='', index='end', iid=count, text='',
								   values=(
								   record[1], record[2], categoriy_s, record[3], record[6], record[7], record[9],
								   record[8], record[10], record[11]),
								   tags=('evenrow',))
				else:
					if record[4] == '1':
						categoriy_s = 'Жилец'
					if record[4] == '2':
						categoriy_s = 'Гость'
					if record[4] == '3':
						categoriy_s = 'Специальный'
					if record[4] == '4':
						categoriy_s = 'Внимание!'
					my_tree.insert(parent='', index='end', iid=count, text='',
								   values=(
								   record[1], record[2], categoriy_s, record[3], record[6], record[7], record[9],
								   record[8], record[10], record[11]),
								   tags=('oddrow',))
				# increment counter
				count += 1

			# Commit changes
			conn.commit()

			# Close our connection
			conn.close()

		def lookup_records():
			global search_entry, search_name, search_fal, search_kv, search_kateg, search

			search = Toplevel(objekt_list)
			search.title("Поиск")
			search.geometry("300x450+600+200")
			# search.iconbitmap('c:/gui/codemy.ico')

            #search_lab = Label(search, text="Поиск по одному или нескольким значениям:")
			#search_lab.pack(padx=10, pady=10)

			search_frame2 = LabelFrame(search, text="Имя")
			search_frame2.pack(padx=10, pady=10)

			search_name = Entry(search_frame2, font=("Helvetica", 10))
			search_name.pack(pady=10, padx=10)

			search_frame3 = LabelFrame(search, text="Фамилия")
			search_frame3.pack(padx=10, pady=10)

			search_fal = Entry(search_frame3, font=("Helvetica", 10))
			search_fal.pack(pady=10, padx=10)

			search_frame = LabelFrame(search, text="Этаж")
			search_frame.pack(padx=10, pady=10)

			# Add entry box
			search_entry = Entry(search_frame, font=("Helvetica", 10))
			search_entry.pack(pady=10, padx=10)

			search_frame4 = LabelFrame(search, text="Номер квартиры")
			search_frame4.pack(padx=10, pady=10)

			search_kv = Entry(search_frame4, font=("Helvetica", 10))
			search_kv.pack(pady=10, padx=10)

			search_frame5 = LabelFrame(search, text="Категория")
			search_frame5.pack(padx=10, pady=10)

			search_kateg_var = ['', 'Жилец', 'Гость', 'Специальный', 'Внимание!']
			search_kateg = ttk.Combobox(search_frame5, values=search_kateg_var, state="readonly")
			#search_kateg = Entry(search_frame5, font=("Helvetica", 10))
			search_kateg.pack(pady=10, padx=10)

			# Add button
			search_button = Button(search, text="Искать", command=search_records)
			search_button.pack(padx=10, pady=10)
			search.grab_set()


		# Add Menu
		my_menu = Menu(objekt_list)
		objekt_list.config(menu=my_menu)

		# Configure our menu
		option_menu = Menu(my_menu, tearoff=0)
		# my_dd_cascade(label="Options", menu=option_menu)
		# Drop dowmenu.an menu
		# option_menu.add_command(label="Primary Color", command=primary_color)
		# option_menu.add_command(label="Secondary Color", command=secondary_color)
		# option_menu.add_command(label="Highlight Color", command=highlight_color)
		# option_menu.add_separator()
		# option_menu.add_command(label="Reset Colors", command=reset_colors)
		# option_menu.add_separator()
		# option_menu.add_command(label="Exit", command=root.quit)

		# Search Menu
		search_menu = Menu(my_menu, tearoff=0)
		my_menu.add_cascade(label="Поиск", menu=search_menu)
		# Drop down menu
		search_menu.add_command(label="Поиск", command=lookup_records)
		search_menu.add_separator()
		search_menu.add_command(label="Очистить результаты поиска", command=query_database)

		def open_file():
			circle = False
			k = modelfolder_entry.get()
			if k == "Unknown" or k == "":
				if k == "Unknown":
					messagebox.showinfo("Внимание!", "Для строки с именем Unknown фото загрузить нельзя!")
				if k == "":
					messagebox.showinfo("Внимание!", "Для загрузки фото выделите строчку!")
			else:
				global object_pic_var
				if object_pic_var == 'circle':
					circle = True
				modelfolderp = os.path.join(os.getcwd(),"data/dataset/" + modelfolder_entry.get())
				filepath = filedialog.askopenfilename(title="Выбор файла", initialdir=modelfolderp, defaultextension="jpg")
				if filepath != "":
					# return filepath
					#print(filepath)
					file02 = modelfolder_entry.get()
					#print(file02)
					if circle == True:
						img1 = cv2.imread(os.path.join(os.getcwd(),'data/photo/objects/white_circle.png'))
						h1, w1 = img1.shape[:2]
						# read image 2
						img2_file = filepath
						img2 = cv2.imread(img2_file)
						img2 = cv2.resize(img2, (400, 400), interpolation=cv2.INTER_LINEAR)  # cv2.INTER_AREA - для сжатия
						h2, w2 = img2.shape[:2]
						# convert img1 to grayscale
						gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
						# threshold to binary
						thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)[1]
						thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
						# crop second image to size of first image
						img2_crop = img2[0:h1, 0:w1]
						# combine img1, img2_crop with threshold as mask
						result = np.where(thresh == 0, img2_crop, img1)
						# save results
						cv2.imwrite(os.path.join(os.getcwd(),str('data/photo/objects/') + str(file02) + '.jpg'), result)
					else:
						file01 = filepath
						shutil.copy2(file01, (os.path.join(os.getcwd(),'data/photo/objects/' + file02 + '.jpg')))  # complete target filename given
					foto_entry.configure(state="normal")
					foto_entry.delete(0, END)
					foto_entry.insert(0, file02 + '.jpg')
					foto_entry.configure(state="disabled")
					img2 = ImageTk.PhotoImage(Image.open(os.path.join(os.getcwd(),("data/photo/objects/" + file02 + '.jpg'))).resize((120, 120)))
					panel.configure(image=img2)
					panel.image = img2

		# Add Some Style
		style = ttk.Style()

		# Pick A Theme
		#style.theme_use('default')

		# Configure the Treeview Colors
		style.configure("Treeview",
						background="lightgrey", #D3D3D3
						foreground="black",
						#rowheight=25,
						fieldbackground="lightgrey")

		# Change Selected Color #347083 #D3D3D3
		style.map('Treeview',
				  background=[('selected', saved_highlight_color)])

		# Create a Treeview Frame
		tree_frame = Frame(objekt_list)
		tree_frame.pack(pady=10)

		# Create a Treeview Scrollbar
		tree_scroll = Scrollbar(tree_frame)
		tree_scroll.pack(side=RIGHT, fill=Y)

		# Create The Treeview
		my_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, selectmode="extended")
		my_tree.pack()

		# Configure the Scrollbar
		tree_scroll.config(command=my_tree.yview)

		# Define Our Columns
		my_tree['columns'] = (
		"last_name", "first_name", "category", "phone", "apartmentnumb", "floornumb", "foto", "modelfolder", "userlink",
		"ob_komments")

		# Format Our Columns
		my_tree.column("#0", width=0, stretch=NO)
		my_tree.column("last_name", anchor=W, width=140)
		my_tree.column("first_name", anchor=W, width=140)
		my_tree.column("category", anchor=W, width=140)
		my_tree.column("phone", anchor=CENTER, width=100)
		my_tree.column("apartmentnumb", anchor=CENTER, width=140)
		my_tree.column("floornumb", anchor=CENTER, width=140)
		my_tree.column("foto", anchor=CENTER, width=140)
		my_tree.column("modelfolder", anchor=CENTER, width=140)
		my_tree.column("userlink", anchor=CENTER, width=140)
		my_tree.column("ob_komments", anchor=CENTER, width=140)

		# Create Headings
		my_tree.heading("#0", text="", anchor=W)
		my_tree.heading("first_name", text="Имя", anchor=W)
		my_tree.heading("last_name", text="Фамилия", anchor=W)
		my_tree.heading("category", text="Категория", anchor=W)
		my_tree.heading("phone", text="Телефон", anchor=CENTER)
		my_tree.heading("apartmentnumb", text="Квартира", anchor=CENTER)
		my_tree.heading("floornumb", text="Этаж", anchor=CENTER)
		my_tree.heading("foto", text="Фотография", anchor=CENTER)
		my_tree.heading("modelfolder", text="modelfolder", anchor=CENTER)
		my_tree.heading("userlink", text="userlink", anchor=CENTER)
		my_tree.heading("ob_komments", text="Комментарий", anchor=CENTER)

		# Create Striped Row Tags
		my_tree.tag_configure('oddrow', background=saved_secondary_color)
		my_tree.tag_configure('evenrow', background=saved_primary_color)

		# Add Record Entry Boxes
		data_frame = LabelFrame(objekt_list, text="Карточка объекта", bg='lightgrey')
		data_frame.pack(fill="x", expand="yes", padx=20)

		img = ImageTk.PhotoImage(Image.open(os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg")).resize((120, 120)))
		panel = Label(data_frame, image=img, bg="lightgrey")
		panel.image = img
		panel.grid(row=0, rowspan=3, column=0, padx=10, pady=10)

		ln_label = Label(data_frame, text="Фамилия", bg="lightgrey")
		ln_label.grid(row=0, column=1, padx=10, pady=10)
		ln_entry = Entry(data_frame)
		ln_entry.grid(row=0, column=2, padx=10, pady=10)

		fn_label = Label(data_frame, text="Имя", bg="lightgrey")
		fn_label.grid(row=0, column=3, padx=10, pady=10)
		fn_entry = Entry(data_frame)
		fn_entry.grid(row=0, column=4, padx=10, pady=10)

		cat_label = Label(data_frame, text="Категория", bg="lightgrey")
		cat_label.grid(row=0, column=5, padx=10, pady=10)
		cat_entry = Entry(data_frame)
		cat_entry.grid(row=0, column=6, padx=10, pady=10)
		cat_entry.configure(state="disabled")

		apartmentnumb_label = Label(data_frame, text="Квартира", bg="lightgrey")
		apartmentnumb_label.grid(row=1, column=1, padx=10, pady=10)
		apartmentnumb_entry = Entry(data_frame)
		apartmentnumb_entry.grid(row=1, column=2, padx=10, pady=10)

		floornumb_label = Label(data_frame, text="Этаж", bg="lightgrey")
		floornumb_label.grid(row=1, column=3, padx=10, pady=10)
		floornumb_entry = Entry(data_frame)
		floornumb_entry.grid(row=1, column=4, padx=10, pady=10)

		phone_label = Label(data_frame, text="Телефон", bg="lightgrey")
		phone_label.grid(row=1, column=5, padx=10, pady=10)
		phone_entry = Entry(data_frame)
		phone_entry.grid(row=1, column=6, padx=10, pady=10)

		userlink_label = Label(data_frame, text="userlink", bg="lightgrey")
		userlink_label.grid(row=2, column=5, padx=10, pady=10)
		userlink_entry = Entry(data_frame)
		userlink_entry.grid(row=2, column=6, padx=10, pady=10)

		foto_label = Label(data_frame, text="Фотография", bg="lightgrey")
		foto_label.grid(row=2, column=1, padx=10, pady=10)
		foto_entry = Entry(data_frame)
		foto_entry.grid(row=2, column=2, padx=10, pady=10)
		foto_entry.configure(state="disabled")

		modelfolder_label = Label(data_frame, text="modelfolder", bg="lightgrey")
		modelfolder_label.grid(row=2, column=3, padx=10, pady=10)
		modelfolder_entry = Entry(data_frame)
		modelfolder_entry.grid(row=2, column=4, padx=10, pady=10)
		modelfolder_entry.configure(state="disabled")

		select_record_button1 = ttk.Button(data_frame, text="Выбрать фото", command=open_file, style='my.TButton')
		select_record_button1.grid(row=3, column=0, padx=10, pady=10)

		ob_komments_label = Label(data_frame, text="Комментарий", bg="lightgrey")
		ob_komments_label.grid(row=3, column=1, padx=10, pady=10)
		ob_komments_entry = Entry(data_frame)
		ob_komments_entry.grid(row=3, columnspan=5, column=2, padx=10, pady=10, sticky=EW)

		def remove_one():
			k = modelfolder_entry.get()
			if k == "Unknown" or k == "":
				if k == "Unknown":
					messagebox.showinfo("Внимание!", "Cтрочку с именем Unknown удалить нельзя!")
				if k == "":
					messagebox.showinfo("Внимание!", "Выделите строчку для удаления!")
			else:
				result22 = askokcancel(title="Вопрос",
									   message="Удалить объект " + k + " из базы данных?\n\nКаталог с фотографиями объекта будет перенесен в архив.")
				if result22:
					# print(object_view_name_dubli)
					path_source = os.path.join(os.getcwd(),"data/dataset/" + k + "/")
					path_dest = (os.path.join(os.getcwd(),"data/data_archives/dataset_archives/"))
					x = my_tree.selection()[0]
					my_tree.delete(x)
					# Create a database or connect to one that exists
					conn = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))

					# Create a cursor instance
					c = conn.cursor()

					# Delete From Database
					c.execute("DELETE from People WHERE modelfolder = ?", (k,))

					# Commit changes
					conn.commit()

					# Close our connection
					conn.close()

					# Clear The Entry Boxes
					clear_entries()

					# Add a little message box for fun
					messagebox.showinfo("Удалено!", "Запись об объкте удалена!")
					try:
						shutil.move(path_source, path_dest)
					except Exception:
						print("исключение")

		# Clear entry boxes
		def clear_entries():
			# Clear entry boxes
			fn_entry.delete(0, END)
			ln_entry.delete(0, END)
			cat_entry.configure(state="normal")
			cat_entry.delete(0, END)
			cat_entry.configure(state="disabled")
			phone_entry.delete(0, END)
			userlink_entry.delete(0, END)
			apartmentnumb_entry.delete(0, END)
			floornumb_entry.delete(0, END)
			modelfolder_entry.configure(state="normal")
			modelfolder_entry.delete(0, END)
			modelfolder_entry.configure(state="disabled")
			foto_entry.configure(state="normal")
			foto_entry.delete(0, END)
			foto_entry.configure(state="disabled")
			ob_komments_entry.delete(0, END)
			img2 = ImageTk.PhotoImage(Image.open(os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg")).resize((120, 120)))
			panel.configure(image=img2)
			panel.image = img2

		# Select Record
		def select_record(e):
			# Clear entry boxes
			fn_entry.delete(0, END)
			ln_entry.delete(0, END)
			cat_entry.configure(state="normal")
			cat_entry.delete(0, END)
			cat_entry.configure(state="disabled")
			phone_entry.delete(0, END)
			userlink_entry.delete(0, END)
			apartmentnumb_entry.delete(0, END)
			floornumb_entry.delete(0, END)
			modelfolder_entry.configure(state="normal")
			modelfolder_entry.delete(0, END)
			modelfolder_entry.configure(state="disabled")
			foto_entry.configure(state="normal")
			foto_entry.delete(0, END)
			foto_entry.configure(state="disabled")
			ob_komments_entry.delete(0, END)
			# img2 = ImageTk.PhotoImage(Image.open("data/photo/objects/no_avatar_grey.jpg").resize((120, 120)))
			# panel.configure(image=img2)
			# panel.image = img2

			# Grab record Number
			selected = my_tree.focus()
			# Grab record values
			values = my_tree.item(selected, 'values')
			# print("select values: ", values)
			if values != "":
				# outpus to entry boxes
				fn_entry.insert(0, values[1])
				ln_entry.insert(0, values[0])
				cat_entry.configure(state="normal")
				cat_entry.insert(0, values[2])
				cat_entry.configure(state="disabled")
				phone_entry.insert(0, values[3])
				userlink_entry.insert(0, values[8])
				apartmentnumb_entry.insert(0, values[4])
				floornumb_entry.insert(0, values[5])
				modelfolder_entry.configure(state="normal")
				modelfolder_entry.insert(0, values[7])
				modelfolder_entry.configure(state="disabled")
				foto_entry.configure(state="normal")
				foto_entry.insert(0, values[6])
				foto_entry.configure(state="disabled")
				ob_komments_entry.insert(0, values[9])
				img2 = ImageTk.PhotoImage(Image.open(os.path.join(os.getcwd(),"data/photo/objects/" + values[6])).resize((120, 120)))
				panel.configure(image=img2)
				panel.image = img2

		# Update record
		def update_record():
			k = modelfolder_entry.get()
			if k == "Unknown" or k == "":
				if k == "Unknown":
					messagebox.showinfo("Внимание!", "Cтрочку с именем Unknown редактировать нельзя!")
				if k == "":
					messagebox.showinfo("Внимание!", "Выделите строчку для редактирования!")
			else:
				# Grab the record number
				selected = my_tree.focus()
				# Update record
				my_tree.item(selected, text="", values=(
					ln_entry.get(), fn_entry.get(), cat_entry.get(), phone_entry.get(), apartmentnumb_entry.get(),
					floornumb_entry.get(),
					foto_entry.get(), modelfolder_entry.get(), userlink_entry.get(), ob_komments_entry.get(),))

				# Update the database
				# Create a database or connect to one that exists
				conn = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))

				# Create a cursor instance
				c = conn.cursor()
				ln = ln_entry.get()
				fn = fn_entry.get()
				# cat = cat_entry.get()
				phone = phone_entry.get()
				apart = apartmentnumb_entry.get()
				floor = floornumb_entry.get()
				foto = foto_entry.get()
				userl = userlink_entry.get()
				ob_ko = ob_komments_entry.get()
				modelfolderp = modelfolder_entry.get()
				#print(modelfolderp)
				c.execute(
					'UPDATE People SET last_name = ?, first_name = ?, phone = ?, apartmentnumb = ?, floornumb = ?, foto = ?, userlink = ?, ob_komments = ? WHERE modelfolder = ?',
					(ln, fn, phone, apart, floor, foto, userl, ob_ko, modelfolderp))

				# Commit changes
				conn.commit()

				# Close our connection
				conn.close()

				# Clear entry boxes
				fn_entry.delete(0, END)
				ln_entry.delete(0, END)
				cat_entry.configure(state="normal")
				cat_entry.delete(0, END)
				cat_entry.configure(state="disabled")
				phone_entry.delete(0, END)
				userlink_entry.delete(0, END)
				apartmentnumb_entry.delete(0, END)
				floornumb_entry.delete(0, END)
				modelfolder_entry.configure(state="normal")
				modelfolder_entry.delete(0, END)
				modelfolder_entry.configure(state="disabled")
				foto_entry.configure(state="normal")
				foto_entry.delete(0, END)
				foto_entry.configure(state="disabled")
				ob_komments_entry.delete(0, END)
				img2 = ImageTk.PhotoImage(Image.open(os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg")).resize((120, 120)))
				panel.configure(image=img2)
				panel.image = img2

		def run_catalog_foto_ob():
			global catalog_foto_ob
			catalog_foto_ob = modelfolder_entry.get()
			katalog_foto_object()



		# Add Buttons
		button_frame = LabelFrame(objekt_list, text="Действия с карточками объектов", bg='lightgrey')
		button_frame.pack(fill="x", expand="yes", padx=20)

		update_button = ttk.Button(button_frame, text="Сохранить изменения", command=update_record, style='my.TButton')
		update_button.grid(row=0, column=0, padx=10, pady=10)

		# add_button = Button(button_frame, text="Add Record", command=add_record)
		# add_button.grid(row=0, column=1, padx=10, pady=10)

		# remove_all_button = Button(button_frame, text="Remove All Records", command=remove_all)
		# remove_all_button.grid(row=0, column=2, padx=10, pady=10)

		remove_one_button = ttk.Button(button_frame, text="Удалить запись", command=remove_one, style='my.TButton')
		remove_one_button.grid(row=0, column=3, padx=10, pady=10)

		# remove_many_button = Button(button_frame, text="Remove Many Selected", command=remove_many)
		# remove_many_button.grid(row=0, column=4, padx=10, pady=10)

		# move_up_button = Button(button_frame, text="Move Up", command=up)
		# move_up_button.grid(row=0, column=5, padx=10, pady=10)

		# move_down_button = Button(button_frame, text="Move Down", command=down)
		# move_down_button.grid(row=0, column=6, padx=10, pady=10)

		select_record_button = ttk.Button(button_frame, text="Очистить значения", command=clear_entries, style='my.TButton')
		select_record_button.grid(row=0, column=7, padx=10, pady=10)

		select_record_obect_card = ttk.Button(button_frame, text="Фотографии объекта", command=run_catalog_foto_ob, style='my.TButton')
		select_record_obect_card.grid(row=0, column=8, padx=10, pady=10)

		# Bind the treeview
		my_tree.bind("<ButtonRelease-1>", select_record)

		# Run to pull data from database on start
		query_database()
		objekt_list.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		objekt_list.grab_set()



	else:
		res = str("Просмотр/ред. объектов наблюдения: необходима авторизация")
		message.configure(text=res)




def new_objekt():   #

	global activeusergroupe
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		aa = os.path.isfile('data\objects.db')
		if aa == False:
			connection = sqlite3.connect('data\objects.db')
			cursor = connection.cursor()
			# rowid INTEGER PRIMARY KEY,
			# Создаем таблицу
			cursor.execute('''
			CREATE TABLE IF NOT EXISTS People (
			last_name TEXT,
			first_name TEXT,
			phone TEXT,
			category TEXT,
			homenumb TEXT,
			apartmentnumb TEXT,
			floornumb TEXT,
			modelfolder TEXT,
			foto TEXT,
			userlink TEXT,
			ob_komments TEXT,
			ob_sets01 TEXT,
			ob_sets02 TEXT,
			ob_sets03 TEXT,
			ob_sets04 TEXT,
			ob_sets05 TEXT
			)
			''')
			# Добавляем начальные настройки
			cursor.execute('INSERT INTO People (last_name, category, modelfolder, foto) VALUES (?, ?, ?, ?)',
						   ('Unknown', '4', 'Unknown', 'no_avatar_grey.jpg'))
			# Сохраняем изменения и закрываем соединение
			connection.commit()
			connection.close()

		windowcreat1 = tk.Toplevel(window)
		#windowcreat1 = tk.Tk()
		windowcreat1.title('Создание объекта наблюдения')
		windowcreat1.geometry('470x550+600+100')
		windowcreat1.configure(bg="lightgrey")
		windowcreat1.resizable(False, False)
# кортежи и словари, содержащие настройки шрифтов и отступов:
		font_header = ('Helvetica', 12)
		font_entry = ('Helvetica', 10)
		label_font = ('Helvetica', 10)
		base_padding = {'padx': 10, 'pady': 15}
		header_padding = {'padx': 10, 'pady': 5}
		s = ttk.Style()
		s.configure('my.TButton', font=('Helvetica', 10))


		def userlist():
			file_path = "data\objects.db"
			conn = sqlite3.connect(file_path)
			c = conn.cursor()
			c.execute('SELECT modelfolder FROM People')
			logins = c.fetchall()
			for login in logins:
				print(login)
			conn.close()

		userlist()

		def chekadmin():
			file_path = "data\objects.db"
			conn = sqlite3.connect(file_path)
			c = conn.cursor()
			c.execute('SELECT first_name FROM People')
			logins = c.fetchall()
			for login in logins:
				if login[0] == "admin":
					print(login)
			conn.close()

		chekadmin()


		object_name = None

		#main_status = Label(windowcreat, text="", font=font_header, justify=CENTER, **header_padding)
		# помещаем виджет в окно по принципу один виджет под другим
		#main_status.pack()

		def clickedtest():
			from transliterate import translit
			global object_name, objeck_family, categor, objeck_homenumb, objeck_apartmentnumb, objeck_floornumb, objeck_tel, formodel_var, formodel_first_name, ob_komment
			object_name = objeck_name_entry.get()
			objeck_family = objeck_family_entry.get()
			categor = category.get()
			objeck_homenumb = homenumb_entry.get()
			objeck_apartmentnumb = apartmentnumb_entry.get()
			objeck_floornumb = floornumb_entry.get()
			objeck_tel = tel_entry.get()
			ob_komment = komment_entry.get()
			#groupe = str(sel1.get())
			object_name = object_name.strip()  # удаляем пробелы в начале и в конце строки
			objeck_family = objeck_family.strip()  # удаляем пробелы в начале и в конце строки
			categor_vopros = categor
			categor = categor[0]
			objeck_homenumb = objeck_homenumb.strip()
			objeck_apartmentnumb = objeck_apartmentnumb.strip()
			objeck_floornumb = objeck_floornumb.strip()
			objeck_tel = objeck_tel.strip()
			print(object_name, objeck_family, categor, objeck_homenumb, objeck_apartmentnumb, objeck_floornumb, objeck_tel)

			connection = sqlite3.connect("data\objects.db")
			cursor = connection.cursor()
			cursor.execute('SELECT modelfolder FROM People')
			logins = cursor.fetchall()
			test_name = False
			test_family = False
			test_koment = False

			if len(object_name) < 20:
				if re.match(r'^[а-яА-ЯёЁa-zA-Z0-9]+$', object_name):
					result = []
					for char in object_name:
						if 'а' <= char <= 'я' or 'А' <= char <= 'Я':
							# Транслитерируем русскую букву
							result.append(translit(char, "ru", "en"))
						# result.append(transliterate(char))
						else:
							# Оставляем символ без изменений
							result.append(char)
					formodel_first_name = ''.join(result)
					test_name = True
				else:
					res = str("Введите имя русскими или анг. буквами")
					main_status.configure(text=res, fg="red")
			else:
				res = str("Имя до 20 символов русскими буквами")
				main_status.configure(text=res, fg="red")

			if len(objeck_family) < 20:
				if re.match(r'^[а-яА-ЯёЁa-zA-Z0-9]+$', objeck_family):
					#print("ok")
					test_family = True
				else:
					res = str("Введите фамилию русскими или анг. буквами")
					main_status.configure(text=res, fg="red")
			else:
				res = str("Фамилия до 20 символов русскими буквами")
				main_status.configure(text=res, fg="red")
			if len(ob_komment) < 500:
				test_koment = True
			else:
				k = len(ob_komment)
				res = str("Комментрарий до 500 символов, \n сейчас: " + str(k) + " символов.")
				main_status.configure(text=res, fg="red")
			if test_name == True and test_family == True and test_koment == True:
				if objeck_homenumb == None or objeck_homenumb == "":
					objeck_homenumb = "0"
				if objeck_apartmentnumb == None or objeck_apartmentnumb == "":
					objeck_apartmentnumb = "0"
				if objeck_floornumb == None or objeck_floornumb == "":
					objeck_floornumb = "0"
				if objeck_tel == None or objeck_tel == "":
					objeck_tel = "0"
				formodel_var = str(file_contents) + "_" + str(categor) + "_" + str(formodel_first_name)
				print(formodel_var)

				result = askokcancel(title="Проверка данных", message="Имя: " + str(object_name) + "\n\nФамилия: " + str(objeck_family) +
																		 "\n\nКатегоря оъекта: " + str(categor_vopros)  +
																		 "\n\nНомер дома: " + str(objeck_homenumb)  +
																		 "\n\nНомер квартиры: " + str(objeck_apartmentnumb) +
																		 "\n\nЭтаж: " + str(objeck_floornumb)  + "\n\nТелефон: " + str(objeck_tel) +
																	    "\n\nКаталог модели: " + str(formodel_var) + "\n\nКоментарий: " + str(ob_komment))
				if result:
					clickedad()



		def clickedad():
			global object_name, objeck_family, categor, objeck_homenumb, objeck_apartmentnumb, objeck_floornumb, objeck_tel, formodel_var, formodel_first_name, ob_komment
			num_file = open((os.path.join(os.getcwd(),'data/numberreestr.txt')), "r")
			try:
				file_contents = num_file.read(5)
				print(file_contents)
				file_contents = str(int(file_contents) + 1)
				print(file_contents)
				num_file.close()
				num_file = open((os.path.join(os.getcwd(),'data/numberreestr.txt')), "w")
				num_file.write(file_contents)
			finally:
				num_file.close()
			formodel_var = str(file_contents) + "_" + str(categor) + "_" + str(formodel_first_name)

			# создание каталога
			if not os.path.isdir(os.path.join(os.getcwd(),'data/dataset/' + formodel_var)):
				os.mkdir(os.path.join(os.getcwd(),'data/dataset/' + formodel_var))
			print(categor)
			if categor == "1":
				foto_url = "no_avatar_green.jpg"
			if categor == "2":
				foto_url = "no_avatar_grey.jpg"
			if categor == "3":
				foto_url = "no_avatar_blue.jpg"
			if categor == "4":
				foto_url = "no_avatar_red.jpg"

			connection = sqlite3.connect(os.path.join(os.getcwd(),"data/objects.db"))
			cursor = connection.cursor()

			# Добавляем нового пользователя
			cursor.execute('INSERT INTO People (last_name, first_name, phone, category, homenumb, apartmentnumb, floornumb, modelfolder, foto, ob_komments) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
						   (objeck_family, object_name, objeck_tel, categor, objeck_homenumb, objeck_apartmentnumb, objeck_floornumb, formodel_var, foto_url, ob_komment))
			# Сохраняем изменения и закрываем соединение
			connection.commit()
			connection.close()
			res = "Добавлен новый объект наблюдения. Папка модели: " + str(formodel_var)
			#message.configure(text=res)
			windowcreat1.destroy()

		#main_status = Label(windowcreat, text="", font=font_header, justify=CENTER, **header_padding)
		# помещаем виджет в окно по принципу один виджет под другим
		#main_status.pack()

		# main_label = Label(windowcreat, text='Дозорный', font=font_header, justify=CENTER,
		# **header_padding)
		# помещаем виджет в окно по принципу один виджет под другим
		# main_label.pack()
		a = os.path.isfile(os.path.join(os.getcwd(),'data/numberreestr.txt'))
		if a == False:
			num_file = open((os.path.join(os.getcwd(),'data/numberreestr.txt')), "w")
			file_contents = str(10000)
			num_file.write(file_contents)
			file_contents = str(int(file_contents) + 1)
			num_file.close()
		else:
			num_file = open((os.path.join(os.getcwd(),'data/numberreestr.txt')), "r")
			try:
				file_contents = num_file.read(5)
				print(file_contents)
				file_contents = str(int(file_contents) + 1)
				# print(file_contents)
				#num_file.close()
				#num_file = open('numberreestr.txt', "w")
				#num_file.write(file_contents)
			finally:
				num_file.close()
		# print("файл закрыт")


		main_label1 = Label(windowcreat1, text='Объект наблюдения, (рег. № ' + file_contents + ')', font=font_header, justify=CENTER,
							**header_padding, bg="lightgrey")
		# помещаем виджет в окно по принципу один виджет под другим
		main_label1.pack()

		category_label = Label(windowcreat1, text='Выбор категории объекта:', font=label_font, **base_padding, bg="lightgrey")
		category_label.pack()

		#sel1 = tk.StringVar()
		category = ttk.Combobox(windowcreat1, values=("1.Жилец дома", "2.Гость", "3.Служебные", "4.Внимание!"), width=25, state="readonly") #textvariable=sel1,
		category.current(0)
		category.pack()


		# метка для поля ввода имени
		objeck_name_label1 = Label(windowcreat1, text='Имя:', font=label_font, bg="lightgrey")
		objeck_name_label1.pack()

		# поле ввода имени
		objeck_name_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		objeck_name_entry.pack()

		objeck_family_label1 = Label(windowcreat1, text='Фамилия:', font=label_font, bg="lightgrey")
		objeck_family_label1.pack()

		# поле ввода имени
		objeck_family_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		objeck_family_entry.pack()

		homenumb_label1 = Label(windowcreat1, text='Номер дома:', font=label_font, bg="lightgrey")
		homenumb_label1.pack()

		homenumb_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		homenumb_entry.pack()

		apartmentnumb_label1 = Label(windowcreat1, text='Номер квартиры:', font=label_font, bg="lightgrey")
		apartmentnumb_label1.pack()

		apartmentnumb_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		apartmentnumb_entry.pack()

		floornumb_label1 = Label(windowcreat1, text='Этаж:', font=label_font, bg="lightgrey")
		floornumb_label1.pack()

		floornumb_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		floornumb_entry.pack()

		tel_label = Label(windowcreat1, text='Телефон:', font=label_font, **base_padding, bg="lightgrey")
		tel_label.pack()

		tel_entry = Entry(windowcreat1, bg='#fff', fg='#444', font=font_entry)
		tel_entry.pack()

		komment_label = Label(windowcreat1, text='Комментарий:', font=label_font, **base_padding, bg="lightgrey")
		komment_label.pack()

		komment_entry = Entry(windowcreat1, bg='#fff', fg='#444', width=55, font=font_entry)
		komment_entry.pack()

		# кнопка отправки формы
		send_btn = ttk.Button(windowcreat1, text='Создать', style='my.TButton', command=clickedtest)
		send_btn.pack(**base_padding)

		main_status = Label(windowcreat1, text="", font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
		# помещаем виджет в окно по принципу один виджет под другим
		main_status.pack()

		windowcreat1.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		#windowcreat1.grab_set() #временно ю применить в основной программе
		windowcreat1.grab_set()
	else:
		res = str("Создать объект наблюдения: необходима авторизация")
		message.configure(text=res)

# Training the images saved in training image folder
def TrainImagesRun():
	global activeusergroupe
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		if __name__ == '__main__':
			global TrainImageRunStatus
			if TrainImageRunStatus == False:
				TrainImageRunStatus = True
				Thread(target=TrainImages, daemon=True).start()
				print("Запущен процесс обучения модели")
				res = "Запущен процесс обучения модели"
			else:
				print("Процесс обучения модели уже запущен")
				res = "Процесс обучения модели уже запущен"
			message.configure(text=res)
	else:
		print("Требуется авторизация в программе")
		res = "Авторизуйтесь для запуска обучения модели"
		message.configure(text=res)

def TranImage_control():
	global for_start_model_mess
	files = folders = 0
	for _, dirnames, filenames in os.walk(os.path.join(os.getcwd(),'data/dataset')):
		# ^ this idiom means "we won't be using this value"
		files += len(filenames)
		folders += len(dirnames)
	total_size = 0
	for dirpath, dirnames, filenames in os.walk(os.path.join(os.getcwd(),'data/dataset')):
		for filename in filenames:
			file_path = os.path.join(dirpath, filename)
			total_size += os.path.getsize(file_path)
	#print('total_size', total_size)
	model_forone = "model_forone"
	folder_bd = 0
	files_bd = 0
	size_bd = 0
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/setting.db'))
	cursor = connection.cursor()
	cursor.execute('SELECT set02 FROM setting WHERE parametr_name = ?', (model_forone,))
	file_folder = cursor.fetchall()
	for row in file_folder:
		folder_bd = row[0]
	#print(folder_bd)
	cursor.execute('SELECT set03 FROM setting WHERE parametr_name = ?', (model_forone,))
	file_folder = cursor.fetchall()
	for row in file_folder:
		files_bd = row[0]
	#print(files_bd)
	cursor.execute('SELECT set04 FROM setting WHERE parametr_name = ?', (model_forone,))
	file_folder = cursor.fetchall()
	for row in file_folder:
		size_bd = row[0]
	#print(size_bd)
	if int(files_bd) != int(files) or int(folder_bd) != int(folders) or int(size_bd) != int(total_size):
		total_size = round(float(int(total_size) / 1024 / 1024), 2)
		size_bd = round(float(int(size_bd) / 1024 / 1024), 2)
		if for_start_model_mess == True:
			res = "Требуется обучение модели: изменился состав элементов (было/стало: объектов " + str(folder_bd) + " / " + str(folders) + ", файлов " + str(files_bd) + " / " + str(files) + ", размер " + str(size_bd) + " / " + str(total_size)  + " Mb."
			message.configure(text=res, fg="black")
			for_start_model_mess = False
		lablel_model_status.configure(text="Модель не актуальна", fg="red")
		#print("не равно БД")
	else:
		total_size = round(float(int(total_size) /1024 / 1024), 2)
		if for_start_model_mess == True:
			res = "Модель актуальна, обучение не требуется (объектов: " + str(folders) + ", файлов: " + str(files) + ", размер: " + str(total_size) + " Mb."
			message.configure(text=res, fg="black")
			for_start_model_mess = False
		lablel_model_status.configure(text="Модель актуальна", fg="black")
	connection.close()

def TranImage_control_button():
	global for_start_model_mess
	for_start_model_mess = True
	TranImage_control()

def TrainImages():
	global TrackIm
	global	TrainImageRunStatus
	global model_algoritm_var
	global v_record_codec_var
	global for_start_model_mess
	# проверка наличия файла модели encodings.pickle
	res = '0'
	res1 = '0'
	file_path = os.path.join(os.getcwd(),"data/encodings.pickle")
	unix_time_model_forone_bd1 = 0
	model_forone = "model_forone"
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/setting.db'))
	cursor = connection.cursor()
	cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (model_forone,))
	unix_time_model_forone_bd = cursor.fetchall()
	for row in unix_time_model_forone_bd:
		#print(str(row[0]))
		unix_time_model_forone_bd1 = row[0]
	#print(str(unix_time_model_forone_bd1))
	connection.close()
	files = folders = 0
	for _, dirnames, filenames in os.walk(os.path.join(os.getcwd(),'data/dataset/')):
		# ^ this idiom means "we won't be using this value"
		files += len(filenames)
		folders += len(dirnames)
	#print("{:,} files, {:,} folders".format(files, folders))
	#print(files)
	if files == 0:
		message.configure(text="Не данных для создания модели")
		TrainImageRunStatus = False
	else:
		if unix_time_model_forone_bd1 != 0 and unix_time_model_forone_bd1 != None:
			model_long_rasschet1 = ((float(unix_time_model_forone_bd1) * files)/60)
			if model_long_rasschet1 < 1:
				model_long_rasschet = "менее одной минуты."
				if model_long_rasschet1 == 0:
					model_long_rasschet = "не определено."
			else:
				model_long_rasschet = str(int(model_long_rasschet1)) + " мин."
		else:
			model_long_rasschet = "не определено."

		result1 = askokcancel(title="Запустить обучение модели?",
							 message="Всего объектов: " + str(folders) + "\n\nВсего файлов: " + str(files) +
									 "\n\nВремя обучения модели: " + str(model_long_rasschet))
		if result1:
			if os.path.isfile(file_path):
				mydir = os.path.join(os.getcwd(),'data/data_archives/model_archives/',
									 datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
				print(mydir)
				if not os.path.isdir(mydir):
					os.makedirs(mydir)
					shutil.copy(file_path, mydir)
					print('Файл ' + file_path + ' скопирован в ' + mydir + '. Начинается обучение модели:')
					res = "Модель обновлена, обработано файлов: "
			else:
				print('Модель (encodings.pickle) не существует. Начинается обучение модели:')
				res = "Создана новая модель, обработано файлов: "

			# в директории dataset хранятся папки со всеми изображениями

			unix_time_model_start = (time.time())
			print(unix_time_model_start)
			knownEncodings, knownNames = [], []
			imagePaths = list(paths.list_images(os.path.join(os.getcwd(),'data/dataset/')))  # dataset here
			for (i, imagePath) in enumerate(imagePaths):
				print('\x1b[2K', end='\r')
				print('{}/{}'.format(i + 1, len(imagePaths)), end='\r')
				res1 = str('{}/{}'.format(i + 1, len(imagePaths)))
				lablel_model_status.configure(text=res1)
				image, name = cv2.imread(imagePath), imagePath.split(os.path.sep)[-2][13:]
				#print(imagePath.split(os.path.sep)[-2][13:])
				rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
				boxes = face_recognition.face_locations(rgb, model=model_algoritm_var)  # detection_method here: cnn, hog
				for encoding in face_recognition.face_encodings(rgb, boxes):
					knownEncodings.append(encoding)
					knownNames.append(name)
			data = {'encodings': knownEncodings, 'names': knownNames}
			f = open(os.getcwd() + '\\data\\encodings.pickle', 'wb')
			f.write(pickle.dumps(data))
			f.close()
			resrezult = str(res + " " + res1)
			#print(resrezult)
			unix_time_model_end = (time.time())
			unix_time_model_long = unix_time_model_end - unix_time_model_start
			unix_time_model_forone = (unix_time_model_long / (i + 1))
			#print(unix_time_model_end, unix_time_model_long, i + 1, unix_time_model_forone)
			message.configure(text=resrezult)
			TrainImageRunStatus = False

			total_size = 0
			for dirpath, dirnames, filenames in os.walk('data\\dataset'):
				for filename in filenames:
					file_path = os.path.join(dirpath, filename)
					total_size += os.path.getsize(file_path)
			print('total_size', total_size)

			model_forone = "model_forone"
			connection = sqlite3.connect('data\setting.db')
			cursor = connection.cursor()
			cursor.execute('UPDATE setting SET set01 = ?, set02 = ?, set03 = ?, set04 = ? WHERE parametr_name = ?', (unix_time_model_forone, folders, i+1, total_size, model_forone,))
			connection.commit()
			connection.close()
			global TrackIm
			if TrackIm == True:
				result11 = askokcancel(title="Применить новую модель?",
									   message="Информация: \n\nВсего объектов: " + str(
										   folders) + "\n\nВсего файлов: " + str(i + 1) +
											   "\n\nОбучение модели заняло: " + str(
										   round((unix_time_model_long / 60), 3)) + " мин.\n\nПрименить новую модель?")
				if result11:
					trakingdef1stop()
					time.sleep(5)
					TrackImages()

			for_start_model_mess = False
			TranImage_control()

		else:
			message.configure(text="Обучение модели отменено пользователем")
			TrainImageRunStatus = False






def getImagesAndLabels(path):
	# get the path of all the files in the folder
	imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
	faces = []
	# creating empty ID list
	Ids = []
	# now looping through all the image paths and loading the
	# Ids and the images saved in the folder
	for imagePath in imagePaths:
		# loading the image and converting it to gray scale
		pilImage = Image.open(imagePath).convert('L')
		# Now we are converting the PIL image into numpy array
		imageNp = np.array(pilImage, 'uint8')
		# getting the Id from the image
		Id = int(os.path.split(imagePath)[-1].split(".")[1])
		# extract the face from the training image sample
		faces.append(imageNp)
		Ids.append(Id)
	return faces, Ids
# For testing phase


def TrackImages():
	global camera01link
	def streamopettest():
		global camera01link
		link = camera01link
		res = "Запущен видео анализ"
		if link != None or link != 0 or link != "":
			source: str = link
			stream = cv2.VideoCapture(source)
			print("Запущен видео анализ1")
			res = "Запущен видео анализ1"
			if stream.isOpened():
				TrackIm = True  # вопрос, нужно ли помещать в глабальную
				canvas.delete("all")
				Thread(target=trakingdef1, daemon=True).start()
				print("Запущен видео анализ1")
				res = "Запущен видео анализ1"
		message.configure(text=res)
	if __name__ == '__main__':
		global TrackIm
		if TrackIm == False:
			Thread(target=streamopettest, daemon=True).start()
			#streamopettest()
			res = "Запущена проверка"
		else:
			print("Анализ видео уже запущен")
			res = "Анализ видео уже запущен"
		message.configure(text=res)




# Главный модуль распознования
def trakingdef1():
	from imutils import paths
	import imutils, face_recognition, os, pickle, time
	import datetime
	# os.environ["MY_ENV_VARIABLE"] = "True" # value must be a string
	import cv2  # variables set after this may not have effect
	# import multiprocessing
	from collections import Counter
	from PIL import Image, ImageTk
	import csv
	import re
	import threading
	import os.path
	import sqlite3
	global imgtk
	#print("trakingdef1 начало " + str(imgtk))
	global TrackImwindows
	global camera01link
	global spisok_ob_vivod
	global enabled_checkbutton_view_scr_state
	global enabled_checkbutton_view_scr_state_last
	global model_algoritm_var
	global resolut_video_model_var
	global foto_save_kadr_var
	global v_record_dlit_var
	global v_record_codec_var
	global v_record_frames_var
	global main_status
	global oper_jurnal_laststroki_var
	global oper_jurnal_laststrokitime_var
	global facerecog_granici1_face_var
	global facerecog_granici2_face_var
	global facerecog_granici3_face_var
	print("проверка настроек ", facerecog_granici1_face_var, facerecog_granici2_face_var,
		  facerecog_granici3_face_var)
	resolut_video_model_var_def = (int(resolut_video_model_var))
	model_algoritm_var_def = model_algoritm_var
	foto_save_kadr_var_def = int(foto_save_kadr_var)
	v_record_dlit_var_def = int(v_record_dlit_var)
	v_record_codec_var_def = v_record_codec_var
	v_record_frames_var_def = int(v_record_frames_var)
	facerecog_granici1_face_var_def = round((float(int(facerecog_granici1_face_var)/100)), 2)
	facerecog_granici2_face_var_def = round((float(int(facerecog_granici2_face_var)/100)), 2)
	facerecog_granici3_face_var_def = round((float(int(facerecog_granici3_face_var)/100)), 2)
	print("проверка настроек ", facerecog_granici1_face_var_def, facerecog_granici2_face_var_def, facerecog_granici3_face_var_def,
		  model_algoritm_var_def, resolut_video_model_var_def, foto_save_kadr_var_def, v_record_dlit_var_def, v_record_codec_var_def, v_record_frames_var_def)
	unix_time = int(time.time())
	date_time = datetime.datetime.fromtimestamp(unix_time)
	date_timef_file_day = date_time.strftime('%Y-%m-%d')
	myFilename = "data\\protocols\\normal_terminal\\nt_d_" + date_timef_file_day + "_t_00.csv"
	if os.path.exists(myFilename) is False:
		myFile = open(myFilename, 'w')
		csv_var1 = ['data_start_s', 'time_start_s', 'long_s', 'categoriy_s', 'name01_s', 'apartmentnumb_s',
					'floornumb_s',
					'name01_m', 'time_start', 'time_end', 'long', 'koordinatstart', 'koordinatend', 'name01',
					'percent01',
					'name02',
					'percent02', 'name03', 'percent03']  # новая
		# csv_var1 = ['time_start', 'time_end', 'long', 'koordinatstart', 'koordinatend', 'name01', 'percent01', 'name02', 'percent02', 'name03', 'percent03'] #рабочая
		with myFile as csvfile:
			writer = csv.writer(csvfile)
			writer.writerow(csv_var1)
			myFile.close()



	#Создание каталога текущей даты для сохранения фоток лиц и видео
	unix_time = int(time.time())
	date_time = datetime.datetime.fromtimestamp(unix_time)
	date_timef = date_time.strftime('%Y-%m-%d')
	catalog_day = "data/faces/" + date_timef
	catalog_day_video = "data/video/records_video/" + date_timef
	if not os.path.exists(catalog_day):
		os.makedirs(catalog_day)
	if not os.path.exists(catalog_day_video):
		os.makedirs(catalog_day_video)

	# предыдущая версия
	myFilename1 = 'example7common.csv'
	myFile1 = open(myFilename1, 'w')
	csv_var10 = ['date_timef', 'name', 'unix_time', 'top', 'right', 'bottom', 'left', 'k_summ']
	with myFile1 as csvfile1:
		writer1 = csv.writer(csvfile1)
		writer1.writerow(csv_var10)
		myFile1.close()

	# включить проверку наличия ссылки на поток и обновление ссылки их БД

	''

	def spisok_ob_odrabotka():
		global enabled_checkbutton_view_scr_state
		global enabled_checkbutton_view_scr_state_last
		global spisok_ob_vivod
		global oper_jurnal_laststroki_var
		global oper_jurnal_laststrokitime_var
		oper_jurnal_laststroki_var_def = int(oper_jurnal_laststroki_var)
		oper_jurnal_laststrokitime_var_def = int(oper_jurnal_laststrokitime_var)
		print('контроль настроекв в spisok_ob_odrabotka ', oper_jurnal_laststroki_var, oper_jurnal_laststrokitime_var)
		connection = sqlite3.connect('data/objects.db')
		cursor = connection.cursor()
		if os.path.exists(myFilename) is False:
			myFile = open(myFilename, 'w')
			csv_var1 = ['data_start_s', 'time_start_s', 'long_s', 'categoriy_s', 'name01_s', 'apartmentnumb_s',
						'floornumb_s', 'name01_m', 'time_start', 'time_end', 'long', 'koordinatstart', 'koordinatend',
						'name01', 'percent01', 'name02',
						'percent02', 'name03', 'percent03']  # новая
			# csv_var1 = ['time_start', 'time_end', 'long', 'koordinatstart', 'koordinatend', 'name01', 'percent01', 'name02', 'percent02', 'name03', 'percent03'] #рабочая
			with myFile as csvfile:
				writer = csv.writer(csvfile)
				writer.writerow(csv_var1)
				myFile.close()
		timeinfo = []
		obinfo = []
		koordinatinfo = []
		rezultstroka = []
		for i in range(0, len(spisok_ob_vivod)):
			aa = str(spisok_ob_vivod[i])
			markerob1 = ','
			markerob2 = ','
			regexPatternob = markerob1 + '(.+?)' + markerob2
			ii1 = re.search(regexPatternob, aa).group(1)
			obinfo.append(ii1)
			markerkoord1 = '.*?,.*?,.*?,.*?,.*?,.*?,.*?,'
			markerkoord2 = "'"
			regexPatternkoord = markerkoord1 + '(.+?)' + markerkoord2
			ii2 = re.search(regexPatternkoord, aa).group(1)
			koordinatinfo.append(ii2)
			markertime1 = '.*?,.*?,'
			markertime2 = ','
			regexPatterntime = markertime1 + '(.+?)' + markertime2
			ii = re.search(regexPatterntime, aa).group(1)
			ii = float(ii)
			timeinfo.append(ii)
		timestart = int(timeinfo[0])
		timeend = int(timeinfo[-1])
		dlitelnost = int(timeinfo[-1] - timeinfo[0])
		coordinatstart = (koordinatinfo[0])
		coordinatend = (koordinatinfo[-1])
		dlinaob = len(obinfo)
		most_common_element = Counter(obinfo).most_common()
		obinfoname1 = most_common_element[0][0]
		procentob1 = (round(((int(most_common_element[0][1]) / int(dlinaob)) * 100), 1))
		procentob2 = "None"
		obinfoname2 = "None"
		obinfoname3 = "None"
		procentob3 = "None"
		kolvoob = len(most_common_element)
		kolvoob = len(most_common_element)
		if kolvoob >= 2:
			rezultstroka = []
			obinfoname2 = most_common_element[1][0]
			procentob2 = (round(((int(most_common_element[1][1]) / int(dlinaob)) * 100), 1))
			if kolvoob >= 3:
				procentob3 = round((100 - procentob1 - procentob2), 1)
				tech_name = ""
				for nameobprocii in most_common_element[2:]:
					# if nameobprocii is not None:
					tech_name = str(tech_name) + str(nameobprocii[0]) + ". "
				obinfoname3 = tech_name
		# row = []

		modelfolder_db = obinfoname1
		print(modelfolder_db)
		cursor.execute(
			'SELECT first_name, last_name, category, apartmentnumb, floornumb FROM People WHERE modelfolder = ?',
			(modelfolder_db,))
		first_name_db = cursor.fetchall()
		print('first_name_db', first_name_db)
		if first_name_db == []:
			name01_s = 'Удален из БД'
			apartmentnumb_s = "0"
			floornumb_s = "0"
			categoriy_s = 'Внимание!'
		else:
			for row in first_name_db:
				print(str(row[0]))
				name01_s = row[1] + ' ' + row[0]
				# print(row)
				if row[2] == '1':
					categoriy_s = 'Жилец'
				if row[2] == '2':
					categoriy_s = 'Гость'
				if row[2] == '3':
					categoriy_s = 'Специальный'
				if row[2] == '4':
					categoriy_s = 'Внимание!'
			apartmentnumb_s = row[3]
			floornumb_s = row[4]
		date_time_s = datetime.datetime.fromtimestamp(timestart)
		date_s = date_time_s.strftime('%Y-%m-%d')
		time_s = date_time_s.strftime('%H-%M-%S')
		# csv_var1 = ['data_start_s', 'time_start_s', 'long_s', 'categoriy_s', 'name01_s', 'apartmentnumb_s', 'floornumb_s', 'name01_s',
		#            'time_start', 'time_end', 'long', 'koordinatstart', 'koordinatend', 'name01', 'percent01', 'name02',
		#            'percent02', 'name03', 'percent03']  # для наглядности
		obinfoname1_m = str(procentob1) + "%, " + str(obinfoname1)
		rezultstroka = [date_s, time_s, dlitelnost, categoriy_s, name01_s, apartmentnumb_s, floornumb_s, obinfoname1_m,
						timestart, timeend, dlitelnost, coordinatstart, coordinatend, obinfoname1, procentob1,
						obinfoname2, procentob2,
						obinfoname3, procentob3]

		connection.close()  # Закрытие файла БД

		myFile = open(myFilename, 'a')
		with myFile as csvfile:
			writer = csv.writer(csvfile)
			writer.writerow(rezultstroka)
			myFile.close()

		def add_event():
			event_name = obinfoname1
			#timeend
			if event_name:
				#current_time = datetime.now().strftime("%H:%M:%S")
				existing_event = find_existing_event(event_name)

				if existing_event:
					# Если событие уже существует, обновляем его время
					values = trv.item(existing_event, option="values")
					values = list(values)
					print("чтение trv", values)
					procentob1_old = trv.item(existing_event, 'values')[14]
					print(procentob1_old)
					procentob1_new = (round((((float(trv.item(existing_event, 'values')[14])) + (float(procentob1)))/2),1))
					print(procentob1_new)
					values[9] = str(timeend)
					values[14] = str(procentob1_new)
					dlitelnost_new = int(timeend) - (int(trv.item(existing_event, 'values')[8]))
					values[2] = str(dlitelnost_new)
					obinfoname1_m_new = str(procentob1_new) + "%, " + str(obinfoname1)
					values[7] = str(obinfoname1_m_new)
					print("новый trv", values)
					trv.item(existing_event, values=values)
				else:
					# Добавляем новое событие
					#trv.insert('', 'end', values=(event_name, current_time))
					trv.insert('', END, text="name", values=(
						date_s, time_s, dlitelnost, categoriy_s, name01_s, apartmentnumb_s, floornumb_s, obinfoname1_m,
						timestart, timeend,
						dlitelnost, coordinatstart, coordinatend, obinfoname1, procentob1, obinfoname2, procentob2,
						obinfoname3, procentob3))
					object_info(modelfolder_db)
					if enabled_checkbutton_view_scr_state == True:
						trv.yview_scroll(number=1, what="units")
					if enabled_checkbutton_view_scr_state_last == True:
						child_id = trv.get_children()[-1]
						print(child_id)
						trv.selection_set(child_id)


		def find_existing_event(event_name):
			print("find_existing_event", event_name)
			# Ищем существующее событие по названию
			#for item in trv.get_children()[-1]:
			item = trv.get_children()
			total_children = len(item)
			print("len", total_children)
			if total_children == 0:
				print("Нет строк для отображения.")
				return None
			start_index = max(total_children - oper_jurnal_laststroki_var_def, 0)
			print(oper_jurnal_laststroki_var_def)
			rezul = None
			for child in reversed(item[start_index:]):
				values = trv.item(child, 'values')
				print("values", values)
				print(trv.item(child, 'values')[13])
			#item = trv.get_children()[-1]
				if trv.item(child, 'values')[13] == event_name:
					if (timestart - (int(trv.item(child, 'values')[9]))) < oper_jurnal_laststrokitime_var_def:
						print(timestart - (int(trv.item(child, 'values')[9])))
						print(oper_jurnal_laststrokitime_var_def)
						print("child", child)
						return child
					else:
						print(timestart - (int(trv.item(child, 'values')[9])))
						rezul = False
				else:
					rezul = False
			if rezul == False:
				return None
		add_event()

	rec_ojects = True # временная переменная, для настройки через меню
	rec_Unknown = True # временная переменная, для настройки через меню

	#recognitionface = True  # временная переменная, потом удалить
	ti = round((time.time()), 3)
	tins = time.time_ns()
	# print(tins)
	# print(ti)

	# tistart = 1723384384.891
	# tiend = 1723384394.552
	# tirezult = round((tiend - tistart), 3)
	# print(tirezult)

	dt_object = datetime.datetime.fromtimestamp(ti)
	print(dt_object)
	try:
		data = pickle.loads(open(os.getcwd() + '\\data\\encodings.pickle', 'rb').read())  # encodings here
	except FileNotFoundError:
		knownEncodings, knownNames = [], []
		imagePaths = list(paths.list_images(os.path.join(os.getcwd(),'data/dataset/')))  # dataset here
		for (i, imagePath) in enumerate(imagePaths):
			print('{}/{}'.format(i + 1, len(imagePaths)), end=', ')
			image, name = cv2.imread(imagePath), imagePath.split(os.path.sep)[-2][13:]
			rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
			boxes = face_recognition.face_locations(rgb, model=model_algoritm_var_def)  # detection_method here , cnn, hog
			for encoding in face_recognition.face_encodings(rgb, boxes):
				knownEncodings.append(encoding)
				knownNames.append(name)
		data = {'encodings': knownEncodings, 'names': knownNames}
		f = open(os.getcwd() + '\\data\\encodings.pickle', 'wb')
		f.write(pickle.dumps(data))
		f.close()

	#stream = cv2.VideoCapture(os.getcwd() + '\\test-nvr_3.mp4')
	stream = cv2.VideoCapture(camera01link)
	width = 0
	if stream.isOpened():
		width = stream.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
		height = stream.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
		sootnoshenie = float(height / width)
		height_canval = int(704 * sootnoshenie)
		desired_size = (704, height_canval)
		x_c = (704 - 704) // 2
		y_c = (603 - height_canval) // 2
		print('width, height:', width, height, sootnoshenie, height_canval, x_c, y_c)

	resolut_video_model_var_def_w = int(int(width) * ((int(resolut_video_model_var_def)) / 100))
	print("Рразрешение для модели", resolut_video_model_var_def, resolut_video_model_var_def_w)

	writer = None
	# record = None
	writer1 = False
	videotime = str(format(time.time()))
	# offset = 50
	#recognitionface = True
	global trakingdef1st
	trakingdef1st = False
	global TrackIm
	TrackIm = True
	global imshowwindows
	global canvaswindows
	imshowwindowsdestroy = False
	imshowwindows = False # читать настройки из файла
	canvaswindows = True # читать настройки из файла


	csv_var = []
	csv_var1 = []

	spisok_ob = [[] for i in range(50)]
	spisok_ob_vivod = []
	ob_koordinat = []
	ob_koordinat.append(int(9999))
	ob_avtiv = []
	ob_avtiv.append('del')
	ob_time = []
	ob_time.append('del')
	# ob_time.append(float(1723374213.111))

	print(ob_koordinat, ob_avtiv, ob_time)
	kadr = 0
	f_kadr = 0
	f_kadr_zapis = foto_save_kadr_var_def

	while True:
		(grabbed, frame) = stream.read()
		if not grabbed:
			#continue
			canvas.delete("all")
			canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Сбой трансляции. Попытка переключения...",
							   fill="#e60004")
			#print("выход break")
			message.configure(text="Сбой трансляции.", fg="red")
			if imshowwindows == True:
				cv2.destroyAllWindows()
			TrackIm = False
			stream.release()
			break
		kadr = kadr + 1
		f_kadr = f_kadr + 1
		rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		rgb = imutils.resize(frame, width=resolut_video_model_var_def_w)  # 704, 352, 400
		r = frame.shape[1] / float(rgb.shape[1])
		# print(r)
		# rgb = rgb[22:91, 350:350]

		boxes = face_recognition.face_locations(rgb, model=model_algoritm_var_def)  # detection_method here hog
		# print(boxes)
		encodings = face_recognition.face_encodings(rgb, boxes)
		# print(encodings)
		names = []
		for encoding in encodings:
			votes = face_recognition.compare_faces(data['encodings'], encoding)

			if True in votes:
				names.append(
					Counter([name for name, vote in list(zip(data['names'], votes)) if vote == True]).most_common()[0][
						0])
			else:
				names.append('Unknown')
		for ((top, right, bottom, left), name) in zip(boxes, names):
			top, right, bottom, left = int(top * r), int(right * r), int(bottom * r), int(left * r)
			unix_time = int(time.time())
			unix_timef = round((time.time()), 3)
			date_time = datetime.datetime.fromtimestamp(unix_time)
			date_timef = date_time.strftime('%Y-%m-%d_t_%H-%M-%S')
			date_timef_catalog_day = date_time.strftime('%Y-%m-%d')

			k_summ = round(((top + right + bottom + left) / 4), 2)
			csv_var = [str(date_timef) + ',' + str(name) + ',' + str(unix_timef) + ',' + str(top) + ',' + str(
				right) + ',' + str(bottom) + ',' + str(left) + ',' + str(k_summ)]
			csv_var1.append([str(date_timef) + ',' + str(name) + ',' + str(kadr) + ',' + str(unix_timef) + ',' + str(
				top) + ',' + str(right) + ',' + str(bottom) + ',' + str(left) + ',' + str(k_summ)])
			# print(csv_var1)

			# блок проверка координат
			ob_koordinat_len = len(ob_koordinat)
			#print(ob_koordinat_len)
			marker1 = None
			ob_index = -1
			for t in ob_koordinat:
				ob_index = ob_index + 1
				if t != 'del':
					# t_granici_v = t + int(t * 0.07)
					# t_granici_n = t - int(t * 0.07)
					t_granici_v = t + (t * facerecog_granici1_face_var_def)
					t_granici_n = t - (t * facerecog_granici1_face_var_def)
					if k_summ >= t_granici_n and k_summ <= t_granici_v:
						# print("верно: " + str(ob_index))
						ob_koordinat[ob_index] = k_summ
						ob_time[ob_index] = (float(unix_timef))
						print("Заменили значение " + str(t) + " на новое " + str(k_summ) + " в списке с номером " + str(
							ob_index) + " Время " + str(ob_time[ob_index]))
						marker1 = True
						spisok_ob[ob_index].append(csv_var)
						# print(spisok_ob)
						break
					else:
						# print("не верно: " + str(ob_index))
						marker1 = False

			if marker1 == False:
				ob_index = -1
				print("2 уровень")
				for t in ob_koordinat:
					ob_index = ob_index + 1
					if t != 'del':
						# t_granici_v = t + int(t * 0.07)
						# t_granici_n = t - int(t * 0.07)
						t_granici_v = t + (t * facerecog_granici2_face_var_def)
						t_granici_n = t - (t * facerecog_granici2_face_var_def)
						if k_summ >= t_granici_n and k_summ <= t_granici_v:
							# print("верно: " + str(ob_index))
							ob_koordinat[ob_index] = k_summ
							ob_time[ob_index] = (float(unix_timef))
							print("Заменили значение " + str(t) + " на новое " + str(
								k_summ) + " в списке с номером " + str(
								ob_index) + " Время " + str(ob_time[ob_index]))
							marker1 = True
							spisok_ob[ob_index].append(csv_var)
							# print(spisok_ob)
							break
						else:
							# print("не верно: " + str(ob_index))
							marker1 = False

			if marker1 == False:
				ob_index = -1
				print("3 уровень")
				for t in ob_koordinat:
					ob_index = ob_index + 1
					if t != 'del':
						# t_granici_v = t + int(t * 0.07)
						# t_granici_n = t - int(t * 0.07)
						t_granici_v = t + (t * facerecog_granici3_face_var_def)
						t_granici_n = t - (t * facerecog_granici3_face_var_def)
						if k_summ >= t_granici_n and k_summ <= t_granici_v:
							# print("верно: " + str(ob_index))
							ob_koordinat[ob_index] = k_summ
							ob_time[ob_index] = (float(unix_timef))
							print("Заменили значение " + str(t) + " на новое " + str(
								k_summ) + " в списке с номером " + str(
								ob_index) + " Время " + str(ob_time[ob_index]))
							marker1 = True
							spisok_ob[ob_index].append(csv_var)
							# print(spisok_ob)
							break
						else:
							# print("не верно: " + str(ob_index))
							marker1 = False

			if marker1 == False:
				ob_koordinat.append((k_summ))
				ob_time.append(float(unix_timef))
				spisok_ob[len(ob_koordinat) - 1].append(csv_var)
				# print(spisok_ob)
				print("Добавили новое значение " + str(k_summ) + " Время " + str(ob_time[ob_index]))
				print(ob_koordinat)
			#Блок распознования
			#if recognitionface is True:
			if name == 'Unknown':
				offset1 = int((bottom - top) / 2)
				if rec_Unknown == True:
					try:
						cv2.imwrite("data/faces/" + str(date_timef_catalog_day) + "/F_d_" + str(
							date_timef) + '_n_' + name + '_u_' + str(unix_timef) + '_top_' + str(
							top) + '_right_' + str(right) + '_bottom_' + str(bottom) + '_left_' + str(
							left) + ".jpg",
									frame[top - offset1:top + offset1 + (bottom - top),
									left - offset1:left + offset1 + (right - left)])
					except Exception:
						print('Face recognition failed, not save')
			y = top - 15 if top - 15 > 15 else top + 15
			if name != 'Unknown':
				offset2 = int((bottom - top) / 2)
				if rec_ojects == True and f_kadr == 1:
					try:
						cv2.imwrite("data/faces/" + str(date_timef_catalog_day) + "/F_d_" + str(
							date_timef) + '_n_' + name + '_u_' + str(unix_timef) + '_top_' + str(top) + '_right_' + str(
							right) + '_bottom_' + str(bottom) + '_left_' + str(left) + ".jpg",
									frame[top - offset2:top + offset2 + (bottom - top),
									left - offset2:left + offset2 + (right - left)])
					except Exception:
						print('Face recognited, not save')
				cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 1)
				cv2.putText(frame, name[8:], (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
			else:
				cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
		if f_kadr == f_kadr_zapis or f_kadr > f_kadr_zapis:
			f_kadr = 0
			# cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 0, 0), 2)
		# cv2.rectangle(im, (x - 50, y - 50), (x + w + 50, y + h + 50), (225, 0, 0), 2)
		# print(str(name), str("top"), str(top), str("right"), str(right), str("bottom"), str(bottom), str("left"),
		# str(left), str(format((time.time()))))

		# csv_var = [{str(date_timef),str(name),str(unix_time),str(top),str(right),str(bottom),str(left)}]

		# if name == 'Unknown':
		# cv2.imshow('im', im[y - offset:y + h + offset, x - offset:x + w + offset])
		# offset1 = int((bottom-top)/2)
		# print(str(offset1))
		# cv2.imwrite("data/face/F_" + name + "_t" + str(format(time.time())) + 'c' + str(top) + ".jpg", frame[top-offset1:top + offset1 + (bottom-top), left-offset1:left + offset1 + (right-left)])

		# Блок контроля времени объекта
		unix_timef_now = round((time.time()), 3)
		# print(unix_timef_now)
		ob_indext = -1
		for obtime in ob_time:
			ob_indext = ob_indext + 1
			if obtime != 'del':
				timerezult = (float(unix_timef_now) - obtime)
				print(timerezult)
				print(ob_time)
				if timerezult >= 4:

					ob_time[ob_indext] = 'del'
					ob_koordinat[ob_indext] = int(9999)
					print("можно формировать данные об объекте")
					spisok_ob_vivod = spisok_ob[ob_indext].copy()
					spisok_ob[ob_indext] = []
					sobo = threading.Thread(target=spisok_ob_odrabotka, daemon=True)
					sobo.start()
					# print("Status", sobo.is_alive())

					myFile1 = open(myFilename1, 'a')
					with myFile1 as csvfile1:
						writer1 = csv.writer(csvfile1)
						writer1.writerows(spisok_ob_vivod)
						csv_razdelitel = ['1']
						writer1.writerow(csv_razdelitel)
						myFile1.close()

					# Блок очистки списка
					if (len(ob_time)) > 30:
						if (ob_time.count('del')) == (len(ob_time)):
							ob_koordinat = []
							ob_koordinat.append(int(9999))
							ob_avtiv = []
							ob_avtiv.append('del')
							ob_time = []
							ob_time.append('del')

		if cv2.waitKey(1) & trakingdef1st == True: #cv2.waitKey(18)
			print("Анализ видео остановлен.")
			res = "Анализ видео остановлен"
			message.configure(text=res)
			canvas.delete("all")
			text_mes00 = "Анализ видео остановлен."
			text_mes01 = 'Для запуска нажмите "Начать анализ видео" в меню "Управление"'
			if WS_spot == True:
				text_mes00 = "Трансляция и анализ видео остановлены."
				text_mes01 = 'Для запуска нажмите: 1."Подключить камеру" и 2."Начать анализ видео" в меню "Управление"'
			canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text=text_mes00,
							   fill="#e60004")
			canvas.create_text(10, 35, font="Helvetica 12", anchor=NW, text=text_mes01, fill="#e60004")
			if imshowwindows == True:
				cv2.destroyAllWindows()
			TrackIm = False
			stream.release()
			break

		# if cv2.waitKey(1) & 0xFF == ord('s'):
		# record = False
		# print("stop")
		# writer1 = False
		# writer.release()
		# print(writer)

		# if cv2.waitKey(1) & 0xFF == ord('c'): #start
		# writer = None
		# videotime = str(format(time.time()))
		# print("start")
		# print(videotime)
		# writer1 = True
		# print(writer1)
		# print(writer)
		# cv2.imshow('Video file1', rgb)
		if TrackImwindows == True:
			if canvaswindows == True:
				img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
				img = Image.fromarray(img)
				img = img.resize(desired_size, Image.LANCZOS)
				imgtk = ImageTk.PhotoImage(image=img)
				canvas.imgtk = imgtk
				canvas.create_image(x_c, y_c, image=imgtk, anchor='nw') #nw
				#canvas.place(x=1105, y=30)
				label.imgtk = imgtk  # keep a reference!
				if imshowwindowsdestroy == True:
					cv2.destroyAllWindows()
					imshowwindowsdestroy = False

			if imshowwindows == True:

				#cv2.namedWindow('Dozor01', cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
				imshowwindowsdestroy = True
				#cv2.namedWindow('Dozor01', cv2.WINDOW_KEEPRATIO)
				try:
					cv2.namedWindow('Dozor_Cam01', cv2.WINDOW_NORMAL)  # работает
					cv2.imshow('Dozor_Cam01', frame)
					cv2.setWindowProperty('Dozor_Cam01', cv2.WND_PROP_TOPMOST, 1)
				except Exception:
					print("Проблема в потоке, окно закрыто")
					cv2.destroyAllWindows()

		else:
			if imshowwindows == True:
			#canvas.create_text(10, 100, anchor=NW, text="Трансляция скрыта, распознование продолжается", fill="#004D40")
				cv2.destroyAllWindows()





def trakingdef1imshow():
	global TrackImwindows
	global TrackIm
	if TrackIm == True:
		if TrackImwindows == True:
			TrackImwindows = False
			print("Видео CV отключено")
			res = "Видео CV отключено"
			message.configure(text=res)
		else:
			TrackImwindows = True
			print("Видео CV включено")
			res = "Видео CV включено"
			message.configure(text=res)
	else:
		print("Настройка доступна при запуске CV2")
		res = "Настройка доступна при запуске CV2"
		message.configure(text=res)


def trakingdef1stop():
	global trakingdef1st
	global TrackIm
	if TrackIm == True:
		if trakingdef1st == False:
			trakingdef1st = True
			#print("Распознование видео отключено")
			#res = "Распознование видео отключено"
			#message.configure(text=res)
		else:
			print("Распознование видео не ведется")
			res = "Распознование видео не ведется"
			message.configure(text=res)
	else:
		print("Распознование видео не ведется")
		res = "Распознование видео не ведется"
		message.configure(text=res)



def RecordVid():
	import datetime, time
	#import cv2, os
	writer = None
	record = None
	writer1 = True
	global rv1
	global stop_thread_rv1
	global v_record_dlit_var
	global v_record_codec_var
	global v_record_frames_var

	v_record_dlit_var_def = int(v_record_dlit_var)
	v_record_codec_var_def = v_record_codec_var
	v_record_frames_var_def = int(v_record_frames_var)

	print("проверка настроек ", v_record_dlit_var_def, v_record_codec_var_def, v_record_frames_var_def)

	#Создание каталога текущей даты для сохранения фоток лиц и видео
	unix_time = int(time.time())
	date_time = datetime.datetime.fromtimestamp(unix_time)
	date_timef = date_time.strftime('%Y-%m-%d')
	catalog_day_video = "data/video/records_video/" + date_timef
	if not os.path.exists(catalog_day_video):
		os.makedirs(catalog_day_video)

	videotime = str(format(time.time()))
	i = 0
	ic = 0
	ftp1 = 20
	stream_rec = cv2.VideoCapture(camera01link)
	# used to record the time when we processed last frame
	prev_frame_time = 0

	# used to record the time at which we processed current frame
	new_frame_time = 0

	if stream_rec.isOpened():
		width = stream_rec.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
		height = stream_rec.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
		print('width, height:', width, height)
		time_start_res = time.time()
		res = "Запущена запись видео"
		message.configure(text=res)
		while True:
			(grabbed, frame) = stream_rec.read()
			if not grabbed:
				continue
			new_frame_time = time.time()
			fps = 1 / (new_frame_time - prev_frame_time)
			prev_frame_time = new_frame_time
			fps = int(fps)
			fps = str(fps)
			# print(str(fps))

			if writer1 is True:
				if writer is None:
					rejim_record = "hand"
					unix_time = int(time.time())
					date_time = datetime.datetime.fromtimestamp(unix_time)
					date_timef = date_time.strftime('%Y-%m-%d_t_%H-%M-%S')
					date_timef_catalog_day = date_time.strftime('%Y-%m-%d')
					writer = cv2.VideoWriter(os.getcwd() + '\\data\\video\\records_video\\' + str(date_timef_catalog_day) + '\\V_d_' + str(date_timef) + '_u_' + str(unix_time) + '_r_' + rejim_record + '.avi',
											 cv2.VideoWriter_fourcc(*v_record_codec_var_def), v_record_frames_var_def, (frame.shape[1], frame.shape[0]),
											 True)
				try:
					writer.write(frame)
				except Exception as e:
					print(f"Ошибка при создании VideoWriter: {e}")

				# i = i + 1
				time_contin_res = time.time()
				ic = int(time_contin_res - time_start_res)
				# print(str(int(ic)))
				if ic == (i + 30):
					i = ic
					res = "Идет запись видео: " + str(float(i / 60)) + " мин."
					message.configure(text=res, fg="red")
				if ic >= v_record_dlit_var_def:
					i = ic
					res = "Запись видео остановлена"
					message.configure(text=res, fg="red")
					RecordStopVideo()
				global stop_thread_rv1
				if stop_thread_rv1:
					break

		stream_rec.release()
		writer.release()
	else:
		message.configure(text="Сбой записи видео, поток не открыт", fg="red")
		#print("Поток не открыт")
		rv1 = None
		stop_thread_rv1 = True

def RecordVideo():
	if __name__ == '__main__':
		global knopka_rv
		global rv1
		global rv
		global stop_thread_rv1
		if rv1 == None:
			rv1 = 1
			#p = Process(target=RecordVid)
			#p.start()
			#p.join()
			stop_thread_rv1 = False
			rv = threading.Thread(target=RecordVid, daemon=True)
			print("Status", rv.is_alive())
			rv.start()
			#print("нажата кнопка: запись видео")
			res = "Поготовка к записи видео"

		else:
			print("Запись уже запущена")
			res = "Запись видео уже ведется"
		message.configure(text=res, fg="black")

def RecordStopVideo():
	global stop_thread_rv1
	global rv
	global rv1
	if stop_thread_rv1 is False:
		print("проверка условия: Запись видео")
		res = "проверка условия: Запись видео"
		if rv1 == 1:
			stop_thread_rv1 = True
			rv1 = None
			#rv.join()
			print("Запись видео остановлена")
			res = "Запись видео остановлена"
			unix_time = int(time.time())
			date_time = datetime.datetime.fromtimestamp(unix_time)
			date_timef = date_time.strftime('%Y-%m-%d')
			video_object_info_m_day(date_timef)
	else:
		print("Запись видео не ведется")
		res = "Запись видео не ведется"
	message.configure(text=res)



def WebStreame():
	global WS_spot
	global WS
	global WS1
	global set03_user
	global TrackIm
	global label_locallink
	global label_locallink_vlc
	canvas.delete("all")
	canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Запуск трансляции...", fill="#e60004")
	if __name__ == "__main__":
		if WS1 == None:
			camera01_link1 = None
			aktiv_number_cam = "channel_01"
			stream_connect = "0"
			connection = sqlite3.connect('data/camerasetting.db')
			cursor = connection.cursor()
			cursor.execute('SELECT link FROM cameras WHERE activ_number = ?', (aktiv_number_cam,))
			camera01_link = cursor.fetchall()
			for row in camera01_link:
				print(str(row[0]))
				camera01_link1 = row[0]
			# print(str(camera01_link))
			connection.close()
			if camera01_link1 != None:
				stream_test = cv2.VideoCapture(camera01_link1)
				if stream_test.isOpened():
					width = stream_test.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
					height = stream_test.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
					print('width, height:', width, height)
					stream_connect = "1"
					stream_test.release()
					if width != 0.0 and height != 0.0:
						# subprocess.run(["python", "webstreaming_1.py"])
						# webstreaming_1.some_function()
						# os.system('python webstreaming_1.py')
						# WS = multiprocessing.Process(target=WebStreame1, daemon=True)
						WS_spot = False
						WS = threading.Thread(target=WebStreame1, daemon=True)
						print("Status", WS.is_alive())
						WS.start()
						# os.system('python webstreaming_1.py')
						WS1 = True
						canvas.delete("all")
						canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Успешное подключение к камере.",
										   fill="#e60004")

						label_locallink = tk.Label(window, text="Открыть трансляцию в браузере", font=('Helvetica', 10),
												   background='lightgrey', foreground='blue', cursor="hand2")
						label_locallink.place(x=1105, y=0)
						label_locallink.bind("<Button-1>", open_link)  # Привязка клика по лейблу к функции

						label_locallink_vlc = tk.Label(window, text="/ VLC", font=('Helvetica', 10),
												   background='lightgrey', foreground='blue', cursor="hand2")
						label_locallink_vlc.place(x=1310, y=0)
						label_locallink_vlc.bind("<Button-1>", open_link_vlc)  # Привязка клика по лейблу к функции

						if set03_user != "1" and TrackIm == False:
							canvas.create_text(10, 35, font="Helvetica 12", anchor=NW, text='Нажмите кнопку "Начать анализ видео" в меню "Управление"',
											   fill="#e60004")
					else:
						canvas.delete("all")
						canvas.create_text(10, 10, font="Helvetica 12", anchor=NW,
										   text='Не удалось подключиться к камере, проверьте настройки.\nОтсутсвует видео поток\n'
												'(шир., выс.: ' + str(width) + ', ' + str(height) + ')',
										   fill="#e60004")
						print("поток WebStreame не открыт.")
				else:
					canvas.delete("all")
					canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Не удалось подключиться к камере, проверьте настройки.",
									   fill="#e60004")
					print("поток WebStreame не открыт.")
			else:
				canvas.delete("all")
				canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Камера не настроена.", fill="#e60004")
		else:
			print("WebStreame уже запущен. off")

def WebStreame1():
	global WS1
	global trakingdef1st
	global TrackIm
	global imshowwindows
	global stream
	global stop_thread_rv1
	global rv
	global rv1
	global WS_spot
	#import webstreaming_1
	#webstreaming_1()
	print("WebStreame")
	#subprocess.run(["python", "webstreaming_1.py"])
	#webstreaming_1.some_function()
	#if __name__ == "__main__":
		#os.system('python webstreaming_1.py')

	def kill(proc_pid):
		global WS1
		process1 = psutil.Process(proc_pid)
		for process in process1.children(recursive=True):
			process.kill()
		process1.kill()
		WS1 = None



	if __name__ == "__main__":
		global WS1
		global trakingdef1st
		global TrackIm
		global imshowwindows
		global stream
		global stop_thread_rv1
		global rv
		global rv1
		global WS_spot
		#process = subprocess.Popen(["python", "webstreaming_1.py"], shell=True) #Popen
		process = subprocess.Popen(["python", "webstreaming_1.py"], shell=True)


		#time.sleep(20)
		pid = process.pid
		print (str(pid))
		#process.send_signal(signal.SIGTERM)
		#process.terminate()
		while True:
			time.sleep(0.5)
			#global WS_spot
			if WS_spot == True:
				try:
					if TrackIm == True:
						trakingdef1st = True
						TrackIm = False
					if imshowwindows == True:
						print("отключение окна")
					if rv1 == 1:
						RecordStopVideo()
					# cv2.destroyAllWindows()
					# stream.release()
					time.sleep(1)
					kill(pid)
					WS1 = None
					#WS.join()
					# os.kill(pid, 0)
					# process.kill()
					print("Forced kill")
				except OSError:
					print("Terminated gracefully")
				break


def WebStreameStop():
	global label_locallink
	global label_locallink_vlc
	global WS_spot
	#global WS
	#global WS1
	if WS_spot is False:
		WS_spot = True
		print("WebStreame остановлено")
		res = "WebStreame остановлено"
		canvas.delete("all")
		canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Трансляция и анализ видео остановлены.", fill="#e60004")
		canvas.create_text(10, 35, font="Helvetica 12", anchor=NW, text='Для запуска нажмите: 1."Подключить камеру" и 2."Начать анализ видео" в меню "Управление"',
						   fill="#e60004")
		if label_locallink != None:
			label_locallink.destroy()
			label_locallink_vlc.destroy()
			label_locallink = None
			label_locallink_vlc = None
	else:
		print("WebStreame не запущен")
		res = "WebStreame не запущен"
	message.configure(text=res)

def createlogin():   # модуль создания учетной записи в программе через администратора
	global activeusergroupe
	if activeusergroupe == "admin":
		import tkinter as tk
		import hashlib
		import re

		windowcreat = Toplevel(window)
		windowcreat.title('Создание учетной записи')
		windowcreat.geometry('470x415+650+160')
		windowcreat.configure(bg="lightgrey")
		windowcreat.resizable(False, False)
		# кортежи и словари, содержащие настройки шрифтов и отступов:
		font_header = ('Helvetica', 10)
		font_entry = ('Helvetica', 10)
		label_font = ('Helvetica', 10)
		base_padding = {'padx': 10, 'pady': 8}
		header_padding = {'padx': 10, 'pady': 8}
		s = ttk.Style()
		s.configure('my.TButton', font=('Helvetica', 10))

		def userlist():
			file_path = "data/avtorizachiy.db"
			conn = sqlite3.connect(file_path)
			c = conn.cursor()
			c.execute('SELECT logins, groupe FROM logins')
			logins = c.fetchall()
			for login in logins:
				print(login)
			conn.close()

		userlist()

		def chekadmin():
			file_path = "data/avtorizachiy.db"
			conn = sqlite3.connect(file_path)
			c = conn.cursor()
			c.execute('SELECT groupe FROM logins')
			logins = c.fetchall()
			for login in logins:
				if login[0] == "admin":
					print(login)
			conn.close()

		chekadmin()


		userid = None
		username = None
		password = None
		groupe = None
		email = None
		groutformombo = None

		#main_status = Label(windowcreat, text="", font=font_header, justify=CENTER, **header_padding)
		# помещаем виджет в окно по принципу один виджет под другим
		#main_status.pack()

		def clickedtest():
			global userid, username, password, groupe, email
			userid = username_entry.get()
			password = password_entry.get()
			password02 = password_entry02.get()
			groupe = groupvibor.get()
			#groupe = str(sel1.get())
			print("groupe:" + groupe)
			email = email_entry.get()
			userid = userid.strip()  # удаляем пробелы в начале и в конце строки

			connection = sqlite3.connect('data/avtorizachiy.db')
			cursor = connection.cursor()
			cursor.execute('SELECT logins FROM logins')
			logins = cursor.fetchall()
			loginfound = False

			for login in logins:
				print(login)
				if login[0] == userid:
					print("Login found " + str(userid))
					loginfound = True
					connection.close()
					break
				else:
					loginfound = False
					print("Login not found")
			connection.close()
			if groupe == "admin" or groupe == "operator":
				if loginfound == False:
					if len(userid) < 21:
						if re.match(r'^[a-zA-Z0-9]+$', userid):
							if len(password) < 30:
								if password == password02:
									print("ok")
									clickedad()
								else:
									print("пароли не совпадают")
									res = str("Пароли не совпадают")
									main_status.configure(text=res, fg="red")
							else:
								print("длинный пароль")
								res = str("Пароль до 30 символов")
								main_status.configure(text=res, fg="red")
						else:
							print("nevernet simvoli")
							res = str("Недопустимые символы в имени пользователя")
							main_status.configure(text=res, fg="red")
					else:
						res = str("Имя пользователя до 20 символов")
						main_status.configure(text=res, fg="red")
						print("ukorotit")
				else:
					res = str("Имя пользователя уже существует")
					main_status.configure(text=res, fg="red")
					print("uje est login")
			else:
				res = str("Выберете группу пользователей")
				main_status.configure(text=res, fg="red")
				print("nujna groupe")


		def clickedad():
			global userid, username, password, groupe, email
			passwordh = password

			def hash_password(passwordh):
				return hashlib.sha256(passwordh.encode()).hexdigest()

			def check_password(stored_password, provided_password):
				return stored_password == hashlib.sha256(provided_password.encode()).hexdigest()

			stored_password = hash_password(passwordh)
			print(stored_password)
			# print(check_password(stored_password, '123456'))  # True
			# print(check_password(stored_password, 'wrong_password'))  # False

			print("Add")
			connection = sqlite3.connect('data/avtorizachiy.db')
			cursor = connection.cursor()

			# Добавляем нового пользователя
			cursor.execute('INSERT INTO logins (logins, passwordtab, groupe, email) VALUES (?, ?, ?, ?)',
						   (userid, stored_password, groupe, email))
			# Сохраняем изменения и закрываем соединение
			connection.commit()
			connection.close()
			res = "Добавлена новая учетная запись: " + str(userid) + ", " + str(groupe)
			message.configure(text=res)
			windowcreat.destroy()

		main_label1 = Label(windowcreat, text='Создание учетной записи', font=font_header, justify=CENTER,
							**header_padding, bg="lightgrey")
		# помещаем виджет в окно по принципу один виджет под другим
		main_label1.pack()

		# метка для поля ввода имени
		username_label1 = Label(windowcreat, text='Имя (login)', font=label_font, bg="lightgrey")
		username_label1.pack()
		username_label2 = Label(windowcreat, text='(англйиские буквы, цифры, до 20 символов):', font=label_font,
								**base_padding, bg="lightgrey")
		username_label2.pack()
		# поле ввода имени
		username_entry = Entry(windowcreat, bg='#fff', fg='#444', font=font_entry)
		username_entry.pack()

		# метка для поля ввода пароля
		password_label = Label(windowcreat, text='Пароль (до 30 символов):', font=label_font, **base_padding, bg="lightgrey")
		password_label.pack()

		# поле ввода пароля
		password_entry = Entry(windowcreat, bg='#fff', fg='#444', font=font_entry)
		password_entry.pack()

		# метка для поля ввода пароля
		password_label = Label(windowcreat, text='Повтор ввода пароля:', font=label_font, **base_padding, bg="lightgrey")
		password_label.pack()

		# поле ввода пароля
		password_entry02 = Entry(windowcreat, bg='#fff', fg='#444', font=font_entry)
		password_entry02.pack()

		# метка для поля ввода пароля
		email_label = Label(windowcreat, text='E-mail, телефон:', font=label_font, **base_padding, bg="lightgrey")
		email_label.pack()

		# поле ввода пароля
		email_entry = Entry(windowcreat, bg='#fff', fg='#444', width=40, font=font_entry)
		email_entry.pack()

		# метка для выбора группы пользователей
		groupvibor_label = Label(windowcreat, text='Выбор группы пользоателя:', font=label_font, **base_padding, bg="lightgrey")
		groupvibor_label.pack()

		#sel1 = tk.StringVar()
		groupvibor = ttk.Combobox(windowcreat, values=("operator", "admin"), width=25, state="readonly") #textvariable=sel1,
		groupvibor.current(0)
		groupvibor.pack()

		# кнопка отправки формы
		send_btn = ttk.Button(windowcreat, text='Создать', style='my.TButton', command=clickedtest)
		send_btn.pack(**base_padding)

		main_status = Label(windowcreat, text="", font=font_header, justify=CENTER, **header_padding, bg="lightgrey")
		# помещаем виджет в окно по принципу один виджет под другим
		main_status.pack()

		windowcreat.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		windowcreat.grab_set()
	else:
		print("Доступно администраторам")
		res = "Доступно администраторам"
		message.configure(text=res)



def userlistdelete():
	global activeusergroupe
	if activeusergroupe == "admin":
		rowidl = None
		naimj1 = None
		my_dict = None
		my_list = None

		# my_w = tk.Tk()
		my_w = tk.Toplevel(window)
		my_w.geometry("750x130+600+200")  # Size of the window
		my_w.configure(bg="lightgrey")
		my_w.title("Список пользователей")  # Adding a title
		from sqlalchemy import create_engine

		my_conn = sqlite3.connect('data/avtorizachiy.db')
		query = "SELECT rowid, logins, groupe, email FROM logins"
		my_data = list(my_conn.execute(query))  # SQLAlchem engine result set
		my_dict = {}  # Create an empty dictionary
		my_list = []  # Create an empty list
		for row in my_data:
			my_dict[[row][0][0]] = row  # id as key
			my_list.append(row[1])  # name as list
		# Print the other values for matching Name
		my_conn.close()

		def my_upd(*args):
			global my_list, my_dict, rowidl, naimj1, activeuserlogin
			print("в модуле y_upd sel.get():" + str(sel.get()))
			my_conn = sqlite3.connect('data/avtorizachiy.db')
			query = "SELECT rowid, logins, groupe, email FROM logins"
			my_data = list(my_conn.execute(query))  # SQLAlchem engine result set
			my_dict = {}  # Create an empty dictionary
			my_list = []  # Create an empty list
			print(my_list)
			for row in my_data:
				my_dict[[row][0][0]] = row  # id as key
				my_list.append(row[1])  # name as list
			print(my_list)
			# Print the other values for matching Name
			my_conn.close()

			# *args is used to pass any number of arguments
			l1.config(text="")  # Clear the label
			rezult = None
			for i, j in my_dict.items():  # Loop through the dictionary
				if j[1] == sel.get():  #
					print(i, j[0], j[1], j[2], j[3])
					vasheimy = ""
					if str(j[1]) == activeuserlogin:
						vasheimy = "АКТИВНЫЙ "
					l1.config(
						text=str(vasheimy) + "Логин: " + str(j[1]) + ", группа: " + str(j[2]) + ", " + str(j[3])
					)
					rowidl = j[0]
					naimj1 = str(j[1])
					print("rowidl " + str(rowidl))
					rezult = True
			if rezult != True:
				l1.config(text="Удаленная запись")
				rowidl = None

		def del_user():
			global rowidl
			global naimj1
			global activeuserlogin
			print("Имя из БД in del_user " + str(naimj1) + " логин активной сессии " + str(activeuserlogin))
			if rowidl != None:
				my_conn = sqlite3.connect('data/avtorizachiy.db')
				c = my_conn.cursor()
				query = c.execute("DELETE FROM logins WHERE rowid = ?", (rowidl,))
				c.close()
				my_conn.commit()
				my_conn.close()
				res = "Удалена учетная запись: " + str(naimj1)
				message.configure(text=res)
				my_upd()

		s = ttk.Style()
		s.configure('my.TButton', background='lightgrey', font=('Helvetica', 10))
		s.configure('MyCustomStyleName.TCombobox', background='blue', width=25, height=20, font=('Helvetica', 10))
		s.configure("My.TLabel",  # имя стиля
							 font="helvetica 10",  # шрифт
							 foreground="#000000",  # цвет текста
							 padding=10,  # отступы
							 background="lightgrey")  # фоновый цвет
		sel = tk.StringVar()  # string variable
		cb1 = ttk.Combobox(my_w, values=my_list, style = 'MyCustomStyleName.TCombobox', textvariable=sel, state="readonly")
		cb1.grid(row=2, column=1, padx=10, pady=30)  # Place it
		l1: Label = ttk.Label(my_w, text="Выберите login из списка", style="My.TLabel")  # Create a label
		l1.grid(row=2, column=2, padx=0, pady=0)  # Place it
		del_button = ttk.Button(my_w, text="Удалить запись", style='my.TButton',
							   command=del_user)
		del_button.place(x=195, y=70)
		btn = ttk.Button(my_w, text="Назад", style='my.TButton', command=my_w.destroy)
		btn.place(x=370, y=70)
		sel.trace("w", my_upd)  # Call the function on change
		my_w.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		my_w.grab_set()
		print("trace" + str(sel.get()))
	else:
		#print("Доступно администраторам")
		res = "Просмотр \ удаление учетных записей: Доступно администраторам"
		message.configure(text=res)







def streameCam1Set1():
	global activeusergroupe, ct1
	if activeusergroupe == "admin":
		print("настройки ссылки на камеры")
		import tkinter as tk
		#from tkinter import *
		from tkinter import ttk
		import sqlite3
		import cv2
		import imutils
		from PIL import Image, ImageTk
		from imutils import paths
		import threading
		from threading import Thread
		# from PyQt4 import QtGui

		# global camera01link
		camera01link = None
		cam1Link = None
		imgtk = None
		knopka_ct = None
		ct1 = False
		ct = None
		stop_thread_ct1 = None
		channel_list = ["channel_01"]
		global height, width, fps, cam_set_a, cam_set_b, cam_set_c, cam_set_d
		height = 0
		width = 0
		fps = 0
		cam_set_a = 0
		cam_set_b = 0
		cam_set_c = 0
		cam_set_d = 0

		file_path_cam = "data/camerasetting.db"
		connection = sqlite3.connect(file_path_cam)
		cursor = connection.cursor()
		cursor.execute('''
			    CREATE TABLE IF NOT EXISTS cameras (
			    id INTEGER PRIMARY KEY,
			    name_cam TEXT,
			    location TEXT,
			    vision TEXT,
			    link TEXT,
			    activ_number TEXT,
			    height TEXT,
			    width TEXT,
			    fps TEXT,   
			    cam_set_a TEXT,
			    cam_set_b TEXT,
			    cam_set_c TEXT,
			    cam_set_d TEXT
			    )
			    ''')
		connection.commit()
		connection.close()

		#windowcamset = tk.Tk()
		windowcamset = Toplevel(window)
		# windowcamset.eval('tk::PlaceWindow . center')
		windowcamset.title('Добавить камеру')
		windowcamset.geometry('425x850+600+100')
		windowcamset.resizable(False, False)
		windowcamset.configure(bg="lightgrey")
		# кортежи и словари, содержащие настройки шрифтов и отступов:
		font_header = ('Helvetica', 10)
		font_entry = ('Helvetica', 10)
		label_font = ('Helvetica', 10)
		base_padding = {'padx': 5, 'pady': 5}
		header_padding = {'padx': 7, 'pady': 7}

		def clickedtestcamset():
			import imutils
			from imutils import paths
			link = cam1Link_entry.get()
			#print(link)
			if link != None or link != 0 or link != "":
				#print("clickedtestcamset")
				source: str = link
				stream = cv2.VideoCapture(source)
				if stream.isOpened():
					width = stream.get(cv2.CAP_PROP_FRAME_WIDTH)  # float `width`
					height = stream.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float `height`
					print('width, height:', width, height)
					if width != 0.0:
						global ct1
						i = 0
						while True:
							(grabbed, frame) = stream.read()
							if not grabbed:
								print("continue")
								continue
							# break - v originalnom kode
							rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
							rgb = imutils.resize(rgb, width=400)  # 704, 352
							# r = frame.shape[1] / float(rgb.shape[1])
							img = Image.fromarray(rgb)
							imgtk = ImageTk.PhotoImage(image=img)
							canvas.imgtk = imgtk
							canvas.create_image(0, 0, image=imgtk, anchor='nw')
							canvas.create_text(10, 80, font="Helvetica 14 bold", anchor=NW, text="Размер изображения: " + str(width) + " x " + str(height),
											   fill="#37F000")
							main_status01.configure(text="Тестирование камеры пройдено", fg="green", bg="lightgrey")
							# canvas.place(x=200, y=300)
							# label.imgtk = imgtk  # keep a reference!
							# label.pack(side=tk.TOP, fill=tk.X, expand=True)
							# cv2.imshow('DozorTest', frame)
							i = i + 1
							print(i)
							if cv2.waitKey(1) & i == 5:
								break
						stream.release()
						ct1 = False
					else:
						canvas.delete("all")
						canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Изображение отсутствует.\nКамера включена,\nно не транслирует видео поток",
										   fill="#e60004")
						main_status01.configure(text="Ошибка проверки камеры", fg="red", bg="lightgrey")
				# cv2.destroyAllWindows()
				else:
					canvas.delete("all")
					canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Изображение отсутствует", fill="#e60004")
					canvas.create_text(10, 30, font="Helvetica 12", anchor=NW, text="или не актуально!",
									   fill="#e60004")
					canvas.create_text(10, 60, font="Helvetica 12", anchor=NW, text="Уточните путь к видео потоку!", fill="#e60004")
					res = "Видео поток не загружается"
					main_status01.configure(text=res, fg="red", bg="lightgrey")
					print("Видео поток не загружается")
					ct1 = False

		# label = Label(windowcamset, image=imgtk)
		##label.pack()
		# canvas.pack()

		def readcamset():
			from PIL import Image, ImageTk
			print("readcamset")
			global camera01link
			global camera1Link
			camera1Link = cam1Link_entry.get()
			print(camera1Link)

			img = cv2.imread('bee.jpg')
			img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
			img = Image.fromarray(img)
			imgtk = ImageTk.PhotoImage(image=img)

		# label = tk.Label(windowcamset, image=imgtk)

		# label.image = imgtk
		# label.pack()

		def capture_image():
			# Get an image from the camera
			cap = cv2.VideoCapture(0)
			ret, frame = cap.read()

			# Convert the image into RGB format
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

			# Convert the image into a Tkinter-compatible format
			frame = Image.fromarray(frame)
			imgtk = ImageTk.PhotoImage(image=frame)

			# Set the captured image as the label's background
			# label.configure(image=imgtk)
			# label.image = imgtk

			# Release the camera
			cap.release()

		def clickedtestcamsetThread():
			if __name__ == '__main__':
				res = "Проверка настроек . . ."
				main_status01.configure(text=res, fg="green")
				canvas.delete("all")
				global knopka_ct
				global ct1
				global ct
				global stop_thread_ct1
				if ct1 == False:
					ct1 = True
					# p = Process(target=RecordVid)
					# p.start()
					# p.join()
					stop_thread_ct1 = False
					ct = threading.Thread(target=clickedtestcamset, daemon=True)
					#print("Status", ct.is_alive())
					ct.start()
					#print("Тест камеры")

				else:
					#print("Тест камеры1")
					res = "Тест камеры1"

		def clickedadcam():
			global height, width, fps, cam_set_a, cam_set_b, cam_set_c, cam_set_d
			name_cam = cam1_entry.get()
			location = locatcam1_entry.get()
			vision = visioncam1_entry.get()
			link = cam1Link_entry.get()
			activ_number = channel_list.get()
			cam_set_a = enabled_view_scr_1.get()
			connection = sqlite3.connect('data/camerasetting.db')
			cursor = connection.cursor()

			# Добавление камеры
			cursor.execute('DELETE FROM cameras WHERE activ_number = ?', (activ_number,))
			# Сохраняем изменения и закрываем соединение
			connection.commit()
			connection.close()
			connection = sqlite3.connect('data/camerasetting.db')
			cursor = connection.cursor()
			cursor.execute(
				'INSERT INTO cameras (name_cam, location, vision, link, activ_number, height, width, fps, cam_set_a, cam_set_b, cam_set_c, cam_set_d) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
				(name_cam, location, vision, link, activ_number, height, width, fps, cam_set_a, cam_set_b, cam_set_c,
				 cam_set_d))
			connection.commit()
			connection.close()

			# res = "Добавлена новая камера " + str(name_cam) + ", для канала " + str(activ_number)
			# main_status01.configure(text=res)
			windowcamset.destroy()

		s = ttk.Style()
		s.configure('my.TButton', font=('Helvetica', 10), background='lightgrey')

		main_status01 = Label(windowcamset, text="Добавление камеры", font=5, bg="lightgrey")
		#main_status01.grid(row=0, column=0, sticky='w', padx=10)
		main_status01.place(x=10, y=10)
		# main_status.pack()



		# метка для поля ввода имени
		cam1_label1 = Label(windowcamset, text='Название камеры:', font=label_font, **base_padding, bg="lightgrey")
		#cam1_label1.grid(row=1, column=0, sticky='w')
		cam1_label1.place(x=10, y=40)
		# cam1_label1.pack()

		# поле ввода имени
		cam1_entry = Entry(windowcamset, bg='#fff', fg='#444', width=30, font=font_entry)
		#cam1_entry.insert(0, "Hello World")
		#cam1_entry.grid(row=2, column=0, sticky='w', padx=10)
		cam1_entry.place(x=10, y=70)
		# cam1_entry.pack()

		# метка для поля линк
		cam1Link_label = Label(windowcamset, text='Путь к видео потоку:', font=label_font, **base_padding, bg="lightgrey")
		#cam1Link_label.grid(row=4, column=0, sticky='w')
		cam1Link_label.place(x=10, y=100)
		# cam1Link_label.pack()

		enabled_view_scr_1 = IntVar()
		enabled_checkbutton_view_scr_1 = ttk.Checkbutton(windowcamset, text="Тестовый файл", variable=enabled_view_scr_1,
												   command=checkbutton_changed_view_scr)
		enabled_checkbutton_view_scr_1.state(['!selected'])
		enabled_checkbutton_view_scr_1.place(x=295, y=105)

		# поле ввода пароля
		cam1Link_entry = Entry(windowcamset, bg='#fff', fg='#444', width=57, font=font_entry)
		#cam1Link_entry.grid(row=5, column=0, sticky='w', padx=10)
		cam1Link_entry.place(x=10, y=130)
		# cam1Link_entry.pack()

		locatcam1_label = Label(windowcamset, text='Где установлена камера:', font=label_font, **base_padding, bg="lightgrey")
		#locatcam1_label.grid(row=6, column=0, sticky='w')
		locatcam1_label.place(x=10, y=160)
		# visioncam1_label.pack()

		# поле ввода пароля
		locatcam1_entry = Entry(windowcamset, bg='#fff', fg='#444', width=30, font=font_entry)
		#locatcam1_entry.grid(row=7, column=0, sticky='w', padx=10)
		locatcam1_entry.place(x=10, y=190)

		# метка для поля ввода пароля
		visioncam1_label = Label(windowcamset, text='Куда смотрит камера:', font=label_font, **base_padding, bg="lightgrey")
		#visioncam1_label.grid(row=8, column=0, sticky='w')
		visioncam1_label.place(x=10, y=210)
		# visioncam1_label.pack()

		# поле ввода пароля
		visioncam1_entry = Entry(windowcamset, bg='#fff', fg='#444', width=30, font=font_entry)
		#visioncam1_entry.grid(row=9, column=0, sticky='w', padx=10)
		visioncam1_entry.place(x=10, y=240)
		# visioncam1_entry.pack()

		# cam1linkaktiv.pack(**base_padding)

		channel_list_label = Label(windowcamset, text='Номер канала:', font=label_font, **base_padding, bg="lightgrey")
		#channel_list_label.grid(row=10, column=0, sticky='w')
		channel_list_label.place(x=10, y=270)
		# cam1linkaktiv_label.pack()

		# поле ввода пароля
		channel_list = ttk.Combobox(windowcamset, values=channel_list, width=35, state="readonly")
		#channel_list.grid(row=11, column=0, sticky='w', padx=10)
		channel_list.place(x=10, y=300)
		channel_list.current(0)

		# метка для поля ввода пароля
		# cam1linkaktiv_label = Label(windowcamset, text='Добавить в список и активировать камеру \ Только добавить в список:', font=label_font, **base_padding)
		# cam1linkaktiv_label.grid(row=12, column=0, sticky='w')
		# cam1linkaktiv_label.pack()

		# поле ввода пароля
		# cam1linkaktiv = ttk.Combobox(windowcamset, values=("Добавить в список и активировать", "Добавить в список"), width=35, state="readonly")
		# cam1linkaktiv.grid(row=13, column=0, sticky='w', padx=10)
		# cam1linkaktiv.current(1)
		# main_status = Label(windowcamset, text="   ", font=5)
		# main_status.grid(row=10, column=0, sticky='w')
		# main_status.pack()

		def camera_set_text():
			camera_set_text_win = Toplevel(windowcamset)
			#camera_set_text_win.eval('tk::PlaceWindow . center')
			camera_set_text_win.title('Действующие настройки камер')
			camera_set_text_win.geometry('850x500+800+150')

			text_box = Text(camera_set_text_win, height=200, width=100)
			text_box.grid(row=1, column=0, sticky='nw', padx=10)

			message = "настройки не считаны"

			try:
				sqlite_connection = sqlite3.connect('data/camerasetting.db')
				cursor = sqlite_connection.cursor()
				#print("Подключен к SQLite")

				sqlite_select_query = """SELECT * from cameras"""
				cursor.execute(sqlite_select_query)
				records = cursor.fetchall()
				message01 = "Количество записей: " + str(len(records))
				message02 = ""
				#print("Всего настроек:  ", len(records))
				#print("Вывод каждой строки")
				for row in records:
					message02 = (message02 + "\n\n" + "Название камеры: " + str(row[1]) + "\n" + "Где установлена камера: " + str(row[2]) + "\n" + "Куда смотрит камера: " + str(row[3]) + "\n" + "Путь к видео потоку: " + "\n" + str(row[4]) + "\n"+ "Номер канала: " + str(row[5]) + "\n")
					#print("Название камеры: ", row[1])
					#print("Где установлена камера:", row[2])
					#print("Куда смотрит камера:", row[3])
					#print("Путь к видео потоку: ", row[4])
					#print("Номер канала:", row[5], end="\n")
				message = message01 + message02
				cursor.close()


			except sqlite3.Error as error:
				print("Ошибка при работе с SQLite", error)
				message = "Настройки не считаны"
			finally:
				if sqlite_connection:
					sqlite_connection.close()
					print("Соединение с SQLite закрыто")
			text_box.insert('end', message)
			#camera_set_text_win.grab_set()

		testcam_btn = ttk.Button(windowcamset, text='Тест камеры', style='my.TButton', command=clickedtestcamsetThread)
		#testcam_btn.grid(row=14, column=0, sticky='nw', padx=10, pady=5)
		testcam_btn.place(x=10, y=340)
		# testcam_btn.pack(**base_padding)
		testcam_btn1 = ttk.Button(windowcamset, text='Посмотреть текущие настройки', style='my.TButton',
								 command=camera_set_text)
		#testcam_btn1.grid(row=15, column=0, sticky='nw', padx=10, pady=5)
		testcam_btn1.place(x=120, y=340)

		# кнопка отправки формы
		send_btn = ttk.Button(windowcamset, text='Сохранить', style='my.TButton', command=clickedadcam)
		#send_btn.grid(row=16, column=0, sticky='nw', padx=10, pady=5)
		# send_btn.pack(**base_padding)
		send_btn.place(x=10, y=380)


		# кнопка отправки формы
		send_btn1 = ttk.Button(windowcamset, text='Отмена', style='my.TButton', command=windowcamset.destroy)
		#send_btn1.grid(row=17, column=0, sticky='nw', padx=10, pady=5)
		# send_btn.pack(**base_padding)
		send_btn1.place(x=120, y=380)

		canvas = tk.Canvas(windowcamset, width=400, height=400)
		canvas.configure(bg="lightgrey")
		#canvas.grid(row=18, column=0, sticky='nw', padx=10)
		canvas.place(x=10, y=420)

		windowcamset.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		windowcamset.grab_set()



	else:
		print("Требуется авторизация администратором")
		res = "Требуется авторизация администратором"
		message.configure(text=res)



def checkboxes_csv_def():
	global activeusergroupe
	global window_csv
	global data_file_csv_for_search
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		#window_csv = tk.Tk()
		window_csv = tk.Toplevel()
		window_csv.title("Просмотр журнала событий")
		window_csv.configure(bg='lightgrey')
		window_csv.geometry("1600x900+100+50")
		window_csv.protocol("WM_DELETE_WINDOW", on_closing_model_status)
		icon_size_width = 100
		icon_size_height = 100
		s = ttk.Style()
		s.configure("My.TLabel",  # имя стиля
					font="helvetica 10",  # шрифт
					foreground="#000000",  # цвет текста
					padding=0,  # отступы
					background="lightgrey")  # фоновый цвет

		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()
		cursor.execute('SELECT set01 FROM logins WHERE logins = ?', (activeuserlogin,))
		set1_razmer_icon = cursor.fetchall()
		set1_razmer_icon = set1_razmer_icon[0][0]
		#print("Прочитанное значение размера: " + str(set1_razmer_icon))
		connection.close()
		razmer_icon_temp = set1_razmer_icon
		#print(razmer_icon_temp)
		if razmer_icon_temp == 'Мелкие значки':
			icon_size_width = 70
			icon_size_height = 70
		if razmer_icon_temp == 'Обычные значки':
			icon_size_width = 120
			icon_size_height = 120
		if razmer_icon_temp == 'Крупные значки':
			icon_size_width = 180
			icon_size_height = 180
		if razmer_icon_temp == 'Огромные значки':
			icon_size_width = 200
			icon_size_height = 200
		data_file_csv_for_search = None
		def open_file_data():
			global data_file_csv_for_search
			data_file_csv = ".\\data\\protocols\\normal_terminal\\"
			filepath = filedialog.askopenfilename(title="Выбор файла", initialdir=data_file_csv, defaultextension="csv")
			# print(filepath)
			if filepath != "":
				f111 = filepath[-19:-9]
				data_file_csv_for_search = f111
				video_podpis.configure(text="Видео на " + str(f111) + ":")
				video_object_info_m_day_def(f111)
				for i in trv.get_children():
					trv.delete(i)
				# print(i)
				window_csv.update()
				# i = str(i) + str(1)
				try:
					df = pd.read_csv(filepath, encoding="windows-1251")  # create DataFrame
					l1 = list(df)  # List of column names as header
					del l1[8:19]
					r_set = df.to_numpy().tolist()  # create list of list using rows
					p = 0
					for dt in r_set:
						p = p + 1
						v = [r for r in dt]
						trv.insert("", 'end', iid="csv0" + str(p), values=v)
						trv.yview_scroll(number=1, what="units")
					if p != 0:
						child_id = trv.get_children()[-1]
						#print(child_id)
						trv.selection_set(child_id)
				except FileNotFoundError:
					print("Данные для заполнения лога событий отсутсвуют")
		def open_file_data_search():
			global data_file_csv_for_search
			filepath = "data\\protocols\\normal_terminal\\nt_d_" + data_file_csv_for_search + "_t_00.csv"
			# print(filepath)
			if filepath != "":
				f111 = filepath[-19:-9]
				video_podpis.configure(text="Видео на " + str(f111) + ":")
				video_object_info_m_day_def(f111)
				for i in trv.get_children():
					trv.delete(i)
				# print(i)
				window_csv.update()
				# i = str(i) + str(1)
				try:
					df = pd.read_csv(filepath, encoding="windows-1251")  # create DataFrame
					l1 = list(df)  # List of column names as header
					del l1[8:19]
					r_set = df.to_numpy().tolist()  # create list of list using rows
					p = 0
					for dt in r_set:
						p = p + 1
						v = [r for r in dt]
						trv.insert("", 'end', iid="csv0" + str(p), values=v)
						trv.yview_scroll(number=1, what="units")
					if p != 0:
						child_id = trv.get_children()[-1]
						#print(child_id)
						trv.selection_set(child_id)
				except FileNotFoundError:
					print("Данные для заполнения лога событий отсутсвуют")
		open_button = ttk.Button(window_csv, text="Открыть журнал событий на дату", style='my.TButton',
								 command=open_file_data)
		open_button.place(x=820, y=5)

		header11f = ttk.Label(window_csv, text="Фотографии, сделанные во время события:", style="My.TLabel")  # , font=("Helvetica", 13)
		header11f.place(x=10, y=10)

		header11f1 = ttk.Label(window_csv, text="Информация из справочника объектов:", style="My.TLabel")  # , font=("Helvetica", 13)
		header11f1.place(x=820, y=642)

		l1 = ['data_start_s', 'time_start_s', 'long_s', 'categoriy_s', 'name01_s', 'apartmentnumb_s', 'floornumb_s',
			  'name01_m']
		trv = ttk.Treeview(window_csv, selectmode='browse', height=29,
						   show='headings', columns=l1)
		trv.place(x=820, y=35)
		vsb = tk.Scrollbar(window_csv, width=30, orient="vertical", command=trv.yview)
		vsb.pack(side=RIGHT, fill=Y)
		# vsb.place(x=30 + 200 + 2, y=95, height=200 + 20)
		trv.configure(yscrollcommand=vsb.set)
		for i in l1:
			trv.column(i, width=90, anchor='c')
			i1 = i
			if i == "long_s":
				trv.column(i, width=60, anchor='w')
				i1 = "Длит.,сек."
			if i == "data_start_s":
				i1 = "Дата,г.м.д."
			if i == "time_start_s":
				i1 = "Время,ч.м.с."
			if i == "categoriy_s":
				trv.column(i, width=90, anchor='w')
				i1 = "Категория"
			if i == "name01_s":
				trv.column(i, width=170, anchor='w')
				i1 = "Фамилия, имя"
			if i == "apartmentnumb_s":
				trv.column(i, width=60, anchor='c')
				i1 = "Квартира"
			if i == "floornumb_s":
				trv.column(i, width=50, anchor='c')
				i1 = "Этаж"
			if i == "name01_m":
				trv.column(i, width=130, anchor='w')
				i1 = "%, модель"
			trv.heading(i, text=str(i1))
		unix_time = int(time.time())
		date_time = datetime.datetime.fromtimestamp(unix_time)
		date_timef_file_day = date_time.strftime('%Y-%m-%d')
		data_file_csv_for_search = date_timef_file_day
		file_csv = "data\\protocols\\normal_terminal\\nt_d_" + date_timef_file_day + "_t_00.csv"
		# print(file_csv)
		try:
			df = pd.read_csv(file_csv, encoding="windows-1251")  # create DataFrame
			l1 = list(df)  # List of column names as header
			del l1[8:19]
			r_set = df.to_numpy().tolist()  # create list of list using rows
			p = 0
			for dt in r_set:
				p = p + 1
				v = [r for r in dt]
				trv.insert("", 'end', iid="csv0" + str(p), values=v)
				trv.yview_scroll(number=1, what="units")
			if p != 0:
				child_id = trv.get_children()[-1]
				#print(child_id)
				trv.selection_set(child_id)
		except FileNotFoundError:
			pass
			print("Данные для заполнения лога событий отсутсвуют")

		def item_selected(event):
			selected_people = ""
			tab_nomer = None
			for selected_item in trv.selection():
				item = trv.item(selected_item)
				# print(item)
				person = item["values"]
				# print(person)
				tab_nomer = person[13]
				data_katalog = person[0]
				vremy_nach = person[8]
				vremy_okonch = person[9]
				#print(tab_nomer, vremy_nach, vremy_okonch)
				selected_people = f"{selected_people}{person}\n"
			# lb2["text"] = selected_people
			print(tab_nomer)
			if tab_nomer != None:
				object_info(tab_nomer)
				foto_object_info(vremy_nach, vremy_okonch, data_katalog)
				video_object_info_m_def(vremy_nach, vremy_okonch, data_katalog)
			else:
				tab_nomer = "emply"
				vremy_nach = '1000000000'
				vremy_okonch = '1000000000'
				data_katalog = '1000-00-00'
				object_info(tab_nomer)
				foto_object_info(vremy_nach, vremy_okonch, data_katalog)
				video_object_info_m_def(vremy_nach, vremy_okonch, data_katalog)

		trv.bind("<<TreeviewSelect>>", item_selected)

		char_editor_csv = Text(window_csv, height=14, width=106, font=('Helvetica', 10), bg="lightgrey", wrap="word")
		char_editor_csv.place(x=820, y=665)

		#char_editor01 = Text(window_csv, height=14, width=18, font=('Helvetica', 10), wrap="word")
		#char_editor01.place(x=969, y=665)

		#char_editor02 = Text(window_csv, height=14, width=18, font=('Helvetica', 10), wrap="word")
		#char_editor02.place(x=1118, y=665)

		#char_editor03 = Text(window_csv, height=14, width=18, font=('Helvetica', 10), wrap="word")
		#char_editor03.place(x=1267, y=665)

		#char_editor04 = Text(window_csv, height=14, width=18, font=('Helvetica', 10), wrap="word")
		#char_editor04.place(x=1416, y=665)

		# checklist_csv = tk.Text(window_csv, width=200, height=40, font=("Helvetica", 12), bg='gray72', fg='#000', wrap=WORD)
		checklist_csv = scrolledtext.ScrolledText(window_csv, undo=True, width=110, height=22, bg="lightgrey", wrap='word')
		checklist_csv['font'] = ('Helvetica', '10')
		checklist_csv.place(x=10, y=35)
		checklist_csv.configure(state='disabled')

		# scrollbar1 = tk.Scrollbar(checklist_csv, width=20, orient="vertical", command=checklist_csv.yview)
		# checklist_csv['yscrollcommand'] = scrollbar1.set
		# scrollbar1.place(x=780, y=0)
		# checklist_csv.configure(yscrollcommand=scrollbar1.set)

		def foto_object_info(vremy_nach1, vremy_okonch1, data_katalog1):
			global imgs_csv
			global checkboxes_csv
			#print("test", vremy_nach1, vremy_okonch1)
			vremy_nach1 = int(vremy_nach1) - 2
			vremy_okonch1 = int(vremy_okonch1) + 2
			#print("test", vremy_nach1, vremy_okonch1, data_katalog1)
			# s1 = 1724950364
			# if int(s1) in range(vremy_nach1, vremy_okonch1):
			#	print("ok")
			path_catalog = (os.getcwd() + "\\data\\faces\\" + data_katalog1 + "\\")
			#print(path_catalog)
			files = glob.glob(path_catalog + '*.jpg')
			path_catalog1 = (os.getcwd() + "\\data\\photo\\event_save\\event_foto\\" + data_katalog1 + "\\")
			files1 = glob.glob(path_catalog1 + '*.jpg')
			files2 = files + files1
			files_rez = []
			#print("files_rez", files_rez)
			favorit_pic = 0
			all_pic = 0
			for f1 in files2:
				#print(f1)
				f11 = re.findall(r'[_][u][_][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][.]', f1)
				f11 = f11[0][3:13]
				if int(f11) in range(vremy_nach1, vremy_okonch1):
					files_rez.append((f1))
					f15 = None
					f15 = re.findall(r'[e][v][e][n][t][_][f][o][t][o]', f1)
					# print(f15)
					all_pic = all_pic + 1
					if f15 == ['event_foto']:
						favorit_pic = int(favorit_pic) + 1
					raznicha_pic = all_pic - favorit_pic
			#print(favorit_pic)
			# print("files_rez", files_rez)
			checklist_csv.delete("1.0", "end")
			checkboxes_csv = {}
			imgs_csv = []
			checklist_csv.configure(state='normal')
			checklist_csv.delete("1.0", "end")

			kolich = 0
			len_pic = len(files_rez)
			#print("len_pic", len_pic)
			for f2 in files_rez:
				var = tk.BooleanVar()
				img = ImageTk.PhotoImage(Image.open(f2).resize((icon_size_width, icon_size_height)))
				imgs_csv.append(img)
				kolich = kolich + 1
				if len_pic == favorit_pic and kolich == 1:
					path01 = os.path.join(os.getcwd(), "data", "photo", "event_save", "event_foto", data_katalog1)
					open_button_c1 = tk.Button(checklist_csv, text=" open ", cursor="hand2",
											   command=lambda path01_1=path01: openFolder(path01_1))
					checklist_csv.window_create("end", window=open_button_c1)
					checklist_csv.insert("end",
										 " Фото в архивной папке:", 'name1')
					checklist_csv.tag_config('name1', foreground='red')
					checklist_csv.insert("end", "\n")
				if len_pic > favorit_pic and kolich == 1:
					path02 = os.path.join(os.getcwd(), "data", "faces", data_katalog1)
					open_button_c2 = tk.Button(checklist_csv, text=" open ", cursor="hand2",
											command=lambda path02_1 = path02: openFolder(path02_1))
					checklist_csv.window_create("end", window=open_button_c2)
					checklist_csv.insert("end",
										 " Фото в рабочей папке:")
					checklist_csv.insert("end", "\n")

				if kolich == (all_pic - favorit_pic + 1) and favorit_pic != 0 and kolich != 1:
					checklist_csv.insert("end", "\n")
					path03 = os.path.join(os.getcwd(), "data", "photo", "event_save", "event_foto", data_katalog1)
					open_button_c3 = tk.Button(checklist_csv, text=" open ", cursor="hand2",
											   command=lambda path03_1=path03: openFolder(path03_1))
					checklist_csv.window_create("end", window=open_button_c3)
					checklist_csv.insert("end",
										 " Фото в архивной папке:", 'name1')
					checklist_csv.tag_config('name1', foreground='red')
					checklist_csv.insert("end", "\n")
				chk = tk.Checkbutton(checklist_csv, text=f2, image=img, variable=var, cursor="arrow", bg="grey67")
				checklist_csv.window_create("end", window=chk)
				checklist_csv.insert("end", " ")
				checkboxes_csv[f2] = {'var': var, 'chk': chk}

			if kolich == 0:
				checklist_csv.insert(tk.INSERT, "не найдены")

			checklist_csv.insert("end", "\n\n")
			# header11f.configure(text="Найдено " + str(kolich) + " фото.")

			checklist_csv.configure(state="disabled")

		def copy_select_foto():
			selected_options = []
			data_katalog = None
			i = 0
			for option, data in checkboxes_csv.items():
				if data['var'].get():
					selected_options.append(option)
					i = i + 1
			if i > 0:
				f11 = re.findall(r'[F][_][d][_][0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9][_]', selected_options[0])
				f11 = f11[0][4:14]
				#print("f11", f11)
				catalog_day_foto = "data/photo/event_save/event_foto/" + str(f11)
				if not os.path.exists(catalog_day_foto):
					os.makedirs(catalog_day_foto)
				for f in selected_options:
					try:
						shutil.copy(f, catalog_day_foto)

					except Exception:
						text01_f = "Файл " + str(f) + " существует в каталоге" + str(
							catalog_day_foto) + ".\n\n"
						#print(text01_f)
				checklist_csv.configure(state='normal')
				checklist_csv.insert("end",
									 "\nФото сохранено.") #Для обновления повторно выделите строку в журнале событий.
				checklist_csv.configure(state="disabled")

				if i == 0:
					text01 = "Не выделено ни одного изображения."
					#print("Не выделено ни одного изображения.")

		def object_info(modelfolder):
			global ch01
			global text_lab
			#global text_lab02
			#global text_lab03
			#global text_lab04
			#global text_lab05
			# ch01 = ch01 + 1
			# from PIL import Image, ImageTk
			global img_text_lab_csv
			#global img_text_lab01
			#global img_text_lab02
			#global img_text_lab03
			#global img_text_lab04
			#text_lab05 = text_lab04
			#text_lab04 = text_lab03
			#text_lab03 = text_lab02
			#text_lab02 = text_lab
			#img_text_lab04 = img_text_lab03
			#img_text_lab03 = img_text_lab02
			#img_text_lab02 = img_text_lab01
			#img_text_lab01 = img_text_lab
			if modelfolder != "emply":
				connection = sqlite3.connect('data/objects.db')
				cursor = connection.cursor()
				cursor.execute(
					'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
					(modelfolder,))
				first_name_db = cursor.fetchall()
				#print(first_name_db)
				if first_name_db == []:
					first_name_db = [('', 'Объект удален из БД', '0', '0', '0', '0', '0', '0', 'no_avatar_yel.jpg', 'None', 'None')]
					modelfolder = "no_avatar_yel"
				#print(first_name_db)
				for row in first_name_db:
					pass
					#print(str(row))
				connection.close()
				if row[2] == '1':
					categoriy_s = 'Жилец'
				if row[2] == '2':
					categoriy_s = 'Гость'
				if row[2] == '3':
					categoriy_s = 'Специальный'
				if row[2] == '4':
					categoriy_s = 'Внимание!'
				if row[2] == '0':
					categoriy_s = ''

				text_lab = ("\n" + categoriy_s + "\n" + str(row[1]) + " " + str(row[0]) + "\nкв. " + str(
					row[3]) + ", этаж " + str(row[4]) + "\n" + str(row[10]) + "\n" + str(row[7]))
				path1 = (os.getcwd() + "\\data\\photo\\objects\\" + modelfolder + ".jpg")
				bb = os.path.isfile(path1)
				if bb:
					img_text_lab_csv = ImageTk.PhotoImage(Image.open(path1).resize((130, 130)))
				else:
					path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
					img_text_lab_csv = ImageTk.PhotoImage(Image.open(path1).resize((130, 130)))

				char_editor_csv.configure(state="normal")
				char_editor_csv.delete("1.0", END)
				char_editor_csv.image_create(END, image=img_text_lab_csv)
				char_editor_csv.insert("end", text_lab)
				char_editor_csv.configure(state="disabled")

				#if img_text_lab01 != None:
				#	char_editor01.configure(state="normal")
				#	char_editor01.delete("1.0", END)
				#	char_editor01.image_create(END, image=img_text_lab01)
				#	char_editor01.insert("end", text_lab02)
				#	char_editor01.configure(state="disabled")

				#if img_text_lab02 != None:
				#	char_editor02.configure(state="normal")
				#	char_editor02.delete("1.0", END)
				#	char_editor02.image_create(END, image=img_text_lab02)
				#	char_editor02.insert("end", text_lab03)
				#	char_editor02.configure(state="disabled")

				#if img_text_lab03 != None:
				#	char_editor03.configure(state="normal")
				#	char_editor03.delete("1.0", END)
				#	char_editor03.image_create(END, image=img_text_lab03)
				#	char_editor03.insert("end", text_lab04)
				#	char_editor03.configure(state="disabled")

				#if img_text_lab04 != None:
				#	char_editor04.configure(state="normal")
				#	char_editor04.delete("1.0", END)
				#	char_editor04.image_create(END, image=img_text_lab04)
				#	char_editor04.insert("end", text_lab05)
				#	char_editor04.configure(state="disabled")
			else:
				char_editor_csv.configure(state="normal")
				char_editor_csv.delete("1.0", END)
				char_editor_csv.configure(state="disabled")

		l12: Label = tk.Label(window_csv, text="Выберите объект и фотографии для загрузки в модель.", font=("Helvetica", 10), background='lightgrey')  # Create a label
		l12.place(x=100, y=435)
		l12a: Label = tk.Label(window_csv, text="", font=("Helvetica", 10), fg="red", background='lightgrey')  # Create a label
		l12a.place(x=100, y=457)
		path11 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
		img_text_lab_csv = ImageTk.PhotoImage(Image.open(path11).resize((74, 74)))
		panel = Label(window_csv, image=img_text_lab_csv, bg="lightgrey")
		panel.image = img_text_lab_csv
		panel.place(x=7, y=405)

		def copy_select_foto_model():
			object_view_name = object_view.get()
			selected_options = []
			l12a.configure(text="")
			data_katalog = None
			i = 0
			for option, data in checkboxes_csv.items():
				if data['var'].get():
					selected_options.append(option)
					i = i + 1
			if  int(len(object_view_name)) > 5 and i > 0:
				#print(object_view_name)
				object_view_name01 = ".\\data\\dataset\\" + str(object_view_name) + "\\"
				с1 = 0
				for f in selected_options:
					try:
						shutil.copy(f, object_view_name01)
						с1 = с1 + 1

					except Exception:
						text01_f = "Файл " + str(f) + " существует в каталоге" + str(
							object_view_name01) + ".\n\n"
						#print(text01_f)
				if с1 != 0:
					#checklist_csv.configure(state='normal')
					l12a.configure(text="Для объекта " + object_view_name + " добавлено " + str(с1) + " фото.")
					#checklist_csv.insert("end",
					#					 "\nДля объекта " + object_view_name + " добавлено " + str(с1) + " фото.")
					#checklist_csv.configure(state="disabled")

				if i == 0:
					text01 = "Не выделено ни одного изображения."
					l12a.configure(text=text01)
			else:
				l12a.configure(text="Для загрузки выберите объект и фотографии.")
		def my_upd_l12_ii(*args):
			object_view_name = object_view.get()
			if object_view_name != "":
				connection = sqlite3.connect('data/objects.db')
				cursor = connection.cursor()
				cursor.execute(
					'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
					(object_view_name,))
				first_name_db = cursor.fetchall()
				# print("first_name_db", first_name_db)
				if first_name_db != []:
					for row in first_name_db:
						pass
						#print(str(row))
					connection.close()
					if row[2] == '1':
						categoriy_s = 'Жилец'
					if row[2] == '2':
						categoriy_s = 'Гость'
					if row[2] == '3':
						categoriy_s = 'Специальный'
					if row[2] == '4':
						categoriy_s = 'Внимание!'

					text_lab = (categoriy_s + ", " + str(row[1]) + " " + str(row[0]) + ", кв. " + str(
						row[3]) + ", этаж " + str(
						row[4]) + " " + str(row[10]))
					path1 = (os.getcwd() + "\\data\\photo\\objects\\" + object_view_name + ".jpg")
					bb = os.path.isfile(path1)
					if bb:
						img_text_lab_csv = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					else:
						path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
						img_text_lab_csv = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					panel.configure(image=img_text_lab_csv)
					panel.image = img_text_lab_csv
					l12.config(text=text_lab)
					l12a.configure(text="")
				# дописать вывод фотографии объекта
				else:
					object_view_name_dubli = object_view_name
					l12.config(text="Объект загрузки не найден в БД")
					result22 = askokcancel(title="Вопрос",
										   message="Объект загрузки не найден в базе данных.\n\nПереместить каталог: " + object_view_name_dubli + " в архив?")
					if result22:
						# print(object_view_name_dubli)
						path_source = os.getcwd() + "\\data\\dataset\\" + object_view_name_dubli + "\\"
						path_dest = (os.getcwd() + "\\data\\data_archives\\dataset_archives\\")
						try:
							shutil.move(path_source, path_dest)
							l12.config(text="Каталог удален. Обновление списка каталогов при следующей загрузке меню.")
						except Exception:
							l12.config(
								text="Каталог не найден. Обновление списка каталогов при следующей загрузке меню.")
			# дописать вопрос об удалении не найденного каталога
			else:
				l12.config(text="Выберите объект загрузки.")

		directory02 = (os.getcwd() + '\\data\\dataset\\')
		dir_list_pre = len(list(os.walk(directory02)))
		#print("dir_list_pre", dir_list_pre)
		# print(dir_list)
		if dir_list_pre > 1:
			object_list = next(os.walk(directory02))[1]
			object_list.sort(reverse=True)
		# print("список директорий объетов " + str(object_list))
		else:
			object_list = ['']
		# sel007 = tk.StringVar()  # string variable
		object_list_list = object_list
		object_view = ttk.Combobox(window_csv, values=object_list_list, width=30,
								   state="readonly")  # textvariable=sel007,
		# object_view.pack(anchor=tk.NW, padx=5, pady=2)
		object_view.place(x=100, y=406)
		#object_view.current(0)  # сделать условие, при 0 списке выходит ошибка!
		#print(object_list_list)
		object_view.bind("<<ComboboxSelected>>", my_upd_l12_ii)

		save_button = ttk.Button(window_csv, text="Загрузить выделенные фото в модель", style='my.TButton',
								 command=copy_select_foto_model)
		save_button.place(x=559, y=405)

		save_button1 = ttk.Button(window_csv, text="Сохранить выделенные фото", style='my.TButton',
								  command=copy_select_foto)
		save_button1.place(x=608, y=5)



		def video_object_info_m_day_def(data_katalog1):
			# global imgs_csv_m_v
			# global checkboxes_csv_m_v
			path_catalog = (os.path.join(os.getcwd(), "data/video/records_video/" + data_katalog1 + "/"))
			files = glob.glob(path_catalog + '*.avi')
			kolich = len(files)
			path_catalog_a = (os.path.join(os.getcwd(), "data/video/archive_video/" + data_katalog1 + "/"))
			files_a = glob.glob(path_catalog_a + '*.avi')
			kolich_a = len(files_a)
			files_itog = files + files_a
			#print("kolich", kolich, files)
			files_rez = []
			favorit_pic = 0
			all_pic = 0
			checklist_csv1_15_day.delete("1.0", "end")
			checklist_csv1_15_day.configure(state='normal')
			checklist_csv1_15_day.delete("1.0", "end")
			ch = 0
			for f2 in files_itog:
				ch = ch + 1
				if ch == kolich + 1:
					if kolich !=0:
						checklist_csv1_15_day.insert("end", "\n")
					checklist_csv1_15_day.insert("end", "В архивной папке:\n", "name001")
					checklist_csv1_15_day.tag_config('name001', foreground='red')
				f2_list = f2.split(os.path.sep)[-1][17:38]
				open_button = tk.Button(checklist_csv1_15_day, text=f2_list, cursor="hand2",
										command=lambda f=os.path.join(f2): video_play(f))
				checklist_csv1_15_day.window_create("end", window=open_button)
				checklist_csv1_15_day.insert("end", " ")

			# chk1.bind("<Button-1>", lambda event: (on_click(), chk.toggle()))
			if (kolich + kolich_a) == 0:
				checklist_csv1_15_day.insert(tk.INSERT, "не найдены")
			checklist_csv1_15_day.configure(state="disabled")

		video_podpis = tk.Label(window_csv, font=('Helvetica', 10), background='lightgrey', foreground='black',
								justify=LEFT, anchor='w', width=18, height=1)
		unix_time = int(time.time())
		date_time = datetime.datetime.fromtimestamp(unix_time)
		date_timef = date_time.strftime('%Y-%m-%d')
		video_podpis.configure(text="Видео на " + str(date_timef) + ":")
		video_podpis.place(x=10, y=490)

		checklist_csv1_15_day = scrolledtext.ScrolledText(window_csv, undo=True, width=61, height=23, wrap='word')
		checklist_csv1_15_day['font'] = ('Helvetica', '10')
		checklist_csv1_15_day.place(x=10, y=515)
		checklist_csv1_15_day.configure(state='disabled', bg="lightgrey")
		video_object_info_m_day_def(date_timef)

		#save_button15_day = ttk.Button(window_csv, text="Обновить", style='my.TButton',
		#							   command=lambda td=data_now(date_timef): video_object_info_m_day_def(td))
		#save_button15_day.place(x=161, y=487)

		def video_object_info_m_def(vremy_nach1, vremy_okonch1, data_katalog1):
			global imgs_csv_m_v_d
			global checkboxes_csv_m_v_d
			icon_size_width = 70
			icon_size_height = 70
			# print("test", vremy_nach1, vremy_okonch1)
			vremy_nach1 = int(vremy_nach1) - 20
			vremy_okonch1 = int(vremy_okonch1) + 20
			# print("test", vremy_nach1, vremy_okonch1, data_katalog1)
			# s1 = 1724950364
			# if int(s1) in range(vremy_nach1, vremy_okonch1):
			#	print("ok")
			path_catalog = (os.path.join(os.getcwd(), "data/video/records_video/" + data_katalog1 + "/"))
			# print(path_catalog)
			files = glob.glob(path_catalog + '*.avi')
			path_catalog1 = (os.path.join(os.getcwd(), "data/video/archive_video/" + data_katalog1 + "/"))
			files1 = glob.glob(path_catalog1 + '*.avi')
			files2 = files + files1
			files_rez = []
			#print("files_rez", files_rez)
			favorit_pic = 0
			all_pic = 0
			for f1 in files2:
				f11 = re.findall(r'[_][u][_][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][_]', f1)
				f11 = f11[0][3:13]
				if int(f11) in range(vremy_nach1, vremy_okonch1):
					files_rez.append((f1))
					f15 = None
					f15 = re.findall(r'[a][r][c][h][i][v][e][_][v][i][d][e][o]', f1)
					# print(f15)
					all_pic = all_pic + 1
					if f15 == ['archive_video']:
						favorit_pic = int(favorit_pic) + 1
			# raznicha_pic = all_pic - favorit_pic
			# print(favorit_pic)
			# print("files_rez", files_rez)
			checklist_csv1_15_d.delete("1.0", "end")
			checkboxes_csv_m_v_d = {}
			imgs_csv_m_v_d = []
			checklist_csv1_15_d.configure(state='normal')
			checklist_csv1_15_d.delete("1.0", "end")
			# vid_play = (os.path.join(os.getcwd(), "data/photo/style/video_play_1.png"))
			# vid_play_img = ImageTk.PhotoImage(Image.open(vid_play).resize((20, 20)))
			kolich = 0
			len_pic = len(files_rez)
			# print("len_pic", len_pic)
			for f2 in files_rez:
				#print(f2)
				f2_list = f2.split(os.path.sep)[-1]
				#print(f2_list)
				var = tk.BooleanVar()
				# var1 = tk.BooleanVar()
				# img = ImageTk.PhotoImage(Image.open(f2).resize((icon_size_width, icon_size_height)))
				# imgs_csv_m_v.append(img)
				kolich = kolich + 1
				checklist_csv1_15_d.configure(state='normal')
				if len_pic == favorit_pic and kolich == 1:
					path01 = os.path.join(os.getcwd(), "data", "video", "archive_video", data_katalog1)
					open_button_c1 = tk.Button(checklist_csv1_15_d, text=" open ", cursor="hand2",
											   command=lambda path01_1=path01: openFolder(path01_1))
					checklist_csv1_15_d.window_create("end", window=open_button_c1)
					checklist_csv1_15_d.insert("end",
											 " Видео в архивной папке:",
											 'name1')
					checklist_csv1_15_d.tag_config('name1', foreground='red')
					checklist_csv1_15_d.insert("end", "\n")
				if len_pic > favorit_pic and kolich == 1:
					path02 = os.path.join(os.getcwd(), "data", "video", "records_video", data_katalog1)
					open_button_c2 = tk.Button(checklist_csv1_15_d, text=" open ", cursor="hand2",
											   command=lambda path02_1=path02: openFolder(path02_1))
					checklist_csv1_15_d.window_create("end", window=open_button_c2)
					checklist_csv1_15_d.insert("end",
											 " Видео в рабочей папке:",
											 'name')
					checklist_csv1_15_d.insert("end", "\n")

				if kolich == (all_pic - favorit_pic + 1) and favorit_pic != 0 and kolich != 1:
					checklist_csv1_15_d.insert("end", "\n")
					path03 = os.path.join(os.getcwd(), "data", "video", "archive_video", data_katalog1)
					open_button_c3 = tk.Button(checklist_csv1_15_d, text=" open ", cursor="hand2",
											   command=lambda path03_1=path03: openFolder(path03_1))
					checklist_csv1_15_d.window_create("end", window=open_button_c3)
					checklist_csv1_15_d.insert("end",
											 " Видео в архивной папке:", #Видео, сохраненное в папке: data\\video\\archive_video\\" + data_katalog1 + ":
											 'name1')
					checklist_csv1_15_d.tag_config('name1', foreground='red')
					checklist_csv1_15_d.insert("end", "\n")
				# checklist_csv.configure(state="normal")
				chk = tk.Checkbutton(checklist_csv1_15_d, text=f2_list, variable=var, cursor="arrow",
									 bg="grey77")  # image=img,
				# chk1 = tk.Label(checklist_csv1, text="открыть", bg="grey67", cursor="hand2")
				open_button = tk.Button(checklist_csv1_15_d, text=" play ", cursor="hand2",
										command=lambda f=os.path.join(f2): video_play(f))
				checklist_csv1_15_d.window_create("end", window=chk)
				checklist_csv1_15_d.insert("end", " ")
				checklist_csv1_15_d.window_create("end", window=open_button)
				checklist_csv1_15_d.insert("end", " ")

				checkboxes_csv_m_v_d[f2] = {'var': var, 'chk': chk}
			# chk1.bind("<Button-1>", lambda event: (on_click(), chk.toggle()))
			if kolich == 0:
				checklist_csv1_15_d.insert(tk.INSERT, "не найдены")

			checklist_csv1_15_d.insert("end", "\n\n")
			# header11f.configure(text="Найдено " + str(kolich) + " фото.")

			checklist_csv1_15_d.configure(state="disabled")

		def copy_select_video_m_def():
			global activeusergroupe
			if activeusergroupe == "admin" or activeusergroupe == "operator":
				selected_options = []
				data_katalog = None
				i = 0
				for option, data in checkboxes_csv_m_v_d.items():
					if data['var'].get():
						selected_options.append(option)
						i = i + 1
				if i > 0:
					f11 = re.findall(r'[V][_][d][_][0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9][_]',
									 selected_options[0])
					f11 = f11[0][4:14]
					# print("f11", f11)
					catalog_day_foto = "data\\video\\archive_video\\" + str(f11)
					if not os.path.exists(os.path.join(os.getcwd(), catalog_day_foto)):
						os.makedirs(catalog_day_foto)
					for f in selected_options:
						try:
							shutil.copy(f, catalog_day_foto)

						except Exception:
							text01_f = "Файл " + str(f) + " существует в каталоге" + str(
								catalog_day_foto) + ".\n\n"
					# print(text01_f)
					checklist_csv1_15_d.configure(state='normal')
					checklist_csv1_15_d.insert("end",
											 "\nВидео сохранено.")  # Для обновления повторно выделите строку в журнале событий.
					checklist_csv1_15_d.configure(state="disabled")
					video_object_info_m_day_def(f11)
					if i == 0:
						text01 = "Не выделено ни одного видео."
				# print("Не выделено ни одного изображения.")
			else:
				# print("Требуется авторизация в программе")
				res = "Для сохранения видео требуется авторизация в программе"

		# message.configure(text=res)

		def search_records():
			lookup_record = search_entry.get()
			lookup_record_kv = search_kv.get()
			lookup_record_name = search_name.get()
			lookup_record_fal = search_fal.get()
			lookup_record_kateg = search_kateg.get()
			# close the search box
			search.destroy()
			print(lookup_record, lookup_record_kv, lookup_record_name, lookup_record_fal, lookup_record_kateg)
			lookup_record = lookup_record.strip()
			lookup_record_kv = lookup_record_kv.strip()
			lookup_record_name = lookup_record_name.strip()
			lookup_record_fal = lookup_record_fal.strip()
			lookup_record_kateg = lookup_record_kateg.strip()
			lookup_record_kateg_bd = None
			print(lookup_record, lookup_record_kv, lookup_record_name, lookup_record_fal, lookup_record_kateg)
			if lookup_record_kateg == 'Жилец':
				lookup_record_kateg_bd = '1'
			if lookup_record_kateg == 'Гость':
				lookup_record_kateg_bd = '2'
			if lookup_record_kateg == 'Специальный':
				lookup_record_kateg_bd = '3'
			if lookup_record_kateg == 'Внимание!':
				lookup_record_kateg_bd = '4'
			global data_file_csv_for_search
			print(data_file_csv_for_search)
			filepath = "data\\protocols\\normal_terminal\\nt_d_" + data_file_csv_for_search + "_t_00.csv"
			# print(filepath)
			if filepath != "":
				for i in trv.get_children():
					trv.delete(i)
				# print(i)
				window_csv.update()
				# i = str(i) + str(1)
				try:
					df = pd.read_csv(filepath, encoding="windows-1251")  # create DataFrame
					l1 = list(df)  # List of column names as header
					del l1[8:19]
					r_set = df.to_numpy().tolist()  # create list of list using rows
					p = 0
					#print (r_set)
					print(lookup_record)
					for dt in r_set:
						#print(dt)
						ch = 0
						ch_0 = 0
						if lookup_record != None and lookup_record != "":
							ch_0 = ch_0 + 1
							if str(lookup_record) == str(dt[6]): #any(str(lookup_record) in str(value) for value in dt[6]):
								ch = ch + 1
						print(ch_0, ch)
						if lookup_record_kv != None and lookup_record_kv != "":
							ch_0 = ch_0 + 1
							if str(lookup_record_kv) == str(
									dt[5]):  # any(str(lookup_record) in str(value) for value in dt[6]):
								ch = ch + 1
						print(ch_0, ch)
						if lookup_record_kateg != None and lookup_record_kateg != "":
							ch_0 = ch_0 + 1
							if str(lookup_record_kateg) == str(
									dt[3]):  # any(str(lookup_record) in str(value) for value in dt[6]):
								ch = ch + 1
						print(ch_0, ch)
						if lookup_record_name != None and lookup_record_name != "":
							ch_0 = ch_0 + 1

							if any(str(lookup_record_name) in str(value) for value in dt[4]):  # any(str(lookup_record) in str(value) for value in dt[6]):
								ch = ch + 1
						print(ch_0, ch)
						if ch_0 != 0:
							if ch_0 == ch:
								p = p + 1
								#print(p)
								v = [r for r in dt]
								trv.insert("", 'end', iid="csv0" + str(p), values=v) #v
								trv.yview_scroll(number=1, what="units")
					if p != 0:
						child_id = trv.get_children()[-1]
						#print(child_id)
						trv.selection_set(child_id)
				except FileNotFoundError:
					print("Данные для заполнения лога событий отсутсвуют")





			# Create a database or connect to one that exists


		def lookup_records():
			global search_entry, search_name, search_fal, search_kv, search_kateg, search

			search = Toplevel(objekt_list)
			search.title("Поиск")
			search.geometry("300x450+600+200")
			# search.iconbitmap('c:/gui/codemy.ico')

			# search_lab = Label(search, text="Поиск по одному или нескольким значениям:")
			# search_lab.pack(padx=10, pady=10)

			search_frame2 = LabelFrame(search, text="Имя")
			search_frame2.pack(padx=10, pady=10)

			search_name = Entry(search_frame2, font=("Helvetica", 10))
			search_name.pack(pady=10, padx=10)

			search_frame3 = LabelFrame(search, text="Фамилия")
			search_frame3.pack(padx=10, pady=10)

			search_fal = Entry(search_frame3, font=("Helvetica", 10))
			search_fal.pack(pady=10, padx=10)

			search_frame = LabelFrame(search, text="Этаж")
			search_frame.pack(padx=10, pady=10)

			# Add entry box
			search_entry = Entry(search_frame, font=("Helvetica", 10))
			search_entry.pack(pady=10, padx=10)

			search_frame4 = LabelFrame(search, text="Номер квартиры")
			search_frame4.pack(padx=10, pady=10)

			search_kv = Entry(search_frame4, font=("Helvetica", 10))
			search_kv.pack(pady=10, padx=10)

			search_frame5 = LabelFrame(search, text="Категория")
			search_frame5.pack(padx=10, pady=10)

			search_kateg_var = ['', 'Жилец', 'Гость', 'Специальный', 'Внимание!']
			search_kateg = ttk.Combobox(search_frame5, values=search_kateg_var, state="readonly")
			# search_kateg = Entry(search_frame5, font=("Helvetica", 10))
			search_kateg.pack(pady=10, padx=10)

			# Add button
			search_button = Button(search, text="Искать", command=search_records)
			search_button.pack(padx=10, pady=10)
			search.grab_set()

		checklist_csv1_15_d = scrolledtext.ScrolledText(window_csv, undo=True, width=45, height=23, wrap='word')
		checklist_csv1_15_d['font'] = ('Helvetica', '10')
		checklist_csv1_15_d.place(x=470, y=515)
		checklist_csv1_15_d.configure(state='disabled', bg="lightgrey")

		save_button15 = ttk.Button(window_csv, text="Сохранить видео", style='my.TButton',
								   command=copy_select_video_m_def)
		save_button15.place(x=680, y=487)

		search_button_0 = ttk.Button(window_csv, text="   Поиск   ", style='my.TButton',
								   command=lookup_records)
		search_button_0.place(x=1265, y=5)

		search_button_1 = ttk.Button(window_csv, text="Очистить результаты поиска", style='my.TButton',
								   command=open_file_data_search)
		search_button_1.place(x=1380, y=5)

		window_csv.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		#window_csv.mainloop()
		window_csv.grab_set()
	else:
		#print("Требуется авторизация в программе")
		res = "Журнал событий: требуется авторизация в программе"
		message.configure(text=res)

def recognSetting1():
	global activeusergroupe
	if activeusergroupe == "admin":
		global timesec
		global model_algoritm_var
		global resolut_video_model_var
		global foto_save_kadr_var
		global v_record_dlit_var
		global v_record_codec_var
		global v_record_frames_var
		global objects_pic_var
		global oper_jurnal_laststroki_var
		global oper_jurnal_laststrokitime_var
		global facerecog_granici1_face_var
		global facerecog_granici2_face_var
		global facerecog_granici3_face_var
		model_algoritm_var1 = "model_algoritm"
		v_record_codec_var1 = 'video_save'
		object_pic_var1 = "objects_pic"
		enabled_sec_var1 = "enabled_sec"
		resolut_video_model_var1 = 'resolut_video_model'
		facerecog_granici1_face_var1 = 'facerecog_granici1_face'
		foto_save_kadr_var1 = 'foto_save'
		oper_jurnal_var1 = 'oper_jurnal'
		parametr_stream_var1 = 'stream'
		parametr_stream_q_var1 = 'stream_res_qua'
		connection = sqlite3.connect('data\setting.db')
		cursor = connection.cursor()
		cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr_stream_var1,))
		parametr_stream_var11 = cursor.fetchall()
		for row in parametr_stream_var11:
			host_acc = row[0]
			stream_port_var = row[1]
		cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr_stream_q_var1,))
		parametr_stream_q_var11 = cursor.fetchall()
		for row in parametr_stream_q_var11:
			stream_res_video_var = row[0]
			stream_qual_video_var = row[1]
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (model_algoritm_var1,))
		model_algoritm_var11 = cursor.fetchall()
		for row in model_algoritm_var11:
			model_algoritm_var = row[0]
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (foto_save_kadr_var1,))
		foto_save_kadr_var11 = cursor.fetchall()
		for row in foto_save_kadr_var11:
			foto_save_kadr_var = row[0]
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (resolut_video_model_var1,))
		resolut_video_model_var11 = cursor.fetchall()
		for row in resolut_video_model_var11:
			resolut_video_model_var = row[0]
		cursor.execute('SELECT set01, set02, set03 FROM setting WHERE parametr_name = ?',
					   (facerecog_granici1_face_var1,))
		facerecog_granici1_face_var11 = cursor.fetchall()
		for row in facerecog_granici1_face_var11:
			facerecog_granici1_face_var = row[0]
			facerecog_granici2_face_var = row[1]
			facerecog_granici3_face_var = row[2]
		cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (oper_jurnal_var1,))
		oper_jurnal_var11 = cursor.fetchall()
		for row in oper_jurnal_var11:
			oper_jurnal_laststroki_var = row[0]
			oper_jurnal_laststrokitime_var = row[1]
		cursor.execute('SELECT set01, set02, set03 FROM setting WHERE parametr_name = ?', (v_record_codec_var1,))
		v_record_codec_var11 = cursor.fetchall()
		for row in v_record_codec_var11:
			v_record_dlit_var = row[0]
			v_record_codec_var = row[1]
			v_record_frames_var = row[2]
		# print(v_record_codec_var)
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (object_pic_var1,))
		object_pic_var11 = cursor.fetchall()
		for row in object_pic_var11:
			object_pic_var = row[0]
		# print(object_pic_var)
		cursor.execute('SELECT set01 FROM setting WHERE parametr_name = ?', (enabled_sec_var1,))
		enabled_sec_var11 = cursor.fetchall()
		for row in enabled_sec_var11:
			enabled_sec_var = row[0]
		connection.close()

		setting_w = tk.Toplevel(window)
		setting_w.title('Параметры программы')
		setting_w.geometry("1250x500")
		setting_w.configure(bg='lightgrey')

		frame1_bg = "grey78"
		frame1 = tk.Frame(master=setting_w, width=100, height=100, bg=frame1_bg)
		frame1.grid(row=1, column=1, padx=5, pady=5, sticky="ns")
		label = tk.Label(master=frame1, text="            Трансляция видео            ", font=('Helvetica', 10, 'bold'),
						 fg="black")
		label.pack(padx=2, pady=10, fill=tk.BOTH, anchor=N)
		stream_list = ['интернет', 'локальная сеть']
		stream_list_label = Label(frame1, bg=frame1_bg, text='Режим трансляции видео:')
		stream_list_label.pack(padx=2, pady=5, anchor=NW)
		stream_list_combo = ttk.Combobox(frame1, values=stream_list, width=15, state="readonly")
		if host_acc == '0.0.0.0':
			stream_list_combo.set("интернет")
		if host_acc == '127.0.0.1':
			stream_list_combo.set("локальная сеть")
		stream_list_combo.pack(padx=2, pady=5, anchor=NW)
		# stream_list_combo.current(0)
		stream_port = ['8000', '8001', '8007', '5000', '5001']
		port_list_label = Label(frame1, bg=frame1_bg, justify=LEFT, text='Локальный порт \nтрансляции видео:')
		port_list_label.pack(padx=2, pady=5, anchor=NW)
		port_list_combo = ttk.Combobox(frame1, values=stream_port, width=10, state="readonly")
		port_list_combo.set(stream_port_var)
		port_list_combo.pack(padx=2, pady=5, anchor=NW)
		stream_res_video = ['400', '704', '800', '900']
		stream_res_video_label = Label(frame1, bg=frame1_bg, justify=LEFT,
									   text='Изменить ширину видео \nдо N (пикселей):')
		stream_res_video_label.pack(padx=2, pady=5, anchor=NW)
		stream_res_video_combo = ttk.Combobox(frame1, values=stream_res_video, width=10, state="readonly")
		stream_res_video_combo.set(stream_res_video_var)
		stream_res_video_combo.pack(padx=2, pady=5, anchor=NW)
		stream_qual_video = ['95', '90', '80', '70', '60']
		stream_qual_video_label = Label(frame1, bg=frame1_bg, justify=LEFT, text='Качество видео (%):')
		stream_qual_video_label.pack(padx=2, pady=5, anchor=NW)
		stream_qual_video_combo = ttk.Combobox(frame1, values=stream_qual_video, width=10, state="readonly")
		stream_qual_video_combo.set(stream_qual_video_var)
		stream_qual_video_combo.pack(padx=2, pady=5, anchor=NW)

		frame2_bg = "lightgrey"
		frame2 = tk.Frame(master=setting_w, width=100, height=100, bg=frame2_bg)
		frame2.grid(row=1, column=2, padx=5, pady=5, sticky="ns")
		label21 = tk.Label(master=frame2, text="        Распознование объектов        ", font=('Helvetica', 10, 'bold'),
						   fg="black")
		label21.pack(padx=2, pady=10, fill=tk.BOTH)
		resolut_video_model = ['100', '90', '85', '80', '75', '70', '65', '60', '55', '50', '45', '40', '30']
		resolut_video_model_label = Label(frame2, bg=frame2_bg, justify=LEFT,
										  text='Разрешение видео \nдля обработки моделью \n(% от начального):')
		resolut_video_model_label.pack(padx=2, pady=5, anchor=NW)
		resolut_video_model_combo = ttk.Combobox(frame2, values=resolut_video_model, width=10, state="readonly")
		resolut_video_model_combo.set(resolut_video_model_var)
		resolut_video_model_combo.pack(padx=2, pady=5, anchor=NW)
		facerecog_model = ['cnn', 'hog']
		facerecog_model_label = Label(frame2, bg=frame2_bg, text='Модель распознования лиц:')
		facerecog_model_label.pack(padx=2, pady=5, anchor=NW)
		facerecog_model_combo = ttk.Combobox(frame2, values=facerecog_model, width=10, state="readonly")
		facerecog_model_combo.set(model_algoritm_var)
		facerecog_model_combo.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici1_face = ['2', '3', '4', '5']
		facerecog_granici1_face_label = Label(frame2, bg=frame2_bg, justify=LEFT,
											  text='Динамика изменений \nПервого уровня проверки (%):')
		facerecog_granici1_face_label.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici1_face_combo = ttk.Combobox(frame2, values=facerecog_granici1_face, width=10, state="readonly")
		facerecog_granici1_face_combo.set(facerecog_granici1_face_var)
		facerecog_granici1_face_combo.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici2_face = ['3', '4', '5', '6', '7', '8', '9']
		facerecog_granici2_face_label = Label(frame2, bg=frame2_bg, justify=LEFT,
											  text='Динамика изменений \nВторого уровня проверки (%):')
		facerecog_granici2_face_label.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici2_face_combo = ttk.Combobox(frame2, values=facerecog_granici2_face, width=10, state="readonly")
		facerecog_granici2_face_combo.set(facerecog_granici2_face_var)
		facerecog_granici2_face_combo.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici3_face = ['4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']
		facerecog_granici3_face_label = Label(frame2, bg=frame2_bg, justify=LEFT,
											  text='Динамика изменений \nТретьего уровня проверки (%):')
		facerecog_granici3_face_label.pack(padx=2, pady=5, anchor=NW)
		facerecog_granici3_face_combo = ttk.Combobox(frame2, values=facerecog_granici3_face, width=10, state="readonly")
		facerecog_granici3_face_combo.set(facerecog_granici3_face_var)
		facerecog_granici3_face_combo.pack(padx=2, pady=5, anchor=NW)

		frame3_bg = "grey78"
		frame3 = tk.Frame(master=setting_w, width=100, height=100, bg=frame3_bg)
		frame3.grid(row=1, column=3, padx=5, pady=5, sticky="ns")
		label31 = tk.Label(master=frame3, text="Отображение событий в журнале", font=('Helvetica', 10, 'bold'),
						   fg="black")
		label31.pack(padx=2, pady=10, fill=tk.BOTH)
		label32 = tk.Label(master=frame3, justify=LEFT, text="Группировка событий \nв реальном времени:",
						   font=('Helvetica', 10), fg="black", bg=frame3_bg)
		label32.pack(padx=2, pady=10, fill=tk.BOTH)
		last_stroki = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
		last_stroki_label = Label(frame3, bg=frame3_bg, text='Анализ последних строк (кол-во):')
		last_stroki_label.pack(padx=2, pady=5, anchor=NW)
		last_stroki_combo = ttk.Combobox(frame3, values=last_stroki, width=10, state="readonly")
		last_stroki_combo.set(oper_jurnal_laststroki_var)
		last_stroki_combo.pack(padx=2, pady=5, anchor=NW)
		last_stroki_time = ['10', '20', '30', '45', '60', '90', '120']
		last_stroki_time_label = Label(frame3, bg=frame3_bg, text='Время ожидания объекта (секунд):')
		last_stroki_time_label.pack(padx=2, pady=5, anchor=NW)
		last_stroki_time_combo = ttk.Combobox(frame3, values=last_stroki_time, width=10, state="readonly")
		last_stroki_time_combo.set(oper_jurnal_laststrokitime_var)
		last_stroki_time_combo.pack(padx=2, pady=5, anchor=NW)

		frame4_bg = "lightgrey"
		frame4 = tk.Frame(master=setting_w, width=100, height=100, bg=frame4_bg)
		frame4.grid(row=1, column=4, padx=5, pady=5, sticky="ns")
		label41 = tk.Label(master=frame4, text="Фото и видео фиксация событий", font=('Helvetica', 10, 'bold'),
						   fg="black")
		label41.pack(padx=2, pady=10, fill=tk.BOTH)
		foto_save_kadr = ['1', '3', '5', '7', '10', '15', '20', '25', '30']
		foto_save_kadr_label = Label(frame4, bg=frame4_bg, justify=LEFT,
									 text='Частота сохранения фото \nдля известных объектов \n(каждый N кадр):')
		foto_save_kadr_label.pack(padx=2, pady=5, anchor=NW)
		foto_save_kadr_combo = ttk.Combobox(frame4, values=foto_save_kadr, width=10, state="readonly")
		foto_save_kadr_combo.set(foto_save_kadr_var)
		foto_save_kadr_combo.pack(padx=2, pady=5, anchor=NW)
		video_save_dlit_hand = ['10', '20', '30', '60', '90', '120', '180']
		video_save_dlit_hand_label = Label(frame4, bg=frame4_bg, justify=LEFT,
										   text='Продолжительность записи видео \nпри ручном старте (секунд):')
		video_save_dlit_hand_label.pack(padx=2, pady=5, anchor=NW)
		video_save_dlit_hand_combo = ttk.Combobox(frame4, values=video_save_dlit_hand, width=10, state="readonly")
		video_save_dlit_hand_combo.set(v_record_dlit_var)
		video_save_dlit_hand_combo.pack(padx=2, pady=5, anchor=NW)
		video_codek = ['XVID', 'MJPG']
		video_codek_label = Label(frame4, bg=frame4_bg, text='Видео кодек для сохранения видео:')
		video_codek_label.pack(padx=2, pady=5, anchor=NW)
		video_codek_combo = ttk.Combobox(frame4, values=video_codek, width=10, state="readonly")
		video_codek_combo.set(v_record_codec_var)
		video_codek_combo.pack(padx=2, pady=5, anchor=NW)
		video_frames = ['12', '15', '20', '25', '30']
		video_frames_label = Label(frame4, bg=frame4_bg, text='Частота кадров сохраняемого видео:')
		video_frames_label.pack(padx=2, pady=5, anchor=NW)
		video_frames_combo = ttk.Combobox(frame4, values=video_frames, width=10, state="readonly")
		video_frames_combo.set(v_record_frames_var)
		video_frames_combo.pack(padx=2, pady=5, anchor=NW)

		frame5_bg = "grey78"
		frame5 = tk.Frame(master=setting_w, width=100, height=100, bg=frame5_bg)
		frame5.grid(row=1, column=5, padx=5, pady=5, sticky="ns")
		label5 = tk.Label(master=frame5, text="      Элементы интерфейса      ", font=('Helvetica', 10, 'bold'),
						  fg="black")
		label5.pack(padx=2, pady=10, fill=tk.BOTH)

		enabled_sec = ['показывать секудны', 'не показывать секунд']
		enabled_sec_label = Label(frame5, bg=frame1_bg, justify=LEFT, text='Секунды (время) \nна главном экране:')
		enabled_sec_label.pack(padx=2, pady=5, anchor=NW)
		enabled_sec_combo = ttk.Combobox(frame5, values=enabled_sec, width=21, state="readonly")
		if enabled_sec_var == '1':
			enabled_sec_combo.set("показывать секудны")
		if enabled_sec_var != '1':
			enabled_sec_combo.set("не показывать секунд")
		enabled_sec_combo.pack(padx=2, pady=5, anchor=NW)

		enabled_circle = ['в кружке', 'квадрат']
		enabled_circle_label = Label(frame5, bg=frame1_bg, text='Стиль фото:')
		enabled_circle_label.pack(padx=2, pady=5, anchor=NW)
		enabled_circle_combo = ttk.Combobox(frame5, values=enabled_circle, width=15, state="readonly")
		if object_pic_var == 'circle':
			enabled_circle_combo.set("в кружке")
		else:
			enabled_circle_combo.set("квадрат")
		enabled_circle_combo.pack(padx=2, pady=5, anchor=NW)

		s = ttk.Style()
		s.configure('my.TButton', background='lightgrey', font=('Helvetica', 10))

		def akcept():
			global timesec
			global facerecog_granici1_face_var
			global facerecog_granici2_face_var
			global facerecog_granici3_face_var
			global model_algoritm_var
			global resolut_video_model_var
			global foto_save_kadr_var
			global v_record_dlit_var
			global v_record_codec_var
			global v_record_frames_var
			model_algoritm_var1 = "model_algoritm"
			v_record_codec_var1 = 'video_save'
			object_pic_var1 = "objects_pic"
			enabled_sec_var1 = "enabled_sec"
			resolut_video_model_var1 = 'resolut_video_model'
			facerecog_granici1_face_var1 = 'facerecog_granici1_face'
			foto_save_kadr_var1 = 'foto_save'
			oper_jurnal_var1 = 'oper_jurnal'
			parametr_stream_var1 = 'stream'
			parametr_stream_q_var1 = 'stream_res_qua'
			connection = sqlite3.connect(os.path.join(os.getcwd(), 'data/setting.db'))
			cursor = connection.cursor()
			slc = stream_list_combo.get()
			if slc == 'интернет':
				slc_bd = '0.0.0.0'
			if slc == 'локальная сеть':
				slc_bd = '127.0.0.1'
			plc = port_list_combo.get()
			srvc = stream_res_video_combo.get()
			sqvc = stream_qual_video_combo.get()
			rvmc = resolut_video_model_combo.get()
			resolut_video_model_var = rvmc
			fmc = facerecog_model_combo.get()
			model_algoritm_var = fmc
			fgfc1 = facerecog_granici1_face_combo.get()
			facerecog_granici1_face_var = fgfc1
			fgfc2 = facerecog_granici2_face_combo.get()
			facerecog_granici2_face_var = fgfc2
			fgfc3 = facerecog_granici3_face_combo.get()
			facerecog_granici3_face_var = fgfc3
			lsc = last_stroki_combo.get()
			lstc = last_stroki_time_combo.get()
			fskc = foto_save_kadr_combo.get()
			foto_save_kadr_var = fskc
			vsdhc = video_save_dlit_hand_combo.get()
			v_record_dlit_var = vsdhc
			vcc = video_codek_combo.get()
			v_record_codec_var = vcc
			vfc = video_frames_combo.get()
			v_record_frames_var = vfc
			es = enabled_sec_combo.get()
			if es == "показывать секудны":
				es_bd = '1'
				timesec = "1"
				timesec_d()
			else:
				es_bd = '0'
				timesec = "0"
				timesec_d()
			ec = enabled_circle_combo.get()
			if ec == "в кружке":
				ec_bd = 'circle'
			else:
				ec_bd = 'other'
			cursor.execute(
				'UPDATE setting SET set01 = ? WHERE parametr_name = ?',
				(es_bd, enabled_sec_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ? WHERE parametr_name = ?',
				(ec_bd, object_pic_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ?, set02 = ?, set03 = ? WHERE parametr_name = ?',
				(vsdhc, vcc, vfc, v_record_codec_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ? WHERE parametr_name = ?',
				(fskc, foto_save_kadr_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ?, set02 = ? WHERE parametr_name = ?',
				(lsc, lstc, oper_jurnal_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ?, set02 = ? WHERE parametr_name = ?',
				(slc_bd, plc, parametr_stream_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ?, set02 = ? WHERE parametr_name = ?',
				(srvc, sqvc, parametr_stream_q_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ? WHERE parametr_name = ?',
				(fmc, model_algoritm_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ? WHERE parametr_name = ?',
				(rvmc, resolut_video_model_var1))
			cursor.execute(
				'UPDATE setting SET set01 = ?, set02 = ?, set03 = ? WHERE parametr_name = ?',
				(fgfc1, fgfc2, fgfc3, facerecog_granici1_face_var1))
			connection.commit()
			connection.close()
			reload_stream_setting()
			message.configure(text="Настройки обновлены", fg="black")
			setting_w.destroy()

		akcept_button = ttk.Button(setting_w, text='Сохранить настройки и закрыть', style='my.TButton', command=akcept)
		akcept_button.grid(row=2, column=4, padx=5, pady=15, sticky="ns")

		cancel_button = ttk.Button(setting_w, text='Выход', style='my.TButton', command=setting_w.destroy)
		cancel_button.grid(row=2, column=5, padx=5, pady=15, sticky="ns")
		setting_w.iconbitmap(os.path.join(os.getcwd(), 'data/dozor.ico'))
		setting_w.grab_set()
	else:
		print("Требуется авторизация в программе")
		res = "Авторизуйтесь для просмотра / редактирования картотеки"
		message.configure(text=res)

def exitmainprogramm():
	#window01 = Tk()
	window01 = tk.Toplevel(window)
	window01.attributes("-topmost", True)
	window01.title("Выход из программы")
	window01.geometry('465x100+600+300')
	window01.configure(bg="lightgrey")
	#window01.attributes('-alpha', 0.95)
	#window01.wm_attributes("-transparentcolor", "lightgrey")
	window01.resizable(False, False)
	s = ttk.Style()
	s.configure('my.TButton', font=('Helvetica', 10), background='lightgrey')
	# window01.grid_rowconfigure(index=4, weight=1)
	# window01.grid_columnconfigure(index=4, weight=1)
	textUserMeny0 = Label(window01, text=" ", bg="lightgrey")
	textUserMeny0.grid(column=0, row=0, sticky=W + E)
	textUserMeny1 = Label(window01, text="Выйти из программы?", font=("Helvetica", 13), bg="lightgrey")
	textUserMeny1.grid(column=0, row=2, padx=20, sticky=W + E)
	# textUserMeny = Label(window01, text=" ")
	# textUserMeny.grid(column=0, row=3, sticky=W+E)
	btn1 = ttk.Button(window01, text="Выход", style='my.TButton', command=quitall)  # quitall
	btn1.grid(column=1, row=4, padx=5, sticky='w')
	btn = ttk.Button(window01, text="Отмена", style='my.TButton', command=window01.destroy)
	btn.grid(column=2, row=4, padx=5, sticky='w')
	window01.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
	window01.grab_set()

def quitall():
	print("полный выход")
	global window

	RecordStopVideo()
	WebStreameStop()
	time.sleep(2)
	window.destroy()
	exit()


canvas_main_width = 704
canvas_main_height = 603
canvas = tk.Canvas(window, bg="lightgrey", width=canvas_main_width, height=canvas_main_height) # width=704, height=576)
label = Label(image=imgtk)
canvas.place(x=1105, y=30)

# Фотограции объекта
def katalog_foto_object():
	global activeusergroupe
	if activeusergroupe == "admin" or activeusergroupe == "operator":

		global catalog_foto_ob
		global win_katalog
		data_view01 = ""
		global checkboxes_cat
		imgs = []
		global checklist_cat
		obect_view_db01 = ""
		set1_razmer_icon = []
		global razmer_icon_temp
		razmer_icon_temp = None
		global fileList2
		i = 0
		ii = 0
		object_view_name = ""
		global icon_size_width
		global icon_size_height
		icon_size_width = 120
		icon_size_height = 120
		obect_view01 = catalog_foto_ob

		mypath = (os.getcwd() + '\\data\\dataset' + '\\' + obect_view01 + '\\')
		if not os.path.isdir(mypath):
			os.mkdir(mypath)


		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()
		cursor.execute('SELECT set01 FROM logins WHERE logins = ?', (activeuserlogin,))
		set1_razmer_icon = cursor.fetchall()
		if set1_razmer_icon != []:
			set1_razmer_icon = set1_razmer_icon[0][0]
		else:
			set1_razmer_icon = "Обычные значки"
		#print("Прочитанное значение размера: " + str(set1_razmer_icon))
		connection.close()
		razmer_icon_temp = set1_razmer_icon
		#print(razmer_icon_temp)

		def my_upd_l12_ii(*args):
			object_view_name = object_view.get()
			if object_view_name != "":
				connection = sqlite3.connect('data/objects.db')
				cursor = connection.cursor()
				cursor.execute(
					'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
					(object_view_name,))
				first_name_db = cursor.fetchall()
				# print("first_name_db", first_name_db)
				if first_name_db != []:
					for row in first_name_db:
						pass
						#print(str(row))
					connection.close()
					if row[2] == '1':
						categoriy_s = 'Жилец'
					if row[2] == '2':
						categoriy_s = 'Гость'
					if row[2] == '3':
						categoriy_s = 'Специальный'
					if row[2] == '4':
						categoriy_s = 'Внимание!'

					text_lab = (categoriy_s + ", " + str(row[1]) + " " + str(row[0]) + ", кв. " + str(
						row[3]) + ", этаж " + str(
						row[4]) + " " + str(row[10]))
					path1 = (os.getcwd() + "\\data\\photo\\objects\\" + object_view_name + ".jpg")
					bb = os.path.isfile(path1)
					if bb:
						img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					else:
						path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
						img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					panel.configure(image=img_text_lab)
					panel.image = img_text_lab
					l12.config(text=text_lab)
				# дописать вывод фотографии объекта
				else:
					object_view_name_dubli = object_view_name
					l12.config(text="Объект не найден в БД")
					result22 = askokcancel(title="Вопрос",
										   message="Объект не найден в базе данных.\n\nПереместить каталог: " + object_view_name_dubli + " в архив?")
					if result22:
						# print(object_view_name_dubli)
						path_source = os.getcwd() + "\\data\\dataset\\" + object_view_name_dubli + "\\"
						path_dest = (os.getcwd() + "\\data\\data_archives\\dataset_archives\\")
						try:
							shutil.move(path_source, path_dest)
							l12.config(text="Каталог удален. Обновление списка каталогов при следующей загрузке меню.")
						except Exception:
							l12.config(text="Каталог не найден. Обновление списка каталогов при следующей загрузке меню.")
					# дописать вопрос об удалении не найденного каталога
			else:
				l12.config(text="Выберите объект для просмотра.")
			obnovit_view()

		win_katalog = tk.Toplevel()
		#root = tk.Tk()
		win_katalog.title("Фотографии объекта")
		win_katalog.geometry("1600x900+100+50")
		win_katalog.configure(bg="lightgrey")
		win_katalog.protocol("WM_DELETE_WINDOW", on_closing_model_status_4)

		s = ttk.Style()
		s.configure('my.TButton', background='lightgrey', font=('Helvetica', 10))
		s.configure("My.TLabel",  # имя стиля
					font="helvetica 10",  # шрифт
					foreground="#000000",  # цвет текста
					padding=0,  # отступы
					background="lightgrey")  # фоновый цвет

		l12_tehn: Label = ttk.Label(win_katalog, text="")  # Create a label
		l12_tehn.pack(anchor=tk.NW)
		l123_tehn: Label = ttk.Label(win_katalog, text="")  # Create a label
		l123_tehn.pack(anchor=tk.NW)
		l124_tehn: Label = ttk.Label(win_katalog, text="")  # Create a label
		l124_tehn.pack(anchor=tk.NW)
		l125_tehn: Label = ttk.Label(win_katalog, text="")  # Create a label
		l125_tehn.pack(anchor=tk.NW)

		razmer_view_list = ['Мелкие значки', 'Обычные значки', 'Крупные значки', 'Огромные значки']
		razmer_view = ttk.Combobox(win_katalog, values=razmer_view_list, width=30, state="readonly")
		# razmer_view.pack(anchor=tk.NW, padx=5, pady=2)
		razmer_view.place(x=170, y=10)
		# print("размер иконки условие: " + str(set1_razmer_icon))
		if set1_razmer_icon == "Мелкие значки":
			razmer_view.current(0)
		# print("размер иконки 0")
		if set1_razmer_icon == "Обычные значки" or set1_razmer_icon == None:
			razmer_view.current(1)
		# print("размер иконки 1")
		if set1_razmer_icon == "Крупные значки":
			razmer_view.current(2)
		# print("размер иконки 2")
		if set1_razmer_icon == "Огромные значки":
			razmer_view.current(3)
		# print("размер иконки 3")

		object_list = []
		directory02 = (os.getcwd() + '\\data\\dataset\\')
		dir_list_pre = len(list(os.walk(directory02)))
		#print("dir_list_pre", dir_list_pre)
		# print(dir_list)
		if dir_list_pre > 1:
			object_list = next(os.walk(directory02))[1]
			object_list.sort(reverse=True)
		# print("список директорий объетов " + str(object_list))
		else:
			object_list = ['']
		# sel007 = tk.StringVar()  # string variable
		object_list_list = object_list
		object_view = ttk.Combobox(win_katalog, values=object_list_list, width=30, state="readonly")  # textvariable=sel007,
		# object_view.pack(anchor=tk.NW, padx=5, pady=2)
		object_view.place(x=170, y=40)
		object_view.set(obect_view01)
		# object_view.current(0) # сделать условие, при 0 списке выходит ошибка!
		#print(object_list_list)
		object_view.bind("<<ComboboxSelected>>", my_upd_l12_ii)
		# sel007.trace("w", my_upd_l12_ii)

		l12_i: Label = ttk.Label(win_katalog, text="Параметры:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12_i.place(x=83, y=10)

		l12_ii: Label = ttk.Label(win_katalog, text="Объект:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12_ii.place(x=107, y=40)

		path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
		img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
		panel = Label(win_katalog, image=img_text_lab, bg="lightgrey")
		panel.image = img_text_lab
		panel.place(x=0, y=0)

		l12: Label = ttk.Label(win_katalog, text="Инфо:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12.place(x=390, y=40)

		def obnovit_view():
			#global obect_view01
			#global data_view01
			global icon_size_width
			global icon_size_height
			#global obect_view_db01
			global razmer_icon_temp
			obect_view01 = object_view.get()
			# obect_view_db01 = obect_view_db.get()
			# print("obect_view_db01: " + obect_view_db01)

			razmer_view01 = razmer_view.get()
			#print("razmer_view01: " + razmer_view01)
			if razmer_view01 == 'Мелкие значки':
				icon_size_width = 70
				icon_size_height = 70
			if razmer_view01 == 'Обычные значки':
				icon_size_width = 120
				icon_size_height = 120
			if razmer_view01 == 'Крупные значки':
				icon_size_width = 180
				icon_size_height = 180
			if razmer_view01 == 'Огромные значки':
				icon_size_width = 200
				icon_size_height = 200
			# Запись размера иконок в настройки для пользователя
			#print(str(razmer_view01))
			if razmer_icon_temp != razmer_view01:
				razmer_icon_temp = razmer_view01
				connection = sqlite3.connect('data/avtorizachiy.db')
				cursor = connection.cursor()
				cursor.execute('UPDATE logins SET set01=? WHERE logins = ?', (razmer_view01, activeuserlogin))
				#print("Сохраняем изменения и закрываем соединение")
				connection.commit()
				connection.close()
				#print("Записаны в БД новые значения размера иконки")
			else:
				pass
				print("Не трубуется запись в БД новых значений размера иконки")

			# data_view01 = data_view.get()
			# print(obect_view01 + ", " + data_view01 + ", " + obect_view_db01)
			checklist_cat.configure(state="normal")
			checklist_cat.delete("1.0", END)
			list_file()

		def akcept_wind():
			def quitall_akcept_wind():
				windowakcept.destroy()

			selected_options = []
			global i
			i = 0
			for option, data in checkboxes_cat.items():
				if data['var'].get():
					selected_options.append(option)
					i = i + 1
			#print("len selected_options: " + str(i) + ": " + str(len(selected_options)))
			#print("selected_options: ", selected_options)

			def akcept_wind_action():
				global i
				if i > 0:
					for f in selected_options:
						os.remove(f)
					if i == 0:
						text01 = "Не выделено ни одного изображения."
						#print("Не выделено ни одного изображения.")
					if i != 0:
						text01 = 'Изображения удалены. Для возврата закройте окно'
						l02.configure(text=text01)
						checklist1.configure(state="normal")
						checklist1.delete("1.0", END)
						checklist1.configure(state="disabled")
						checklist_cat.configure(state="normal")
						checklist_cat.delete("1.0", END)
						obnovit_view()
						#print("Изображения удалены.")
						del selected_options[:]
						i = 0
						delete_button_akc.configure(text="Закрыть окно", command=quitall_akcept_wind)

				else:
					text01 = "Не выделено ни одного изображения. Для возврата закройте окно."
					l02.configure(text=text01)

			windowakcept = Toplevel(win_katalog)
			windowakcept.title('Удалить фото?')
			windowakcept.geometry('1200x800+300+100')
			text01 = ""
			if i == 0:
				text01 = "Не выделено ни одного изображения. Для возврата закройте окно."
			if i != 0:
				text01 = "Кол-во: " + str(i) + ". Проверьте и подтвердите удаление."

			l02: Label = ttk.Label(windowakcept, text=text01, style="My.TLabel")  # Create a label
			l02.pack()
			if i == 0:
				delete_button_akc = ttk.Button(windowakcept, text="Закрыть окно", style='my.TButton',
											   command=quitall_akcept_wind)
			if i != 0:
				delete_button_akc = ttk.Button(windowakcept, text="Подтвердить удаление", style='my.TButton',
											   command=akcept_wind_action)
			delete_button_akc.pack(padx=30, pady=5)

			scrollbar1 = tk.Scrollbar(windowakcept, width=30)
			scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
			checklist1 = tk.Text(windowakcept, width=800, height=800, font=("Helvetica", 5), bg='gray72', fg='#000',
								 yscrollcommand=scrollbar1.set)
			#print("scrollbar: " + str(scrollbar1))
			checklist1.pack()
			kolich = 0
			checklist1.configure(state="normal")
			for option1 in selected_options:
				var = tk.BooleanVar()
				img = ImageTk.PhotoImage(Image.open(option1).resize((icon_size_width, icon_size_height)))

				#print(option1)
				imgs.append(img)
				kolich = kolich + 1

				checklist1.image_create('end', image=img)
				checklist1.insert("end", "   ")

			checklist1.configure(state="disabled")
			windowakcept.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
			windowakcept.grab_set()

		obnovit_view_button = ttk.Button(win_katalog, text="Обновить список", style='my.TButton', command=obnovit_view)
		# obnovit_view_button.pack(anchor=tk.NW, padx=200, pady=2)
		obnovit_view_button.place(x=390, y=10)

		# finalize_button = ttk.Button(root, text="Количество выделенных изобр.", style='my.TButton', command=lambda: print(get_selected_options()))
		# finalize_button.pack(anchor=tk.SE, padx=30, pady=5)
		delete_button = ttk.Button(win_katalog, text="Удалить отмеченые фото", style='my.TButton', command=akcept_wind)
		delete_button.pack(anchor=tk.SE, padx=30, pady=5)
		delete_button.place(x=530, y=10)

		obect_view01 = object_view.get()
		# obect_view_db01 = obect_view_db.get()

		if razmer_icon_temp == 'Мелкие значки':
			icon_size_width = 70
			icon_size_height = 70
		if razmer_icon_temp == 'Обычные значки':
			icon_size_width = 120
			icon_size_height = 120
		if razmer_icon_temp == 'Крупные значки':
			icon_size_width = 180
			icon_size_height = 180
		if razmer_icon_temp == 'Огромные значки':
			icon_size_width = 200
			icon_size_height = 200

		scrollbar = tk.Scrollbar(win_katalog, width=30)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
		checklist_cat = tk.Text(win_katalog, width=800, height=800, font=("Helvetica", 5), bg='gray72', fg='#000',
							yscrollcommand=scrollbar.set)
		#print("scrollbar: " + str(scrollbar))
		checklist_cat.pack()

		def list_file():
			#global obect_view01
			#global data_view01
			global checkboxes_cat
			#global fileList2
			global imgs
			global checklist_cat
			global icon_size_width
			global icon_size_height
			#global obect_view_db01
			obect_view01 = object_view.get()

			mypath = (os.getcwd() + '\\data\\dataset' + '\\' + obect_view01 + '\\')
			mypath_prov = os.path.isdir(mypath)
			# lblText = StringVar()
			# lbl = Label(root, textvariable=lblText)
			if obect_view01 != "Unknown":
				if mypath_prov == True:
					fileList = [f for f in listdir(mypath) if isfile(join(mypath, f))]
					fileList.sort()
				else:
					fileList = []
			else:
				fileList = []
			#print(fileList)

			# name_obekt = obect_view01
			# data_obekt = data_view01

			fileList2: list[str] = glob.glob(mypath + '/' + '*.jpg')
			#print("fileList2: " + str(fileList2))

			# F_d_2024-07-27_t_14-15_n_10002_1_Vasily_u_1719741457.94386_c_95

			# checkboxes_cat = {}
			#print("def checkboxes: " + str(checkboxes_cat))

			imgs = []
			#print("def imgs: " + str(imgs))
			checklist_cat.delete("1.0", "end")
			checkboxes_cat = {}
			kolich = 0
			for option in fileList2:
				var = tk.BooleanVar()
				img = ImageTk.PhotoImage(Image.open(option).resize((icon_size_width, icon_size_height)))
				imgs.append(img)
				kolich = kolich + 1
				chk = tk.Checkbutton(checklist_cat, text=option, image=img, variable=var, cursor="arrow", bg="grey67")
				checklist_cat.window_create("end", window=chk)
				checklist_cat.insert("end", "  ")
				checkboxes_cat[option] = {'var': var, 'chk': chk}
			#print("def1 checkboxes: " + str(checkboxes_cat))
			#print("def imgs: " + str(imgs))
			#print(kolich)
			checklist_cat.config(yscrollcommand=scrollbar.set)
			scrollbar.config(command=checklist_cat.yview)
			checklist_cat.configure(state="disabled")
			#print("scrollbar: " + str(scrollbar))
			#print("checklist: " + str(checklist_cat))

		list_file()

		object_view_name = object_view.get()
		if object_view_name != "":
			connection = sqlite3.connect('data/objects.db')
			cursor = connection.cursor()
			cursor.execute(
				'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
				(object_view_name,))
			first_name_db = cursor.fetchall()
			# print("first_name_db", first_name_db)
			if first_name_db != []:
				for row in first_name_db:
					pass
					#print(str(row))
				connection.close()
				if row[2] == '1':
					categoriy_s = 'Жилец'
				if row[2] == '2':
					categoriy_s = 'Гость'
				if row[2] == '3':
					categoriy_s = 'Специальный'
				if row[2] == '4':
					categoriy_s = 'Внимание!'

				text_lab = (categoriy_s + ", " + str(row[1]) + " " + str(row[0]) + ", кв. " + str(row[3]) + ", этаж " + str(
					row[4]) + " " + str(row[10]))
				path1 = (os.getcwd() + "\\data\\photo\\objects\\" + object_view_name + ".jpg")
				bb = os.path.isfile(path1)
				if bb:
					img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
				else:
					path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
					img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
				img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
				panel.configure(image=img_text_lab)
				panel.image = img_text_lab
				l12.config(text=text_lab)
			# дописать вывод фотографии объекта
			else:
				object_view_name_dubli = object_view_name
				l12.config(text="Объект не найден в БД")
				result22 = askokcancel(title="Вопрос",
									   message="Объект не найден в базе данных.\n\nПереместить каталог: " + object_view_name_dubli + " в архив?")
				if result22:
					# print(object_view_name_dubli)
					path_source = os.getcwd() + "\\data\\dataset\\" + object_view_name_dubli + "\\"
					path_dest = (os.getcwd() + "\\data\\data_archives\\dataset_archives\\")
					try:
						shutil.move(path_source, path_dest)
						l12.config(text="Каталог удален. Обновление списка каталогов при следующей загрузке меню.")
					except Exception:
						l12.config(text="Каталог не найден. Обновление списка каталогов при следующей загрузке меню.")
				# дописать вопрос об удалении не найденного каталога
		else:
			l12.config(text="Выберите объект для просмотра.")

		win_katalog.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		#root.mainloop()
		win_katalog.grab_set()
	else:
		res = str("Фото объектов модели: необходима авторизация")
		message.configure(text=res)

#Сохраненные фото
def save_foto_listr():
	global activeusergroupe
	global data_view
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		global activeuserlogin
		global checklist
		global checkboxes
		global obect_view01
		# activeuserlogin = "3" # временный параметр для теста, удалить
		obect_view01 = ""
		data_view01 = ""
		checkboxes = {}
		# fileList2 = []
		imgs = []
		checklist = ""
		obect_view_db01 = ""
		set1_razmer_icon = []
		razmer_icon_temp = None
		i = 0
		ii = 0
		object_view_name = ""
		icon_size_width = 120
		icon_size_height = 120

		unix_time = int(time.time())
		date_time = datetime.datetime.fromtimestamp(unix_time)
		date_timef = date_time.strftime('%Y-%m-%d')
		path_abs = 'data\\faces\\'
		walk = list(os.walk(path_abs))
		#print(walk)
		#print(walk[1:])
		walk = walk[1:]
		#print(walk)
		for path, _, _ in walk[::-1]:
			if len(os.listdir(path)) == 0:
				if (path[-10:]) != date_timef:
					#print(path[-10:])
					# os.rmdir(path)
					shutil.rmtree(path)

		connection = sqlite3.connect('data/avtorizachiy.db')
		cursor = connection.cursor()
		cursor.execute('SELECT set01 FROM logins WHERE logins = ?', (activeuserlogin,))
		set1_razmer_icon = cursor.fetchall()
		set1_razmer_icon = set1_razmer_icon[0][0]
		#print("Прочитанное значение размера: " + str(set1_razmer_icon))
		connection.close()
		razmer_icon_temp = set1_razmer_icon
		#print(razmer_icon_temp)

		def my_upd_l12_ii(*args):
			object_view_name = object_view.get()
			if object_view_name != "":
				connection = sqlite3.connect('data/objects.db')
				cursor = connection.cursor()
				cursor.execute(
					'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
					(object_view_name,))
				first_name_db = cursor.fetchall()
				# print("first_name_db", first_name_db)
				if first_name_db != []:
					for row in first_name_db:
						pass
						#print(str(row))
					connection.close()
					if row[2] == '1':
						categoriy_s = 'Жилец'
					if row[2] == '2':
						categoriy_s = 'Гость'
					if row[2] == '3':
						categoriy_s = 'Специальный'
					if row[2] == '4':
						categoriy_s = 'Внимание!'

					text_lab = (categoriy_s + ", " + str(row[1]) + " " + str(row[0]) + ", кв. " + str(
						row[3]) + ", этаж " + str(
						row[4]) + " " + str(row[10]))
					path1 = (os.getcwd() + "\\data\\photo\\objects\\" + object_view_name + ".jpg")
					bb = os.path.isfile(path1)
					if bb:
						img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					else:
						path1 = (os.getcwd() + "\\data\\photo\\objects\\no_avatar_grey.jpg")
						img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
					panel.configure(image=img_text_lab)
					panel.image = img_text_lab
					l12.config(text=text_lab)
				# дописать вывод фотографии объекта
				else:
					object_view_name_dubli = object_view_name
					l12.config(text="Объект загрузки не найден в БД")
					result22 = askokcancel(title="Вопрос",
										   message="Объект загрузки не найден в базе данных.\n\nПереместить каталог: " + object_view_name_dubli + " в архив?")
					if result22:
						# print(object_view_name_dubli)
						path_source = os.getcwd() + "\\data\\dataset\\" + object_view_name_dubli + "\\"
						path_dest = (os.getcwd() + "\\data\\data_archives\\dataset_archives\\")
						try:
							shutil.move(path_source, path_dest)
							l12.config(text="Каталог удален. Обновление списка каталогов при следующей загрузке меню.")
						except Exception:
							l12.config(
								text="Каталог не найден. Обновление списка каталогов при следующей загрузке меню.")
					# дописать вопрос об удалении не найденного каталога
			else:
				l12.config(text="Выберите объект загрузки.")

		# root = tk.Tk()
		global win_katalog02
		win_katalog02 = tk.Toplevel()
		win_katalog02.title("Фото событий (на дату)")
		win_katalog02.configure(bg="lightgrey")
		win_katalog02.geometry("1600x900+100+50")
		win_katalog02.protocol("WM_DELETE_WINDOW", on_closing_model_status_2)

		s = ttk.Style()
		s.configure('my.TButton', background='lightgrey', font=('Helvetica', 10))
		s.configure("My.TLabel",  # имя стиля
					font="helvetica 10",  # шрифт
					foreground="#000000",  # цвет текста
					padding=0,  # отступы
					background="lightgrey")  # фоновый цвет

		l12_tehn: Label = ttk.Label(win_katalog02, text="")  # Create a label
		l12_tehn.pack(anchor=tk.NW)
		l123_tehn: Label = ttk.Label(win_katalog02, text="")  # Create a label
		l123_tehn.pack(anchor=tk.NW)
		l124_tehn: Label = ttk.Label(win_katalog02, text="")  # Create a label
		l124_tehn.pack(anchor=tk.NW)
		l125_tehn: Label = ttk.Label(win_katalog02, text="")  # Create a label
		l125_tehn.pack(anchor=tk.NW)


		razmer_view_list = ['Мелкие значки', 'Обычные значки', 'Крупные значки', 'Огромные значки']
		razmer_view = ttk.Combobox(win_katalog02, values=razmer_view_list, width=30, state="readonly")
		# razmer_view.pack(anchor=tk.NW, padx=5, pady=2)
		razmer_view.place(x=170, y=10)
		#print("размер иконки условие: " + str(set1_razmer_icon))
		if set1_razmer_icon == "Мелкие значки":
			razmer_view.current(0)
			#print("размер иконки 0")
		if set1_razmer_icon == "Обычные значки" or set1_razmer_icon == None:
			razmer_view.current(1)
			#print("размер иконки 1")
		if set1_razmer_icon == "Крупные значки":
			razmer_view.current(2)
			#print("размер иконки 2")
		if set1_razmer_icon == "Огромные значки":
			razmer_view.current(3)
			#print("размер иконки 3")

		object_list = []
		directory02 = (os.path.join(os.getcwd(),'data/dataset/'))
		dir_list_pre = len(list(os.walk(directory02)))
		#print("dir_list_pre", dir_list_pre)
		# print(dir_list)
		if dir_list_pre > 1:
			object_list = next(os.walk(directory02))[1]
			object_list.sort(reverse=True)
		# print("список директорий объетов " + str(object_list))
		else:
			object_list = ['']
		# sel007 = tk.StringVar()  # string variable
		object_list_list = object_list
		object_view = ttk.Combobox(win_katalog02, values=object_list_list, width=30,
								   state="readonly")  # textvariable=sel007,
		# object_view.pack(anchor=tk.NW, padx=5, pady=2)
		object_view.place(x=170, y=40)
		object_view.set("")
		#object_view.current(0)  # сделать условие, при 0 списке выходит ошибка!
		#print(object_list_list)
		object_view.bind("<<ComboboxSelected>>", my_upd_l12_ii)
		# sel007.trace("w", my_upd_l12_ii)

		l12_i: Label = ttk.Label(win_katalog02, text="Параметры:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12_i.place(x=83, y=10)

		l12_ii: Label = ttk.Label(win_katalog02, text="Объект:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12_ii.place(x=107, y=40)

		path1 = (os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg"))
		img_text_lab07 = ImageTk.PhotoImage(Image.open(path1).resize((74, 74)))
		panel = Label(win_katalog02, image=img_text_lab07, bg="lightgrey")
		panel.image = img_text_lab07
		panel.place(x=1, y=1)

		l12: Label = ttk.Label(win_katalog02, text="Инфо:", style="My.TLabel")  # Create a label
		# l12.pack(anchor=tk.NW)
		l12.place(x=390, y=40)

		def obnovit_view(*args):
			global obect_view01
			global data_view01
			global icon_size_width
			global icon_size_height
			global obect_view_db01
			global razmer_icon_temp
			obect_view01 = obect_view.get()
			obect_view_db01 = obect_view_db.get()
			#print("obect_view_db01: " + obect_view_db01)
			if obect_view01 == 'Все зафиксированные':
				obect_view01 = '*'
				if obect_view_db01 == 'Все записи':
					obect_view01 = '*'
				if obect_view_db01 != 'Все записи':
					obect_view01 = obect_view_db01

			if obect_view01 == 'Все жильцы':
				obect_view01 = '*_1_'
				if obect_view_db01 == 'Все записи':
					obect_view01 = '*_1_'
				if obect_view_db01 != 'Все записи':
					obect_view01 = obect_view_db01 + '1_'

			if obect_view01 == 'Все гости':
				obect_view01 = '*_2_'
				if obect_view_db01 == 'Все записи':
					obect_view01 = '*_2_'
				if obect_view_db01 != 'Все записи':
					obect_view01 = obect_view_db01 + '2_'

			if obect_view01 == 'Только неизвестные':
				obect_view01 = '_n_Unknown'
			razmer_view01 = razmer_view.get()
			#print("razmer_view01: " + razmer_view01)
			if razmer_view01 == 'Мелкие значки':
				icon_size_width = 70
				icon_size_height = 70
			if razmer_view01 == 'Обычные значки':
				icon_size_width = 120
				icon_size_height = 120
			if razmer_view01 == 'Крупные значки':
				icon_size_width = 180
				icon_size_height = 180
			if razmer_view01 == 'Огромные значки':
				icon_size_width = 200
				icon_size_height = 200
			# Запись размера иконок в настройки для пользователя
			#print(str(razmer_view01))
			if razmer_icon_temp != razmer_view01:
				razmer_icon_temp = razmer_view01
				connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
				cursor = connection.cursor()
				cursor.execute('UPDATE logins SET set01=? WHERE logins = ?', (razmer_view01, activeuserlogin))
				#print("Сохраняем изменения и закрываем соединение")
				connection.commit()
				connection.close()
				#print("Записаны в БД новые значения размера иконки")
			else:
				print("Не трубуется запись в БД новых значений размера иконки")

			# Блок обновленияф списка объектов в группе
			obect_view_db_list = []
			data_view02 = data_view.get()
			#print("data_view02 " + data_view02)
			directory_file = (os.path.join(os.getcwd(),'data/faces/' + str(data_view02) + '/'))
			onlyfiles = [f for f in listdir(directory_file) if isfile(join(directory_file, f))]
			onlyfiles_1 = str(onlyfiles)
			#print("вывод:" + str(onlyfiles_1))
			original_list = re.findall(r'[_][n][_][0-9][0-9][0-9][0-9][0-9][_]', onlyfiles_1)
			unique_list = list(set(original_list))
			unique_list.sort()
			#print("vota: " + str(unique_list))
			# unique_list = unique_list.insert(0, 'Все записи') # так не заработало
			unique_list = ['Все записи'] + unique_list  # а так не заработало!
			#print("vot: " + str(unique_list))
			obect_view_db_list1 = unique_list
			obect_view_db.configure(values=obect_view_db_list1)

			data_view01 = data_view.get()
			#print(obect_view01 + ", " + data_view01 + ", " + obect_view_db01)
			checklist.configure(state="normal")
			checklist.delete("1.0", END)
			list_file()

		obect_view_list = ['Все зафиксированные', 'Только неизвестные', 'Все жильцы', 'Все гости']
		obect_view = ttk.Combobox(win_katalog02, values=obect_view_list, width=30, state="readonly")
		# obect_view.pack(anchor=tk.NW, padx=5, pady=2)
		obect_view.place(x=610, y=10)
		obect_view.current(0)
		obect_view.bind("<<ComboboxSelected>>", obnovit_view)

		dir_list = []
		directory = (os.path.join(os.getcwd(),'data/faces/'))
		dir_list_pre = len(list(os.walk(directory)))
		# print("dir_list_pre", dir_list_pre)
		# print(dir_list_pre)
		# print(dir_list)
		if dir_list_pre > 1:
			dir_list = next(os.walk(directory))[1]
			dir_list.sort(reverse=True)
		# print("список директорий " + str(dir_list))
		else:
			dir_list = ['']
		data_view_list = dir_list
		# print("data_view_list", data_view_list)
		data_view = ttk.Combobox(win_katalog02, values=data_view_list, width=30, state="readonly")
		# data_view.pack(anchor=tk.NW, padx=5, pady=2)
		data_view.place(x=390, y=10)
		if dir_list_pre > 1:
			data_view.current(0)  # сделать условие, при 0 списке выходит ошибка!
		data_view.bind("<<ComboboxSelected>>", obnovit_view)
		# time_view_list = ['Весь день', 'c 00-00 до 10-00', 'с 10-00 до 20-00', 'с 20-00 до 24-00']
		# time_view = ttk.Combobox(win_katalog02, values=time_view_list, width=30, state="readonly")
		# time_view.pack(anchor=tk.NW, padx=5, pady=2)
		# time_view.current(0)

		obect_view_db_list = []
		dir_list_pre = len(list(os.walk(os.path.join(os.getcwd(),'data/faces/'))))
		# print("dir_list_pre", dir_list_pre)
		# print(dir_list)
		if dir_list_pre != 0:
			data_view02 = data_view.get()
			#print("data_view02 " + data_view02)
			directory_file = (os.path.join(os.getcwd(),'data/faces/' + str(data_view02) + '/'))
			onlyfiles = [f for f in listdir(directory_file) if isfile(join(directory_file, f))]
			onlyfiles_1 = str(onlyfiles)
			#print("вывод:" + str(onlyfiles_1))
			original_list = re.findall(r'[_][n][_][0-9][0-9][0-9][0-9][0-9][_]', onlyfiles_1)
			unique_list = list(set(original_list))
			unique_list.sort()
			#print("vota: " + str(unique_list))
			# unique_list = unique_list.insert(0, 'Все записи') # так не заработало
			unique_list = ['Все записи'] + unique_list  # а так не заработало!
			#print("vot: " + str(unique_list))
			obect_view_db_list1 = unique_list
			#print(obect_view_db_list1)
		else:
			unique_list = ['Все записи']
			obect_view_db_list1 = unique_list
		obect_view_db = ttk.Combobox(win_katalog02, values=obect_view_db_list1, width=30, state="readonly")
		obect_view_db.place(x=830, y=10)
		obect_view_db.current(0)  # сделать условие, при о списке выходит ошибка!
		obect_view_db.bind("<<ComboboxSelected>>", obnovit_view)


		def akcept_wind_model():
			data_view = None
			object_view_name007 = object_view.get()
			if object_view_name007 != '':

				def quitall_akcept_wind_model():
					windowakcept01.destroy()

				selected_options = []
				global ii
				global object_view_name
				object_view_name = object_view.get()
				#print("obect_view_name " + object_view_name)
				ii = 0
				for option, data in checkboxes.items():
					if data['var'].get():
						selected_options.append(option)
						ii = ii + 1
				#print(str(i) + ": " + str(len(selected_options)))
				# return selected_options
				#print(selected_options)

				def akcept_wind_model_action():
					global ii
					global object_view_name
					object_view_name01 = os.path.join(os.getcwd(),"data/dataset/" + str(object_view_name) + "/")
					#print(str(object_view_name01))
					i_text = 0
					text01_f = ""
					if ii > 0:
						for f in selected_options:
							# rezult_file = (f[f.find('F_d_'):])
							# print("rezult_file " + str(rezult_file))
							# print("Имя F " + str(f))
							# print(str("Имя объкта " + str(object_view_name01)))
							try:
								shutil.move(f, object_view_name01)
							except Exception:
								i_text = i_text + 1
								text01_f = text01_f + "Файл " + str(f) + " существует в каталоге" + str(
									object_view_name) + ".\n\n"

						if i_text == 0:
							text01 = "Изображения загружены для объекта: " + object_view_name + ". Для возврата закройте окно."
						else:
							text01 = "Количество не загруженных файлов: " + str(i_text) + ". Список файлов в протоколе."
							windowakcept_info = Toplevel(windowakcept01)
							windowakcept_info.title('Протокол - Не загруженые фото')
							windowakcept_info.geometry('1200x300+300+200')
							scrollbar_inf = tk.Scrollbar(windowakcept_info, width=30)
							scrollbar_inf.pack(side=tk.RIGHT, fill=tk.Y)
							checklist_inf = tk.Text(windowakcept_info, width=800, height=800, font=("Helvetica", 10),
													bg='gray72',
													fg='#000',
													yscrollcommand=scrollbar_inf.set)
							checklist_inf.insert("end", text01_f)
							# print("scrollbar: " + str(scrollbar_inf))
							checklist_inf.pack()

						if ii == 0:
							text01 = "Не выбрано ни одного изображения. Для возврата закройте окно."
							#print("Не выбрано ни одного изображения. Для возврата закройте окно.")
						if ii != 0:
							# text01 = "Изображения загружены для объекта: " + object_view_name +  ". Для возврата закройте окно."
							l03.configure(text=text01)
							checklist1.configure(state="normal")
							checklist1.delete("1.0", END)
							# checklist1.insert("end", 'Изображения удалены. Для возврата закройте окно')
							checklist1.configure(state="disabled")
							checklist.configure(state="normal")
							checklist.delete("1.0", END)
							obnovit_view()
							# checklist.configure(state="disabled")
							#print("Изображения загружены.")
							del selected_options[:]
							ii = 0
							delete_button_akc.configure(text="Закрыть окно", command=quitall_akcept_wind_model)
						# delete_button_akc.pack(padx=30, pady=5)
						# quitall_akcept_wind()

					else:
						text01 = "Не выбрано ни одного изображения. Для возврата закройте окно."
						l03.configure(text=text01)
						delete_button_akc.configure(text="Закрыть окно", command=quitall_akcept_wind_model)

				windowakcept01 = Toplevel(win_katalog02)
				windowakcept01.title('Загрузка фото в модель')
				windowakcept01.configure(bg='lightgrey')
				windowakcept01.geometry('1200x800+300+100')
				text01 = ""
				if ii == 0:
					text01 = "Не выбрано ни одного изображения. Для возврата закройте окно."
				if ii != 0:
					text01 = "Oбъект: " + object_view_name + ". Кол-во: " + str(
						ii) + ". Проверьте и подтвердите загрузку в модель."

				l03: Label = ttk.Label(windowakcept01, text=text01, style="My.TLabel")  # Create a label
				l03.pack()
				if ii == 0:
					delete_button_akc = ttk.Button(windowakcept01, text="Закрыть окно", style='my.TButton',
												   command=quitall_akcept_wind_model)
				if ii != 0:
					delete_button_akc = ttk.Button(windowakcept01, text="Загрузить фото в модель", style='my.TButton',
												   command=akcept_wind_model_action)
				delete_button_akc.pack(padx=30, pady=5)

				scrollbar1 = tk.Scrollbar(windowakcept01, width=30)
				scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
				checklist1 = tk.Text(windowakcept01, width=800, height=800, font=("Helvetica", 5), bg='gray72',
									 fg='#000',
									 yscrollcommand=scrollbar1.set)
				#print("scrollbar: " + str(scrollbar1))
				checklist1.pack()
				kolich = 0
				checklist1.configure(state="normal")
				# checklist1.insert("end", 'Для корректировки списка нажмите "Назад"')
				for option1 in selected_options:
					var = tk.BooleanVar()
					img = ImageTk.PhotoImage(Image.open(option1).resize((icon_size_width, icon_size_height)))
					# img = ImageTk.PhotoImage(Image.open(mypath + '\\' + option).resize((icon_size_width, icon_size_height)))
					#print(option1)
					imgs.append(img)
					kolich = kolich + 1
					# print(imgs)
					# chk1 = tk.Checkbutton(checklist1, text=option1, image=img, variable=var, cursor="arrow")
					checklist1.image_create('end', image=img)
					checklist1.insert("end", "   ")

				# chk = tk.Checkbutton(checklist, text=option, variable=var, cursor="arrow")
				# checklist1.window_create("end", window=chk1)
				# checklist1.insert("end", "  ")
				checklist1.configure(state="disabled")
				windowakcept01.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
				windowakcept01.grab_set()
			else:
				l12.configure(text="Инфо: Для загрузки выберите объект и фотографии!")
			# print("Инфо: Для загрузки фото выберите объект!")

		def akcept_wind():
			def quitall_akcept_wind():
				windowakcept.destroy()

			selected_options = []
			global i
			i = 0
			for option, data in checkboxes.items():
				if data['var'].get():
					selected_options.append(option)
					i = i + 1
			#print(str(i) + ": " + str(len(selected_options)))
			# return selected_options
			#print(selected_options)

			def akcept_wind_action():
				global i
				if i > 0:
					for f in selected_options:
						os.remove(f)
					if i == 0:
						text01 = "Не выделено ни одного изображения."
						#print("Не выделено ни одного изображения.")
					if i != 0:
						text01 = 'Изображения удалены. Для возврата закройте окно'
						l02.configure(text=text01)
						checklist1.configure(state="normal")
						checklist1.delete("1.0", END)
						# checklist1.insert("end", 'Изображения удалены. Для возврата закройте окно')
						checklist1.configure(state="disabled")
						checklist.configure(state="normal")
						checklist.delete("1.0", END)
						obnovit_view()
						# checklist.configure(state="disabled")
						#print("Изображения удалены.")
						del selected_options[:]
						i = 0
						delete_button_akc.configure(text="Закрыть окно", command=quitall_akcept_wind)
					# delete_button_akc.pack(padx=30, pady=5)
					# quitall_akcept_wind()

				else:
					text01 = "Не выделено ни одного изображения. Для возврата закройте окно."
					l02.configure(text=text01)

			windowakcept = Toplevel(win_katalog02)
			windowakcept.title('Удалить фото?')
			windowakcept.geometry('1200x800+300+100')
			windowakcept.configure(bg="lightgrey")
			text01 = ""
			if i == 0:
				text01 = "Не выделено ни одного изображения. Для возврата закройте окно."
			if i != 0:
				text01 = "Кол-во: " + str(i) + ". Проверьте и подтвердите удаление."

			l02: Label = ttk.Label(windowakcept, text=text01, style="My.TLabel")  # Create a label
			l02.pack()
			if i == 0:
				delete_button_akc = ttk.Button(windowakcept, text="Закрыть окно", style='my.TButton',
											   command=quitall_akcept_wind)
			if i != 0:
				delete_button_akc = ttk.Button(windowakcept, text="Подтвердить удаление", style='my.TButton',
											   command=akcept_wind_action)
			delete_button_akc.pack(padx=30, pady=5)

			scrollbar1 = tk.Scrollbar(windowakcept, width=30)
			scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
			checklist1 = tk.Text(windowakcept, width=800, height=800, font=("Helvetica", 5), bg='gray72', fg='#000',
								 yscrollcommand=scrollbar1.set)
			#print("scrollbar: " + str(scrollbar1))
			checklist1.pack()
			kolich = 0
			checklist1.configure(state="normal")
			# checklist1.insert("end", 'Для корректировки списка нажмите "Назад"')
			for option1 in selected_options:
				var = tk.BooleanVar()
				img = ImageTk.PhotoImage(Image.open(option1).resize((icon_size_width, icon_size_height)))
				# img = ImageTk.PhotoImage(Image.open(mypath + '\\' + option).resize((icon_size_width, icon_size_height)))
				#print(option1)
				imgs.append(img)
				kolich = kolich + 1
				# print(imgs)
				# chk1 = tk.Checkbutton(checklist1, text=option1, image=img, variable=var, cursor="arrow")
				checklist1.image_create('end', image=img)
				checklist1.insert("end", "   ")

			# chk = tk.Checkbutton(checklist, text=option, variable=var, cursor="arrow")
			# checklist1.window_create("end", window=chk1)
			# checklist1.insert("end", "  ")
			checklist1.configure(state="disabled")
			windowakcept.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
			windowakcept.grab_set()

#		def select_all():
#			print("select_all")

		def akcept_wind_dir():
			global data_view
			data_view03 = data_view.get()
			unix_time = int(time.time())
			date_time = datetime.datetime.fromtimestamp(unix_time)
			date_timef = date_time.strftime('%Y-%m-%d')
			if data_view03 != '':
				if data_view03 != date_timef:
					result224 = askokcancel(title="Вопрос",
										   message="Удалить все фотографии на дату: " + data_view03 + " ?")
					if result224:
						# print(data_view03)
						path_abs = os.path.join(os.getcwd(),'data/faces/')
						# print(path_abs)
						shutil.rmtree(path_abs + str(data_view03))
						time.sleep(0.5)
						# блок обновления списка каталогов
						dir_list = []
						directory = (os.path.join(os.getcwd(),'data/faces/'))
						dir_list_pre = len(list(os.walk(directory)))
						# print("dir_list_pre", dir_list_pre)
						# print(dir_list_pre)
						# print(dir_list)
						if dir_list_pre > 1:
							dir_list = next(os.walk(directory))[1]
							dir_list.sort(reverse=True)
						# print("список директорий " + str(dir_list))
						else:
							dir_list = ['']
						data_view_list = dir_list
						# print("data_view_list", data_view_list)
						data_view = ttk.Combobox(win_katalog02, values=data_view_list, width=30, state="readonly")
						# data_view.pack(anchor=tk.NW, padx=5, pady=2)
						data_view.place(x=390, y=10)
						if dir_list_pre > 1:
							data_view.current(0)  # сделать условие, при 0 списке выходит ошибка!

						data_view.set('')
						# data_view.current(0)
						obnovit_view()
				else:
					messagebox.showinfo("Внимание", "Текущую дату удалить нельзя!")
			else:
				print("нет удаления")

		obnovit_view_button = ttk.Button(win_katalog02, text="Обновить список", style='my.TButton',
										 command=obnovit_view)
		# obnovit_view_button.pack(anchor=tk.NW, padx=200, pady=2)
		obnovit_view_button.place(x=1050, y=10)

		# finalize_button = ttk.Button(win_katalog02, text="Количество выделенных изобр.", style='my.TButton', command=lambda: print(get_selected_options()))
		# finalize_button.pack(anchor=tk.SE, padx=30, pady=5)
		delete_button = ttk.Button(win_katalog02, text="Удалить отмеченые фото", style='my.TButton',
								   command=akcept_wind)
		delete_button.pack(anchor=tk.SE, padx=30, pady=5)
		delete_button.place(x=1190, y=10)

		delete_button_dir = ttk.Button(win_katalog02, text="Удалить каталог", style='my.TButton',
									   command=akcept_wind_dir)
		delete_button_dir.pack(anchor=tk.SE, padx=30, pady=5)
		delete_button_dir.place(x=1360, y=10)

		model_button = ttk.Button(win_katalog02, text="Загрузить отмеченые фото в модель", style='my.TButton',
								  command=akcept_wind_model)
		# model_button.pack(anchor=tk.SE, padx=30, pady=5)
		model_button.place(x=1050, y=40)
		# select_all_button = ttk.Button(win_katalog02, text="Выделить все изображения", style='my.TButton', command=select_all)
		# select_all_button.pack(anchor=tk.SE, padx=30, pady=5)
		# select_all_button.place(x=1020, y=10)

		obect_view01 = obect_view.get()
		obect_view_db01 = obect_view_db.get()
		#print("obect_view_db01: " + obect_view_db01)
		if obect_view01 == 'Все зафиксированные':
			obect_view01 = '*'
			if obect_view_db01 == 'Все записи':
				obect_view01 = '*'
			if obect_view_db01 != 'Все записи':
				obect_view01 = obect_view_db01
		if obect_view01 == 'Только неизвестные':
			obect_view01 = '_n_Unknown'
		data_view01 = data_view.get()
		#print(obect_view01 + ", " + data_view01)
		razmer_view01 = razmer_view.get()
		#print("razmer_view01: " + razmer_view01)
		if razmer_view01 == 'Мелкие значки':
			icon_size_width = 70
			icon_size_height = 70
		if razmer_view01 == 'Обычные значки':
			icon_size_width = 120
			icon_size_height = 120
		if razmer_view01 == 'Крупные значки':
			icon_size_width = 180
			icon_size_height = 180
		if razmer_view01 == 'Огромные значки':
			icon_size_width = 200
			icon_size_height = 200

		scrollbar = tk.Scrollbar(win_katalog02, width=30)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
		checklist = tk.Text(win_katalog02, width=800, height=800, font=("Helvetica", 5), bg='gray72', fg='#000',
							yscrollcommand=scrollbar.set)
		#print("scrollbar: " + str(scrollbar))
		checklist.pack()

		def get_selected_options():
			selected_options = []
			for option, data in checkboxes.items():
				if data['var'].get():
					selected_options.append(option)
			return selected_options

		def list_file():
			global obect_view01
			global data_view01
			global checkboxes
			# global fileList2
			global imgs
			global checklist
			global icon_size_width
			global icon_size_height
			global obect_view_db01

			data_view01 = data_view.get()

			if icon_size_width == None:
				connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
				cursor = connection.cursor()
				cursor.execute('SELECT set01 FROM logins WHERE logins = ?', (activeuserlogin,))
				set1_razmer_icon = cursor.fetchall()
				set1_razmer_icon = set1_razmer_icon[0][0]
				#print("Прочитанное значение размера: " + str(set1_razmer_icon))
				connection.close()
				razmer_icon_temp = set1_razmer_icon
				if razmer_view01 == 'Мелкие значки':
					icon_size_width = 70
					icon_size_height = 70
				if razmer_view01 == 'Обычные значки':
					icon_size_width = 120
					icon_size_height = 120
				if razmer_view01 == 'Крупные значки':
					icon_size_width = 180
					icon_size_height = 180
				if razmer_view01 == 'Огромные значки':
					icon_size_width = 200
					icon_size_height = 200

			# imagePaths = list(paths.list_images(os.getcwd() + '\\data\\face'))  # dataset here
			# mypath = (os.getcwd() + '\\dataset\\face')
			mypath = (os.path.join(os.getcwd(),'data/faces' + '/' + data_view01 + '/'))
			#print(mypath)
			# lblText = StringVar()
			# lbl = Label(win_katalog02, textvariable=lblText)

			fileList = [f for f in listdir(mypath) if isfile(join(mypath, f))]
			fileList.sort()
			#print(fileList)

			name_obekt = obect_view01
			#print("def " + name_obekt)
			time_obekt = '??-??-??'
			data_obekt = data_view01
			#print("def " + data_obekt)

			fileList2: list[str] = glob.glob(mypath + 'F_d_' + data_obekt + '_t_' + time_obekt + name_obekt + '*.jpg')
			#print("fileList2: " + str(fileList2))

			# F_d_2024-07-27_t_14-15_n_10002_1_Vasily_u_1719741457.94386_c_95

			checkboxes = {}
			#print("def checkboxes: " + str(checkboxes))

			imgs = []
			#print("def imgs: " + str(imgs))

			# col = 1  # start from column 1
			# row = 10  # start from row 3

			# finalize_button = tk.Button(win_katalog02, text="Finalize Selection", command=lambda: print(get_selected_options()))
			# finalize_button.grid(row=1, column=1)

			# vertical_scrollbar = tk.Scrollbar(win_katalog02, orient="vertical", width=30, cursor="heart")
			# vertical_scrollbar.pack(side="right", fill="y")
			checklist.delete("1.0", "end")
			kolich = 0
			# img1p = 'C:\\Users\\user\\PycharmProjects\\pythonProject_conda3_10\\programma\\F_d_.jpg'
			# img1 = ImageTk.PhotoImage(Image.open(img1p).resize((icon_size_width, icon_size_height)))
			# checklist.delete("1.0", "end")

			#print(icon_size_width, icon_size_height)
			for option in fileList2:
				var = tk.BooleanVar()
				img = ImageTk.PhotoImage(Image.open(option).resize((icon_size_width, icon_size_height)))
				# img = ImageTk.PhotoImage(Image.open(mypath + '\\' + option).resize((icon_size_width, icon_size_height)))
				#print(option)
				imgs.append(img)
				kolich = kolich + 1
				# print(imgs)
				chk = tk.Checkbutton(checklist, text=option, image=img, variable=var, cursor="arrow", bg="grey67")
				# chk = tk.Checkbutton(checklist, text=option, variable=var, cursor="arrow")
				checklist.window_create("end", window=chk)
				checklist.insert("end", "  ")
				#print(str(checklist))
				# chk.grid(row=row, column=col)
				# if (col == 10):  # start new line after third column
				# row = row + 1  # start wtih next row
				# col = 1  # start with first column
				# else:  # within the same row
				# col = col + 1  # increase to next column
				# chk.pack(anchor=tk.NW)
				checkboxes[option] = {'var': var, 'chk': chk}
			#print("def imgs: " + str(imgs))
			#print(kolich)
			checklist.config(yscrollcommand=scrollbar.set)
			scrollbar.config(command=checklist.yview)
			checklist.configure(state="disabled")
			#print("scrollbar: " + str(scrollbar))
			#print("checklist: " + str(checklist))

		list_file()
		# checklist.delete("1.0", "end")
		# vertical_scrollbar.grid(row=0, column=1, sticky="ns")
		# vertical_scrollbar.config(command=chk.yview)
		win_katalog02.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
		# win_katalog02.mainloop()
		win_katalog02.grab_set()
		time.sleep(0.3)
		obnovit_view()
		#print(path1)
		#print(img_text_lab07)
	else:
		res = str("Фото событий: необходима авторизация")
		message.configure(text=res)


# переключатели для видео анализа: в окне или в программе

winchoose = None
def my_upd_winchoose(*args):
	global winchoose, canvaswindows, imshowwindows
	#print (str(winchoose.get()))
	if winchoose.get() == "canvaswindows":
		if canvaswindows == False:
			canvaswindows = True
			imshowwindows = False
			canvas.delete("all")
			print("в модуле my_upd_winchoose " + str(winchoose.get()))
	if winchoose.get() == "imshowwindows":
		if imshowwindows == False:
			imshowwindows = True
			canvaswindows = False
			if TrackIm == True:
				canvas.delete("all")
				canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Видео открыто в отдельном окне.", fill="#e60004")
			# скрытие экрана видео
			print("в модуле my_upd_winchoose " + str(winchoose.get()))

def checkbutton_changed():
	global set02_user, enabled_check, activeuserlogin
	if activeuserlogin == None:
		res = "Данная настройка только для авторизованных пользователей!"
		message.configure(text=res)
	else:
		if enabled_check.get() == 1:
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			cursor.execute('UPDATE logins SET set02 = "1" WHERE logins = ?', (activeuserlogin,))
			connection.commit()
			connection.close()
			set02_user = "1"
			res = "Установлен автоматический запуск камеры при входе в программу!"
			message.configure(text=res)
		else:
			#showinfo(title="Внимание", message="Отключен автоматический запуск камеры при входе в программу!")
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			cursor.execute('UPDATE logins SET set02 = "0" WHERE logins = ?', (activeuserlogin,))
			connection.commit()
			connection.close()
			set02_user = "0"
			res = "Отключен автоматический запуск камеры при входе в программу!"
			message.configure(text=res)


def checkbutton03_changed():
	global set03_user, enabled_check03, activeuserlogin
	if activeuserlogin == None:
		res = "Данная настройка для авторизованных пользователей!"
		message.configure(text=res)
	else:
		if enabled_check03.get() == 1:
			showinfo(title="Внимание", message='Установлен автомат. анализа видео при входе в программу! \nРаботает только при включении опции: "Подключать камеру автомат."')
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			cursor.execute('UPDATE logins SET set03 = "1" WHERE logins = ?', (activeuserlogin,))
			connection.commit()
			connection.close()
			set03_user = "1"
			res = "Установлен автомат. анализ видео при входе в программу!"
			message.configure(text=res)
		else:
			#showinfo(title="Внимание", message="Отключен автоматический запуск анализа видео при входе в программу!")
			connection = sqlite3.connect(os.path.join(os.getcwd(),'data/avtorizachiy.db'))
			cursor = connection.cursor()
			cursor.execute('UPDATE logins SET set03 = "0" WHERE logins = ?', (activeuserlogin,))
			connection.commit()
			connection.close()
			set03_user = "0"
			res = "Отключен автомат. анализ видео при входе в программу!"
			message.configure(text=res)

img_a2 = os.path.join(os.getcwd(),"data/photo/style/canvas_001.png")
imgtk_a2 = PhotoImage(file=img_a2)
img_a2_c = os.path.join(os.getcwd(),"data/photo/style/canvas_002.png")
imgtk_a2_c = PhotoImage(file=img_a2_c)
canvas_a2 = Canvas(frame3, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a2.create_image( 0, 0, image = imgtk_a2, anchor = "nw")
canvas_a2.place(x=0, y=0)
#canvas_a2.create_line(196 ,50, 196, 90, fill='slateblue3', width=3) #darkslateblue
canvas_a1 = Canvas(frame1, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a1.create_image( 0, 0, image = imgtk_a2, anchor = "nw")
canvas_a1.place(x=0, y=0)
canvas_a11 = Canvas(frame5, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a11.create_image( 0, 0, image = imgtk_a2, anchor = "nw")
canvas_a11.place(x=0, y=0)
canvas_a111 = Canvas(frame4, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a111.create_image( 0, 0, image = imgtk_a2, anchor = "nw")
canvas_a111.place(x=0, y=0)
canvas_a1111 = Canvas(frame2, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a1111.create_image( 0, 0, image = imgtk_a2, anchor = "nw")
canvas_a1111.place(x=0, y=0)
canvas_a2_c = Canvas(frame3, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a2_c.create_image( 0, 0, image = imgtk_a2_c, anchor = "nw")
canvas_a2_c.place(x=1808, y=0)
canvas_a21_c = Canvas(frame1, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a21_c.create_image( 0, 0, image = imgtk_a2_c, anchor = "nw")
canvas_a21_c.place(x=1808, y=0)
canvas_a211_c = Canvas(frame5, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a211_c.create_image( 0, 0, image = imgtk_a2_c, anchor = "nw")
canvas_a211_c.place(x=1808, y=0)
canvas_a2111_c = Canvas(frame4, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a2111_c.create_image( 0, 0, image = imgtk_a2_c, anchor = "nw")
canvas_a2111_c.place(x=1808, y=0)
canvas_a21111_c = Canvas(frame2, bg='lightgrey', width=1807, height=1200, bd=0, highlightthickness=0, relief='ridge')
canvas_a21111_c.create_image( 0, 0, image = imgtk_a2_c, anchor = "nw")
canvas_a21111_c.place(x=1808, y=0)


s = ttk.Style()

s.configure('my.TButton', background='lightgrey', font=('Helvetica', 10))
s.configure("My.TLabel",  # имя стиля
             font="helvetica 10",  # шрифт
             foreground="#000000",  # цвет текста
             padding=10,  # отступы
             background="lightgrey")
s.configure("TRadiobutton",  background='lightgrey', font=('Helvetica', 9))

imshow1 = "imshowwindows"
canvas1 = "canvaswindows"
winchoose = StringVar(value=canvas1)  # по умолчанию будет выбран элемент с value=canvas
#header = ttk.Label(frame3, textvariable=lang)
#header.pack(**position)
header11 = Label(window, text="Показ видео:",font=("Helvetica", 10), bg="lightgrey") #, font=("Helvetica", 13)
header11.place(x=1360, y=0)
canvas_btn = ttk.Radiobutton(window, text="в программе", value=canvas1, variable=winchoose)
canvas_btn.place(x=1450, y=0)
imshow1_btn = ttk.Radiobutton(window, text="в отдельном окне", value=imshow1, variable=winchoose)
imshow1_btn.place(x=1550, y=0)
winchoose.trace("w", my_upd_winchoose)  # Call the function on change
#print("trace" + str(winchoose.get()))

# enabled_checkbutton_view_scr.place(x=1033, y=640)

fullscreen_main_status = False
def fullscreen_main():
	global fullscreen_main_status
	if fullscreen_main_status == False:
		fullscreen_main_status = True
		root1.attributes("-fullscreen", True)
	else:
		fullscreen_main_status = False
		root1.attributes("-fullscreen", False)

def katalog_foto_object_forbutton():
	global catalog_foto_ob
	catalog_foto_ob = ""
	katalog_foto_object()

streameWindow = ttk.Button(frame3, text="Подключить камеру", width=32, style='my.TButton',
					command=WebStreame)
streameWindow.place(x=-4, y=45)
streameWindow1 = ttk.Button(frame3, text="Отключить камеру", width=32, style='my.TButton',
					command=WebStreameStop)
streameWindow1.place(x=-4, y=80)


trackImg = ttk.Button(frame3, text="Начать анализ видео", width=32, style='my.TButton',
					command=TrackImages)
trackImg.place(x=-4, y=125)

cv2trakingdef1stop = ttk.Button(frame3, text="Остановить анализ видео", width=32, style='my.TButton',
					command=trakingdef1stop)
cv2trakingdef1stop.place(x=-4, y=160)


RecordWindow = ttk.Button(frame3, text="Начать запись видео", width=32, style='my.TButton',
					command=RecordVideo)
RecordWindow.place(x=-4, y=205)
RecorStopdWindow = ttk.Button(frame3, text="Остановить запись видео", width=32, style='my.TButton',
					command=RecordStopVideo)
RecorStopdWindow.place(x=-4, y=240)



UserMenyWindow = ttk.Button(frame2, text="Создать объект наблюдения", width=32, style='my.TButton',
					command=new_objekt)
UserMenyWindow.place(x=-4, y=45)

UserMenyWindow02 = ttk.Button(frame2, text="Просмотр/ред. объектов наблюдения", width=32, style='my.TButton',
					command=objekt_list_edit)
UserMenyWindow02.place(x=-4, y=80)

UserMenyWindow0233_2 = ttk.Button(frame2, text="Просмотр/удал. фото объектов", width=32, style='my.TButton',
					command=katalog_foto_object_forbutton)
UserMenyWindow0233_2.place(x=-4, y=115)

UserMenyWindow0233_1 = ttk.Button(frame1, text="Журнал событий (на дату)", width=32, style='my.TButton',
					command=checkboxes_csv_def)
UserMenyWindow0233_1.place(x=-4, y=45)

UserMenyWindow022 = ttk.Button(frame1, text="Фото событий (на дату)", width=32, style='my.TButton',
					command=save_foto_listr)
UserMenyWindow022.place(x=-4, y=80)


trainImg = ttk.Button(frame2, text="Обучить модель", width=32, style='my.TButton',
					command=TrainImagesRun)
trainImg.place(x=-4, y=150)

trainImg = ttk.Button(frame2, text="Проверить актуальность модели", width=32, style='my.TButton',
					command=TranImage_control_button)
trainImg.place(x=-4, y=185)

streameCam1Set = ttk.Button(frame4, text="Настройка камеры", width=32, style='my.TButton',
					command=streameCam1Set1)
streameCam1Set.place(x=-4, y=80)

recognSetting = ttk.Button(frame4, text="Общие настройки", width=32, style='my.TButton',
					command=recognSetting1)
recognSetting.place(x=-4, y=45)

#recognSetting_1 = ttk.Button(frame4, text="Сетевые настройки (в разработке)", width=32, style='my.TButton',
#					command=recognSetting1)
#recognSetting_1.place(x=-4, y=115)

createuser = ttk.Button(frame4, text="Создать уч. запись", width=32, style='my.TButton',
					command=createlogin)
createuser.place(x=-4, y=195)

listteuser = ttk.Button(frame4, text="Просм.\ удал. уч.зап.", width=32, style='my.TButton',
					command=userlistdelete)
listteuser.place(x=-4, y=230)

enabled_check = IntVar()
canvas_checkbutton = ttk.Checkbutton(frame4, text="Подключать камеру автомат.", variable=enabled_check, command=checkbutton_changed)
if set02_user == "1":
	canvas_checkbutton.state(["selected"])
canvas_checkbutton.place(x=0, y=265)

enabled_check03 = IntVar()
canvas_checkbutton03 = ttk.Checkbutton(frame4, text="Включать анализ видео автомат.", variable=enabled_check03, command=checkbutton03_changed)
if set03_user == "1":
	canvas_checkbutton03.state(["selected"])
canvas_checkbutton03.place(x=0, y=285)

#cv2imshowwindows = tk.Button(frame2, text="Скрыть\ показать_видео",
#					command=trakingdef1imshow, fg="white", bg="gray",
#					width=26, height=2, activebackground="Red",
#					font=('times', 15, ' bold '))
#cv2imshowwindows.place(x=2, y=267)

quitWindowuser = ttk.Button(frame4, text="Смена пользоватателя", width=32, style='my.TButton',
					command=Authenticationinside)
quitWindowuser.place(x=-4, y=160)

quitWindowuser2 = ttk.Button(frame5, text="Смена пользоватателя", width=32, style='my.TButton',
					command=Authenticationinside)
quitWindowuser2.place(x=-4, y=80)

quitWindow = ttk.Button(frame5, text="Выйти из программы", width=32, style='my.TButton',
					command=exitmainprogramm)
quitWindow.place(x=-4, y=45)

fullscreen = ttk.Button(frame5, text="Полноэкранный режим (вкл/выкл)", width=32, style='my.TButton',
					command=fullscreen_main)
fullscreen.place(x=-4, y=125)


top_frame = ttk.Frame(window, width=761, height=606, relief='raised')
top_frame.pack_propagate(False)  # Отключаем автоматическую подгонку размера
top_frame.place(x=238, y=30)
l1 = ['data_start_s', 'time_start_s', 'long_s', 'categoriy_s', 'name01_s', 'apartmentnumb_s', 'floornumb_s', 'name01_m']
style = ttk.Style()


# Настройка стилей для Treeview
style.configure("Treeview",
                background="lightgrey",  # Цвет фона
                foreground="black",      # Цвет текста
                fieldbackground="lightgrey")  # Цвет фона ячеек
style.configure("Treeview.Heading",
                background="darkgrey",  # Цвет фона заголовков
                foreground="black")     # Цвет текста заголовков
style.map("Treeview",
          background=[("selected", "blue")],  # Цвет фона выделенной строки
          foreground=[("selected", "white")])  # Цвет текста выделенной строки


trv = ttk.Treeview(top_frame, selectmode='browse', height=29,
				   show='headings', columns=l1, style='Treeview')
trv.place(x=0, y=0)
vsb = tk.Scrollbar(top_frame, width=20, orient="vertical", command=trv.yview)
vsb.pack(side = RIGHT, fill = Y)
#vsb.place(x=30 + 200 + 2, y=95, height=200 + 20)

trv.configure(yscrollcommand=vsb.set)
for i in l1:
	trv.column(i, width=90, anchor='c')
	i1 = i
	if i == "long_s":
		trv.column(i, width=60, anchor='w')
		i1 = "Длит.,сек."
	if i == "data_start_s":
		i1 = "Дата,г.м.д."
	if i == "time_start_s":
		i1 = "Время,ч.м.с."
	if i == "categoriy_s":
		trv.column(i, width=90, anchor='w')
		i1 = "Категория"
	if i == "name01_s":
		trv.column(i, width=170, anchor='w')
		i1 = "Фамилия, имя"
	if i == "apartmentnumb_s":
		trv.column(i, width=60, anchor='c')
		i1 = "Квартира"
	if i == "floornumb_s":
		trv.column(i, width=50, anchor='c')
		i1 = "Этаж"
	if i == "name01_m":
		trv.column(i, width=130, anchor='w')
		i1 = "%, модель"
	trv.heading(i, text=str(i1))
unix_time = int(time.time())
date_time = datetime.datetime.fromtimestamp(unix_time)
date_timef_file_day = date_time.strftime('%Y-%m-%d')
file_csv = os.path.join(os.getcwd(),"data/protocols/normal_terminal/nt_d_" + date_timef_file_day + "_t_00.csv")
#print(file_csv)
try:
	df = pd.read_csv(file_csv, encoding="windows-1251")  # create DataFrame
	l1 = list(df)  # List of column names as header
	del l1[8:19]
	r_set = df.to_numpy().tolist()  # create list of list using rows
	p = 0
	for dt in r_set:
		p = p + 1
		v = [r for r in dt]
		trv.insert("", 'end', iid="csv0" + str(p), values=v)
		trv.yview_scroll(number=1, what="units")
	if p != 0:
		child_id = trv.get_children()[-1]
		if LOGGING_ENABLED:
			main_logger.debug(f"Загружено {p} записей из протокола событий")
		else:
			print(child_id)
		trv.selection_set(child_id)
	if LOGGING_ENABLED:
		main_logger.info(f"Протокол событий загружен успешно: {p} записей")
		
except FileNotFoundError:
	if LOGGING_ENABLED:
		main_logger.info(f"Файл протокола событий не найден: {file_csv}")
	else:
		print("Данные для заполнения лога событий отсутсвуют")
		
except pd.errors.EmptyDataError:
	if LOGGING_ENABLED:
		main_logger.warning(f"Файл протокола событий пуст: {file_csv}")
	else:
		print("Файл протокола событий пуст")
		
except pd.errors.ParserError as e:
	if LOGGING_ENABLED:
		main_logger.error(f"Ошибка парсинга файла протокола: {e}")
		log_exception(main_logger, e, "Загрузка CSV протокола")
	else:
		print(f"Ошибка чтения файла протокола: {e}")
		
except Exception as e:
	if LOGGING_ENABLED:
		main_logger.error(f"Неожиданная ошибка при загрузке протокола событий: {e}")
		log_exception(main_logger, e, "Загрузка CSV протокола - общая ошибка")
	else:
		print(f"Ошибка при загрузке протокола событий: {e}")


def item_selected(event):
	selected_people = ""
	for selected_item in trv.selection():
		item = trv.item(selected_item)
		# print(item)
		person = item["values"]
		# print(person)
		tab_nomer = person[13]
		data_katalog = person[0]
		vremy_nach = person[8]
		vremy_okonch = person[9]
		# print(tab_nomer)
		selected_people = f"{selected_people}{person}\n"
	#lb2["text"] = selected_people
	# print(selected_people)
	object_info_kard(tab_nomer)
	foto_object_info_m(vremy_nach, vremy_okonch, data_katalog)
	video_object_info_m(vremy_nach, vremy_okonch, data_katalog)

def video_play(event):
	global enabled_checkbutton_video_close_state
	def update_duration(event):
		""" updates the duration after finding the duration """
		duration = vid_player.video_info()["duration"]
		duration = int(duration)
		print(duration)
		end_time["text"] = str(datetime.timedelta(seconds=duration))
		progress_slider["to"] = duration

	def update_scale(event):
		""" updates the scale value """
		progress_slider.set(vid_player.current_duration())

	def load_video():
		""" loads the video """

	# file_path = filedialog.askopenfilename(filetypes=[("Mp4", "*.mp4",)])
	# print(file_path)

	def seek(event=None):
		""" used to seek a specific timeframe """
		vid_player.seek(int(progress_slider.get()))

	def skip(value: int):
		""" skip seconds """
		vid_player.seek(int(progress_slider.get()) + value)
		progress_slider.set(progress_slider.get() + value)

	def play_pause():
		""" pauses and plays """
		if vid_player.is_paused():
			vid_player.play()
			play_pause_btn["text"] = "Pause"

		else:
			vid_player.pause()
			play_pause_btn["text"] = "Play"

	def video_ended(event):
		""" handle video ended """
		progress_slider.set(progress_slider["to"])
		play_pause_btn["text"] = "Play"
		# progress_slider.set(0)
		if enabled_checkbutton_video_close_state:
			root.destroy()

	root = tk.Toplevel()
	root.title("Дозор")
	root.geometry('576x500+600+100')

	vid_player = TkinterVideo(scaled=True, master=root)
	vid_player.pack(expand=True, fill="both")

	play_pause_btn = tk.Button(root, text="Play", command=play_pause)
	play_pause_btn.pack()

	skip_plus_5sec = tk.Button(root, text="Назад -5 сек", command=lambda: skip(-5))
	skip_plus_5sec.pack(side="left")

	# start_time = tk.Label(root, text=str(datetime.timedelta(seconds=0)))
	# start_time.pack(side="left")

	progress_slider = tk.Scale(root, from_=0, to=0, orient="horizontal")
	progress_slider.bind("<ButtonRelease-1>", seek)
	progress_slider.pack(side="left", fill="x", expand=True)

	end_time = tk.Label(root, text=str(datetime.timedelta(seconds=0)))
	end_time.pack(side="left")

	vid_player.bind("<<Duration>>", update_duration)
	vid_player.bind("<<SecondChanged>>", update_scale)
	vid_player.bind("<<Ended>>", video_ended)

	skip_plus_5sec = tk.Button(root, text="Вперед +5 сек.", command=lambda: skip(5))
	skip_plus_5sec.pack(side="left")

	file_path = event
	#print(file_path)
	if file_path:
		vid_player.load(file_path)

		progress_slider.config(to=0, from_=0)
		play_pause_btn["text"] = "Play"
		progress_slider.set(0)

	play_pause()

	root.iconbitmap(os.path.join(os.getcwd(), 'data/dozor.ico'))
	# root.mainloop()
	root.grab_set()

def video_object_info_m(vremy_nach1, vremy_okonch1, data_katalog1):
	global imgs_csv_m_v
	global checkboxes_csv_m_v
	icon_size_width = 70
	icon_size_height = 70
	#print("test", vremy_nach1, vremy_okonch1)
	vremy_nach1 = int(vremy_nach1) - 20
	vremy_okonch1 = int(vremy_okonch1) + 20
	#print("test", vremy_nach1, vremy_okonch1, data_katalog1)
	# s1 = 1724950364
	# if int(s1) in range(vremy_nach1, vremy_okonch1):
	#	print("ok")
	path_catalog = (os.path.join(os.getcwd(),"data/video/records_video/" + data_katalog1 + "/"))
	#print(path_catalog)
	files = glob.glob(path_catalog + '*.avi')
	path_catalog1 = (os.path.join(os.getcwd(),"data/video/archive_video/" + data_katalog1 + "/"))
	files1 = glob.glob(path_catalog1 + '*.avi')
	files2 = files + files1
	files_rez = []
	print("files_rez", files_rez)
	favorit_pic = 0
	all_pic = 0
	for f1 in files2:
		f11 = re.findall(r'[_][u][_][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][_]', f1)
		f11 = f11[0][3:13]
		if int(f11) in range(vremy_nach1, vremy_okonch1):
			files_rez.append((f1))
			f15 = None
			f15 = re.findall(r'[a][r][c][h][i][v][e][_][v][i][d][e][o]', f1)
			# print(f15)
			all_pic = all_pic + 1
			if f15 == ['archive_video']:
				favorit_pic = int(favorit_pic) + 1
			#raznicha_pic = all_pic - favorit_pic
	#print(favorit_pic)
	# print("files_rez", files_rez)
	checklist_csv1_15.delete("1.0", "end")
	checkboxes_csv_m_v = {}
	imgs_csv_m_v = []
	checklist_csv1_15.configure(state='normal')
	checklist_csv1_15.delete("1.0", "end")
	#vid_play = (os.path.join(os.getcwd(), "data/photo/style/video_play_1.png"))
	#vid_play_img = ImageTk.PhotoImage(Image.open(vid_play).resize((20, 20)))
	kolich = 0
	len_pic = len(files_rez)
	#print("len_pic", len_pic)
	for f2 in files_rez:
		print(f2)
		f2_list = f2.split(os.path.sep)[-1]
		print(f2_list)
		var = tk.BooleanVar()
		#var1 = tk.BooleanVar()
		#img = ImageTk.PhotoImage(Image.open(f2).resize((icon_size_width, icon_size_height)))
		#imgs_csv_m_v.append(img)
		kolich = kolich + 1
		checklist_csv1_15.configure(state='normal')
		if len_pic == favorit_pic and kolich == 1:
			path01 = os.path.join(os.getcwd(), "data", "video", "archive_video", data_katalog1)
			open_button_c1 = tk.Button(checklist_csv1_15, text=" open ", cursor="hand2",
									   command=lambda path01_1=path01: openFolder(path01_1))
			checklist_csv1_15.window_create("end", window=open_button_c1)
			checklist_csv1_15.insert("end",
								 " Видео в архивной папке:", 'name1')
			checklist_csv1_15.tag_config('name1', foreground='red')
			checklist_csv1_15.insert("end", "\n")
		if len_pic > favorit_pic and kolich == 1:
			path02 = os.path.join(os.getcwd(), "data", "video", "records_video", data_katalog1)
			open_button_c2 = tk.Button(checklist_csv1_15, text=" open ", cursor="hand2",
									   command=lambda path02_1=path02: openFolder(path02_1))
			checklist_csv1_15.window_create("end", window=open_button_c2)
			checklist_csv1_15.insert("end",
								 " Видео в рабочей папке:", 'name')
			checklist_csv1_15.insert("end", "\n")

		if kolich == (all_pic - favorit_pic + 1) and favorit_pic != 0 and kolich != 1:
			checklist_csv1_15.insert("end", "\n")
			path03 = os.path.join(os.getcwd(), "data", "video", "archive_video", data_katalog1)
			open_button_c3 = tk.Button(checklist_csv1_15, text=" open ", cursor="hand2",
									   command=lambda path03_1=path03: openFolder(path03_1))
			checklist_csv1_15.window_create("end", window=open_button_c3)
			checklist_csv1_15.insert("end",
								 " Видео в архивной папке:", 'name1')
			checklist_csv1_15.tag_config('name1', foreground='red')
			checklist_csv1_15.insert("end", "\n")
		# checklist_csv.configure(state="normal")
		chk = tk.Checkbutton(checklist_csv1_15, text=f2_list,  variable=var, cursor="arrow", bg="grey77") #image=img,
		#chk1 = tk.Label(checklist_csv1, text="открыть", bg="grey67", cursor="hand2")
		open_button = tk.Button(checklist_csv1_15, text=" play ", cursor="hand2",
								command=lambda f=os.path.join(f2): video_play(f))
		checklist_csv1_15.window_create("end", window=chk)
		checklist_csv1_15.insert("end", " ")
		checklist_csv1_15.window_create("end", window=open_button)
		checklist_csv1_15.insert("end", " ")

		checkboxes_csv_m_v[f2] = {'var': var, 'chk': chk}
		#chk1.bind("<Button-1>", lambda event: (on_click(), chk.toggle()))
	if kolich == 0:
		checklist_csv1_15.insert(tk.INSERT, "не найдены")





	checklist_csv1_15.insert("end", "\n\n")
	# header11f.configure(text="Найдено " + str(kolich) + " фото.")

	checklist_csv1_15.configure(state="disabled")

def copy_select_video_m():
	global activeusergroupe
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		selected_options = []
		data_katalog = None
		i = 0
		for option, data in checkboxes_csv_m_v.items():
			if data['var'].get():
				selected_options.append(option)
				i = i + 1
		if i > 0:
			f11 = re.findall(r'[V][_][d][_][0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9][_]', selected_options[0])
			f11 = f11[0][4:14]
			#print("f11", f11)
			catalog_day_foto = "data\\video\\archive_video\\" + str(f11)
			if not os.path.exists(os.path.join(os.getcwd(),catalog_day_foto)):
				os.makedirs(catalog_day_foto)
			for f in selected_options:
				try:
					shutil.copy(f, catalog_day_foto)

				except Exception:
					text01_f = "Файл " + str(f) + " существует в каталоге" + str(
						catalog_day_foto) + ".\n\n"
					#print(text01_f)
			checklist_csv1_15.configure(state='normal')
			checklist_csv1_15.insert("end",
								  "\nВидео сохранено.") #Для обновления повторно выделите строку в журнале событий.
			checklist_csv1_15.configure(state="disabled")
			unix_time = int(time.time())
			date_time = datetime.datetime.fromtimestamp(unix_time)
			date_timef = date_time.strftime('%Y-%m-%d')
			video_object_info_m_day(date_timef)

			if i == 0:
				text01 = "Не выделено ни одного видео."
				#print("Не выделено ни одного изображения.")
	else:
		#print("Требуется авторизация в программе")
		res = "Для сохранения видео требуется авторизация в программе"
		#message.configure(text=res)

checklist_csv1_15 = scrolledtext.ScrolledText(window, undo=True, width=62, height=16, wrap='word')
checklist_csv1_15['font'] = ('Helvetica', '10')
checklist_csv1_15.place(x=1105, y=665)
checklist_csv1_15.configure(state='disabled', bg="lightgrey")


RecordWindow = ttk.Button(window, text="Запись видео", style='my.TButton',
					command=RecordVideo)
RecordWindow.place(x=1290, y=637)

save_button15 = ttk.Button(window, text="Сохранить видео", style='my.TButton',
						  command=copy_select_video_m)
save_button15.place(x=1400, y=637)



def video_object_info_m_day(data_katalog1):
	#global imgs_csv_m_v
	#global checkboxes_csv_m_v
	path_catalog = (os.path.join(os.getcwd(),"data/video/records_video/" + data_katalog1 + "/"))
	files = glob.glob(path_catalog + '*.avi')
	kolich = len(files)
	path_catalog_a = (os.path.join(os.getcwd(), "data/video/archive_video/" + data_katalog1 + "/"))
	files_a = glob.glob(path_catalog_a + '*.avi')
	kolich_a = len(files_a)
	files_itog = files + files_a
	#print("kolich", kolich, files)
	files_rez = []
	favorit_pic = 0
	all_pic = 0
	checklist_csv1_15_day.delete("1.0", "end")
	checklist_csv1_15_day.configure(state='normal')
	checklist_csv1_15_day.delete("1.0", "end")
	ch = 0
	for f2 in files_itog:
		ch = ch + 1
		if ch == kolich + 1:
			if kolich != 0:
				checklist_csv1_15_day.insert("end", "\n")
			checklist_csv1_15_day.insert("end", "В архивной папке:\n", "name001")
			checklist_csv1_15_day.tag_config('name001', foreground='red')
		#print(f2)
		f2_list = f2.split(os.path.sep)[-1][17:25]
		open_button = tk.Button(checklist_csv1_15_day, text=f2_list, cursor="hand2",
								command=lambda f=os.path.join(f2): video_play(f))
		checklist_csv1_15_day.window_create("end", window=open_button)
		checklist_csv1_15_day.insert("end", "  ")
		#chk1.bind("<Button-1>", lambda event: (on_click(), chk.toggle()))
	if (kolich + kolich_a) == 0:
		checklist_csv1_15_day.insert(tk.INSERT, "не найдены")
	checklist_csv1_15_day.configure(state="disabled")

video_podpis = tk.Label(window, font=('Helvetica', 10), background='lightgrey', foreground='black', justify=LEFT, anchor='w', width=18, height=1)
unix_time = int(time.time())
date_time = datetime.datetime.fromtimestamp(unix_time)
date_timef = date_time.strftime('%Y-%m-%d')
video_podpis.configure(text="Видео за день:") #str(date_timef) +
video_podpis.place(x=1576, y=640)

checklist_csv1_15_day = scrolledtext.ScrolledText(window, undo=True, width=31, height=16, wrap='word')
checklist_csv1_15_day['font'] = ('Helvetica', '10')
checklist_csv1_15_day.place(x=1576, y=665)
checklist_csv1_15_day.configure(state='disabled', bg="lightgrey")
video_object_info_m_day(date_timef)

def data_now(date_timef):
	unix_time = int(time.time())
	date_time = datetime.datetime.fromtimestamp(unix_time)
	date_timef = date_time.strftime('%Y-%m-%d')
	return date_timef

#save_button15_day = ttk.Button(window, text="Обновить", style='my.TButton',
#						  command=lambda td=data_now(date_timef): video_object_info_m_day(td))
#save_button15_day.place(x=1727, y=637)

def foto_object_info_m(vremy_nach1, vremy_okonch1, data_katalog1):
	global imgs_csv_m
	global checkboxes_csv_m
	icon_size_width = 65
	icon_size_height = 65
	#print("test", vremy_nach1, vremy_okonch1)
	vremy_nach1 = int(vremy_nach1) - 2
	vremy_okonch1 = int(vremy_okonch1) + 2
	#print("test", vremy_nach1, vremy_okonch1, data_katalog1)
	# s1 = 1724950364
	# if int(s1) in range(vremy_nach1, vremy_okonch1):
	#	print("ok")
	path_catalog = (os.path.join(os.getcwd(),"data/faces/" + data_katalog1 + "/"))
	#print(path_catalog)
	files = glob.glob(path_catalog + '*.jpg')
	path_catalog1 = (os.path.join(os.getcwd(),"data/photo/event_save/event_foto/" + data_katalog1 + "/"))
	files1 = glob.glob(path_catalog1 + '*.jpg')
	files2 = files + files1
	files_rez = []
	#print("files_rez", files_rez)
	favorit_pic = 0
	all_pic = 0
	for f1 in files2:
		f11 = re.findall(r'[_][u][_][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][.]', f1)
		f11 = f11[0][3:13]
		if int(f11) in range(vremy_nach1, vremy_okonch1):
			files_rez.append((f1))
			f15 = None
			f15 = re.findall(r'[e][v][e][n][t][_][f][o][t][o]', f1)
			# print(f15)
			all_pic = all_pic + 1
			if f15 == ['event_foto']:
				favorit_pic = int(favorit_pic) + 1
			#raznicha_pic = all_pic - favorit_pic
	#print(favorit_pic)
	# print("files_rez", files_rez)
	checklist_csv1.delete("1.0", "end")
	checkboxes_csv_m = {}
	imgs_csv_m = []
	checklist_csv1.configure(state='normal')
	checklist_csv1.delete("1.0", "end")

	kolich = 0
	len_pic = len(files_rez)
	#print("len_pic", len_pic)
	for f2 in files_rez:
		var = tk.BooleanVar()
		img = ImageTk.PhotoImage(Image.open(f2).resize((icon_size_width, icon_size_height)))
		imgs_csv_m.append(img)
		kolich = kolich + 1
		checklist_csv1.configure(state='normal')
		if len_pic == favorit_pic and kolich == 1:
			path01 = os.path.join(os.getcwd(), "data", "photo", "event_save", "event_foto", data_katalog1)
			open_button_c1 = tk.Button(checklist_csv1, text=" open ", cursor="hand2",
									   command=lambda path01_1=path01: openFolder(path01_1))
			checklist_csv1.window_create("end", window=open_button_c1)
			checklist_csv1.insert("end",
								 " Фото в архивной папке:", 'name1')
			checklist_csv1.tag_config('name1', foreground='red')
			checklist_csv1.insert("end", "\n")
		if len_pic > favorit_pic and kolich == 1:
			path02 = os.path.join(os.getcwd(), "data", "faces", data_katalog1)
			open_button_c2 = tk.Button(checklist_csv1, text=" open ", cursor="hand2",
									   command=lambda path02_1=path02: openFolder(path02_1))
			checklist_csv1.window_create("end", window=open_button_c2)
			checklist_csv1.insert("end",
								 " Фото в рабочей папке:")
			checklist_csv1.insert("end", "\n")

		if kolich == (all_pic - favorit_pic + 1) and favorit_pic != 0 and kolich != 1:
			checklist_csv1.insert("end", "\n")
			path03 = os.path.join(os.getcwd(), "data", "photo", "event_save", "event_foto", data_katalog1)
			open_button_c3 = tk.Button(checklist_csv1, text=" open ", cursor="hand2",
									   command=lambda path03_1=path03: openFolder(path03_1))
			checklist_csv1.window_create("end", window=open_button_c3)
			checklist_csv1.insert("end",
								 " Фото в архивной папке:", 'name1')
			checklist_csv1.tag_config('name1', foreground='red')
			checklist_csv1.insert("end", "\n")
		# checklist_csv.configure(state="normal")
		chk = tk.Checkbutton(checklist_csv1, text=f2, image=img, variable=var, cursor="arrow", bg="grey67")
		checklist_csv1.window_create("end", window=chk)
		checklist_csv1.insert("end", " ")
		checkboxes_csv_m[f2] = {'var': var, 'chk': chk}

	if kolich == 0:
		checklist_csv1.insert(tk.INSERT, "не найдены")

	checklist_csv1.insert("end", "\n\n")
	# header11f.configure(text="Найдено " + str(kolich) + " фото.")

	checklist_csv1.configure(state="disabled")


def copy_select_foto_m():
	global activeusergroupe
	if activeusergroupe == "admin" or activeusergroupe == "operator":
		selected_options = []
		data_katalog = None
		i = 0
		for option, data in checkboxes_csv_m.items():
			if data['var'].get():
				selected_options.append(option)
				i = i + 1
		if i > 0:
			f11 = re.findall(r'[F][_][d][_][0-9][0-9][0-9][0-9][-][0-9][0-9][-][0-9][0-9][_]', selected_options[0])
			f11 = f11[0][4:14]
			#print("f11", f11)
			catalog_day_foto = "data/photo/event_save/event_foto/" + str(f11)
			if not os.path.exists(os.path.join(os.getcwd(),catalog_day_foto)):
				os.makedirs(catalog_day_foto)
			for f in selected_options:
				try:
					shutil.copy(f, catalog_day_foto)

				except Exception:
					text01_f = "Файл " + str(f) + " существует в каталоге" + str(
						catalog_day_foto) + ".\n\n"
					#print(text01_f)
			checklist_csv1.configure(state='normal')
			checklist_csv1.insert("end",
								  "\nФото сохранено.") #Для обновления повторно выделите строку в журнале событий.
			checklist_csv1.configure(state="disabled")

			if i == 0:
				text01 = "Не выделено ни одного изображения."
				#print("Не выделено ни одного изображения.")
	else:
		#print("Требуется авторизация в программе")
		res = "Для сохранения фото требуется авторизация в программе"
		message.configure(text=res)


trv.bind("<<TreeviewSelect>>", item_selected)


def checkbutton_changed_video_close():
	global enabled_checkbutton_video_close_state
	if enabled_video_clos.get() == 1:
		enabled_checkbutton_video_close_state = True
	else:
		enabled_checkbutton_video_close_state = False

enabled_video_clos = IntVar()

enabled_checkbutton_video_close1 = ttk.Checkbutton(window, text="Авто закрытие окна", variable=enabled_video_clos, command=checkbutton_changed_video_close)
enabled_checkbutton_video_close1.place(x=1105, y=640)
enabled_checkbutton_video_close1.state(["selected"])


def checkbutton_changed_view_scr():
	global enabled_checkbutton_view_scr_state
	if enabled_view_scr.get() == 1:
		enabled_checkbutton_view_scr_state = True
	else:
		enabled_checkbutton_view_scr_state = False

enabled_view_scr = IntVar()

enabled_checkbutton_view_scr = ttk.Checkbutton(window, text="Авто прокрутка списка", variable=enabled_view_scr, command=checkbutton_changed_view_scr)
enabled_checkbutton_view_scr.place(x=238, y=640)
enabled_checkbutton_view_scr.state(["selected"])

def checkbutton_changed_view_scr_last():
	global enabled_checkbutton_view_scr_state_last
	if enabled_view_scr_last.get() == 1:
		enabled_checkbutton_view_scr_state_last = True
	else:
		enabled_checkbutton_view_scr_state_last = False

enabled_view_scr_last = IntVar()

enabled_checkbutton_view_scr_last = ttk.Checkbutton(window, text="Авто показ карточки", variable=enabled_view_scr_last, command=checkbutton_changed_view_scr_last)
enabled_checkbutton_view_scr_last.place(x=405, y=640)
enabled_checkbutton_view_scr_last.state(["selected"])

#UserMenyWindow023 = ttk.Button(window, text="Фото событий", width=22, style='my.TButton',
#					command=save_foto_listr)
#UserMenyWindow023.place(x=1465, y=637)

#UserMenyWindow0233 = ttk.Button(window, text="Журнал (на дату)", width=15, style='my.TButton',
#					command=checkboxes_csv_def)
#UserMenyWindow0233.place(x=835, y=637)

save_button1 = ttk.Button(window, text="Сохранить фото", style='my.TButton',
						  command=copy_select_foto_m)
save_button1.place(x=835, y=637) #705

path11 = (os.path.join(os.getcwd(),"data/photo/objects/grey_circle_2_d.png"))
img_text_lab = ImageTk.PhotoImage(Image.open(path11).resize((100, 100)))
panel = Label(window, image=img_text_lab, bg="lightgrey")
panel.image = img_text_lab
panel.place(x=1000, y=30)

#def show_info(event):
#	global text_lab02
#	print(text_lab02)
#	info_label.place(x=1000, y=250)  # Положение метки может быть скорректировано

#def hide_info(event):
#	info_label.place_forget()

#info_label = tk.Label(window, text=text_lab02, bg="yellow")

path112 = (os.path.join(os.getcwd(),"data/photo/objects/grey_circle_2_o.png"))
img_text_lab = ImageTk.PhotoImage(Image.open(path112).resize((100, 100)))
panel01 = Label(window, image=img_text_lab, bg="lightgrey")
panel01.image = img_text_lab
panel01.place(x=1000, y=150)
#panel01_text = tk.Label(window, text=text_lab02, bg="lightgrey")
#panel01_text.place(x=1000, y=250)
#panel01.bind("<Enter>", show_info)
#panel01.bind("<Leave>", hide_info)
#panel01.bind("<Motion>", show_info)

path113 = (os.path.join(os.getcwd(),"data/photo/objects/grey_circle_2_z.png"))
img_text_lab = ImageTk.PhotoImage(Image.open(path113).resize((100, 100)))
panel02 = Label(window, image=img_text_lab, bg="lightgrey")
panel02.image = img_text_lab
panel02.place(x=1000, y=270)

path114 = (os.path.join(os.getcwd(),"data/photo/objects/grey_circle_2_o2.png"))
img_text_lab = ImageTk.PhotoImage(Image.open(path114).resize((100, 100)))
panel03 = Label(window, image=img_text_lab, bg="lightgrey")
panel03.image = img_text_lab
panel03.place(x=1000, y=390)

path115 = (os.path.join(os.getcwd(),"data/photo/objects/grey_circle_2_r.png"))
img_text_lab = ImageTk.PhotoImage(Image.open(path115).resize((100, 100)))
panel04 = Label(window, image=img_text_lab, bg="lightgrey")
panel04.image = img_text_lab
panel04.place(x=1000, y=510)

frame_kard = ttk.Frame(window, width=137, height=260, relief='raised')
frame_kard.place(x=238, y=665)

char_editor = Text(frame_kard, height=17, width=19, bg="lightgrey", font=('Helvetica', 9), wrap="word")
char_editor.place(x=0, y=0)
char_editor.configure(state='disabled')

#char_editor01 = Text(height=15, width=19, bg="lightgrey", font=('Helvetica', 9), wrap="word")
#char_editor01.place(x=467, y=665)
#char_editor01.configure(state='disabled')

#char_editor02 = Text(height=15, width=19, bg="lightgrey", font=('Helvetica', 9), wrap="word")
#char_editor02.place(x=608, y=665)
#char_editor02.configure(state='disabled')

#char_editor03 = Text(height=15, width=19, bg="lightgrey", font=('Helvetica', 9), wrap="word")
#char_editor03.place(x=750, y=665)
#char_editor03.configure(state='disabled')

#char_editor04 = Text(height=15, width=19, bg="lightgrey", font=('Helvetica', 9), wrap="word")
#char_editor04.place(x=891, y=665)
#char_editor04.configure(state='disabled')

checklist_csv1_height = 16
checklist_csv1 = scrolledtext.ScrolledText(window, undo=True, width=98, height=checklist_csv1_height, wrap='word')
checklist_csv1['font'] = ('Helvetica', '10')
checklist_csv1.place(x=384, y=665)
checklist_csv1.configure(state='disabled', bg="lightgrey")


def object_info(modelfolder):
	global ch01
	global text_lab
	global text_lab02
	global text_lab03
	global text_lab04
	global text_lab05
	#ch01 = ch01 + 1
	#from PIL import Image, ImageTk
	global img_text_lab
	global img_text_lab01
	global img_text_lab02
	global img_text_lab03
	global img_text_lab04
	text_lab05 = text_lab04
	text_lab04 = text_lab03
	text_lab03 = text_lab02
	text_lab02 = text_lab
	img_text_lab04 = img_text_lab03
	img_text_lab03 = img_text_lab02
	img_text_lab02 = img_text_lab01
	img_text_lab01 = img_text_lab
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))
	cursor = connection.cursor()
	cursor.execute('SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
                   (modelfolder,))
	first_name_db = cursor.fetchall()
	if first_name_db == []:
		first_name_db = [('', 'Объект удален из БД', '0', '0', '0', '0', '0', '0', 'no_avatar_yel.jpg', 'None', 'None')]
		modelfolder = "no_avatar_yel"
	for row in first_name_db:
		print(str(row))
	connection.close()
	if row[2] == '1':
		categoriy_s = 'Жилец'
	if row[2] == '2':
		categoriy_s = 'Гость'
	if row[2] == '3':
		categoriy_s = 'Специальный'
	if row[2] == '4':
		categoriy_s = 'Внимание!'
	if row[2] == '0':
		categoriy_s = ''

	text_lab = ("\n" + categoriy_s + "\n" + str(row[1]) + " " + str(row[0]) + "\nкв. " + str(row[3]) + ", этаж " + str(row[4]) + "\n" + str(row[10]) + "\n" + str(row[7]))
	#text_lab = (str(row[1]))

	path1 = (os.path.join(os.getcwd(),"data/photo/objects/" + modelfolder + ".jpg"))
	bb = os.path.isfile(path1)
	if bb:
		img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize((100, 100)))
	else:
		path1 = (os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg"))
		img_text_lab = ImageTk.PhotoImage(Image.open(path1).resize(100, 100))
	panel.configure(image=img_text_lab)
	panel.image = img_text_lab
	#char_editor.configure(state="normal", bg="lightgrey")
	#char_editor.delete("1.0", END)
	#char_editor.image_create(END, image=img_text_lab)
	#char_editor.insert("end", text_lab)
	#char_editor.configure(state="disabled")

	if img_text_lab01 != None:
		panel01.configure(image=img_text_lab01)
		panel01.image = img_text_lab01
		#panel01_text.configure(text=text_lab02)
		#print(text_lab)
		#char_editor01.configure(state="normal")
		#char_editor01.delete("1.0", END)
		#char_editor01.image_create(END, image=img_text_lab01)
		#char_editor01.insert("end", text_lab02)
		#char_editor01.configure(state="disabled")

	if img_text_lab02 != None:
		panel02.configure(image=img_text_lab02)
		panel02.image = img_text_lab02
		#char_editor02.configure(state="normal")
		#char_editor02.delete("1.0", END)
		#char_editor02.image_create(END, image=img_text_lab02)
		#char_editor02.insert("end", text_lab03)
		#char_editor02.configure(state="disabled")

	if img_text_lab03 != None:
		panel03.configure(image=img_text_lab03)
		panel03.image = img_text_lab03
		#char_editor03.configure(state="normal")
		#char_editor03.delete("1.0", END)
		#char_editor03.image_create(END, image=img_text_lab03)
		#char_editor03.insert("end", text_lab04)
		#char_editor03.configure(state="disabled")

	if img_text_lab04 != None:
		panel04.configure(image=img_text_lab04)
		panel04.image = img_text_lab04
		#char_editor04.configure(state="normal")
		#char_editor04.delete("1.0", END)
		#char_editor04.image_create(END, image=img_text_lab04)
		#char_editor04.insert("end", text_lab05)
		#char_editor04.configure(state="disabled")


def object_info_kard(modelfolder):
	global ch01
	global text_lab_kard
	#global text_lab02
	#global text_lab03
	#global text_lab04
	#global text_lab05
	# ch01 = ch01 + 1
	# from PIL import Image, ImageTk
	global img_text_lab_kard
	#global img_text_lab01
	#global img_text_lab02
	#global img_text_lab03
	#global img_text_lab04
	#text_lab05 = text_lab04
	#text_lab04 = text_lab03
	#text_lab03 = text_lab02
	#text_lab02 = text_lab
	#img_text_lab04 = img_text_lab03
	#img_text_lab03 = img_text_lab02
	#img_text_lab02 = img_text_lab01
	#img_text_lab01 = img_text_lab
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))
	cursor = connection.cursor()
	cursor.execute(
		'SELECT first_name, last_name, category, apartmentnumb, floornumb, homenumb, phone, modelfolder, foto, userlink, ob_komments FROM People WHERE modelfolder = ?',
		(modelfolder,))
	first_name_db = cursor.fetchall()
	#print(first_name_db)
	if first_name_db == []:
		first_name_db = [('', 'Объект удален из БД', '0', '0', '0', '0', '0', '0', 'no_avatar_yel.jpg', 'None', 'None')]
		modelfolder = "no_avatar_yel"
	#print(first_name_db)
	for row in first_name_db:
		print(str(row))
	connection.close()
	if row[2] == '1':
		categoriy_s = 'Жилец'
	if row[2] == '2':
		categoriy_s = 'Гость'
	if row[2] == '3':
		categoriy_s = 'Специальный'
	if row[2] == '4':
		categoriy_s = 'Внимание!'
	if row[2] == '0':
		categoriy_s = ''

	text_lab_kard = ("\n" + categoriy_s + "\n" + str(row[1]) + " " + str(row[0]) + "\nкв. " + str(
		row[3]) + ", этаж " + str(row[4]) + "\n" + str(row[10]) + "\n" + str(row[7]))
	path1 = (os.path.join(os.getcwd(),"data/photo/objects/" + modelfolder + ".jpg"))
	bb = os.path.isfile(path1)
	if bb:
		img_text_lab_kard = ImageTk.PhotoImage(Image.open(path1).resize((130, 130)))
	else:
		path1 = (os.path.join(os.getcwd(),"data/photo/objects/no_avatar_grey.jpg"))
		img_text_lab_kard = ImageTk.PhotoImage(Image.open(path1).resize((130, 130)))

	char_editor.configure(state="normal")
	char_editor.delete("1.0", END)
	char_editor.image_create(END, image=img_text_lab_kard)
	char_editor.insert("end", text_lab_kard)
	char_editor.configure(state="disabled")

	#if img_text_lab01 != None:
	#	char_editor01.configure(state="normal")
	#	char_editor01.delete("1.0", END)
	#	char_editor01.image_create(END, image=img_text_lab01)
	#	char_editor01.insert("end", text_lab02)
	#	char_editor01.configure(state="disabled")

	#if img_text_lab02 != None:
	#	char_editor02.configure(state="normal")
	#	char_editor02.delete("1.0", END)
	#	char_editor02.image_create(END, image=img_text_lab02)
	#	char_editor02.insert("end", text_lab03)
	#	char_editor02.configure(state="disabled")

	#if img_text_lab03 != None:
	#	char_editor03.configure(state="normal")
	#	char_editor03.delete("1.0", END)
	#	char_editor03.image_create(END, image=img_text_lab03)
	#	char_editor03.insert("end", text_lab04)
	#	char_editor03.configure(state="disabled")

	#if img_text_lab04 != None:
	#	char_editor04.configure(state="normal")
	#	char_editor04.delete("1.0", END)
	#	char_editor04.image_create(END, image=img_text_lab04)
	#	char_editor04.insert("end", text_lab05)
	#	char_editor04.configure(state="disabled")

# статус строка вывода системных сообщение
frame_status = ttk.Frame(window, width=1800, height=22, relief='raised')
frame_status.pack(anchor="sw", fill=X, expand=True)

message = tk.Label(
	frame_status, text=":-)", justify=LEFT, anchor='w',
	bg="grey70", fg="black", width=105,
	height=1, font=('Helvetica', 10))
message.place(x=400, y=0)

lableuser = tk.Label(frame_status, font=('Helvetica', 10), background='grey70', foreground='black', justify=LEFT, width=22, height=1)
lableuser.place(x=0, y=0)

lablel_model_status = tk.Label(frame_status, font=('Helvetica', 10), background='grey70', foreground='black', justify=LEFT, width=22, height=1)
lablel_model_status.place(x=200, y=0)

if activeuserlogin is None:
	lableuser.config(text="Не авториз.", fg="red")
	message.configure(text="Пользователь не авторизован!")
else:
	lableuser.config(text="Логин: " + str(activeuserlogin), fg="black")
	res = "Режим: " + activeusergroupe + ", модель распозн.: " + model_algoritm_var + ", видео кодек: " + v_record_codec_var + ")."
	message.configure(text=res)

if activatmainprogram is False and activeuserlogin is None:
	print("выход из программы - условие")
	quitall()

aa = os.path.isfile(os.path.join(os.getcwd(),'data\objects.db'))
if aa == False:
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/objects.db'))
	cursor = connection.cursor()
	# rowid INTEGER PRIMARY KEY,
	# Создаем таблицу
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS People (
	last_name TEXT,
	first_name TEXT,
	phone TEXT,
	category TEXT,
	homenumb TEXT,
	apartmentnumb TEXT,
	floornumb TEXT,
	modelfolder TEXT,
	foto TEXT,
	userlink TEXT,
	ob_komments TEXT,
	ob_sets01 TEXT,
	ob_sets02 TEXT,
	ob_sets03 TEXT,
	ob_sets04 TEXT,
	ob_sets05 TEXT
	)
	''')
	# Добавляем начальные настройки
	cursor.execute('INSERT INTO People (last_name, first_name, category, apartmentnumb, floornumb, modelfolder, foto) VALUES (?, ?, ?, ?, ?, ?, ?)',
				   ('Unknown', 'Unknown', '4', '0', '0', 'Unknown', 'no_avatar_grey.jpg'))
	# Сохраняем изменения и закрываем соединение
	connection.commit()
	connection.close()

bb = os.path.isfile(os.path.join(os.getcwd(),'data/camerasetting.db'))
if bb == False:
	file_path_cam = "data/camerasetting.db"
	try:
		connection = sqlite3.connect(os.path.join(os.getcwd(),file_path_cam))
		cursor = connection.cursor()
		cursor.execute('''
				CREATE TABLE IF NOT EXISTS cameras (
				id INTEGER PRIMARY KEY,
				name_cam TEXT,
				location TEXT,
				vision TEXT,
				link TEXT,
				activ_number TEXT,
				height TEXT,
				width TEXT,
				fps TEXT,   
				cam_set_a TEXT,
				cam_set_b TEXT,
				cam_set_c TEXT,
				cam_set_d TEXT
				)
				''')
		connection.commit()
		connection.close()
		if LOGGING_ENABLED:
			camera_logger.info("База данных настроек камер создана успешно")
	except sqlite3.Error as e:
		if LOGGING_ENABLED:
			camera_logger.error(f"Ошибка при создании базы данных камер: {e}")
			log_exception(camera_logger, e, "Создание camerasetting.db")
		else:
			print(f"ОШИБКА: Не удалось создать базу данных камер: {e}")

aktiv_number_cam = "channel_01"
stream_connect = "0"
camera01_link11 = None

try:
	connection = sqlite3.connect(os.path.join(os.getcwd(),'data/camerasetting.db'))
	cursor = connection.cursor()
	cursor.execute('SELECT link FROM cameras WHERE activ_number = ?', (aktiv_number_cam,))
	camera01_link = cursor.fetchall()
	
	for row in camera01_link:
		if LOGGING_ENABLED:
			camera_logger.debug(f"Найдена ссылка на камеру: {row[0]}")
		else:
			print(str(row[0]))
		camera01_link11 = row[0]
	
	if LOGGING_ENABLED:
		camera_logger.info(f"Настройки камеры загружены: {camera01_link11}")
	else:
		print("camera01_link11 равен", camera01_link11)
		
except sqlite3.OperationalError as e:
	if LOGGING_ENABLED:
		camera_logger.warning(f"Таблица камер не найдена или пуста: {e}")
	else:
		print(f"Таблица камер не найдена: {e}")
	camera01_link11 = None
	
except sqlite3.Error as e:
	if LOGGING_ENABLED:
		camera_logger.error(f"Ошибка БД при загрузке настроек камеры: {e}")
		log_exception(camera_logger, e, "Загрузка настроек камеры")
	else:
		print(f"Ошибка БД: {e}")
	camera01_link11 = None
	
except Exception as e:
	if LOGGING_ENABLED:
		camera_logger.error(f"Неожиданная ошибка при загрузке настроек камеры: {e}")
		log_exception(camera_logger, e, "Загрузка настроек камеры - общая")
	else:
		print(f"camera01_link11 равен {camera01_link11}, ошибка: {e}")
		
finally:
	try:
		connection.close()
	except:
		pass

if camera01_link11 != None:
	if set02_user == "1":
		canvas.create_text(10, 10, font="Helvetica 12", anchor=NW, text="Идет подключение к камере.",
						   fill="#e60004")
		if LOGGING_ENABLED:
			camera_logger.info("Автозапуск подключения к камере")
		else:
			print("автозапуск WebStreame")
		WebStreame()
		time.sleep(5)
		if set03_user == "1" and WS1 == True:
			canvas.create_text(10, 35, font="Helvetica 12", anchor=NW, text="Идет запуск анализа видео.",
							   fill="#e60004")
			if LOGGING_ENABLED:
				recognition_logger.info("Автозапуск анализа видео")
			else:
				print("автозапуск WebStreame")
			TrackImages()

# Планирование заданий
scheduler = BlockingScheduler()
def job_make_dir_sche():

	def job_make_dir():
		unix_time = int(time.time())
		date_time = datetime.datetime.fromtimestamp(unix_time)
		date_timef = date_time.strftime('%Y-%m-%d')
		catalog_day = "data/faces/" + date_timef
		catalog_day_video = "data/video/records_video/" + date_timef
		print("Проверка: ", catalog_day, "Проверка: ", catalog_day_video)
		if not os.path.exists(os.path.join(os.getcwd(),catalog_day)):
			os.makedirs(os.path.join(os.getcwd(),catalog_day))
			print("Создан каталог: ", catalog_day)
		if not os.path.exists(os.path.join(os.getcwd(),catalog_day_video)):
			os.makedirs(os.path.join(os.getcwd(),catalog_day_video))
			print("Создан каталог: ", catalog_day_video)

	def job_del_dir():
		unix_time = int(time.time())
		date_time = datetime.datetime.fromtimestamp(unix_time)
		date_timef = date_time.strftime('%Y-%m-%d')
		path_abs = 'data/video/records_video/'
		walk = list(os.walk(os.path.join(os.getcwd(),path_abs)))
		print(walk)
		print(walk[1:])
		walk = walk[1:]
		print(walk)
		for path, _, _ in walk[::-1]:
			if len(os.listdir(path)) == 0:
				if (path[-10:]) != date_timef:
					print(path[-10:])
					# os.rmdir(path)
					shutil.rmtree(path)

	def job_del_dir_model():
		object_list = []
		directory02 = (os.path.join(os.getcwd(),'data/data_archives/model_archives/'))
		dir_list_pre = len(list(os.walk(directory02)))
		#print("dir_list_pre", dir_list_pre)
		#print(directory02)
		if dir_list_pre > 1:
			object_list = next(os.walk(directory02))[1]
			object_list.sort()
			if dir_list_pre > 10:
				object_list = object_list[:-10]
				for folder in object_list:
					shutil.rmtree(directory02 + str(folder))
					#print(directory02 + str(folder))
			else:
				object_list = [None, ]
		# print("список директорий объетов " + str(object_list))
		else:
			object_list = [None, ]

	scheduler.add_job(job_make_dir, 'cron', hour='00', minute='00-01', second='01', id='job_3')
	scheduler.add_job(job_del_dir, 'cron', hour='00', minute='02', second='01', id='job_4')
	scheduler.add_job(job_del_dir_model, 'cron', hour='00', minute='03', second='01', id='job_5')
	scheduler.start()

job_make_dir_sche = threading.Thread(target=job_make_dir_sche, daemon=True)
print("Status", job_make_dir_sche.is_alive())
job_make_dir_sche.start()
TranImage_control()
root1.iconbitmap(os.path.join(os.getcwd(),'data/dozor.ico'))
window.mainloop()
