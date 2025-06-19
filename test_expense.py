import mongomock
from expenses import Expense, ExpenseTracker

# ----- Тесты класса Expense ------

def test_expense_name_and_category_capitalize():
    """
    Проверяем, что при создании объекта Expense
    поля name и category автоматически преобразуются к требуемому формату.
    Например, 'молоко' -> 'Молоко', 'еда' -> 'Еда'
    """
    exp = Expense('молоко', 'еда', 100, '02.05')
    assert exp.name == 'Молоко'
    assert exp.category == 'Еда'

def test_expense_get_month():
    """
    Проверяем, что метод get_month() корректно выделяет месяц из даты формата 'дд.мм'
    """
    exp = Expense('молоко', 'еда', 100, '02.05')
    assert exp.get_month() == '05'

def test_expense_match_category_case_insensitive():
    """
    Тестируем, что метод match_category() сравнивает категории без учёта регистра,
    корректно сопоставляя 'еДа' с 'еда', 'Еда', 'ЕДА' и не сопоставляя с неправильными значениями.
    """
    exp = Expense('молоко', 'еДа', 100, '02.05')
    assert exp.match_category('еда')
    assert exp.match_category('Еда')
    assert exp.match_category('ЕДА')
    assert not exp.match_category('Еда1')


# ----- Тесты класса ExpenseTracker -----
def make_tracker():
    """
    Утилита для создания нового экземпляра ExpenseTracker с моковой базой mongomock.
    Возвращает также объект клиент базы, чтобы можно было проверять содержимое.
    Для изоляции данных между тестами.
    """
    mock_client = mongomock.MongoClient()
    return ExpenseTracker(db_client=mock_client), mock_client

def test_add_expense_success():
    """
    Проверяем успешное добавление корректной траты.
    Проверяем сообщение об успешном добавлении,
    а также что запись реально появилась в базе с нужными данными.
    """
    tracker, mock_client = make_tracker()
    # вызываем метод добавления траты в базу (в данном случае это будет мок-клиент)
    msg = tracker.add_expense('молоко', 'еда', 100, '02.05')

    assert "Трата 'Молоко' добавлена" in msg
    # Проверяем, что запись действительно добавлена в коллекцию
    assert mock_client['expenses_db']['expenses'].count_documents({}) == 1
    # Извлекаем и проверяем сам документ
    expense = mock_client['expenses_db']['expenses'].find_one({'name': 'Молоко'})
    assert expense['category'] == 'Еда'
    assert expense['amount'] == 100
    assert expense['date'] == '02.05'

def test_add_expense_missing_field_name():
    """
    Проверяем, что при отсутствии поля 'name' метод add_expense сообщает об ошибке,
    и в базу ничего не добавляет.
    """
    tracker, mock_client = make_tracker()
    msg = tracker.add_expense('', 'еда', 100, '02.05')
    assert "не заполнены все необходимые поля" in msg
    assert mock_client['expenses_db']['expenses'].count_documents({}) == 0

def test_add_expense_missing_field_category():
    """
    Проверяем поведение при отсутствии категории.
    Метод должен вернуть сообщение об ошибке.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', '', 100, '02.05')
    assert "не заполнены все необходимые поля" in msg

def test_add_expense_missing_field_amount():
    """
    Проверяем поведение при отсутствии суммы (None).
    Метод должен вернуть сообщение об ошибке.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', None, '02.05')
    assert "не заполнены все необходимые поля" in msg

def test_add_expense_missing_field_date():
    """
    Проверяем поведение при отсутствии даты.
    Метод должен вернуть сообщение об ошибке.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 100, None)
    assert "не заполнены все необходимые поля" in msg

def test_add_expense_amount_zero():
    """
    Проверяем, что сумма 0 за трату не принимается и метод выдаёт ошибку.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 0, '02.05')
    assert "сумма должна быть положительным числом" in msg

def test_add_expense_amount_negative():
    """
    Проверяем, что сумма ниже 0 должна вызвать ошибку.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', -50, '02.05')
    assert "сумма должна быть положительным числом" in msg

def test_add_expense_amount_not_number():
    """
    Проверка на некорректный тип суммы (не число),
    метод должен возвращать ошибку.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 'abc', '02.05')
    assert "сумма должна быть числом" in msg

def test_add_expense_invalid_date_format_dot_missing():
    """
    Проверяем формат даты: если отсутствует точка-разделитель — должна возвращаться ошибка.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 100, '02-05')
    assert "неверный формат даты" in msg

def test_add_expense_invalid_date_day_out_of_range():
    """
    Проверяем, что день больше 31 недопустим, метод возвращает ошибку.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 100, '32.05')
    assert "некорректные значения дня или месяца" in msg

def test_add_expense_invalid_date_month_out_of_range():
    """
    Проверяем, что месяц за пределами 1-12 недопустим.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 100, '02.13')
    assert "некорректные значения дня или месяца" in msg

def test_add_expense_invalid_date_not_integers():
    """
    Проверяем, что в дате должны быть числа, иначе ошибка.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молоко', 'еда', 100, 'день.месяц')
    assert "неверный формат даты" in msg

