"""
Модуль веб-стриминга для приложения "Дозор".
Обеспечивает трансляцию видеопотока через Flask.
"""
from flask import Response, render_template, Flask
from multiprocessing import Process, Manager
import os
import cv2
import time
import hashlib
import logging
import sqlite3

# Настройка FFMPEG
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp|preset;slow|faststart'

# Попытка импорта модуля логирования
try:
    from logger_config import stream_logger, camera_logger, log_exception
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False
    # Создаём базовый логгер если модуль логирования недоступен
    stream_logger = logging.getLogger("webstreaming")
    stream_logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler("log.log", mode='w', encoding='utf-8')
    log_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    log_handler.setFormatter(log_formatter)
    stream_logger.addHandler(log_handler)
    
    def log_exception(logger, error, context=""):
        logger.error(f"[{context}] {type(error).__name__}: {error}")

# Попытка импорта ffmpegcv
try:
    import ffmpegcv
    FFMPEGCV_AVAILABLE = True
except ImportError:
    FFMPEGCV_AVAILABLE = False
    stream_logger.warning("ffmpegcv не установлен, некоторые функции будут недоступны")

# Инициализация переменных с значениями по умолчанию
aktiv_number_cam = "channel_01"
camera01_link1 = None
rejim = None
host_acc = '127.0.0.1'
stream_port = '8000'
stream_res_video_var = '704'
stream_qual_video_var = '90'

# Загрузка настроек камеры из базы данных
try:
    connection = sqlite3.connect('data/camerasetting.db')
    cursor = connection.cursor()
    cursor.execute('SELECT link, cam_set_a FROM cameras WHERE activ_number = ?', (aktiv_number_cam,))
    camera_rows = cursor.fetchall()
    
    for row in camera_rows:
        camera01_link1 = row[0]
        rejim = row[1]
    
    connection.close()
    stream_logger.info(f"Настройки камеры загружены: link={camera01_link1}, режим={rejim}")
    
except sqlite3.OperationalError as e:
    stream_logger.warning(f"Таблица камер не найдена или недоступна: {e}")
    camera01_link1 = None
    
except sqlite3.Error as e:
    stream_logger.error(f"Ошибка базы данных при загрузке настроек камеры: {e}")
    log_exception(stream_logger, e, "Загрузка настроек камеры")
    camera01_link1 = None
    
except Exception as e:
    stream_logger.error(f"Неожиданная ошибка при загрузке настроек камеры: {e}")
    log_exception(stream_logger, e, "Загрузка настроек камеры - общая")
    camera01_link1 = None
    
finally:
    try:
        connection.close()
    except:
        pass

# Загрузка настроек стриминга
parametr = 'stream'
parametr_stream_q_var1 = 'stream_res_qua'

try:
    connection = sqlite3.connect(os.path.join(os.getcwd(), 'data/setting.db'))
    cursor = connection.cursor()
    
    # Загружаем хост и порт
    cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr,))
    file_folder = cursor.fetchall()
    for row in file_folder:
        host_acc = row[0]
        stream_port = row[1]
    
    # Загружаем разрешение и качество
    cursor.execute('SELECT set01, set02 FROM setting WHERE parametr_name = ?', (parametr_stream_q_var1,))
    parametr_stream_q_var11 = cursor.fetchall()
    for row in parametr_stream_q_var11:
        stream_res_video_var = row[0]
        stream_qual_video_var = row[1]
    
    connection.close()
    stream_logger.info(f"Настройки стриминга: host={host_acc}, port={stream_port}, res={stream_res_video_var}, qual={stream_qual_video_var}")
    
except sqlite3.Error as e:
    stream_logger.error(f"Ошибка базы данных при загрузке настроек стриминга: {e}")
    log_exception(stream_logger, e, "Загрузка настроек стриминга")
    # Используем значения по умолчанию
    
except Exception as e:
    stream_logger.error(f"Неожиданная ошибка при загрузке настроек стриминга: {e}")
    log_exception(stream_logger, e, "Загрузка настроек стриминга - общая")
    
finally:
    try:
        connection.close()
    except:
        pass

