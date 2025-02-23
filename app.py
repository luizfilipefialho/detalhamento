import streamlit as st
import sqlite3
from typing import List, Optional
import json

# Configuração da página (deve ser a primeira instrução)
st.set_page_config(
    page_title="Processos Financeiros - Configuração",
    page_icon=":money_with_wings:",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "https://github.com/seu-repositorio/bugreport",
        "About": "Automação e configuração de processos financeiros."
    }
)

# --- Funções do Banco de Dados ---
def get_db_connection():
    # Retorna uma conexão SQLite
    return sqlite3.connect("processos.db", check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS cliente (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_empresa TEXT,
                logo BLOB,
                nome_pessoa TEXT,
                cargo TEXT,
                email TEXT,
                celular TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS cnpjs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE,
                cliente_id INTEGER,
                FOREIGN KEY(cliente_id) REFERENCES cliente(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS processos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                tipo TEXT,
                frequencia TEXT,
                cliente_id INTEGER,
                configurado INTEGER DEFAULT 0,
                FOREIGN KEY(cliente_id) REFERENCES cliente(id)
            )
        ''')
        # Tabela para configurações avançadas do processo
        c.execute('''
            CREATE TABLE IF NOT EXISTS processo_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processo_id INTEGER,
                cnpjs TEXT,
                layouts TEXT,
                encadeamento TEXT,
                retorno TEXT,
                FOREIGN KEY(processo_id) REFERENCES processos(id)
            )
        ''')
        conn.commit()

# --- Funções de carregamento e inserção de dados ---
@st.cache_data(ttl=300)
def load_cliente(cliente_id: int) -> Optional[tuple]:
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM cliente WHERE id = ?", (cliente_id,)).fetchone()

@st.cache_data(ttl=300)
def load_cnpjs(cliente_id: int) -> List[tuple]:
    with get_db_connection() as conn:
        return conn.execute("SELECT id, numero FROM cnpjs WHERE cliente_id = ?", (cliente_id,)).fetchall()

def add_cnpj(cliente_id: int, numero: str) -> bool:
    with get_db_connection() as conn:
        try:
            conn.execute("INSERT INTO cnpjs (numero, cliente_id) VALUES (?, ?)", (numero, cliente_id))
            conn.commit()
            st.cache_data.clear()  # Limpa cache para atualizar a lista
            return True
        except sqlite3.IntegrityError:
            st.warning(f"CNPJ {numero} já existe!")
        return False

@st.cache_data(ttl=300)
def load_processos(cliente_id: int) -> List[tuple]:
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT id, nome, tipo, frequencia FROM processos WHERE cliente_id = ?",
            (cliente_id,)
        ).fetchall()

def save_cliente(nome_empresa, logo, nome_pessoa, cargo, email, celular):
    with get_db_connection() as conn:
        c = conn.cursor()
        if st.session_state.cliente_id:
            c.execute("""
                UPDATE cliente
                SET nome_empresa=?, logo=?, nome_pessoa=?, cargo=?, email=?, celular=?
                WHERE id=?
            """, (nome_empresa, logo, nome_pessoa, cargo, email, celular, st.session_state.cliente_id))
        else:
            c.execute("""
                INSERT INTO cliente (nome_empresa, logo, nome_pessoa, cargo, email, celular)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome_empresa, logo, nome_pessoa, cargo, email, celular))
            st.session_state.cliente_id = c.lastrowid
        conn.commit()
    st.cache_data.clear()
    st.session_state.tela = "visao_cliente"
    st.rerun()

# --- Inicialização do Banco de Dados e Session State ---
init_db()
st.session_state.setdefault("cliente_id", None)
st.session_state.setdefault("tela", "inicial")
# Para agrupamento, armazenamos os CNPJs selecionados (chave "selected_cnpjs")
st.session_state.setdefault("selected_cnpjs", [])
# Flag para indicar se o processo foi criado com agrupamento
st.session_state.setdefault("grupar", False)

# --- Telas do App ---
def tela_inicial():
    """Tela para cadastro do cliente."""
    st.title("Cadastro de Cliente")
    st.markdown("<p style='color: #6c757d; font-size: 18px;'>Preencha os dados do cliente para iniciar o cadastro.</p>", unsafe_allow_html=True)
    
    cliente = load_cliente(st.session_state.cliente_id) if st.session_state.cliente_id else None
    
    with st.form("cliente_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            nome_empresa = st.text_input("Nome da Empresa", value=cliente[1] if cliente else "Minha Empresa")
            nome_pessoa  = st.text_input("Nome Completo", value=cliente[3] if cliente else "")
            cargo        = st.text_input("Cargo", value=cliente[4] if cliente else "")
        with col2:
            logo_file = st.file_uploader("Logo do Cliente", type=["png", "jpg", "jpeg"])
            email     = st.text_input("E-mail", value=cliente[5] if cliente else "")
            celular   = st.text_input("Celular", value=cliente[6] if cliente else "")
        
        if st.form_submit_button("Salvar Cliente"):
            logo_bytes = logo_file.read() if logo_file is not None else None
            save_cliente(nome_empresa, logo_bytes, nome_pessoa, cargo, email, celular)
            st.success("Cliente salvo com sucesso!")
    st.markdown("<hr>", unsafe_allow_html=True)
    st.info("Após preencher os dados, clique em 'Salvar Cliente' para prosseguir.")

def tela_visao_cliente():
    """Exibe os detalhes do cliente e gerencia CNPJs."""
    cliente = load_cliente(st.session_state.cliente_id)
    if not cliente:
        st.error("Cliente não encontrado!")
        st.session_state.tela = "inicial"
        st.rerun()
        return
    st.title(f"📁 {cliente[1]} - Detalhes do Cliente")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Informações Principais")
        st.write(f"👤 <b>Nome:</b> {cliente[3]}", unsafe_allow_html=True)
        st.write(f"🎓 <b>Cargo:</b> {cliente[4]}", unsafe_allow_html=True)
        st.write(f"📧 <b>E-mail:</b> {cliente[5]}", unsafe_allow_html=True)
        st.write(f"📱 <b>Celular:</b> {cliente[6]}", unsafe_allow_html=True)
    with col2:
        if cliente[2]:
            st.image(cliente[2], width=150)
    
    st.subheader("CNPJs Cadastrados")
    cnpjs = load_cnpjs(st.session_state.cliente_id)
    if cnpjs:
        for cnpj in cnpjs:
            st.write(f"✅ {cnpj[1]}")
    novo_cnpj = st.text_input("Adicionar Novo CNPJ", key="novo_cnpj")
    if st.button("Adicionar CNPJ") and novo_cnpj:
        if add_cnpj(st.session_state.cliente_id, novo_cnpj):
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("✏️ Editar Cliente", on_click=lambda: st.session_state.update(tela="inicial"))
    with col2:
        st.button("⏭️ Continuar para Processos", on_click=lambda: st.session_state.update(tela="processos"))

def tela_processos():
    """Tela para criação e listagem de processos."""
    st.title("⚙️ Configuração de Processos")
    st.write("Gerencie e adicione processos financeiros para este cliente.")
    processos = load_processos(st.session_state.cliente_id)
    if processos:
        st.subheader("🔍 Processos Existentes")
        for proc in processos:
            if st.button(f"🔗 {proc[1]} - {proc[2]} ({proc[3]})", key=f"processo_{proc[0]}"):
                st.session_state.processo_id = proc[0]
                st.session_state.tela = "configurar_processo"
                print(f"DEBUG: Abrindo processo {proc[0]}")  # Debug print
                st.rerun()
    
    with st.form("novo_processo"):
        nome_processo = st.text_input("Nome do Processo")
        tipo_processo = st.selectbox("Tipo de Processo", ["Análise Tabular", "Conciliação", "Saldos", "Pagamentos"])
        frequencia = st.selectbox("Frequência", ["Diária", "Semanal", "Mensal"])
        agrupar = st.checkbox("Agrupar CNPJs para layouts diferentes?")
        if agrupar:
            cnpjs = load_cnpjs(st.session_state.cliente_id)
            cnpj_options = [cnpj[1] for cnpj in cnpjs] if cnpjs else []
            selected_cnpjs = st.multiselect("Selecione os CNPJs para agrupamento", options=cnpj_options)
            st.session_state.selected_cnpjs = selected_cnpjs
            st.session_state.grupar = True
            print(f"DEBUG: Agrupar selecionado com CNPJs: {selected_cnpjs}")  # Debug print
        if st.form_submit_button("Salvar Processo") and nome_processo:
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO processos (nome, tipo, frequencia, cliente_id)
                    VALUES (?, ?, ?, ?)
                """, (nome_processo, tipo_processo, frequencia, st.session_state.cliente_id))
                conn.commit()
                proc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"DEBUG: Processo criado com ID: {proc_id}")  # Debug print
            st.session_state.processo_id = proc_id
            st.cache_data.clear()
            if st.session_state.get("grupar", False):
                st.session_state.tela = "agrupamento"
            else:
                st.session_state.tela = "configurar_processo"
            st.rerun()

def tela_configurar_processo():
    """
    Tela para configurar um processo individual.
    Para processos não agrupados, carrega os dados salvos (layouts, retorno) para edição.
    """
    processo_id = st.session_state.get("processo_id")
    if not processo_id:
        st.error("Processo não selecionado.")
        st.session_state.tela = "processos"
        st.rerun()

    with get_db_connection() as conn:
        processo = conn.execute(
            "SELECT id, nome, tipo, frequencia FROM processos WHERE id = ?", 
            (processo_id,)
        ).fetchone()
        proc_conf = conn.execute(
            "SELECT * FROM processo_config WHERE processo_id = ?", (processo_id,)
        ).fetchone()
    print(f"DEBUG: Abrindo tela_configurar_processo para processo {processo_id}")  # Debug

    # Se já existir configuração, carrega os valores
    if proc_conf:
        try:
            default_cnpjs = json.loads(proc_conf[2]) if proc_conf[2] else []
        except Exception as e:
            print("DEBUG: Erro ao carregar cnpjs salvos:", e)
            default_cnpjs = []
        try:
            default_layouts = json.loads(proc_conf[3]) if proc_conf[3] else []
        except Exception as e:
            print("DEBUG: Erro ao carregar layouts salvos:", e)
            default_layouts = []
        try:
            default_retorno = json.loads(proc_conf[5]) if proc_conf[5] else {}
        except Exception as e:
            print("DEBUG: Erro ao carregar retorno salvos:", e)
            default_retorno = {}
    else:
        default_cnpjs = []
        default_layouts = []
        default_retorno = {}

    st.title(f"Configuração do Processo: {processo[1]}")
    st.markdown("---")

    # Nesta tela não permitimos alterar os CNPJs (já definidos no agrupamento ou na criação)
    st.header("CNPJs Associados")
    st.write("CNPJs deste processo:", default_cnpjs)

    # Passo: Definição dos Layouts de Entrada
    st.header("Definição dos Layouts de Entrada")
    # Se houver configurações salvas, usa o número salvo; senão, valor padrão 1
    num_layouts = st.number_input(
        "Número de Layouts de Entrada", 
        min_value=1, 
        step=1, 
        value=len(default_layouts) if default_layouts else 1, 
        key="num_layouts"
    )
    layouts_config = []
    # Se houver configurações salvas, vamos tentar pré-preencher
    for i in range(1, num_layouts + 1):
        st.markdown(f"**Layout de Entrada #{i}**")
        # Se existe um layout salvo para este índice, utiliza-o; caso contrário, deixa em branco
        if default_layouts and i <= len(default_layouts):
            layout_salvo = default_layouts[i-1]
            default_tipo = layout_salvo.get("tipo", "Arquivo")
        else:
            default_tipo = "Arquivo"
        layout_tipo = st.radio(
            f"Selecione o tipo de entrada para o layout #{i}",
            options=["Arquivo", "Encadeamento"],
            index=0 if default_tipo=="Arquivo" else 1,
            key=f"layout_tipo_{i}"
        )
        if layout_tipo == "Arquivo":
            if default_layouts and i <= len(default_layouts) and layout_salvo.get("modo") in ["novo", "existente"]:
                modo_default = layout_salvo.get("modo")
            else:
                modo_default = "novo"
            modo = st.radio(
                f"Modo para o layout #{i}",
                options=["novo", "existente"],
                index=0 if modo_default=="novo" else 1,
                key=f"modo_layout_{i}"
            )
            if modo == "novo":
                if default_layouts and i <= len(default_layouts):
                    tipo_arquivo_default = layout_salvo.get("arquivo_tipo", "Excel")
                    nome_layout_default = layout_salvo.get("nome", "")
                else:
                    tipo_arquivo_default = "Excel"
                    nome_layout_default = ""
                tipo_arquivo = st.selectbox(
                    f"Tipo de Arquivo para o layout #{i}",
                    options=[
                        "Excel", "CSV", "TXT", "OFX", "CNAB", "SPED", "EDI",
                        "XML", "SWIFT", "Extrato Adquirente", "API", "Banco de Dados", "PDF"
                    ],
                    index=["Excel", "CSV", "TXT", "OFX", "CNAB", "SPED", "EDI",
                           "XML", "SWIFT", "Extrato Adquirente", "API", "Banco de Dados", "PDF"].index(tipo_arquivo_default),
                    key=f"tipo_layout_{i}"
                )
                nome_layout = st.text_input(
                    f"Nome do Layout #{i}",
                    value=nome_layout_default,
                    key=f"nome_layout_{i}"
                )
                layouts_config.append({
                    "tipo": "Arquivo",
                    "modo": "novo",
                    "arquivo_tipo": tipo_arquivo,
                    "nome": nome_layout
                })
            else:
                escolha_layout = st.selectbox(
                    f"Selecione um layout para a entrada #{i}",
                    options=[
                        "Excel - Extrato.xlsx", 
                        "CSV - Transacoes.csv", 
                        "PDF - Relatorio.pdf"
                    ],
                    index=0,
                    key=f"layout_escolha_{i}"
                )
                layouts_config.append({
                    "tipo": "Arquivo",
                    "modo": "existente",
                    "arquivo": escolha_layout
                })
        else:  # Caso "Encadeamento"
            processos_existentes = load_processos(st.session_state.cliente_id)
            processos_filtrados = [proc for proc in processos_existentes if proc[0] != processo_id]
            if processos_filtrados:
                processo_encadeado = st.selectbox(
                    f"Selecione o processo de origem para a entrada #{i}",
                    options=[f"{proc[1]} - {proc[2]}" for proc in processos_filtrados],
                    key=f"proc_encadeado_{i}"
                )
                layouts_config.append({
                    "tipo": "Encadeamento",
                    "processo": processo_encadeado
                })
            else:
                st.info("Nenhum processo disponível para encadeamento.")
                layouts_config.append({
                    "tipo": "Encadeamento",
                    "processo": None
                })

    st.markdown("---")

    # Passo: Especificação de Arquivos de Retorno (Opcional)
    st.header("Especificação de Arquivos de Retorno (Opcional)")
    usar_retorno = st.checkbox("Este processo requer arquivos de retorno?")
    retorno_config = {}
    if usar_retorno:
        if default_retorno:
            tipo_retorno_default = default_retorno.get("tipo", "CSV")
            proposito_default = default_retorno.get("proposito", "")
        else:
            tipo_retorno_default = "CSV"
            proposito_default = ""
        tipo_retorno = st.selectbox(
            "Tipo de Arquivo de Retorno",
            ["CSV", "XML", "TXT", "JSON"],
            index=["CSV", "XML", "TXT", "JSON"].index(tipo_retorno_default),
            key="retorno_tipo"
        )
        proposito_retorno = st.text_input(
            "Propósito do Arquivo de Retorno",
            value=proposito_default,
            key="retorno_proposito"
        )
        retorno_config = {
            "tipo": tipo_retorno,
            "proposito": proposito_retorno
        }

    st.markdown("---")
    if st.button("Gerenciar Layouts", key="gerenciar_layouts"):
        st.session_state.tela = "layouts"
        st.rerun()

    if st.button("Salvar Configuração do Processo"):
        print(f"DEBUG: Salvando configuração para processo {processo_id}")  # Debug
        with get_db_connection() as conn:
            proc_conf = conn.execute("SELECT id FROM processo_config WHERE processo_id = ?", (processo_id,)).fetchone()
            if proc_conf:
                conn.execute("""
                    UPDATE processo_config 
                    SET layouts = ?, encadeamento = ?, retorno = ?
                    WHERE processo_id = ?
                """, (
                    json.dumps(layouts_config),
                    "",
                    json.dumps(retorno_config),
                    processo_id
                ))
            else:
                conn.execute("""
                    INSERT INTO processo_config (processo_id, layouts, encadeamento, retorno)
                    VALUES (?, ?, ?, ?)
                """, (
                    processo_id,
                    json.dumps(layouts_config),
                    "",
                    json.dumps(retorno_config)
                ))
            conn.execute("UPDATE processos SET configurado = 1 WHERE id = ?", (processo_id,))
            conn.commit()
        print("DEBUG: Configuração salva com sucesso!")  # Debug
        st.success("Configuração do processo salva com sucesso!")
        st.session_state.tela = "processos"
        st.rerun()

    if st.button("Voltar para Processos"):
        st.session_state.tela = "processos"
        st.rerun()

def tela_agrupamento():
    """Tela para definir os grupos de CNPJs a partir da seleção feita na criação do processo."""
    st.title("Agrupamento de CNPJs")
    selected_cnpjs = st.session_state.get("selected_cnpjs", [])
    if not selected_cnpjs:
        st.info("Nenhum CNPJ selecionado para agrupamento.")
        if st.button("Voltar"):
            st.session_state.tela = "configurar_processo"
            st.rerun()
        return

    st.subheader("Defina os grupos para os CNPJs:")
    group_dict = {}
    for cnpj in selected_cnpjs:
        grupo = st.text_input(f"Grupo para CNPJ {cnpj}", key=f"agrupamento_{cnpj}", value="1")
        group_dict[cnpj] = grupo
    st.session_state.group_dict = group_dict
    print(f"DEBUG: group_dict = {group_dict}")  # Debug

    st.subheader("Resumo dos Grupos:")
    distinct_groups = {}
    for cnpj, grupo in group_dict.items():
        distinct_groups.setdefault(grupo, []).append(cnpj)
    for grupo, cnpjs in distinct_groups.items():
        st.write(f"Grupo {grupo}: {', '.join(cnpjs)}")
    
    if st.button("Confirmar Agrupamento"):
        original_processo_id = st.session_state.get("processo_id")
        with get_db_connection() as conn:
            processo = conn.execute(
                "SELECT id, nome, tipo, frequencia, cliente_id FROM processos WHERE id = ?", 
                (original_processo_id,)
            ).fetchone()
        if not processo:
            st.error("Processo original não encontrado.")
            return
        
        sorted_grupos = sorted(distinct_groups.keys())
        # Atualiza o processo original com o primeiro grupo
        first_grupo = sorted_grupos[0]
        cnpjs_grupo = distinct_groups[first_grupo]
        with get_db_connection() as conn:
            conn.execute("UPDATE processos SET nome = ? WHERE id = ?", (f"{processo[1]} - Grupo {first_grupo}", original_processo_id))
            conn.execute("""
                INSERT OR REPLACE INTO processo_config (processo_id, cnpjs, layouts, encadeamento, retorno)
                VALUES (?, ?, ?, ?, ?)
            """, (
                original_processo_id,
                json.dumps(cnpjs_grupo),
                json.dumps([]),
                "",
                json.dumps({})
            ))
            conn.commit()
        # Cria novos processos para os demais grupos
        for grupo in sorted_grupos[1:]:
            cnpjs_grupo = distinct_groups[grupo]
            with get_db_connection() as conn:
                conn.execute("""
                    INSERT INTO processos (nome, tipo, frequencia, cliente_id, configurado)
                    VALUES (?, ?, ?, ?, ?)
                """, (f"{processo[1]} - Grupo {grupo}", processo[2], processo[3], processo[4], 1))
                new_proc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.execute("""
                    INSERT INTO processo_config (processo_id, cnpjs, layouts, encadeamento, retorno)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_proc_id,
                    json.dumps(cnpjs_grupo),
                    json.dumps([]),
                    "",
                    json.dumps({})
                ))
                conn.commit()
        print("DEBUG: Processos agrupados criados com sucesso!")  # Debug
        st.success("Processos agrupados criados com sucesso!")
        st.session_state.pop("group_dict", None)
        st.session_state.pop("selected_cnpjs", None)
        st.session_state.grupar = False
        st.session_state.tela = "processos"
        st.rerun()
    
    if st.button("Voltar"):
        st.session_state.tela = "configurar_processo"
        st.rerun()

def tela_layouts():
    st.title("Gerenciamento de Layouts")
    processo_id = st.session_state.get("processo_id")
    with get_db_connection() as conn:
        proc_conf = conn.execute("SELECT layouts FROM processo_config WHERE processo_id = ?", (processo_id,)).fetchone()
    layouts_config = []
    if proc_conf and proc_conf[0]:
        try:
            layouts_config = json.loads(proc_conf[0])
        except Exception as e:
            print("DEBUG: Erro ao carregar layouts:", e)
    st.subheader("Layouts Criados")
    if layouts_config:
        for idx, layout in enumerate(layouts_config):
            st.write(f"Layout {idx+1}: {layout}")
    else:
        st.info("Nenhum layout criado.")
    
    if st.button("Adicionar Novo Layout"):
        st.session_state.tela = "adicionar_layout"
        st.rerun()
    
    if st.button("Voltar"):
        st.session_state.tela = "configurar_processo"
        st.rerun()

def tela_adicionar_layout():
    st.title("Adicionar Novo Layout")
    tipo_layout = st.radio("Tipo de Layout", ["Arquivo", "Encadeamento"])
    if tipo_layout == "Arquivo":
        modo = st.radio("Modo", ["novo", "existente"])
        if modo == "novo":
            tipo_arquivo = st.selectbox("Tipo de Arquivo", ["Excel", "CSV", "TXT", "OFX", "CNAB", "SPED", "EDI", "XML", "SWIFT", "Extrato Adquirente", "API", "Banco de Dados", "PDF"])
            nome_layout = st.text_input("Nome do Layout")
            novo_layout = {"tipo": "Arquivo", "modo": "novo", "arquivo_tipo": tipo_arquivo, "nome": nome_layout}
        else:
            arquivo = st.selectbox("Selecione um layout existente", ["Excel - Extrato.xlsx", "CSV - Transacoes.csv", "PDF - Relatorio.pdf"])
            novo_layout = {"tipo": "Arquivo", "modo": "existente", "arquivo": arquivo}
    else:
        processos_existentes = load_processos(st.session_state.cliente_id)
        processos_filtrados = [proc for proc in processos_existentes if proc[0] != st.session_state.processo_id]
        if processos_filtrados:
            processo_encadeado = st.selectbox("Selecione o processo de origem", [f"{proc[1]} - {proc[2]}" for proc in processos_filtrados])
        else:
            processo_encadeado = None
        novo_layout = {"tipo": "Encadeamento", "processo": processo_encadeado}

    if st.button("Salvar Novo Layout"):
        processo_id = st.session_state.processo_id
        with get_db_connection() as conn:
            proc_conf = conn.execute("SELECT id, layouts FROM processo_config WHERE processo_id = ?", (processo_id,)).fetchone()
            layouts_config = []
            if proc_conf and proc_conf[1]:
                try:
                    layouts_config = json.loads(proc_conf[1])
                except Exception as e:
                    print("DEBUG: Erro ao carregar layouts para edição:", e)
            layouts_config.append(novo_layout)
            if proc_conf:
                conn.execute("UPDATE processo_config SET layouts = ? WHERE id = ?", (json.dumps(layouts_config), proc_conf[0]))
            else:
                conn.execute("INSERT INTO processo_config (processo_id, layouts) VALUES (?, ?)", (processo_id, json.dumps(layouts_config)))
            conn.commit()
        print("DEBUG: Layout adicionado!")  # Debug
        st.success("Layout adicionado!")
        st.session_state.tela = "layouts"
        st.rerun()

    if st.button("Voltar"):
        st.session_state.tela = "layouts"
        st.rerun()

# --- Controle de Navegação das Telas ---
telas = {
    "inicial": tela_inicial,
    "visao_cliente": tela_visao_cliente,
    "processos": tela_processos,
    "configurar_processo": tela_configurar_processo,
    "agrupamento": tela_agrupamento,
    "layouts": tela_layouts,
    "adicionar_layout": tela_adicionar_layout
}

# Chama a tela vigente conforme st.session_state.tela
tela = st.session_state.tela
if tela in telas:
    telas[tela]()
else:
    st.error("Tela não encontrada!")
    st.session_state.tela = "inicial"
    st.rerun()
