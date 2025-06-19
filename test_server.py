import threading
import time
import requests
import pytest
import mongomock
from http.server import HTTPServer

import http_server  # импорт сервера
from expenses import ExpenseTracker

@pytest.fixture(scope='function')
def mock_tracker(monkeypatch):
    """
    Фикстура создаёт моковую версию ExpenseTracker с базой данных в памяти (mongomock),
    и подменяет глобальный объект tracker в модуле http_server на моковый.

    scope='function' - фикстура создаётся заново для каждого теста,
    чтобы данные не пересекались между тестами.
    """
    # создаём mongomock клиент без подключений к реальной БД
    client = mongomock.MongoClient()
    # Создаём объект ExpenseTracker, указывая ему использовать моковый клиент
    tracker = ExpenseTracker(db_client=client)
    # Подменяем глобальный tracker в http_server на моковый, чтобы сервер работал с имитацией БД
    monkeypatch.setattr(http_server, 'tracker', tracker)
    # Возвращаем трекер, если понадобится в тестах напрямую
    return tracker

@pytest.fixture(scope='function')
def start_test_server(mock_tracker):
    """
    Фикстура запускает HTTP-сервер в отдельном потоке для тестов.
    Использует моковый tracker из фикстуры mock_tracker.

    По окончании теста корректно останавливает сервер.
    """
    port = 8081  # порт для тестов
    server_address = ('', port)
    httpd = HTTPServer(server_address, http_server.SimpleHTTPRequestHandler)
    # Запускаем сервер в отдельном демоническом потоке — чтобы не блокировать основной поток
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)  # дать серверу стартануть
    yield f'http://localhost:{port}'
    # После завершения теста выключаем сервер и ждем завершения потока
    httpd.shutdown()
    thread.join()

def test_add_expense_api_success(start_test_server):
    """
    Тест проверяет успешное добавление траты через POST /add_expense.
    Отправляем корректные данные и проверяем, что сервер ответил 200 OK и сообщает об успешном добавлении.
    """
    url = start_test_server + '/add_expense'
    data = {
        "name": "яблоко",
        "category": "фрукты",
        "amount": 120,
        "date": "10.06"
    }
    response = requests.post(url, json=data)
    assert response.status_code == 200
    json_data = response.json()
    assert "Трата 'Яблоко' добавлена" in json_data.get('message', '')

def test_add_expense_api_missing_fields(start_test_server):
    """
    Тест проверяет поведение сервера при отсутствии необходимых данных в POST /add_expense.
    Отправляем запрос с пустым именем, ожидаем ошибку 400 Bad Request с соответствующим сообщением.
    """
    url = start_test_server + '/add_expense'
    data = {
        "name": "",
        "category": "фрукты",
        "amount": 120,
        "date": "10.06"
    }
    response = requests.post(url, json=data)
    assert response.status_code == 400
    json_data = response.json()
    assert "Недостаточно данных" in json_data.get('message', '')

def test_get_top_category_api(start_test_server):
    """
    Тест проверяет GET запрос /top_category?month=06.
    Проверяем, что сервер вернул код 200 при наличии данных или 404 если данных нет.
    """
    url = start_test_server + '/top_category?month=06'
    response = requests.get(url)
    assert response.status_code in (200, 404)

def test_get_max_expense_api(start_test_server):
    """
    Тест проверяет GET запрос /max_expense?month=06&category=фрукты.
    Проверяем, что сервер вернул корректный статус (200 при наличии данных, либо 404 если данных нет).
    """
    url = start_test_server + '/max_expense?month=06&category=фрукты'
    response = requests.get(url)
    assert response.status_code in (200, 404)

def test_full_records_api(start_test_server):
    """
    Тест проверяет GET /full_records - весь список расходов.
    Проверяем, что сервер возвращает либо 200 OK с данными, либо 404 если записей нет.
    """
    url = start_test_server + '/full_records'
    response = requests.get(url)
    assert response.status_code in (200, 404)

def test_404_api(start_test_server):
    """
    Тест проверяет корректность обработки запроса к несуществующему GET-эндпоинту.
    Ожидаем статус 404, а тело ответа содержит сообщение об ошибке.
    """
    url = start_test_server + '/non_existing_endpoint'
    response = requests.get(url)
    assert response.status_code == 404
    json_data = response.json()
    assert "На сервере не обнаружено" in json_data.get('message', '')

def test_post_to_unknown_path_returns_404(start_test_server):
    """
    Тест проверяет, что POST-запрос к неизвестному пути возвращает 404 Not Found.
    Проверяем статус код и содержание JSON-ответа с описанием ошибки.
    """
    url = start_test_server + '/unknown_path'
    response = requests.post(url, json={"dummy": "data"})
    assert response.status_code == 404
    data = response.json()
    assert data.get("error") == "Not Found"
    assert "не обнаружено запрашиваемого метода" in data.get("message", "").lower()
    assert "unknown_path" in data.get("message", "")