source: str = camera01_link1
stream_logger.info(f"Источник видео: {source}, режим: {rejim}")

app: Flask = Flask(__name__)

# Инициализация для тестового режима
fps = 20  # значение по умолчанию
frame_delay = 1.0 / fps

if rejim == "1":  # 1 это тест
    stream_logger.info("Запуск в тестовом режиме")
    try:
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            stream_logger.error(f"Не удалось открыть видеоисточник: {source}")
        else:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                duration = total_frames / fps
                stream_logger.info(f"Видео: {total_frames} кадров, {fps} FPS, длительность: {duration:.2f} сек")
            else:
                stream_logger.warning("Не удалось определить FPS видео, используется значение по умолчанию")
                fps = 20
        cap.release()
        frame_delay = 1.0 / fps
        
    except cv2.error as e:
        stream_logger.error(f"Ошибка OpenCV при инициализации тестового режима: {e}")
        log_exception(stream_logger, e, "Тестовый режим - OpenCV")
        
    except Exception as e:
        stream_logger.error(f"Ошибка при инициализации тестового режима: {e}")
        log_exception(stream_logger, e, "Тестовый режим - общая")

import urllib.error


def cache_frames(source: str, last_frame: list, running) -> None:
    """
    Кэширует кадры из видеопотока для передачи клиентам.
    
    Args:
        source: URL или путь к источнику видео
        last_frame: Список для хранения последнего кадра (разделяемая память)
        running: Флаг для управления работой процесса
    """
    global stream_res_video_var
    global stream_qual_video_var
    
    # Проверка доступности CUDA
    try:
        cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
        if cuda_count == 0:
            stream_logger.info("CUDA не доступен, используется CPU")
            cuda_gpu_codec = False
        else:
            stream_logger.info(f"Доступно CUDA устройств: {cuda_count}")
            cuda_gpu_codec = True
    except Exception as e:
        stream_logger.warning(f"Ошибка при проверке CUDA: {e}")
        cuda_gpu_codec = False
    
    index_error_count01 = 0
    
    # Попытка открыть источник видео
    try:
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            stream_logger.error(f"Не удалось открыть источник видеопотока: {source}")
            return
    except cv2.error as e:
        stream_logger.error(f"Ошибка OpenCV при открытии источника: {e}")
        return
    except Exception as e:
        stream_logger.error(f"Неожиданная ошибка при открытии источника: {e}")
        return

    # Получение характеристик видео
    try:
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        stream_logger.info(f"Характеристики видео: {width}x{height}")
    except Exception as e:
        stream_logger.error(f"Ошибка при получении характеристик видео: {e}")
        width = 0.0
        height = 0.0

    if width != 0.0 and height != 0.0:
        try:
            aspect_ratio = width / height
            new_width = int(stream_res_video_var)
            quality_jpg = int(stream_qual_video_var)
            new_height = int(new_width / aspect_ratio)
            stream_logger.info(f"Целевое разрешение: {new_width}x{new_height}, качество JPEG: {quality_jpg}")
        except (ValueError, ZeroDivisionError) as e:
            stream_logger.error(f"Ошибка при расчёте параметров видео: {e}")
            cap.release()
            return
        
        reconnect_attempts = 0
        max_reconnect_attempts = 10
        
        while running.value:
            if not cap.isOpened():
                reconnect_attempts += 1
                if reconnect_attempts > max_reconnect_attempts:
                    stream_logger.error(f"Превышено максимальное количество попыток переподключения ({max_reconnect_attempts})")
                    break
                    
                stream_logger.warning(f"Камера не открыта. Попытка переподключения {reconnect_attempts}/{max_reconnect_attempts}...")
                cap.release()
                time.sleep(5)
                
                try:
                    cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                    if not cap.isOpened():
                        stream_logger.error("Переподключение не удалось. Следующая попытка через 5 секунд.")
                        time.sleep(5)
                    else:
                        stream_logger.info("Переподключение успешно")
                        reconnect_attempts = 0
                except Exception as e:
                    stream_logger.error(f"Ошибка при переподключении: {e}")
                continue

            try:
                ret, frame = cap.read()
            except cv2.error as e:
                stream_logger.error(f"Ошибка OpenCV при чтении кадра: {e}")
                time.sleep(1)
                continue
                
            if not ret:
                if rejim == "1":
                    stream_logger.info("Достигнут конец видео (тестовый режим)")
                    break
                stream_logger.warning("Не удалось получить кадр. Пересоздание подключения...")
                cap.release()
                time.sleep(2)
                continue

            # Обработка кадра
            try:
                frame = cv2.resize(frame, (new_width, new_height))
                success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality_jpg])
                if not success:
                    stream_logger.error("Ошибка кодирования изображения в JPEG")
                    continue
                last_frame[0] = buffer.tobytes()
                if rejim == "1":
                    time.sleep(frame_delay)
            except cv2.error as e:
                stream_logger.error(f"Ошибка OpenCV при обработке кадра: {e}")
                continue
            except Exception as e:
                stream_logger.error(f"Неожиданная ошибка при обработке кадра: {e}")
                continue
        
        stream_logger.info("Цикл захвата кадров завершен. Освобождение ресурсов.")
        cap.release()
    else:
        stream_logger.warning("Не удалось прочитать характеристики видео (ширина или высота равны 0)")


