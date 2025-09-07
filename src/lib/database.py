import psycopg2
import time
import logging

LOGGER = logging.getLogger(__name__)

class Database:
    """
    Database class to handle database connections and operations
    """
    def __init__(self, 
                 host: str, port: int, user: str, 
                 password: str, database: str
        ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.connect()
    
    def connect(self):
        self.db = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.database
        )
        self.cursor = self.db.cursor()
    
    def reconnect(self):
        try:
            self.db.close()
        except Exception as e:
            LOGGER.error(f"Error closing database connection: {e}")
        self.connect()

    def __del__(self):
        try:
            self.cursor.close()
            self.db.close()
        except Exception as e:
            LOGGER.error(f"Error closing database connection: {e}")

    def execute(self, query: str, args: dict = {}, retries: int = 5, delay: float = 10.0) -> list:
        attempt = 0
        while attempt < retries:
            try:
                self.cursor.execute(query, args)
                return self.cursor.fetchall()
            except psycopg2.OperationalError as e:
                attempt += 1
                LOGGER.error(f"DB connection error: {e} -- retrying {attempt}/{retries} in {delay} secs.")
                self.reconnect()
                time.sleep(delay)
            except Exception as e:
                LOGGER.error(f"Unexpected error: {e}")
                raise
        raise psycopg2.OperationalError(
            f"execute failed after {retries} retries: {query} with args {args}"
        )

    def safe_execute(self, query: str, args: dict = {}, retries: int = 5, delay: float = 10.0) -> None:
        attempt = 0
        while attempt < retries:
            try:
                self.cursor.execute(query, args)
                return  # success
            except psycopg2.OperationalError as e:
                attempt += 1
                LOGGER.error(f"OperationalError: {e} -- retrying {attempt}/{retries}.")
                self.reconnect()
                time.sleep(delay)
            except Exception as e:
                LOGGER.error(f"Unexpected error: {e}")
                raise
        raise psycopg2.OperationalError(
            f"safe_execute failed after {retries} retries: {query} with args {args}"
        )

    
    def commit(self):
        try:
            self.db.commit()
        except psycopg2.OperationalError as e:
            LOGGER.error(f"OperationalError: {e} -- attempting reconnect.")
            self.reconnect()
            self.db.commit()


class CRUD(Database):
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        super().__init__(host, port, user, password, database)

    # CRUD FUNCTIONS
    def create_table(self, table_name: str, columns: str) -> None:
        """
        Create a table with explicit locking to prevent deadlocks.
        """
        try:
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
            self.safe_execute(query)
            self.commit()
        except psycopg2.errors.DeadlockDetected as e:
            LOGGER.error(f"Deadlock detected while creating table '{table_name}': {e}")
            self.db.rollback()
        except Exception as e:
            LOGGER.error(f"Error creating table: {e}")
            self.db.rollback()

    def create_index(self, table_name: str, index_name: str, columns: str) -> None:
        """
        Create an index on a table with explicit locking to prevent deadlocks.
        """
        try:
            query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
            self.safe_execute(query)
            self.commit()
        except psycopg2.errors.DeadlockDetected as e:
            LOGGER.error(f"Deadlock detected while creating index '{index_name}' on table '{table_name}': {e}")
            self.db.rollback()
        except Exception as e:
            LOGGER.error(f"Error creating index: {e}")
            self.db.rollback()

    def drop_table(self, table_name: str) -> None:
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.safe_execute(query)
        self.commit()

    def insert(self, table_name: str, columns: str, values: list) -> None:
        placeholders = ", ".join(["%s"] * len(values))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.safe_execute(query, values)
        self.commit()

    def read(self, table_name: str, columns: str = "*", conditions: dict = {}, special: str = "") -> list:
        query = f"SELECT {columns} FROM {table_name}"
        if conditions:
            condition_clause = " AND ".join([f"{col} = %s" for col in conditions.keys()])
            query += f" WHERE {condition_clause}"
            values = list(conditions.values())
        else:
            values = []
        if special != "":
            query += f" {special}"
        return self.execute(query, values)

    def update(self, table_name: str, set_values: dict = {}, conditions: dict = {}, special: str = "") -> None:
        """
        Update method for database.
        
        :param table: str, the name of the table
        :param set_values: dict, column-value pairs to update
        :param conditions: dict, column-value pairs for WHERE clause
        """
        set_clause = ", ".join([f"{col} = %s" for col in set_values.keys()])
        query = f"UPDATE {table_name} SET {set_clause}"
        
        values = list(set_values.values())
        
        if conditions:
            condition_clause = " AND ".join([f"{col} = %s" for col in conditions.keys()])
            query += f" WHERE {condition_clause}"
            values += list(conditions.values())
        
        if special != "":
            query += f" {special}"
        
        self.safe_execute(query, values)
        self.commit()

    def delete(self, table_name: str, conditions: dict = {}) -> None:
        condition_clause = " AND ".join([f"{col} = %s" for col in conditions.keys()])
        query = f"DELETE FROM {table_name} WHERE {condition_clause}"
        values = list(conditions.values())
        self.safe_execute(query, values)
        self.commit()


    def add_column(self, table_name: str, column_definition: str) -> None:
        """
        Add a new column to an existing table after checking its existence.
        """
        try:
            self.safe_execute(f"LOCK TABLE {table_name} IN ACCESS EXCLUSIVE MODE")
            query = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
            self.safe_execute(query)
            self.commit()
        except psycopg2.errors.DeadlockDetected as e:
            LOGGER.error(f"Deadlock detected while adding column to table '{table_name}': {e}")
            self.db.rollback()
        except Exception as e:
            LOGGER.error(f"Error adding column: {e}")
            self.db.rollback()

    # HELPER FUNCTIONS
    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in the database
        returns True if exists, False otherwise
        """
        query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
        result = self.execute(query)
        return result[0][0]

    def column_exists(self, table_name: str, column_name: str) -> int:
        """
        Check if a column exists in a table
        returns 1 if exists, 0 otherwise
        """
        query = f"""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name='{table_name}' 
            AND column_name='{column_name}'
        )
        """
        result = self.execute(query)
        return 1 if result[0][0] else 0

    def value_exists(self, table_name: str, conditions: dict = {}) -> int:
        """
        Check if a value exists in a column based on given conditions
        returns 1 if exists, 0 otherwise
        """
        condition_clause = " AND ".join([f"{col} = %s" for col in conditions.keys()])
        query = f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE {condition_clause})"
        values = list(conditions.values())
        result = self.execute(query, values)
        return 1 if result[0][0] else 0