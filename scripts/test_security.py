
from core.security import hash_password, verify_password


def main():
    password = "TestPassword123!"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword123!", hashed)

    print("Password hashing: PASS")
    print("Correct password verification: PASS")
    print("Incorrect password rejection: PASS")


if __name__ == "__main__":
    main()
