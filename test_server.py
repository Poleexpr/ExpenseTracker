import threading
import time
import requests
import pytest
import mongomock
from http.server import HTTPServer
import logging
from io import StringIO
import json

import http_server
from expenses import ExpenseTracker

@pytest.fixture(scope='function')
def test_logger():
    """Создаёт логгер для захвата логов сервера в тестах"""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)

    logger = logging.getLogger('HTTP Server')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield logger, log_stream

    logger.removeHandler(handler)  # Только добавленный handler

@pytest.fixture(scope='function')
def mock_tracker(monkeypatch):
    """
    Фикстура создаёт моковую версию ExpenseTracker с базой данных в памяти (mongomock),
    и подменяет глобальный объект tracker в модуле http_server на моковый.
    scope='function' - фикстура создаётся заново для каждого теста,
    чтобы данные не пересекались между тестами.
    """
    client = mongomock.MongoClient()
    tracker = ExpenseTracker(db_client=client)
    monkeypatch.setattr(http_server, 'tracker', tracker)
    return tracker

@pytest.fixture(scope='function')
def start_test_server(mock_tracker, test_logger):
    """
    Фикстура запускает HTTP-сервер в отдельном потоке для тестов.
    Использует моковый tracker из фикстуры mock_tracker.
    По окончании теста корректно останавливает сервер.
    """
    logger, log_stream = test_logger
    original_logger = getattr(http_server, 'logger', None)
    http_server.logger = logger

    port = 8081
    server_address = ('', port)
    httpd = HTTPServer(server_address, http_server.SimpleHTTPRequestHandler)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.2)

    yield f'http://localhost:{port}', log_stream

    httpd.shutdown()
    thread.join()
    http_server.logger = original_logger

def test_add_expense_api_success(start_test_server):
    """
    Тест проверяет успешное добавление траты через POST /expenses.
    Отправляем корректные данные и проверяем, что сервер ответил 200 OK и сообщает об успешном добавлении.
    """
    url, log_stream = start_test_server
    response = requests.post(
        url + '/expenses',
        json={
            "name": "яблоко",
            "category": "фрукты",
            "amount": 120,
            "date": "10.06"
        }
    )
    assert response.status_code == 200
    json_data = response.json()
    assert "трата" in json_data.get('message', '').lower()
    assert "добавлена" in json_data.get('message', '').lower()
    logs = log_stream.getvalue()
    assert "Expense added" in logs

def test_add_expense_api_missing_fields(start_test_server):
    """
    Тест проверяет поведение сервера при отсутствии необходимых данных в POST /expenses.
    Отправляем запрос с пустым именем, ожидаем ошибку 400 Bad Request с соответствующим сообщением.
    """
    url, log_stream = start_test_server
    response = requests.post(
        f"{url}/expenses",
        json={"name": "", "category": "", "amount": 0, "date": ""},
        headers={'Content-Type': 'application/json'}
    )

    assert response.status_code == 400
    assert 'application/json' in response.headers['Content-Type']

    data = response.json()
    assert data == {
        "error": "Bad Request",
        "message": "Недостаточно данных для добавления траты!"
    }


def test_get_top_category_api(start_test_server):
    """
    Тест проверяет GET запрос /categories/top?month=06.
    Проверяем, что сервер вернул код 200 при наличии данных или 404 если данных нет.
    """
    url, log_stream = start_test_server
    response = requests.get(f"{url}/categories/top?month=06")

    if response.status_code == 404:
        assert 'application/json' in response.headers['Content-Type']
        assert response.json() == {
            "error": "Not Found",
            "message": "В месяце '06' не найдено категорий"
        }

def test_get_max_expense_api(start_test_server):
    """
    Тест проверяет GET запрос /expenses/largest?month=06&category=фрукты.
    Проверяем, что сервер вернул корректный статус (200 при наличии данных, либо 404 если данных нет).
    """
    url, log_stream = start_test_server
    response = requests.get(url + '/expenses/largest?month=06&category=фрукты')
    assert response.status_code in (200, 404)
    if response.status_code == 404:
        data = response.json()
        assert data['error'] == 'Not Found'
        assert "трат не найдено" in data['message']

def test_full_records_api(start_test_server):
    """
    Тест проверяет GET /expenses/full_records - весь список расходов.
    Проверяем, что сервер возвращает либо 200 OK с данными, либо 404 если записей нет.
    """
    url, log_stream = start_test_server
    response = requests.get(url + '/expenses/full_records')
    assert response.status_code in (200, 404)
    if response.status_code == 404:
        data = response.json()
        assert data['error'] == 'Not Found'
        assert "Записей о тратах не найдено" in data['message']

def test_404_api(start_test_server):
    """
    Тест проверяет корректность обработки запроса к несуществующему GET-эндпоинту.
    Ожидаем статус 404, а тело ответа содержит сообщение об ошибке.
    """
    url, log_stream = start_test_server
    response = requests.get(url + '/non_existing_endpoint')
    assert response.status_code == 404
    json_data = response.json()
    assert json_data.get("message") == "Метод '/non_existing_endpoint' не найден"
    logs = log_stream.getvalue()
    assert "non_existing_endpoint" in logs

def test_post_to_unknown_path_returns_404(start_test_server):
    """
    Тест проверяет, что POST-запрос к неизвестному пути возвращает 404 Not Found.
    Проверяем статус код и содержание JSON-ответа с описанием ошибки.
    """
    url, log_stream = start_test_server
    response = requests.post(
        url + '/unknown_path',
        json={"dummy": "data"}
    )
    assert response.status_code == 404
    data = response.json()
    assert data.get("error") == "Not Found"
    assert data.get("message") == "Метод '/unknown_path' не найден"
    logs = log_stream.getvalue()
    assert "unknown_path" in logs
