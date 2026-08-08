import sqlite3

conn = sqlite3.connect('data/campus.db')
cursor = conn.cursor()

print("--- RESOURCES TABLE ---")
resources = cursor.execute('SELECT * FROM resources').fetchall()
for row in resources:
    print(row)
print(f"Total Resources: {len(resources)}\n")

print("--- READINGS TABLE ---")
readings = cursor.execute('SELECT * FROM readings').fetchall()
for row in readings:
    print(row)
print(f"Total Readings: {len(readings)}")

conn.close()