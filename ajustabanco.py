import sqlite3

def main():
    # Caminho para o arquivo do seu banco
    db_path = "processos.db"

    # Conecta ao banco
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Executa o ALTER TABLE
    try:
        c.execute("ALTER TABLE processos ADD COLUMN descricao TEXT")
        conn.commit()
        print("Coluna 'descricao' adicionada com sucesso!")
    except sqlite3.OperationalError as e:
        print(f"Erro ao adicionar coluna: {e}")

    conn.close()

if __name__ == "__main__":
    main()
