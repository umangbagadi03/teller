import json

from teller import config

SOURCE_DATABASE = config.BANKING_DATA_DIR / "db.json"
DEMO_DATABASE = config.INDEX_DIR / "demo_db.json"

# The web app shows these sample customers. The benchmark keeps its own database,
# because its tasks refer to customers by their original names.
INDIAN_NAMES = [
    "Aarav Sharma", "Ananya Iyer", "Vivaan Patel", "Diya Reddy", "Arjun Nair",
    "Isha Gupta", "Rohan Mehta", "Kavya Menon", "Aditya Joshi", "Meera Kulkarni",
    "Kabir Singh", "Saanvi Rao", "Ishaan Verma", "Priya Desai", "Rahul Chatterjee",
    "Neha Bhat", "Karan Malhotra", "Tara Pillai", "Siddharth Jain", "Pooja Hegde",
    "Varun Agarwal", "Sneha Banerjee", "Nikhil Kapoor", "Riya Saxena", "Yash Thakur",
    "Aditi Mishra", "Manish Yadav", "Shreya Ghosh", "Harsh Pandey", "Nandini Das",
    "Dev Choudhary", "Lakshmi Krishnan", "Omkar Patil", "Fatima Shaikh", "Gurpreet Gill",
    "Zoya Khan", "Rakesh Sinha", "Anjali Tiwari", "Vikram Shetty",
]

INDIAN_ADDRESSES = [
    "14 MG Road, Bengaluru, Karnataka 560001",
    "22 Linking Road, Mumbai, Maharashtra 400050",
    "7 Park Street, Kolkata, West Bengal 700016",
    "31 Anna Salai, Chennai, Tamil Nadu 600002",
    "9 Connaught Place, New Delhi, Delhi 110001",
    "18 Jubilee Hills, Hyderabad, Telangana 500033",
    "5 FC Road, Pune, Maharashtra 411004",
    "26 CG Road, Ahmedabad, Gujarat 380009",
    "11 Hazratganj, Lucknow, Uttar Pradesh 226001",
    "3 MI Road, Jaipur, Rajasthan 302001",
]


def make_demo_details(position):
    name = INDIAN_NAMES[position]
    email_name = name.lower().replace(" ", ".")
    address_position = position % len(INDIAN_ADDRESSES)

    return {
        "name": name,
        "email": email_name + "@example.com",
        "phone_number": "+91 90000 " + str(10000 + position),
        "address": INDIAN_ADDRESSES[address_position],
    }


def get_customers_from_file(path):
    with open(path) as file:
        database = json.load(file)

    customers = []
    for customer in database["users"]["data"].values():
        customers.append(customer)
    return customers


def get_user_id(customer):
    return customer["user_id"]


def build_demo_database():
    source_text = SOURCE_DATABASE.read_text()
    customers = get_customers_from_file(SOURCE_DATABASE)
    customers.sort(key=get_user_id)

    # Replacing the text changes each detail everywhere it appears, including
    # other tables, so verification and account lookups still agree.
    demo_text = source_text
    for position, customer in enumerate(customers):
        details = make_demo_details(position)
        for field, new_value in details.items():
            demo_text = demo_text.replace(json.dumps(customer[field]), json.dumps(new_value))

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DATABASE.write_text(demo_text)
    return DEMO_DATABASE


def get_demo_database_path():
    if not DEMO_DATABASE.exists():
        build_demo_database()
    return DEMO_DATABASE
