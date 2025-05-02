from entities import ExpenseTracker
from helpers import add_expenses_demonstration, view_largest_expenses_demonstration, \
    view_most_expensive_categories_demonstration


def main():
    expense_tracker = ExpenseTracker()
    add_expenses_demonstration(expense_tracker)
    view_largest_expenses_demonstration(expense_tracker)
    view_most_expensive_categories_demonstration(expense_tracker)

    print("Программа завершена.")


if __name__ == "__main__":
    main()