def generate(shared_last_frame: list):
    """
    Генератор кадров для HTTP-стриминга.
    
    Args:
        shared_last_frame: Список с последним кадром (разделяемая память)
    
    Yields:
        Байтовые данные для multipart/x-mixed-replace отклика
    """
    frame_data = None
    index_error_count = 0
    max_errors = 10
    
    while True:
        try:
            if frame_data != shared_last_frame[0]:
                frame_data = shared_last_frame[0]
                if frame_data is not None:
                    timestamp = int(time.time())
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')

        except IndexError:
            index_error_count += 1
            if index_error_count >= max_errors:
                stream_logger.error(f"Достигнуто максимальное количество ошибок IndexError ({max_errors}). Завершение.")
                break
            stream_logger.warning(f"IndexError при генерации кадра ({index_error_count}/{max_errors})")
            continue

        except TypeError as e:
            # Может произойти если frame_data еще не инициализирован
            stream_logger.debug(f"TypeError при генерации кадра (возможно, кадр не готов): {e}")
            time.sleep(0.1)
            continue

        except Exception as e:
            stream_logger.error(f"Ошибка при генерации кадра: {e}")
            log_exception(stream_logger, e, "generate")
            continue
        #try:
            #yield (b'--frame\r\n'
            #        b'Content-Type:image/jpeg\r\n'
            #        b'Content-Length: ' + f"{len(frame_data)}".encode() + b'\r\n'
            #                                                       b'\r\n' + frame_data + b'\r\n')
            #except:
                #print("Yield Exception")
                #return

        #time.sleep(1 / 15)  # Задержка


@app.route("/")
def index() -> str:
    # Возвращаем отрендеренный шаблон
    return render_template("index_video.html")


@app.route("/video_feed")
def video_feed() -> Response:
    return Response(generate(last_frame),
                    mimetype="multipart/x-mixed-replace; boundary=frame")  # Запуск генератора




if __name__ == '__main__':
    with Manager() as manager:
        last_frame = manager.list([None])  # Кэш последнего кадра
        running = manager.Value('i', 1)  # Управляемый флаг для контроля выполнения процесса

        # Создаём процесс для кэширования кадров
        p = Process(target=cache_frames, args=(source, last_frame, running))
        p.start()

        # Запуск Flask-приложения в блоке try/except
        try:
            app.run(host=host_acc, port=stream_port, debug=True, threaded=True, use_reloader=False)
        except KeyboardInterrupt:
            print("Получено прерывание с клавиатуры, инициирую завершение...")
        finally:
            print("Завершение работы дочернего процесса...")
            running.value = 0  # Сигнализируем процессу о необходимости завершения
            p.join(timeout=5)  # Ожидаем штатного завершения процесса в течение 5 секунд
            if p.is_alive():
                print("Процесс не завершился штатно. Принудительное завершение.")
                p.terminate()  # Принудительно завершаем, если он все еще жив
            p.join()
            print("Дочерний процесс завершен.")