def test_category_and_name_capitalized_on_add():
    """
    Проверяем, что при добавлении траты имя и категория приводятся к виду с заглавной буквы.
    """
    tracker, _ = make_tracker()
    msg = tracker.add_expense('молокО', 'едА', 100, '02.05')
    assert "'Молоко'" in msg
    assert "'Еда'" in msg

def test_get_top_category_one():
    """
    Проверяем, что если добавить одну трату в одном месяце,
    метод get_top_category возвращает её категорию.
    """
    tracker, _ = make_tracker()
    tracker.add_expense('молоко', 'еда', 100, '10.05')
    assert tracker.get_top_category('05') == 'Еда'

def test_get_top_category_multiple():
    """
    Проверяем корректный подсчёт категории с максимальными расходами,
    когда трат нескольких категорий суммируются в одном месяце.
    Пример: категория "Еда" - 100+150=250, "Авто" - 200.
    Ожидаем вернуть "Еда".
    """
    tracker, _ = make_tracker()
    tracker.add_expense('молоко', 'еда', 100, '10.05')
    tracker.add_expense('бензин', 'авто', 200, '21.05')
    tracker.add_expense('бензин', 'авто', 200, '21.06')
    tracker.add_expense('соки', 'еда', 150, '15.05')
    top = tracker.get_top_category('05')
    assert top == 'Еда'  # 100+150=250 vs 200

def test_get_top_category_none():
    """
    Проверяем, что если за указанный месяц нет трат,
    метод get_top_category возвращает None.
    """
    tracker, _ = make_tracker()
    assert tracker.get_top_category('08') is None

def test_get_top_category_month_with_leading_zero():
    """
    Проверяем, что метод корректно работает, если месяц передан без ведущего нуля
    """
    tracker, _ = make_tracker()
    tracker.add_expense('молоко', 'еда', 50, '10.05')
    tracker.add_expense('бензин', 'авто', 60, '21.5')
    cat = tracker.get_top_category('5')
    assert cat == 'Авто'

def test_get_max_expense_category_case_insensitive():
    """
    Проверяем, что метод get_max_expense корректно учитывает регистр категории при поиске.
    """
    tracker, _ = make_tracker()
    tracker.add_expense('молоко', 'еда', 80, '01.05')
    tracker.add_expense('соки', 'еда', 110, '05.05')
    exp = tracker.get_max_expense('05', 'ЕДА')
    assert exp['name'] == 'Соки'
    assert exp['amount'] == 110

def test_get_max_expense_month_with_leading_zero_and_no_zero():
    """
    Проверяем, что метод get_max_expense работает с месяцем,
    переданным в формате с ведущим или без ведущего нуля.
    """
    tracker, _ = make_tracker()
    tracker.add_expense('рис', 'еда', 120, '02.4')
    tracker.add_expense('макароны', 'еда', 250, '15.04')
    exp = tracker.get_max_expense('04', 'еда')
    assert exp['name'] == 'Макароны'
    exp2 = tracker.get_max_expense('4', 'еда')
    assert exp2['name'] == 'Макароны'

def test_get_max_expense_none():
    """
    Проверяем, что если в заданном месяце и категории нет расходов,
    метод get_max_expense возвращает None.
    """
    tracker, _ = make_tracker()
    tracker.add_expense('соки', 'еда', 110, '05.06')
    assert tracker.get_max_expense('05', 'еда') is None
    assert tracker.get_max_expense('06', 'авто') is None

def test_get_max_expense_several_expenses():
    """
    Проверяем, что из нескольких трат в категории выбирается с максимальной суммой траты.
    """
    tracker, _ = make_tracker()
    tracker.add_expense('апельсин', 'фрукты', 100, '12.05')
    tracker.add_expense('банан', 'фрукты', 70, '14.05')
    tracker.add_expense('ананас', 'фрукты', 120, '25.05')
    tracker.add_expense('автомобиль', 'авто', 1200, '25.05')
    exp = tracker.get_max_expense('05', 'фрукты')
    assert exp['name'] == 'Ананас'

def test_get_full_records():
    """
    Проверяем, что метод get_full_records возвращает все записи о тратах,
    сохранённые в базе.
    Проверяем, что все добавленные в тесте записи присутствуют в результате.
    """
    tracker, mock_client = make_tracker()
    tracker.add_expense('апельсин', 'фрукты', 100, '12.05')
    tracker.add_expense('банан', 'фрукты', 70, '14.05')
    tracker.add_expense('ананас', 'фрукты', 120, '25.05')
    tracker.add_expense('автомобиль', 'авто', 1200, '25.05')
    # Ожидаем, что get_full_records возвращает список документов из коллекции
    records = tracker.get_full_records()
    # Можно проверить, что все вставленные траты есть в результатах
    names = {record['name'] for record in records}
    assert {'Апельсин', 'Банан', 'Ананас', 'Автомобиль'}.issubset(names)
