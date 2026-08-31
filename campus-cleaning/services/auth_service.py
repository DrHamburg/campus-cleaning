from config.database import query, execute
from utils.password import hash_password, verify_password


def _find_account_sql(where_clause):
    return f"""
        SELECT ua.User_ID, ua.Staff_ID, ua.University_Email, ua.Password_Hash,
               ua.Role, ua.Account_Status, ua.Must_Change_Password,
               ua.Created_At, ua.Last_Login,
               s.Name AS Full_Name
        FROM USER_ACCOUNT ua
        LEFT JOIN STAFF s ON s.Staff_ID = ua.Staff_ID
        WHERE {where_clause}
        LIMIT 1
    """


def find_account_by_email(email):
    return query(_find_account_sql("ua.University_Email = %s"), (email,), fetchone=True)


def find_account_by_id(user_id):
    return query(_find_account_sql("ua.User_ID = %s"), (user_id,), fetchone=True)


def find_account_by_id_and_email(user_id, email):
    row = query(
        """SELECT User_ID, University_Email, Account_Status
           FROM USER_ACCOUNT WHERE User_ID = %s AND University_Email = %s LIMIT 1""",
        (user_id, email), fetchone=True
    )
    return row


def authenticate(email, plain_password):
    """Returns dict: {status: 'ok'|'invalid'|'inactive'|'suspended', account: {...}?}"""
    account = find_account_by_email(email)

    if not account:
        return {"status": "invalid"}

    if account["Account_Status"] == "INACTIVE":
        return {"status": "inactive"}
    if account["Account_Status"] == "SUSPENDED":
        return {"status": "suspended"}

    if not verify_password(plain_password, account["Password_Hash"]):
        return {"status": "invalid"}

    return {"status": "ok", "account": account}


def touch_last_login(user_id):
    execute("UPDATE USER_ACCOUNT SET Last_Login = NOW() WHERE User_ID = %s", (user_id,))


def change_password(user_id, current_password, new_password):
    account = find_account_by_id(user_id)
    if not account:
        return {"ok": False, "reason": "not_found"}

    if not verify_password(current_password, account["Password_Hash"]):
        return {"ok": False, "reason": "current_password_invalid"}

    new_hash = hash_password(new_password)
    execute(
        "UPDATE USER_ACCOUNT SET Password_Hash = %s, Must_Change_Password = FALSE WHERE User_ID = %s",
        (new_hash, user_id)
    )
    return {"ok": True}


def reset_password(user_id, email, new_password):
    new_hash = hash_password(new_password)
    _, rowcount = execute(
        """UPDATE USER_ACCOUNT
           SET Password_Hash = %s, Must_Change_Password = FALSE
           WHERE User_ID = %s AND University_Email = %s""",
        (new_hash, user_id, email)
    )
    return rowcount > 0
