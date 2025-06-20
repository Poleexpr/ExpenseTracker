import re

# logic
# Класс, описывающий отдельную трату
class Expense:
    def __init__(self, name, category, amount, date):
        # Преобразуем первый символ строки в верхний регистр, а все остальные — в нижний регистр
        self.name = name.capitalize()
        self.category = category.capitalize()
        self.amount = amount # сумма траты (число)
        self.date = date  # строка вида "день.месяц"

    def get_month(self):
        """
        Возвращает часть даты в виде месяца.
        """
        return self.date.split(".")[1]

    def match_category(self, cat):
        """
        Проверяет, совпадает ли категория траты с заданной.
        Сравнивает в нижнем регистре, чтобы игнорировать регистр.
        """
        return self.category.lower() == cat.lower()

    def as_dict(self):
        """
        Возвращает словарь с полями объекта для сохранения в БД Mongo
        """
        return {
            "name": self.name,
            "category": self.category,
            "amount": self.amount,
            "date": self.date
        }

class ExpenseTracker:
    def __init__(self, db_client=None):
        """
        Инициализация ExpenseTracker — интерфейса для работы с MongoDB.
        Если передан соответствующий db_client (mongomock.MongoClient для тестов),
        то он используется для подключения,
        иначе — создаём реальное подключение к MongoDB.
        """
        if db_client is not None:
            self.client = db_client
        else:
            # Подключение к настоящей MongoDB
            from pymongo import MongoClient
            self.client = MongoClient('mongodb://localhost:27017/') # здесь нужно подставить актуальный адрес Mongo
        # Используем/создаём БД и коллекцию
        self.db = self.client['expenses_db'] # self.db: используемая база данных "expenses_db"
        self.collection = self.db['expenses'] # self.collection: коллекция "expenses", где хранятся документы трат

    def add_expense(self, name, category, amount, date):
        """
        Добавляет новую трату в базу данных (MongoDB).
        Проверяет корректность данных и формат даты.

        Проверки:
          - Все поля должны быть обязательно заполнены
          - Сумма должна быть числом и больше 0
          - Дата должна соответствовать формату "день.месяц"
            с адекватным диапазоном значений дня и месяца
        Если проверки не прошли — возвращает текст с ошибкой.

        Если всё хорошо — добавляет в коллекцию документ и возвращает сообщение об успешной вставке.
        """
        # Проверка наличия всех обязательных данных
        if not (name and category and amount is not None and date):
            return "Ошибка: не заполнены все необходимые поля."

        # Сумма должна быть положительным числом
        try:
            amount = float(amount)
            if amount <= 0:
                return "Ошибка: сумма должна быть положительным числом."
        except ValueError:
            return "Ошибка: сумма должна быть числом."

        # Проверка формата даты
        if not re.fullmatch(r'^\d{1,2}\.\d{1,2}$', date):
            return "Ошибка: неверный формат даты. Ожидался <день.месяц>"
    
        try:
            day, month = date.split(".")
            day = int(day)
            month = int(month)
            # Проверка корректности дня и месяца с учётом месяцев:
            if not ((1 <= day <= 31 and month in [1, 3, 5, 7, 8, 10, 12]) or \
                    (1 <= day <= 31 and month in [4, 6, 9, 11]) or (1 <= day <= 29 and month == 2)):
                return "Ошибка: некорректные значения дня или месяца."
            date = f"{day:02d}.{month:02d}"  # день и месяц с двумя цифрами
        except ValueError:
            return "Ошибка: неверный формат даты. Ожидался <день.месяц>"

        # Форматирование данных для стандарта
        name = name.capitalize()
        category = category.capitalize()

        expense = Expense(name, category, amount, date)

        # Вставляем документ в MongoDB
        self.collection.insert_one(expense.as_dict())

        return f"Трата '{expense.name}' добавлена в категорию '{expense.category}' на "+\
        f"сумму {expense.amount} за {expense.date}."

    def get_full_records(self):
        """
        Возвращает полный список всех затрат из коллекции.
        Поиск документов без фильтра.
        """
        return list(self.collection.find({}))

    def get_top_category(self, month):
        """
        Находит категорию с максимальной суммарной тратой за указанный месяц.

        Формирование pipeline для MongoDB:

        1) $match:
           Фильтруем документы по полю "date", чтобы месяц в дате совпадал с заданным.
           Используется регулярное выражение для проверки формата "dd.mm",
           где "mm" — переданный месяц (с ведущим нулём, например '07').

        2) $group:
           Группируем документы по категории ("category").
           Считаем сумму "amount" для каждой категории (поле "total").

        3) $sort:
           Сортируем категории по убыванию суммы "total" — чтобы самая большая была первой.

        4) $limit:
           Ограничиваем результат одним элементом — самой "тяжёлой" категорией.

        После выполнения агрегирования возвращаем категорию или None, если нет данных.
        """
        # Делаем так, чтобы месяц был в формате 2 символов
        month = month.zfill(2)
        pipeline = [
            {
                # В фильтре применяем регулярное выражение для подбора даты с нужным месяцем.
                # ^\d{2}\. означает: два любых символа (число дня), точка, затем месяц
                "$match": {
                    "date": { "$regex": r"^\d{1,2}\." + month + r"$" }
                }
            },
            {
                # Группируем по категории, суммируя значения amount
                "$group": {
                    "_id": "$category", # сгруппировать по категории
                    "total": { "$sum": "$amount" } # суммируем поле amount в total
                }
            },
            # Сортируем по total в порядке убывания
            { "$sort": { "total": -1 } },
            # Берём только первый результат — категорию с максимальной тратой
            { "$limit": 1 }
        ]

        # Выполнение агрегации в MongoDB
        result = list(self.collection.aggregate(pipeline))
        if not result: # если ничего не найдено — возвращаем None
            return None
        return result[0]['_id'] # Возвращаем название категории

    def get_max_expense(self, month, category):
        """
        Находит максимальную по сумме трату в указанном месяце и категории.

        Формируем запрос (query) с фильтрацией по категории и дате

        Выполняем запрос find_one с сортировкой по убыванию поля "amount",
        чтобы получить максимальную по сумме трату.

        Если документ найден — возвращаем его (без поля _id).
        Если нет — возвращаем None.
        """
        # Приводим параметры к единому формату
        month = month.zfill(2)
        category = category.capitalize()
        # Выполняем запрос с условиями
        query = {
            "category": category,
            "date": { "$regex": r"^\d{1,2}\." + month + r"$" }
        }
        # Ищем один документ, сортируя по amount в порядке убывания
        expense = self.collection.find_one(
            query,
            sort=[("amount", -1)]
        )
        if not expense:
            return None
        # Удаляем поле _id для удобства
        if '_id' in expense:
            del expense['_id']
        # Возвращаем словарь с данными траты
        return expense
