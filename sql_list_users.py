import sqlite3


def main() -> None:
    conn = sqlite3.connect("ca_tadley_debt_tool.db")
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, role, status FROM users ORDER BY email ASC"
        )
        rows = cur.fetchall()
        print(f"COUNT\t{len(rows)}")
        print("id\temail\trole\tstatus", flush=True)
        for row in rows:
            user_id, email, role, status = row
            print(f"{user_id}\t{email}\t{role}\t{status}", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()


