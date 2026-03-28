import app
with app.master_db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("DESCRIBE pose_setting_table")
    for row in cursor.fetchall():
        if row[0].lower() == 'image':
            print("Image column type:", row[1])
