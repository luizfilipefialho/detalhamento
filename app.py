import streamlit as st
import sqlite3
from typing import List, Optional
import json
import unicodedata
import streamlit.components.v1 as components

# ------------------------------------------------------------------
# Configuração da página (deve ser a primeira instrução)
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Processos Financeiros - Configuração",
    page_icon=":money_with_wings:",
    initial_sidebar_state="auto",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "https://github.com/seu-repositorio/bugreport",
        "About": "Automação e configuração de processos financeiros."
    }
)

# ------------------------------------------------------------------
# Funções do Banco de Dados
# ------------------------------------------------------------------
def get_db_connection():
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

# ------------------------------------------------------------------
# Funções de carregamento e inserção de dados
# ------------------------------------------------------------------
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
            st.cache_data.clear()
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

# ------------------------------------------------------------------
# Inicialização do Banco de Dados e Session State
# ------------------------------------------------------------------
init_db()
st.session_state.setdefault("cliente_id", None)
st.session_state.setdefault("tela", "login")
st.session_state.setdefault("selected_cnpjs", [])
st.session_state.setdefault("grupar", False)

# ------------------------------------------------------------------
# Função para remover acentuação e caracteres especiais
# ------------------------------------------------------------------
def remove_accents(s: str) -> str:
    """
    Remove acentuação de uma string para evitar quebra no Mermaid.js
    """
    nfkd = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])

# ------------------------------------------------------------------
# Telas do App
# ------------------------------------------------------------------
def tela_login():
    """
    Tela de login simples com estilo básico e seguro.
    """
    st.markdown("""
        <style>
            .stApp {
                background-color: #f0f2f6;
            }
            div.stButton > button:first-child {
                width: 100%;
            }
            .login-title {
                font-size: 28px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 0px;
                color: #333;
            }
            .login-subtitle {
                font-size: 14px;
                text-align: center;
                margin-bottom: 30px;
                color: #666;
            }
            [data-testid="stForm"] {
                background-color: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 8px 16px rgba(0,0,0,0.15);
            }
        </style>
    """, unsafe_allow_html=True)

    st.write("#")
    login_container = st.container()

    with login_container:
        with st.form("login_form"):
            col_logo1, col_logo2, col_logo3 = st.columns([1,2,1])
            with col_logo2:
                # Ajuste o caminho da imagem conforme a sua necessidade
                st.image("logo_dattos.png", width=250)

            st.markdown('<div class="login-title">Gerador de Detalhamento de Escopo Dattos</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Bem-vindo ao sistema que gera o detalhamento de escopo para seus processos financeiros.<br>Insira seu código de cliente para prosseguir.</div>', unsafe_allow_html=True)

            codigo = st.text_input("Digite o código do cliente:", placeholder="Ex: 123")

            col1, col2 = st.columns(2)
            with col1:
                entrar = st.form_submit_button("Entrar")
            with col2:
                cadastrar = st.form_submit_button("Cadastrar Novo Cliente")

            if entrar:
                try:
                    codigo_int = int(codigo)
                except ValueError:
                    st.error("Por favor, digite um código numérico válido.")
                    return
                cliente = load_cliente(codigo_int)
                if cliente:
                    st.session_state.cliente_id = codigo_int
                    st.success("Cliente encontrado! Carregando informações...")
                    st.session_state.tela = "visao_cliente"
                    st.rerun()
                else:
                    st.error("Código não encontrado. Verifique ou cadastre um novo cliente.")

            if cadastrar:
                st.session_state.tela = "inicial"
                st.rerun()

