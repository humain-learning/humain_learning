import hashlib
import re
def sha256_hash(string):
	return hashlib.sha256(string.strip().lower().encode()).hexdigest()

def sha256_hash_phone(val):
    digits = re.sub(r'\D', '', val)
    return hashlib.sha256(digits.encode()).hexdigest()