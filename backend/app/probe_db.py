import psycopg2
import sys

passwords = ["", "postgres", "changeme", "admin", "postgresql", "password"]
users = ["postgres", "crimemind_user"]

print("Probing database connections...")
for user in users:
    for pwd in passwords:
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user=user,
                password=pwd,
                dbname="template1" if user == "postgres" else "crimemind",
                connect_timeout=2
            )
            print(f"SUCCESS: user={user}, password='{pwd}' connected successfully!")
            conn.close()
            sys.exit(0)
        except Exception as e:
            # print(f"Failed user={user} pwd={pwd}: {e}")
            pass

print("FAILED: Could not connect with any common credentials.")
sys.exit(1)
