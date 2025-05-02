# класс траты с названием и суммой траты
class Expense:

    def __init__(self, name: str, amount: float):
        self.name = name
        self.amount = amount


# класс категории с названием категории и массивом сумм трат категории
class Category:

    def __init__(self, name: str):
        self.name = name
        self.expenses = [[], [], [], [], [], [], [], [], [], [], [], []]

    # добавляет дату в ячейку соответсующего месяца
    def add_expense(self, name: str, amount: float, month: int):
        if 1 <= month <= 12:
            self.expenses[month - 1].append(Expense(name, amount))
        else:
            print("Пожалуйста, введите корректную дату")

    # считает масячные затраты
    def calculate_expenses(self, month: int):
        if 1 <= month <= 12:
            balance = sum(expense.amount for expense in self.expenses[month - 1])
            return balance
        else:
            print("Пожалуйста, введите корректную дату")

    # ищет самую большую трату за месяц
    def find_largest_expense(self, month: int):
        if 1 <= month <= 12:
            largest_expense = max(expense.amount for expense in self.expenses[month - 1])
            return largest_expense
        else:
            print("Пожалуйста, введите корректную дату")


# класс трекера трат
class ExpenseTracker:

    def __init__(self):
        self.categories = []

    # добавляет уникальную категорию
    def add_category(self, category_name: str):
        for category in self.categories:
            if category_name.lower() == category.name.lower():
                return category

        new_category = Category(category_name)
        self.categories.append(new_category)
        return new_category

    # добавляет трату в категорию
    def add_expense(self, category: Category, name: str, amount: float, month: int):
        category.add_expense(name, amount, month)

    # показывает категорию, на которую пришлось больше всего трат за указанный месяц
    def view_most_expensive_category(self, month: int):
        most_expensive_category = max(
            self.categories,
            key=lambda i: i.calculate_expenses(month),
            default=None
        )
        if most_expensive_category:
            most_expensive_category_balance = most_expensive_category.calculate_expenses(month) or 0
        else:
            most_expensive_category_balance = 0

        if most_expensive_category_balance == 0:
            print("В этом месяце не было трат")
        else:
            print(
                f"На категорию '{most_expensive_category.name}' пришлось больше всего трат за {month} месяц, а именно {most_expensive_category_balance}р.")
        return most_expensive_category.name

    # показывает самую крупную трату за указанный месяц и в указанной категории
    def view_largest_expense(self, category_name, month):
        largest_expense = 0
        for category in self.categories:
            if (category.name.lower() == category_name.lower()):
                largest_expense = category.find_largest_expense(month)

        if largest_expense == 0:
            print("В этой категории не было трат")
        else:
            print(f"Самая крупная трата за {month} месяц в категории '{category_name}' составила {largest_expense}р.")
        return largest_expense
