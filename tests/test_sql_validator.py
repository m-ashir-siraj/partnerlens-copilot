from src.sql_validator import validate_sql


def test_valid_select_query():
    sql = "SELECT * FROM partners LIMIT 10;"
    is_valid, message = validate_sql(sql)
    assert is_valid is True


def test_blocked_delete_query():
    sql = "DELETE FROM partners;"
    is_valid, message = validate_sql(sql)
    assert is_valid is False


def test_empty_query():
    sql = ""
    is_valid, message = validate_sql(sql)
    assert is_valid is False
