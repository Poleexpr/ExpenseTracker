import json
# noinspection PyUnresolvedReferences
from bson.json_util import dumps
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from expenses import ExpenseTracker

# Инициализация объекта ExpenseTracker, который хранит и обрабатывает данные о тратах
tracker = ExpenseTracker()

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
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

    def do_POST(self): # noqa: N802
        """
        Обработка POST-запросов.
        В проекте поддерживается путь /add_expense, который позволяет добавить новую трату.
        """
        parsed_url = urlparse(self.path) # Выполняем парсинг пути
        path = parsed_url.path # Получаем путь запроса
        if path == "/add_expense":
            # Получаем длину тела запроса из заголовков
            content_length = int(self.headers.get('Content-Length', 0))
            # Читаем тело запроса (байты), декодируем из utf-8 в строку
            body = self.rfile.read(content_length).decode('utf-8')
            # Парсим JSON из строки в словарь, если тело не пустое
            data = json.loads(body) if body else {}
            # Извлекаем необходимые параметры для добавления траты
            name = data.get('name')
            category = data.get('category')
            amount = data.get('amount')
            date = data.get('date')

            # Проверяем, что все поля заполнены - если нет, возвращаем 400 Bad Request
            if not name or not category or not amount or not date:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                # Отправляем JSON-ответ с сообщением об ошибке
                self.wfile.write(json.dumps({
                    "error": "Bad Request",
                    "message": "Недостаточно данных для добавления траты в базу данных!"
                }).encode('utf-8'))
                return
            # Если все данные присутствуют, добавляем трату через tracker
            msg = tracker.add_expense(name, category, amount, date)
            # Устанавливаем стандартные заголовки с кодом 200 OK
            self._set_headers()
            # Отправляем сообщение об успешном добавлении
            self.wfile.write(json.dumps({"message": msg}).encode('utf-8'))
        else:
            # Если POST-запрос на неизвестный путь, возвращаем 404 Not Found
            self._set_headers(404)
            self.wfile.write(json.dumps({
                "error": "Not Found",
                "message": f"На сервере не обнаружено запрашиваемого метода '{path}'."
            }).encode('utf-8'))

    def do_GET(self): # noqa: N802
        """
        Обработка GET-запросов.
        Поддерживаются следующие пути:
         - /top_category?month=<месяц с нулем или без> — возвращает категорию с максимальной тратой за месяц
         - /max_expense?month=<месяц с нулем или без>&category=... — возвращает максимальную трату в категории за месяц
         - /full_records — возвращает все записи о тратах
        """
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        params = parse_qs(parsed_url.query) # Разбираем параметры запроса в словарь: ключ -> список значений
        if path == "/top_category":
            # Получаем параметр month (если нет, пустая строка)
            month = params.get("month", [""])[0]
            # Получаем категорию с максимальной тратой в этом месяце
            top = tracker.get_top_category(month)
            if top:
                self._set_headers()
                self.wfile.write(json.dumps({
                    f"Категория с максимальной тратой в месяце {month}": top
                }).encode('utf-8'))
            else:
                # Если данных нет - 404 Not Found с сообщением
                self._set_headers(404)
                response = {
                    "error": "Not Found",
                    "message": f"В месяце '{month}' не найдено ни одной категории с тратами!"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
        elif path == "/max_expense":
            # Получаем параметры month и category
            month = params.get("month", [""])[0]
            category = params.get("category", [""])[0]
            # Получаем максимальную трату по данным параметрам
            exp = tracker.get_max_expense(month, category)
            if exp:
                self._set_headers()
                response = {f"Максимальная трата в месяце '{month}' и категории '{category}'": exp['name']}
            else:
                self._set_headers(404)
                response = {
                    "error": "Not Found",
                    "message": f"В месяце '{month}' и категории '{category}' трат не найдено!"
                }
            # Отправляем JSON-ответ с результатом или ошибкой
            self.wfile.write(json.dumps(response).encode('utf-8'))
        elif path == "/full_records":
            # Получаем все записи о тратах
            expenses = tracker.get_full_records()
            if expenses:
                self._set_headers()
                # Используем bson.json_util.dumps — сериализация, поддерживающая BSON-объекты из MongoDB
                self.wfile.write(dumps(expenses).encode('utf-8'))
            else:
                # Если записей нет, то Not Found 404 с сообщением
                self._set_headers(404)
                response = {
                    "error": "Not Found",
                    "message": "Записей о тратах не найдено!"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            # Для всех других путей возвращаем 404 Not Found с сообщением
            self._set_headers(404)
            self.wfile.write(json.dumps({
                "error": "Not Found",
                "message": f"На сервере не обнаружено запрашиваемого метода '{path}'."
            }).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    """
    Функция запуска HTTP-сервера на указанном порту (по умолчанию 8080).
    Создаёт экземпляр сервера, передавая ему обработчик запросов,
    и запускает обработку запросов в бесконечном цикле.
    """
    server_address = ('', port) # '' - означает слушать на всех сетевых интерфейсах
    httpd = server_class(server_address, handler_class)
    print(f'HTTP-сервер запущен на порту {port}')
    httpd.serve_forever() # Запускает бесконечный цикл обработки входящих запросов

if __name__ == '__main__':
    # Если скрипт запускается как основная программа, стартуем сервер
    run()
