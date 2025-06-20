import json
import logging

# noinspection PyUnresolvedReferences
from bson.json_util import dumps
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from expenses import ExpenseTracker

# Инициализация логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger('HTTP Server')

# Инициализация объекта ExpenseTracker, который хранит и обрабатывает данные о тратах
tracker = ExpenseTracker()

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        """Переопределение стандартного вывода логов запросов"""
        logger.info("%s - - [%s] %s" % (
            self.address_string(),
            self.log_date_time_string(),
            format % args
        ))

    """
    Класс обработчика HTTP-запросов, наследуется от BaseHTTPRequestHandler.
    Реализует методы do_GET и do_POST для обработки GET и POST запросов соответственно.
    """
    def _set_headers(self, code=200):
        """
        Установка HTTP-заголовков для ответа.
        По умолчанию устанавливает код ответа 200 OK и Content-Type: application/json в кодировке utf-8.
        """
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()

    def _send_json_response(self, data, code=200):
        """Отправка JSON-ответа"""
        self._set_headers(code)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _handle_error(self, code, message):
        """Обработчик ошибок с правильным Content-Type"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        error_response = {
            "error": self.responses[code][0],
            "message": message
        }
        self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def do_POST(self): # noqa: N802
        """
        Обработка POST-запросов.
        В проекте поддерживается путь /add_expense, который позволяет добавить новую трату.
        """
        try:
            parsed_url = urlparse(self.path) # Выполняем парсинг пути
            path = parsed_url.path # Получаем путь запроса
            
            if path == "/add_expense":
                # Получаем длину тела запроса из заголовков
                content_length = int(self.headers.get('Content-Length', 0))
                # Читаем тело запроса (байты), декодируем из utf-8 в строку
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    # Парсим JSON из строки в словарь, если тело не пустое
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    self._send_json_response({
                        "error": "Bad Request", 
                        "message": "Неверный формат JSON"
                    }, 400)
                    return

                # Записываем в дебаг лог
                logger.debug(f"POST data received: {data}")

                # Извлекаем необходимые параметры для добавления траты
                name = data.get('name')
                category = data.get('category')
                amount = data.get('amount')
                date = data.get('date')

                # Проверяем, что все поля заполнены - если нет, возвращаем 400 Bad Request
                if not name or not category or not amount or not date:
                    # Отправляем JSON-ответ с сообщением об ошибке
                    self._handle_error(400, "Недостаточно данных для добавления траты!")
                    return

                # Если все данные присутствуют, добавляем трату через tracker с проверкой на валидацию
                msg = tracker.add_expense(name, category, amount, date)
                logger.info(f"Expense added: {msg}")

                if msg.startswith("Ошибка:"):
                    # Валидация не прошла — отдаем 400 Bad Request
                    self._send_json_response({
                        "error": "Bad Request",
                        "message": msg
                    }, 400)
                else:
                    self._send_json_response({"message": msg}, 200)

            else:
                # Если POST-запрос на неизвестный путь, возвращаем 404 Not Found
                self._send_json_response({
                    "error": "Not Found",
                    "message": f"Метод '{path}' не найден"
                }, 404)

        except Exception as e:
            logger.exception("Unexpected error in POST handler")
            self._send_json_response({
                "error": "Internal Server Error",
                "message": str(e)
            }, 500)
    
    def do_GET(self): # noqa: N802
        """
        Обработка GET-запросов.
        Поддерживаются следующие пути:
         - /top_category?month=<месяц с нулем или без> — возвращает категорию с максимальной тратой за месяц
         - /max_expense?month=<месяц с нулем или без>&category=... — возвращает максимальную трату в категории за месяц
         - /full_records — возвращает все записи о тратах
        """

        try:

            parsed_url = urlparse(self.path)
            path = parsed_url.path
            params = parse_qs(parsed_url.query) # Разбираем параметры запроса в словарь: ключ -> список значений
            
            # Записываем дебаг лог о плученном запросе
            logger.debug(f"GET request: {path} with params {params}")

            if path == "/top_category":
                # Получаем параметр month (если нет, пустая строка)
                month = params.get("month", [""])[0]
                # Получаем категорию с максимальной тратой в этом месяце
                top = tracker.get_top_category(month)

                if not top:
                    self._handle_error(404, f"В месяце '{month}' не найдено категорий")
                    return
                
                self._set_headers()
                response = {f"Категория с максимальной тратой в месяце {month}": top}
                self.wfile.write(json.dumps(response).encode('utf-8'))

            elif path == "/max_expense":
                # Получаем параметры month и category
                month = params.get("month", [""])[0]
                category = params.get("category", [""])[0]
                # Получаем максимальную трату по данным параметрам
                exp = tracker.get_max_expense(month, category)

                if not exp:
                    self._handle_error(404, f"В месяце '{month}' и категории '{category}' трат не найдено")
                    return

                self._set_headers()
                response = {f"Максимальная трата в месяце '{month}' и категории '{category}'": exp['name']}
                self.wfile.write(json.dumps(response).encode('utf-8'))

            elif path == "/full_records":
                # Получаем все записи о тратах
                expenses = tracker.get_full_records()

                # Если записей нет, то Not Found 404 с сообщением
                if not expenses:
                    self._handle_error(404, "Записей о тратах не найдено")
                    return
                
                self._set_headers()
                # Используем bson.json_util.dumps — сериализация, поддерживающая BSON-объекты из MongoDB
                self.wfile.write(dumps(expenses).encode('utf-8'))
                
            else:
                # Для всех других путей возвращаем 404 Not Found с сообщением
                self._handle_error(404, f"Метод '{path}' не найден")

        except Exception as e:
            logger.exception("Unexpected error in GET handler")
            self._handle_error(500, "Внутренняя ошибка сервера")


def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    """
    Функция запуска HTTP-сервера на указанном порту (по умолчанию 8080).
    Создаёт экземпляр сервера, передавая ему обработчик запросов,
    и запускает обработку запросов в бесконечном цикле.
    """
    server_address = ('', port) # '' - означает слушать на всех сетевых интерфейсах
    httpd = server_class(server_address, handler_class)
    logger.info(f"HTTP-сервер запущен на порту {port}")
    httpd.serve_forever() # Запускает бесконечный цикл обработки входящих запросов

if __name__ == '__main__':
    client_module = tracker.client.__class__.__module__
    if not client_module.startswith('mongomock'):
        try:
            tracker.client.admin.command('ping')
            logger.info("Соединение с MongoDB установлено успешно.")
        except Exception as e:
            logger.exception("Не удалось подключиться к MongoDB!")

    else:
        logger.info("Обнаружен mongomock — проверка подключения к MongoDB пропущена.")

    # Если скрипт запускается как основная программа, стартуем сервер
    run()
