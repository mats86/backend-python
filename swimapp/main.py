import os
import sqlalchemy
import bcrypt
from flask import Flask, request, jsonify
from sqlalchemy.pool import QueuePool
from flask_cors import CORS
import logging

# Entfernt, da SSH-Tunneling nicht mehr verwendet wird
# from sshtunnel import SSHTunnelForwarder
import pymysql

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

app = Flask(__name__)
CORS(app)

# Globale Variablen für die Datenbankkonfiguration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

# Erstelle eine globale Engine-Instanz
engine = sqlalchemy.create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    poolclass=QueuePool,
    max_overflow=10,
    pool_size=5,
)

# Tabelle-Definition
metadata = sqlalchemy.MetaData()
user_credentials = sqlalchemy.Table(
    'Logindaten',
    metadata,
    sqlalchemy.Column('LoginID', sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column('User', sqlalchemy.String),
    sqlalchemy.Column('Pass', sqlalchemy.String),
)

# Erstelle die Tabelle, wenn sie nicht existiert
with engine.connect() as conn:
    if not conn.dialect.has_table(conn, "Logindaten"):
        user_credentials.create(engine)

@app.route('/registerUser', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        username = data.get('username')
        received_password = data.get('password')

        # Hashen des Passworts vor dem Speichern in die Datenbank
        password = bcrypt.hashpw(received_password.encode('utf-8'), bcrypt.gensalt())

        with engine.connect() as conn:
            with conn.begin() as transaction:
                try:
                    insert_query = user_credentials.insert().values(User=username, Pass=password.decode('utf-8'))
                    result = conn.execute(insert_query)

                    # Commit der Transaktion
                    transaction.commit()
                    return jsonify({'message': 'Benutzer erfolgreich hinzugefügt.'}), 200
                except Exception as e:
                    # Rollback der Transaktion im Fehlerfall
                    transaction.rollback()
                    return jsonify({'error': str(e)}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
