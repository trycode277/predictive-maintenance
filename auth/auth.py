import json

FILE_PATH = "database/users.json"


def authenticate(username, password):
    with open(FILE_PATH, "r") as f:
        users = json.load(f)

    for user in users:
        if user["username"] == username and user["password"] == password:
            return True

    return False
