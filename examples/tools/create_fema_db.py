#!/usr/bin/env python3
"""Create the FEMA disaster SQLite database on disk.

Run once before using the fema_supervisor agent:
    python examples/tools/create_fema_db.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "fema_disaster.db"

RECORDS = [
    ("DR-4001", 2020, "California", "Wildfire", 5, 820000, 1800000000, "2020-08-18"),
    ("DR-4002", 2020, "Oregon", "Wildfire", 4, 340000, 650000000, "2020-09-10"),
    ("DR-4003", 2020, "Louisiana", "Hurricane", 5, 760000, 1500000000, "2020-08-27"),
    ("DR-4004", 2020, "Texas", "Hurricane", 4, 450000, 900000000, "2020-08-26"),
    ("DR-4005", 2020, "Florida", "Hurricane", 3, 280000, 420000000, "2020-09-15"),
    ("DR-4006", 2020, "Iowa", "Tornado", 4, 95000, 180000000, "2020-08-10"),
    ("DR-4007", 2020, "Michigan", "Flood", 3, 120000, 200000000, "2020-05-20"),
    ("DR-4008", 2020, "Colorado", "Wildfire", 3, 85000, 150000000, "2020-10-15"),
    ("DR-4009", 2020, "Puerto Rico", "Earthquake", 4, 500000, 800000000, "2020-01-07"),
    ("DR-4010", 2020, "Tennessee", "Tornado", 4, 150000, 310000000, "2020-03-03"),
    ("DR-4011", 2020, "Alabama", "Tornado", 3, 75000, 120000000, "2020-04-12"),
    ("DR-4012", 2020, "Mississippi", "Tornado", 3, 60000, 95000000, "2020-04-13"),
    ("DR-4013", 2020, "North Carolina", "Hurricane", 3, 190000, 350000000, "2020-09-16"),
    ("DR-4014", 2020, "Washington", "Wildfire", 4, 250000, 500000000, "2020-09-12"),
    ("DR-4015", 2020, "Nebraska", "Flood", 3, 45000, 80000000, "2020-03-15"),
    ("DR-4016", 2020, "South Carolina", "Hurricane", 3, 160000, 280000000, "2020-09-17"),
    ("DR-4017", 2020, "Oklahoma", "Tornado", 3, 55000, 90000000, "2020-05-04"),
    ("DR-4018", 2020, "Montana", "Wildfire", 2, 18000, 35000000, "2020-08-20"),
    ("DR-4019", 2020, "Arkansas", "Flood", 3, 70000, 110000000, "2020-06-01"),
    ("DR-4020", 2020, "Missouri", "Flood", 3, 85000, 130000000, "2020-06-05"),
    ("DR-4021", 2020, "Georgia", "Hurricane", 2, 110000, 180000000, "2020-10-10"),
    ("DR-4022", 2020, "Kentucky", "Flood", 2, 40000, 65000000, "2020-03-01"),
    ("DR-4023", 2020, "Utah", "Earthquake", 3, 200000, 250000000, "2020-03-18"),
    ("DR-4024", 2020, "Virginia", "Flood", 2, 35000, 55000000, "2020-07-14"),
    ("DR-4025", 2020, "Kansas", "Tornado", 3, 42000, 75000000, "2020-05-21"),
    ("DR-4031", 2021, "Louisiana", "Hurricane", 5, 950000, 2100000000, "2021-08-29"),
    ("DR-4032", 2021, "New Jersey", "Hurricane", 4, 420000, 800000000, "2021-09-01"),
    ("DR-4033", 2021, "New York", "Flood", 4, 550000, 950000000, "2021-09-02"),
    ("DR-4034", 2021, "Texas", "Flood", 4, 380000, 720000000, "2021-02-19"),
    ("DR-4035", 2021, "Kentucky", "Tornado", 5, 300000, 650000000, "2021-12-11"),
    ("DR-4036", 2021, "California", "Wildfire", 5, 700000, 1600000000, "2021-07-14"),
    ("DR-4037", 2021, "Oregon", "Wildfire", 4, 280000, 520000000, "2021-07-20"),
    ("DR-4038", 2021, "Pennsylvania", "Flood", 3, 190000, 320000000, "2021-09-03"),
    ("DR-4039", 2021, "Mississippi", "Hurricane", 4, 310000, 580000000, "2021-08-30"),
    ("DR-4040", 2021, "Tennessee", "Flood", 4, 250000, 470000000, "2021-08-21"),
    ("DR-4041", 2021, "Colorado", "Wildfire", 4, 160000, 380000000, "2021-12-30"),
    ("DR-4042", 2021, "Alabama", "Tornado", 3, 85000, 140000000, "2021-03-25"),
    ("DR-4043", 2021, "Illinois", "Tornado", 3, 72000, 115000000, "2021-12-11"),
    ("DR-4044", 2021, "North Carolina", "Hurricane", 3, 175000, 300000000, "2021-09-05"),
    ("DR-4045", 2021, "Montana", "Wildfire", 3, 45000, 85000000, "2021-07-10"),
    ("DR-4066", 2022, "Florida", "Hurricane", 5, 1500000, 2800000000, "2022-09-28"),
    ("DR-4067", 2022, "South Carolina", "Hurricane", 4, 350000, 680000000, "2022-09-30"),
    ("DR-4068", 2022, "Kentucky", "Flood", 5, 400000, 850000000, "2022-07-28"),
    ("DR-4069", 2022, "California", "Wildfire", 4, 520000, 1100000000, "2022-09-02"),
    ("DR-4070", 2022, "New Mexico", "Wildfire", 4, 180000, 400000000, "2022-04-22"),
    ("DR-4071", 2022, "Alaska", "Flood", 4, 85000, 200000000, "2022-09-17"),
    ("DR-4072", 2022, "Mississippi", "Flood", 3, 150000, 280000000, "2022-08-29"),
    ("DR-4073", 2022, "Montana", "Flood", 4, 110000, 220000000, "2022-06-13"),
    ("DR-4074", 2022, "Puerto Rico", "Hurricane", 5, 1200000, 2200000000, "2022-09-18"),
    ("DR-4075", 2022, "North Carolina", "Hurricane", 3, 200000, 380000000, "2022-10-01"),
    ("DR-4078", 2022, "Oklahoma", "Tornado", 4, 140000, 260000000, "2022-05-02"),
    ("DR-4101", 2023, "Hawaii", "Wildfire", 5, 850000, 2000000000, "2023-08-09"),
    ("DR-4102", 2023, "California", "Flood", 4, 600000, 1200000000, "2023-01-09"),
    ("DR-4103", 2023, "Florida", "Hurricane", 4, 480000, 950000000, "2023-08-30"),
    ("DR-4104", 2023, "Mississippi", "Tornado", 4, 220000, 450000000, "2023-03-24"),
    ("DR-4105", 2023, "Texas", "Flood", 3, 180000, 340000000, "2023-05-01"),
    ("DR-4106", 2023, "Vermont", "Flood", 4, 150000, 350000000, "2023-07-10"),
    ("DR-4107", 2023, "Louisiana", "Hurricane", 3, 260000, 480000000, "2023-08-31"),
    ("DR-4108", 2023, "Oregon", "Wildfire", 3, 140000, 270000000, "2023-07-20"),
    ("DR-4112", 2023, "Oklahoma", "Tornado", 4, 175000, 330000000, "2023-04-19"),
    ("DR-4136", 2024, "Florida", "Hurricane", 5, 1300000, 2500000000, "2024-10-09"),
    ("DR-4137", 2024, "North Carolina", "Hurricane", 5, 900000, 1800000000, "2024-09-27"),
    ("DR-4138", 2024, "Texas", "Hurricane", 4, 550000, 1050000000, "2024-07-08"),
    ("DR-4139", 2024, "California", "Wildfire", 4, 480000, 980000000, "2024-07-26"),
    ("DR-4140", 2024, "Oregon", "Wildfire", 3, 160000, 300000000, "2024-07-22"),
    ("DR-4141", 2024, "Georgia", "Hurricane", 4, 380000, 720000000, "2024-09-27"),
    ("DR-4144", 2024, "Iowa", "Tornado", 4, 120000, 230000000, "2024-05-21"),
    ("DR-4145", 2024, "Oklahoma", "Tornado", 4, 150000, 290000000, "2024-05-06"),
    ("DR-4146", 2024, "Vermont", "Flood", 3, 80000, 150000000, "2024-07-10"),
    ("DR-4147", 2024, "Colorado", "Wildfire", 3, 85000, 165000000, "2024-06-20"),
    ("DR-4171", 2025, "California", "Wildfire", 5, 1100000, 2400000000, "2025-01-08"),
    ("DR-4172", 2025, "Texas", "Flood", 4, 420000, 820000000, "2025-03-15"),
    ("DR-4173", 2025, "Florida", "Hurricane", 4, 600000, 1150000000, "2025-06-15"),
    ("DR-4174", 2025, "Oklahoma", "Tornado", 5, 280000, 620000000, "2025-04-26"),
    ("DR-4175", 2025, "Louisiana", "Hurricane", 4, 380000, 750000000, "2025-07-20"),
    ("DR-4176", 2025, "Oregon", "Wildfire", 3, 145000, 280000000, "2025-07-10"),
    ("DR-4177", 2025, "Kentucky", "Flood", 4, 200000, 400000000, "2025-03-28"),
    ("DR-4178", 2025, "North Carolina", "Hurricane", 3, 250000, 470000000, "2025-08-15"),
    ("DR-4179", 2025, "Colorado", "Wildfire", 3, 95000, 185000000, "2025-06-25"),
    ("DR-4180", 2025, "Georgia", "Tornado", 3, 110000, 200000000, "2025-04-10"),
]


def create_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE disaster_data (
            disaster_id TEXT PRIMARY KEY,
            year INTEGER,
            state TEXT,
            disaster_type TEXT,
            severity INTEGER,
            affected_population INTEGER,
            federal_aid_amount INTEGER,
            declaration_date TEXT
        )
    """)
    cursor.executemany(
        "INSERT INTO disaster_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        RECORDS,
    )
    conn.commit()
    conn.close()
    print(f"Created {DB_PATH} with {len(RECORDS)} records")


if __name__ == "__main__":
    create_database()