def tela_inicial():
    """Tela para cadastro de novo cliente."""
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
    """Tela para exibir os detalhes do cliente e gerenciar CNPJs."""
    cliente = load_cliente(st.session_state.cliente_id)
    if not cliente:
        st.error("Cliente não encontrado!")
        st.session_state.tela = "login"
        st.rerun()
        return
    st.title(f"📁 {cliente[1]} - Detalhes do Cliente")
    st.write(f"**Código do Cliente:** {st.session_state.cliente_id}")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Informações Principais")
        st.write(f"👤 **Nome:** {cliente[3]}")
        st.write(f"🎓 **Cargo:** {cliente[4]}")
        st.write(f"📧 **E-mail:** {cliente[5]}")
        st.write(f"📱 **Celular:** {cliente[6]}")
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


    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    """, unsafe_allow_html=True)

    st.markdown("""
    <i class="fa-solid fa-file-csv"></i> Arquivo CSV  
    <i class="fa-solid fa-file-pdf"></i> Arquivo PDF  
    <i class="fa-solid fa-file-excel"></i> Arquivo Excel  
    <i class="fa-solid fa-file-word"></i> Arquivo Word  
    <i class="fa-solid fa-file-zipper"></i> Arquivo Zip  
    """, unsafe_allow_html=True)


def tela_processos():
    """
    Tela para listar e criar processos, além de permitir a geração de um diagrama
    selecionando um processo via selectbox.
    """
    st.title("⚙️ Configuração de Processos")
    st.write("Gerencie e adicione processos financeiros para este cliente.")

    processos = load_processos(st.session_state.cliente_id)
    
    if processos:
        st.subheader("🔍 Processos Existentes")

        # Botões para editar cada processo (opcional, pode remover se quiser apenas o selectbox)
        for proc in processos:
            if st.button(f"🔗 {proc[1]} - {proc[2]} ({proc[3]})", key=f"processo_{proc[0]}"):
                st.session_state.processo_id = proc[0]
                st.session_state.tela = "configurar_processo"
                st.rerun()

        # st.write("---")
        # st.subheader("Gerar Diagrama do Processo")

        # # Cria uma lista de opções no formato "ID - NomeDoProcesso"
        # opcoes_diagrama = [f"{p[0]} - {p[1]}" for p in processos]
        # selecao = st.selectbox("Selecione um processo para gerar o diagrama", opcoes_diagrama)

        # if st.button("Gerar Diagrama do Processo"):
        #     # Extrai o ID do processo da string "ID - Nome"
        #     proc_id_str = selecao.split(" - ")[0]
        #     proc_id = int(proc_id_str)
        #     st.session_state.processo_id = proc_id
        #     st.session_state.tela = "diagrama"
        #     st.rerun()

    else:
        st.info("Nenhum processo cadastrado para este cliente.")

    st.write("---")
    st.subheader("Criar Novo Processo")

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
    else:
        st.session_state.grupar = False

    if st.button("Salvar Processo") and nome_processo:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO processos (nome, tipo, frequencia, cliente_id)
                VALUES (?, ?, ?, ?)
            """, (nome_processo, tipo_processo, frequencia, st.session_state.cliente_id))
            conn.commit()
            proc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        st.session_state.processo_id = proc_id
        st.cache_data.clear()
        if st.session_state.get("grupar", False):
            st.session_state.tela = "agrupamento"
        else:
            st.session_state.tela = "configurar_processo"
        st.rerun()


