"""验证数据库结构"""
import sqlite3

conn = sqlite3.connect('database.sqlite')
cursor = conn.cursor()

print("=" * 50)
print("Database Tables:")
print("=" * 50)
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  [OK] {t[0]}")

print("\n" + "=" * 50)
print("user_profiles Table Schema:")
print("=" * 50)
schema = cursor.execute("PRAGMA table_info(user_profiles)").fetchall()
for s in schema:
    print(f"  {s[1]:<20} {s[2]:<15} {'NOT NULL' if s[3] else ''} {'DEFAULT: ' + str(s[4]) if s[4] else ''}")

print("\n" + "=" * 50)
print("users Table Schema:")
print("=" * 50)
schema = cursor.execute("PRAGMA table_info(users)").fetchall()
for s in schema:
    print(f"  {s[1]:<20} {s[2]:<15} {'NOT NULL' if s[3] else ''}")

conn.close()
print("\n[SUCCESS] Database verification completed!")
