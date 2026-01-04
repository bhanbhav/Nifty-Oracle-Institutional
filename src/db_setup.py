import psycopg2

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

def create_schema():
    try:
        print("🔌 Connecting to Database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. DROP the old messy table (WIPE DATA)
        # Warning: This deletes all historical data!
        cur.execute("DROP TABLE IF EXISTS market_data CASCADE;")
        print("🗑  Old 'market_data' table wiped.")

        # 2. Re-Create with UNIQUE Constraint
        print("🛠  Building New Secure Vault...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT NOT NULL,
                open            DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close           DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                is_adjusted     BOOLEAN DEFAULT FALSE,
                
                -- THE SECURITY GUARD: No duplicate (time + symbol) allowed
                UNIQUE (time, symbol)
            );
        """)
        
        # 3. Convert to Hypertable
        try:
            cur.execute("SELECT create_hypertable('market_data', 'time');")
            print("✅ 'market_data' Hypertable created.")
        except psycopg2.errors.InternalError: 
             print("ℹ️ 'market_data' is already a Hypertable.")

        cur.close()
        conn.close()
        print("\n🚀 SUCCESS: Vault is now secure and duplicate-proof.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_schema()