def tela_configurar_processo():
    """
    Tela para configurar o processo (layouts, arquivos de retorno etc.) e,
    ao final, exibir dinamicamente o diagrama Mermaid do processo na mesma tela.
    Encadeamentos e Arquivos terão a mesma forma ([ ]) porém com cores diferentes.
    """
    processo_id = st.session_state.get("processo_id")
    if not processo_id:
        st.error("Processo não selecionado.")
        st.session_state.tela = "processos"
        st.rerun()

    with get_db_connection() as conn:
        processo = conn.execute(
            "SELECT id, nome, tipo, frequencia FROM processos WHERE id = ?", (processo_id,)
        ).fetchone()
        proc_conf = conn.execute(
            "SELECT * FROM processo_config WHERE processo_id = ?", (processo_id,)
        ).fetchone()

    # Carrega layouts/retorno já salvos, se existirem
    if proc_conf:
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
        default_layouts = []
        default_retorno = {}

    st.title(f"Configuração do Processo: {processo[1]}")
    st.markdown("---")
    st.header("Definição dos Layouts de Entrada")

    num_layouts = st.number_input(
        "Número de Layouts de Entrada",
        min_value=1,
        step=1,
        value=len(default_layouts) if default_layouts else 1,
        key="num_layouts"
    )
    layouts_config = []

    for i in range(1, num_layouts + 1):
        st.markdown(f"**Layout de Entrada #{i}**")

        # Carrega config antiga para este índice, se existir
        if default_layouts and i <= len(default_layouts):
            layout_salvo = default_layouts[i-1]
            default_tipo = layout_salvo.get("tipo", "Arquivo")
        else:
            layout_salvo = {}
            default_tipo = "Arquivo"

        layout_tipo = st.radio(
            f"Selecione o tipo de entrada para o layout #{i}",
            options=["Arquivo", "Encadeamento"],
            index=0 if default_tipo == "Arquivo" else 1,
            key=f"layout_tipo_{i}"
        )

        if layout_tipo == "Arquivo":
            modo_default = layout_salvo.get("modo", "novo")
            modo = st.radio(
                f"Modo para o layout #{i}",
                options=["novo", "existente"],
                index=0 if modo_default == "novo" else 1,
                key=f"modo_layout_{i}"
            )
            if modo == "novo":
                tipo_arquivo_default = layout_salvo.get("arquivo_tipo", "Excel")
                nome_layout_default = layout_salvo.get("nome", "")
                tipo_arquivo = st.selectbox(
                    f"Tipo de Arquivo para o layout #{i}",
                    options=["Excel", "CSV", "TXT", "OFX", "CNAB", "SPED", "EDI", "XML",
                             "SWIFT", "Extrato Adquirente", "API", "Banco de Dados", "PDF"],
                    index=0 if tipo_arquivo_default not in ["Excel","CSV","TXT","OFX","CNAB",
                                                            "SPED","EDI","XML","SWIFT","Extrato Adquirente",
                                                            "API","Banco de Dados","PDF"]
                          else ["Excel","CSV","TXT","OFX","CNAB","SPED","EDI","XML","SWIFT",
                                "Extrato Adquirente","API","Banco de Dados","PDF"].index(tipo_arquivo_default),
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
                    options=["Excel - Extrato.xlsx", "CSV - Transacoes.csv", "PDF - Relatorio.pdf"],
                    index=0,
                    key=f"layout_escolha_{i}"
                )
                layouts_config.append({
                    "tipo": "Arquivo",
                    "modo": "existente",
                    "arquivo": escolha_layout
                })

        else:
            # Encadeamento
            processos_existentes = load_processos(st.session_state.cliente_id)
            processos_filtrados = [proc for proc in processos_existentes if proc[0] != processo_id]
            if processos_filtrados:
                processo_encadeado = st.selectbox(
                    f"Selecione o processo de origem para a entrada #{i}",
                    options=[f"{proc[1]} - {proc[2]}" for proc in processos_filtrados],
                    key=f"proc_encadeado_{i}"
                )
            else:
                st.info("Nenhum processo disponível para encadeamento.")
                processo_encadeado = None
            layouts_config.append({
                "tipo": "Encadeamento",
                "processo": processo_encadeado
            })

    st.markdown("---")
    st.header("Especificação de Arquivos de Retorno (Opcional)")
    usar_retorno = st.checkbox("Este processo requer arquivos de retorno?")
    retorno_config = {}
    if usar_retorno:
        tipo_retorno_default = default_retorno.get("tipo", "CSV")
        proposito_default = default_retorno.get("proposito", "")
        tipo_retorno = st.selectbox(
            "Tipo de Arquivo de Retorno",
            ["CSV", "XML", "TXT", "JSON"],
            index=0 if tipo_retorno_default not in ["CSV","XML","TXT","JSON"]
                  else ["CSV","XML","TXT","JSON"].index(tipo_retorno_default),
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

    if st.button("Salvar Configuração do Processo"):
        print(f"DEBUG: Salvando configuração para processo {processo_id}")
        with get_db_connection() as conn:
            existing_conf = conn.execute(
                "SELECT id FROM processo_config WHERE processo_id = ?",
                (processo_id,)
            ).fetchone()
            if existing_conf:
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
        st.success("Configuração do processo salva com sucesso!")
        st.rerun()

    if st.button("Voltar para Processos"):
        st.session_state.tela = "processos"
        st.rerun()

    st.markdown("---")
    st.write("### Visualização do Diagrama do Processo")

    # Depois de tudo, exibimos o diagrama atual (se existir config)
    # Recarregamos a config para refletir as mudanças salvas (ou as antigas, se não salvou)
    with get_db_connection() as conn:
        re_proc_conf = conn.execute(
            "SELECT layouts, retorno FROM processo_config WHERE processo_id = ?",
            (processo_id,)
        ).fetchone()

    if not re_proc_conf:
        st.info("Ainda não há configurações para gerar um diagrama.")
        return

    layouts_str, retorno_str = re_proc_conf
    final_layouts = []
    final_retorno = {}

    if layouts_str:
        try:
            final_layouts = json.loads(layouts_str)
        except Exception as e:
            print("DEBUG: Erro ao carregar layouts (diagrama):", e)
    if retorno_str:
        try:
            final_retorno = json.loads(retorno_str)
        except Exception as e:
            print("DEBUG: Erro ao carregar retorno (diagrama):", e)

    # Gera o diagrama Mermaid
    import unicodedata
    def remove_accents(s: str) -> str:
        nfkd = unicodedata.normalize('NFKD', s)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    nome_proc = remove_accents(processo[1])

    mermaid_code = [
        "flowchart LR",
        "  %% Estilos Modernos",
        "  classDef arquivo fill:#E0F7FA,stroke:#00ACC1,stroke-width:1.5px,color:#006064,stroke-dasharray: 5 5",
        "  classDef processo fill:#E8EAF6,stroke:#3949AB,stroke-width:2px,color:#1A237E",
        "  classDef retorno fill:#FFF3E0,stroke:#FB8C00,stroke-width:1.5px,color:#E65100",
        "  classDef encadeamento fill:#FCE4EC,stroke:#E91E63,stroke-width:1.5px,color:#880E4F,stroke-dasharray: 5 2",
        "",
        "  %% Fontes de Informação",
        '  subgraph DataSources["🔍 Fontes"]',
        "    direction TB"
    ]

    ds_counter = 1
    connections = []

    for layout in final_layouts:
        ds_name = f"DS{ds_counter}"
        ds_counter += 1

        if layout["tipo"] == "Arquivo":
            if layout.get("modo") == "existente":
                label = layout.get("arquivo", "Layout Existente")
            else:
                label = f"{layout.get('arquivo_tipo','?')}: {layout.get('nome','?')}"
            label = remove_accents(label)
            mermaid_code.append(f'    {ds_name}(["📗 {label}"]):::arquivo')
            connections.append(f"{ds_name} --> PROC")
        else:
            enc_label = remove_accents(layout.get("processo", "Processo Encadeado"))
            # Mesmo formato de colchetes para encadeamento
            mermaid_code.append(f'    {ds_name}(["🔁 {enc_label}"]):::encadeamento')
            connections.append(f"{ds_name} --> PROC")

    mermaid_code.append("  end\n")
    mermaid_code.append(f'  PROC(["🔄 {nome_proc}"]):::processo')

    for c in connections:
        mermaid_code.append(f"  {c}")

    if final_retorno:
        ret_tipo = remove_accents(final_retorno.get("tipo", "Retorno"))
        mermaid_code.append(f'  RET(["📑 {ret_tipo}"]):::retorno')
        mermaid_code.append("  PROC --> RET")

    mermaid_code_str = "\n".join(mermaid_code)

    mermaid_html = f"""
    <div class="mermaid">
    {mermaid_code_str}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
    """

    components.html(mermaid_html, height=600, scrolling=True)

def tela_agrupamento():
    """Tela para agrupar CNPJs em diferentes processos."""
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
    print(f"DEBUG: group_dict = {group_dict}")
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
        print("DEBUG: Processos agrupados criados com sucesso!")
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
    """Tela para gerenciar layouts de um processo."""
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
    """Tela para adicionar um novo layout."""
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
        print("DEBUG: Layout adicionado!")
        st.success("Layout adicionado!")
        st.session_state.tela = "layouts"
        st.rerun()
    if st.button("Voltar"):
        st.session_state.tela = "layouts"
        st.rerun()

# ------------------------------------------------------------------
# Nova Tela: Diagrama em Mermaid.js
# ------------------------------------------------------------------
def tela_diagrama():
    """
    Exibe o diagrama do processo em Mermaid.js usando st.components.v1.html.
    Aplica estilos modernos (arquivo, processo, retorno) e remove acentuação 
    para evitar quebras no Mermaid.
    """
    st.title("Visualização do Processo - Diagrama")

    processo_id = st.session_state.get("processo_id")
    if not processo_id:
        st.error("Processo não selecionado.")
        st.session_state.tela = "processos"
        st.rerun()

    with get_db_connection() as conn:
        proc = conn.execute(
            "SELECT nome FROM processos WHERE id = ?", 
            (processo_id,)
        ).fetchone()
        proc_conf = conn.execute(
            "SELECT layouts, retorno FROM processo_config WHERE processo_id = ?",
            (processo_id,)
        ).fetchone()

    if not proc_conf:
        st.warning("Nenhuma configuração encontrada para este processo.")
        if st.button("Voltar"):
            st.session_state.tela = "configurar_processo"
            st.rerun()
        return

    layouts_str, retorno_str = proc_conf
    layouts_list = []
    retorno_dict = {}

    if layouts_str:
        layouts_list = json.loads(layouts_str)
    if retorno_str:
        retorno_dict = json.loads(retorno_str)

    nome_processo = remove_accents(proc[0]) if proc else "Processo"

    # Início do diagrama Mermaid em formato HTML para uso com st.components.v1.html
    mermaid_body = []
    mermaid_body.append("---")
    mermaid_body.append("config:")
    mermaid_body.append("  look: neo")
    mermaid_body.append("  theme: neutral")
    mermaid_body.append("---")
    mermaid_body.append("flowchart LR")
    mermaid_body.append("  %% Estilos Modernos")
    mermaid_body.append("  classDef arquivo fill:#E0F7FA,stroke:#00ACC1,stroke-width:1.5px,color:#006064,stroke-dasharray: 5 5")
    mermaid_body.append("  classDef processo fill:#E8EAF6,stroke:#3949AB,stroke-width:2px,color:#1A237E")
    mermaid_body.append("  classDef retorno fill:#FFF3E0,stroke:#FB8C00,stroke-width:1.5px,color:#E65100")
    mermaid_body.append("")
    mermaid_body.append("  %% Fontes de Informação")
    mermaid_body.append("  subgraph DataSources[🔍 Fontes]")
    mermaid_body.append("    direction TB")

    ds_counter = 1
    connections = []

    for layout in layouts_list:
        ds_name = f"DS{ds_counter}"
        ds_counter += 1

        if layout["tipo"] == "Arquivo":
            # Exemplo de label: "📗 Excel - LayoutX"
            if layout.get("modo") == "existente":
                label = layout.get("arquivo", "Layout Existente")
            else:
                label = f"{layout.get('arquivo_tipo', '?')} - {layout.get('nome', '?')}"
            label = remove_accents(label)
            mermaid_body.append(f'    {ds_name}(["📗 {label}"]):::arquivo')
        else:
            # Encadeamento (se quiser um estilo especial, adicione outra classDef)
            label = remove_accents(layout.get("processo", "Processo Encadeado?"))
            mermaid_body.append(f'    {ds_name}(["🔗 {label}"]):::arquivo')

        # Depois conectamos no processo
        connections.append(f"{ds_name} --> PROC")

    mermaid_body.append("  end")
    mermaid_body.append("")

    # Processo central
    mermaid_body.append(f'  %% Processo')
    mermaid_body.append(f'  PROC(["🔄 {nome_processo}"]):::processo')
    mermaid_body.append("")

    # Conexões (Fontes -> Processo)
    for c in connections:
        mermaid_body.append(f"  {c}")

    # Se houver retorno
    if retorno_dict:
        tipo_ret = remove_accents(retorno_dict.get("tipo", "Retorno?"))
        mermaid_body.append(f'  %% Retorno')
        mermaid_body.append(f'  RET(["📑 Retorno {tipo_ret}"]):::retorno')
        mermaid_body.append(f'  PROC --> RET')

    # Junta todo o diagrama
    mermaid_code = "\n".join(mermaid_body)

    # HTML final para exibir com st.components
    html_diagrama = f"""
    <div class="mermaid">
    {mermaid_code}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>
    mermaid.initialize({{ startOnLoad: true }});
    </script>
    """

    components.html(html_diagrama, height=600, scrolling=True)

    # Botão de voltar
    if st.button("Voltar"):
        st.session_state.tela = "configurar_processo"
        st.rerun()


# ------------------------------------------------------------------
# Dicionário de Telas
# ------------------------------------------------------------------
telas = {
    "login": tela_login,
    "inicial": tela_inicial,
    "visao_cliente": tela_visao_cliente,
    "processos": tela_processos,
    "configurar_processo": tela_configurar_processo,
    "agrupamento": tela_agrupamento,
    "layouts": tela_layouts,
    "adicionar_layout": tela_adicionar_layout,
    "diagrama": tela_diagrama
}

# ------------------------------------------------------------------
# Controle de Navegação das Telas
# ------------------------------------------------------------------
tela = st.session_state.tela
if tela in telas:
    telas[tela]()
else:
    st.error("Tela não encontrada!")
    st.session_state.tela = "login"
    st.rerun()
