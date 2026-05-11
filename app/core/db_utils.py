from sqlalchemy.dialects.postgresql import insert

def postgres_upsert(table, conn, keys, data_iter):
    """
    Custom insert function for pandas to handle PostgreSQL ON CONFLICT DO NOTHING.
    Prevents duplicate primary key crashes.
    """
    data = [dict(zip(keys, row)) for row in data_iter]
    
    insert_stmt = insert(table.table).values(data)
    upsert_stmt = insert_stmt.on_conflict_do_nothing(
        index_elements=['stock_id', 'date']
    )
    conn.execute(upsert_stmt)