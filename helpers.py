# демонстирирует добавление траты
def add_expenses_demo(expense_tracker):
    while True:
        category_name = input("Введите категорию или 'продолжить' ").strip()
        if category_name.lower() == "продолжить" or category_name.lower() == "":
            break

        category = expense_tracker.add_category(category_name)

        expense_name = input("Введите наименование траты: ").strip()

        while True:
            try:
                amount = float(input("Введите сумму: "))
                break
            except ValueError:
                print("Пожалуйста, введите корректную сумму")

        while True:
            date = input("Введите дату в числовом формате «день.месяц», например «10.9»").strip()
            try:
                day, month = map(int, date.split('.'))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    break
            except ValueError:
                print("Пожалуйста, введите корректную дату")

        expense_tracker.add_expense(category, expense_name, amount, month)
        print(f"Добавлено: {amount}р в категорию '{category_name}'")


def view_largest_expenses_demo(expense_tracker):
    while True:
        category_name = input(
            "Введите категорию, чтобы посмотреть самую крупную трату, или введите 'продолжить' ").strip()
        if category_name.lower() == "продолжить" or category_name.lower() == "":
            break

        while True:
            month = input("Введите месяц в числовом формате ").strip()
            try:
                month_number = int(month)
                if 1 <= month_number <= 12:
                    expense_tracker.view_largest_expense(category_name, month_number)
                    break
            except ValueError:
                print("Пожалуйста, введите корректную дату")


def view_most_expensive_categories_demo(expense_tracker):
    while True:
        month = input(
            "Введите месяц в числовом формате, чтобы посмотреть, на какую из категорий пришлось больше всего трат, или введите 'завершить' ").strip()
        if month.lower() == "завершить" or month.lower() == "":
            break

        try:
            month_number = int(month)
            if 1 <= month_number <= 12:
                expense_tracker.view_most_expensive_category(month_number)
        except ValueError:
            print("Пожалуйста, введите корректную дату")
