from entities import ExpenseTracker


def test_add_category():
    expense_tracker = ExpenseTracker()

    expense_tracker.add_category("food")

    assert expense_tracker.categories[0].name == "food"


def test_view_most_expensive_category():
    expense_tracker = ExpenseTracker()

    category_food = expense_tracker.add_category("food")
    category_tv = expense_tracker.add_category("tv")
    expense_tracker.add_expense(category_food, "milk", 100, 1)
    expense_tracker.add_expense(category_food, "cake", 10, 1)
    expense_tracker.add_expense(category_tv, "plus plan", 90, 1)

    actual = expense_tracker.view_most_expensive_category(1)

    assert actual == "food"


def test_view_biggest_expense():
    expense_tracker = ExpenseTracker()

    category_food = expense_tracker.add_category("food")
    expense_tracker.add_expense(category_food, "milk", 100, 1)
    expense_tracker.add_expense(category_food, "cake", 10, 1)
    expense_tracker.add_expense(category_food, "fish", 190, 1)

    actual = expense_tracker.view_largest_expense("food", 1)

    assert actual == 190
