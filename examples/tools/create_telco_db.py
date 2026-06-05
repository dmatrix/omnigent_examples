#!/usr/bin/env python3
"""Create the telco customer SQLite database on disk.

Run once before using the telco_customer_agent:
    python examples/tools/create_telco_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "telco.db"

PLANS = [
    ("PLAN-ES", "Essentials Saver", 55, 50, 0, "none", "none", 0),
    ("PLAN-EI", "Essentials", 65, 50, 0, "none", "none", 0),
    ("PLAN-EM", "Experience More", 90, -1, 60, "5gb_intl", "netflix_ads,apple_tv", 5),
    ("PLAN-EB", "Experience Beyond", 105, -1, -1, "15gb_intl", "netflix,hulu,apple_tv", 5),
    ("PLAN-BZ", "Business Unlimited", 200, -1, -1, "unlimited", "none", 3),
]

CUSTOMERS = [
    ("CUST-1001", "Sarah Chen", "sarah.chen@gmail.com", "(415) 555-0142", "4829", "California", "individual", "A", "active", "2022-03-15", "true"),
    ("CUST-1002", "Marcus Johnson", "m.johnson@outlook.com", "(212) 555-0198", "7731", "New York", "individual", "A", "active", "2023-01-22", "true"),
    ("CUST-1003", "Priya Patel", "priya.patel@yahoo.com", "(408) 555-0234", "5512", "California", "family", "B", "active", "2023-06-10", "false"),
    ("CUST-1004", "James O'Brien", "jobrien@icloud.com", "(312) 555-0167", "8843", "Illinois", "individual", "A", "active", "2021-11-08", "true"),
    ("CUST-1005", "Yuki Tanaka", "yuki.t@gmail.com", "(206) 555-0289", "3367", "Washington", "individual", "B", "active", "2024-02-14", "true"),
    ("CUST-1006", "Maria Rodriguez", "maria.r@hotmail.com", "(305) 555-0145", "9954", "Florida", "family", "A", "active", "2022-08-20", "true"),
    ("CUST-1007", "David Kim", "d.kim@gmail.com", "(213) 555-0312", "2248", "California", "individual", "C", "suspended", "2023-04-05", "false"),
    ("CUST-1008", "Emily Watson", "emily.w@outlook.com", "(469) 555-0178", "6635", "Texas", "business", "A", "active", "2021-05-12", "true"),
    ("CUST-1009", "Ahmed Hassan", "a.hassan@gmail.com", "(678) 555-0256", "1129", "Georgia", "individual", "B", "active", "2023-09-18", "false"),
    ("CUST-1010", "Lisa Thompson", "lisa.t@yahoo.com", "(602) 555-0193", "7781", "Arizona", "individual", "D", "past_due", "2024-01-03", "false"),
    ("CUST-1011", "Robert Chen", "r.chen@icloud.com", "(425) 555-0267", "4456", "Washington", "family", "A", "active", "2022-11-30", "true"),
    ("CUST-1012", "Jennifer Adams", "j.adams@gmail.com", "(503) 555-0134", "8892", "Oregon", "individual", "B", "active", "2023-07-25", "true"),
    ("CUST-1013", "Carlos Mendez", "carlos.m@outlook.com", "(713) 555-0298", "3318", "Texas", "business", "A", "active", "2021-09-14", "true"),
    ("CUST-1014", "Aisha Williams", "aisha.w@gmail.com", "(404) 555-0176", "5567", "Georgia", "individual", "C", "past_due", "2024-03-08", "false"),
    ("CUST-1015", "Michael Park", "m.park@yahoo.com", "(646) 555-0243", "9921", "New York", "individual", "A", "active", "2022-06-17", "true"),
    ("CUST-1016", "Rachel Green", "rachel.g@icloud.com", "(303) 555-0189", "2274", "Colorado", "family", "B", "active", "2023-02-28", "false"),
    ("CUST-1017", "Daniel Nguyen", "d.nguyen@gmail.com", "(510) 555-0321", "6643", "California", "individual", "A", "active", "2022-01-10", "true"),
    ("CUST-1018", "Sophia Martinez", "sophia.m@hotmail.com", "(480) 555-0156", "8835", "Arizona", "individual", "D", "churned", "2023-11-20", "false"),
    ("CUST-1019", "William Taylor", "w.taylor@outlook.com", "(972) 555-0278", "1147", "Texas", "business", "A", "active", "2021-03-05", "true"),
    ("CUST-1020", "Hannah Lee", "hannah.l@gmail.com", "(253) 555-0212", "4498", "Washington", "individual", "B", "active", "2024-04-12", "true"),
]

SUBSCRIPTIONS = [
    ("SUB-2001", "CUST-1001", "PLAN-EB", "primary", 105, "postpaid", 24, "2023-06-15", "2025-06-15", "true", 0, None, None),
    ("SUB-2002", "CUST-1002", "PLAN-EM", "primary", 90, "postpaid", 24, "2023-01-22", "2025-01-22", "true", 10, "LOYAL20", None),
    ("SUB-2003", "CUST-1003", "PLAN-EI", "primary", 65, "postpaid", 12, "2024-06-10", "2025-06-10", "false", 0, None, "att"),
    ("SUB-2004", "CUST-1004", "PLAN-EB", "primary", 105, "postpaid", 36, "2021-11-08", "2024-11-08", "true", 15, "SWITCH15", "verizon"),
    ("SUB-2005", "CUST-1005", "PLAN-EM", "primary", 90, "postpaid", 24, "2024-02-14", "2026-02-14", "true", 0, None, None),
    ("SUB-2006", "CUST-1006", "PLAN-EB", "primary", 105, "postpaid", 24, "2022-08-20", "2024-08-20", "true", 20, "MILITARY", None),
    ("SUB-2007", "CUST-1007", "PLAN-ES", "primary", 55, "prepaid", 0, "2023-04-05", None, "false", 0, None, "t-mobile"),
    ("SUB-2008", "CUST-1008", "PLAN-BZ", "primary", 200, "postpaid", 36, "2021-05-12", "2024-05-12", "true", 10, "BIZ10", None),
    ("SUB-2009", "CUST-1009", "PLAN-EM", "primary", 90, "postpaid", 24, "2023-09-18", "2025-09-18", "false", 0, None, None),
    ("SUB-2010", "CUST-1010", "PLAN-ES", "primary", 55, "postpaid", 12, "2024-01-03", "2025-01-03", "false", 0, None, "att"),
    ("SUB-2011", "CUST-1011", "PLAN-EB", "primary", 105, "postpaid", 24, "2022-11-30", "2024-11-30", "true", 0, None, None),
    ("SUB-2012", "CUST-1012", "PLAN-EM", "primary", 90, "postpaid", 24, "2023-07-25", "2025-07-25", "true", 0, None, None),
    ("SUB-2013", "CUST-1013", "PLAN-BZ", "primary", 200, "postpaid", 36, "2021-09-14", "2024-09-14", "true", 15, "BIZ15", None),
    ("SUB-2014", "CUST-1014", "PLAN-EI", "primary", 65, "postpaid", 12, "2024-03-08", "2025-03-08", "false", 0, None, None),
    ("SUB-2015", "CUST-1015", "PLAN-EB", "primary", 105, "postpaid", 24, "2022-06-17", "2024-06-17", "true", 10, "LOYAL20", None),
    ("SUB-2016", "CUST-1016", "PLAN-EM", "primary", 90, "postpaid", 24, "2023-02-28", "2025-02-28", "false", 0, None, "verizon"),
    ("SUB-2017", "CUST-1017", "PLAN-EB", "primary", 105, "postpaid", 36, "2022-01-10", "2025-01-10", "true", 0, None, None),
    ("SUB-2018", "CUST-1018", "PLAN-ES", "primary", 55, "prepaid", 0, "2023-11-20", None, "false", 0, None, None),
    ("SUB-2019", "CUST-1019", "PLAN-BZ", "primary", 200, "postpaid", 36, "2021-03-05", "2024-03-05", "true", 20, "BIZ20", None),
    ("SUB-2020", "CUST-1020", "PLAN-EI", "primary", 65, "postpaid", 12, "2024-04-12", "2025-04-12", "true", 0, None, "t-mobile"),
]

DEVICES = [
    ("DEV-4001", "SUB-2001", "Apple", "iPhone 16 Pro Max", "353456789012345", 42, 18, 1500, "total_protect", 18),
    ("DEV-4002", "SUB-2002", "Samsung", "Galaxy S25 Ultra", "353456789012346", 36, 24, 1300, "basic_protect", 15),
    ("DEV-4003", "SUB-2003", "Apple", "iPhone 15", "353456789012347", 30, 12, 1100, "none", 0),
    ("DEV-4004", "SUB-2004", "Google", "Pixel 9 Pro", "353456789012348", 25, 0, 900, "basic_protect", 15),
    ("DEV-4005", "SUB-2005", "Apple", "iPhone 16 Pro", "353456789012349", 36, 22, 1300, "total_protect", 18),
    ("DEV-4006", "SUB-2006", "Samsung", "Galaxy S24", "353456789012350", 0, 0, 0, "none", 0),
    ("DEV-4007", "SUB-2007", "Apple", "iPhone SE", "353456789012351", 0, 0, 0, "none", 0),
    ("DEV-4008", "SUB-2008", "Apple", "iPhone 16 Pro Max", "353456789012352", 42, 6, 1500, "total_protect", 18),
    ("DEV-4009", "SUB-2009", "Google", "Pixel 9", "353456789012353", 25, 20, 800, "none", 0),
    ("DEV-4010", "SUB-2010", "Samsung", "Galaxy A55", "353456789012354", 15, 8, 400, "none", 0),
    ("DEV-4011", "SUB-2011", "Apple", "iPhone 15 Pro", "353456789012355", 30, 0, 1100, "basic_protect", 15),
    ("DEV-4012", "SUB-2012", "Samsung", "Galaxy S25", "353456789012356", 30, 18, 1000, "none", 0),
    ("DEV-4013", "SUB-2013", "Apple", "iPhone 16 Pro Max", "353456789012357", 42, 12, 1500, "total_protect", 18),
    ("DEV-4014", "SUB-2014", "Google", "Pixel 8a", "353456789012358", 15, 10, 500, "none", 0),
    ("DEV-4015", "SUB-2015", "Apple", "iPhone 15 Pro Max", "353456789012359", 36, 0, 1200, "basic_protect", 15),
    ("DEV-4016", "SUB-2016", "Samsung", "Galaxy S24 Ultra", "353456789012360", 36, 14, 1300, "none", 0),
    ("DEV-4017", "SUB-2017", "Apple", "iPhone 16", "353456789012361", 30, 6, 1000, "none", 0),
    ("DEV-4018", "SUB-2018", "Samsung", "Galaxy A35", "353456789012362", 0, 0, 0, "none", 0),
    ("DEV-4019", "SUB-2019", "Apple", "iPhone 16 Pro", "353456789012363", 36, 0, 1300, "total_protect", 18),
    ("DEV-4020", "SUB-2020", "Google", "Pixel 9 Pro", "353456789012364", 25, 24, 900, "basic_protect", 15),
]

BILLING = []
for i, cust in enumerate(CUSTOMERS):
    cust_id = cust[0]
    sub = SUBSCRIPTIONS[i]
    plan_rate = sub[4]
    dev = DEVICES[i]
    dev_installment = dev[5]
    insurance = dev[9]
    has_autopay = cust[10] == "true"
    discount_pct = sub[10]

    for month_idx, month in enumerate(["2025-04", "2025-05", "2025-06"]):
        overage = [0, 0, 12, 0, 0, 0, 25, 0, 0, 15, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0][i] if month_idx == 2 else 0
        intl = [0, 8, 0, 15, 0, 0, 0, 45, 0, 0, 0, 0, 25, 0, 0, 0, 0, 0, 30, 0][i] if month_idx >= 1 else 0
        taxes = round(plan_rate * 0.08)
        autopay_disc = -10 if has_autopay else 0
        promo_disc = round(-plan_rate * discount_pct / 100) if discount_pct > 0 else 0
        total = plan_rate + dev_installment + insurance + overage + intl + taxes + autopay_disc + promo_disc

        status = "current"
        late_fee = 0
        if cust_id in ("CUST-1010", "CUST-1014"):
            status = "past_due_30" if month_idx < 2 else "past_due_60"
            late_fee = 15 if month_idx >= 1 else 0
        elif cust_id == "CUST-1018":
            status = "collections"
            late_fee = 25

        total += late_fee
        bill_id = f"BILL-{5001 + i * 3 + month_idx}"
        BILLING.append((bill_id, cust_id, month, plan_rate, dev_installment, insurance, overage, intl, taxes, autopay_disc, promo_disc, total, status, late_fee))


def create_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute("""CREATE TABLE plans (
        plan_id TEXT PRIMARY KEY, plan_name TEXT, monthly_rate INTEGER,
        data_limit_gb INTEGER, hotspot_gb INTEGER, international TEXT,
        streaming_perks TEXT, price_guarantee_years INTEGER)""")
    c.executemany("INSERT INTO plans VALUES (?,?,?,?,?,?,?,?)", PLANS)

    c.execute("""CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY, name TEXT, email TEXT,
        phone_number TEXT, ssn_last4 TEXT, address_state TEXT,
        account_type TEXT, credit_class TEXT, account_status TEXT,
        signup_date TEXT, auto_pay TEXT)""")
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?)", CUSTOMERS)

    c.execute("""CREATE TABLE subscriptions (
        subscription_id TEXT PRIMARY KEY, customer_id TEXT, plan_id TEXT,
        line_type TEXT, monthly_rate INTEGER, contract_type TEXT,
        contract_months INTEGER, contract_start TEXT, contract_end TEXT,
        auto_renew TEXT, discount_pct INTEGER, promo_code TEXT, ported_from TEXT)""")
    c.executemany("INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", SUBSCRIPTIONS)

    c.execute("""CREATE TABLE devices (
        device_id TEXT PRIMARY KEY, subscription_id TEXT, make TEXT,
        model TEXT, imei TEXT, installment_monthly INTEGER,
        installment_remaining INTEGER, installment_total INTEGER,
        insurance_plan TEXT, insurance_monthly INTEGER)""")
    c.executemany("INSERT INTO devices VALUES (?,?,?,?,?,?,?,?,?,?)", DEVICES)

    c.execute("""CREATE TABLE billing (
        billing_id TEXT PRIMARY KEY, customer_id TEXT, month TEXT,
        plan_charge INTEGER, device_installment INTEGER, insurance INTEGER,
        overage_charges INTEGER, international_charges INTEGER,
        taxes_and_fees INTEGER, autopay_discount INTEGER, promo_discount INTEGER,
        total_due INTEGER, payment_status TEXT, late_fee INTEGER)""")
    c.executemany("INSERT INTO billing VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", BILLING)

    conn.commit()
    conn.close()
    print(f"Created {DB_PATH}")
    print(f"  plans: {len(PLANS)} records")
    print(f"  customers: {len(CUSTOMERS)} records")
    print(f"  subscriptions: {len(SUBSCRIPTIONS)} records")
    print(f"  devices: {len(DEVICES)} records")
    print(f"  billing: {len(BILLING)} records")


if __name__ == "__main__":
    create_database()
