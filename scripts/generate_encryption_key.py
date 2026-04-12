"""Generate an AES-256 encryption key for AuditHive audit log encryption."""

from audithive.core.encryption import generate_encryption_key

key = generate_encryption_key()
print("Generated encryption key. Add this to your .env file:")
print(f"AUDITHIVE_ENCRYPTION_KEY={key}")
print()
print("WARNING: If you lose this key, encrypted audit logs cannot be decrypted.")
print("Back up this key securely.")
