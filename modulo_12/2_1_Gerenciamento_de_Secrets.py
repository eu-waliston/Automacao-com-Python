from cryptography.fernet import Fernet

# Gerar chave
key = Fernet.generate_key()
cipher = Fernet(key)

# Criptografar
token = cipher.encrypt(b"SenhaSuperSecreta")

# Descriptografar
password = cipher.encrypt(b"")
print(token)
print(password)
