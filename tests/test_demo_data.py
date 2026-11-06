from tau2.domains.banking_knowledge.data_model import TransactionalDB

from teller.bank.demo_data import (
    INDIAN_NAMES,
    SOURCE_DATABASE,
    build_demo_database,
    get_customers_from_file,
)


def test_every_customer_gets_a_different_indian_name():
    path = build_demo_database()
    customers = get_customers_from_file(path)

    names = []
    for customer in customers:
        names.append(customer["name"])

    assert len(INDIAN_NAMES) == len(customers)
    assert sorted(names) == sorted(INDIAN_NAMES)


def test_old_details_are_gone_everywhere():
    path = build_demo_database()
    demo_text = path.read_text()

    for customer in get_customers_from_file(SOURCE_DATABASE):
        assert '"' + customer["name"] + '"' not in demo_text
        assert customer["email"] not in demo_text


def test_demo_database_loads_in_the_benchmark_format():
    path = build_demo_database()
    database = TransactionalDB.load(str(path))
    assert database is not None


def test_benchmark_database_is_not_changed():
    before = SOURCE_DATABASE.read_text()
    build_demo_database()
    assert SOURCE_DATABASE.read_text() == before
