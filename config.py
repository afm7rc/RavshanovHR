import os

TOKEN = os.getenv("TOKEN")
ADMINS = {int(os.getenv("ADMINS", "1163250764"))}  # Standart qiymat qo'shish mumkin
SUPER_ADMIN = int(os.getenv("SUPER_ADMIN", "1163250764"))  # Standart qiymat qo'shish mumkin
