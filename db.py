import mysql.connector
import csv
import asyncio
from datetime import datetime

# 📌 MySQL bazasiga ulanish funksiyasi
def connect_db():
    """MySQL ulanishini yaratish."""
    try:
        # MySQL ulanishini yaratish
        db_connection = mysql.connector.connect(
            host="DB_HOST",
            user="DB_USER",
            password="DB_PASSWORD",
            database="DB_NAME"
        )
        return db_connection
    except Exception as e:
        print(f"Xatolik: {e}")
        return None

def save_user(user_id, username, nickname, fullname, phone=None):
    db = connect_db()
    cursor = db.cursor()

    sql = """
    INSERT INTO users (user_id, username, nickname, fullname, phone, status, created_at) 
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    ON DUPLICATE KEY UPDATE 
    username = VALUES(username), 
    nickname = VALUES(nickname), 
    fullname = VALUES(fullname), 
    phone = VALUES(phone)
    """
    
    values = (user_id, username, nickname, fullname, phone, "faol")
    cursor.execute(sql, values)
    db.commit()

    cursor.close()
    db.close()

def save_user_info(user_id, fullname, phone):
    db = connect_db()
    cursor = db.cursor()

    # Agar user mavjud bo'lsa, nomi va telefonini yangilash
    sql = """
    UPDATE users 
    SET fullname = %s, phone = %s 
    WHERE user_id = %s
    """
    values = (fullname, phone, user_id)
    cursor.execute(sql, values)
    db.commit()

    cursor.close()
    db.close()
    print(f"✅ Foydalanuvchi {user_id} uchun ism va telefon yangilandi!")

def get_all_users():
    """Barcha foydalanuvchilarni bazadan olish."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, nickname, username, fullname, phone, status, created_at FROM users")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return users

def update_user_status(user_id, status):
    """Foydalanuvchi statusini yangilash (faol yoki bloklangan)."""
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET status = %s WHERE user_id = %s", (status, user_id))
    conn.commit()
    
    cursor.close()
    conn.close()

def get_stats():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]  # Umumiy foydalanuvchilar soni

    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'faol'")
    active_users = cursor.fetchone()[0]  # Faol foydalanuvchilar soni

    cursor.execute("SELECT COUNT(*) FROM admins")
    admins_count = cursor.fetchone()[0]  # Adminlar soni

    cursor.close()
    db.close()

    return users_count, active_users, admins_count  # 3ta qiymat qaytariladi

def update_status():
    db = connect_db()
    cursor = db.cursor()

    # 7 kundan ortiq faol bo‘lmaganlarni "bloklangan" qilish
    cursor.execute("""
        UPDATE users 
        SET status = 'bloklangan' 
        WHERE last_active < NOW() - INTERVAL 7 DAY
    """)
    
    db.commit()
    cursor.close()
    db.close()

def mark_active(user_id):
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("UPDATE users SET status = 'faol', last_active = NOW() WHERE user_id = %s", (user_id,))
    db.commit()

    cursor.close()
    db.close()

def fix_blocked_users():
    db = connect_db()
    cursor = db.cursor()

    # Agar foydalanuvchi oxirgi 7 kun ichida aktiv bo'lsa, uni faolga o‘tkazish
    cursor.execute("""
        UPDATE users 
        SET status = 'faol' 
        WHERE status = 'bloklangan' AND last_active >= NOW() - INTERVAL 7 DAY
    """)
    
    db.commit()
    cursor.close()
    db.close()

    print("✅ Bloklangan foydalanuvchilar avtomatik tiklandi!")

def is_admin(user_id):
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM admins WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    return result[0] > 0  # Agar 0 bo‘lsa, admin emas

# 📌 Barcha jadvallarni ko‘rish uchun (test maqsadida)
def show_tables():
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SHOW TABLES;")
    tables = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    return tables  # Natijani qaytarish

# 📌 Foydalanuvchini ID bo‘yicha bazadan olish funksiyasi
def get_user_by_id(user_id):
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    return user  # Agar foydalanuvchi topilsa, dict shaklida, aks holda None qaytaradi

def update_user_info(user_id, username=None, fullname=None, phone=None):
    db = connect_db()
    cursor = db.cursor()

    try:
        # Faqat bor foydalanuvchini yangilash
        sql = """
        UPDATE users 
        SET username = COALESCE(%s, username),
            fullname = COALESCE(%s, fullname),
            phone = COALESCE(%s, phone)
        WHERE user_id = %s
        """
        values = (username, fullname, phone, user_id)

        cursor.execute(sql, values)
        db.commit()
        print(f"✅ {user_id} foydalanuvchi ma'lumotlari yangilandi.")

    except Exception as e:
        print(f"❌ Bazaga yozishda xatolik: {e}")
    finally:
        cursor.close()
        db.close()

async def get_user_data(user_id: int):
    """Foydalanuvchi ma'lumotlarini bazadan olish (sinxron funksiyani asinxron chaqirish)."""
    loop = asyncio.get_event_loop()
    user_data = await loop.run_in_executor(None, _get_user_data_sync, user_id)
    return user_data

def _get_user_data_sync(user_id: int):
    """Sinxron tarzda foydalanuvchi ma'lumotlarini olish."""
    try:
        db_connection = connect_db()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT full_name, phone FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        db_connection.close()
        return user_data
    except Exception as e:
        print(f"Xatolik: {e}")
        return None

def export_users_to_csv():
    db = connect_db()
    cursor = db.cursor()

    cursor.execute("SELECT user_id, nickname, username, fullname, phone, status, created_at FROM users ORDER BY user_id ASC")
    users = cursor.fetchall()

    with open("usersdata.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["user_id", "nickname", "username", "fullname", "phone", "status", "created_at"])  # Sarlavha qo‘shish
        writer.writerows(users)

    cursor.close()
    db.close()
    print("✅ Foydalanuvchilar CSV faylga muvaffaqiyatli eksport qilindi!")
