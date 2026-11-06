from teller.bank.demo_data import get_customers_from_file, get_demo_database_path


def get_customer_name(customer):
    return customer["name"]


def load_customers():
    customers = get_customers_from_file(get_demo_database_path())
    customers.sort(key=get_customer_name)
    return customers
