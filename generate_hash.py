import bcrypt
try:
    hashed = bcrypt.hashpw(b'admin@hyro', bcrypt.gensalt()).decode('utf-8')
    with open('hash.txt', 'w') as f:
        f.write(hashed)
    print("Hash written to hash.txt")
except Exception as e:
    with open('error.txt', 'w') as f:
        f.write(str(e))
