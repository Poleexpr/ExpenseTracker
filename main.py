from entities import ExpenseTracker
from helpers import (
    add_expenses_demo,
    view_largest_expenses_demo,
    view_most_expensive_categories_demo,
)


def main():
    expense_tracker = ExpenseTracker()
    add_expenses_demo(expense_tracker)
    view_largest_expenses_demo(expense_tracker)
    view_most_expensive_categories_demo(expense_tracker)

    print("Программа завершена.")


if __name__ == "__main__":
    main()
