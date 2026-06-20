import os
import sys
import random
from datetime import timedelta

from .helpers import fetch_id,call_procedure
from .faker_br import FakerBR
# ==============================================================================
# 1. TABELAS DE DOMÍNIO / LOOKUP
# ==============================================================================
# CONFIGURAÇÕES:
# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

SEED = 42  # fixo -> massa de dados reprodutível. Use None para variar a cada run.


# Alternativa: defina ECOCIENTE_DSN com a connection string completa
DSN = os.environ.get("ECOCIENTE_DSN")

# ---- Volumetria da carga --------------------------------
N_CONDOMINIOS_RESIDENCIAL = 4
N_CONDOMINIOS_COMERCIAL = 2
N_COOPERATIVAS = 3
N_USUARIOS_COMUM = 12

TORRES_POR_RESIDENCIAL = (2, 3)          # (min, max) torres por condomínio residencial
UNIDADES_POR_TORRE = (4, 8)              # (min, max) unidades por torre
UNIDADES_POR_COMERCIAL = (5, 10)         # unidades diretas (sem torre) em condomínio comercial
CHANCE_UNIDADE_OCUPADA = 80              # % de chance da unidade ter morador/ocupante

PONTOS_COLETA_POR_COOPERATIVA = (2, 3)
POSTAGENS_POR_OCUPANTE = (0, 6)
NOTIFICACOES_POR_USUARIO = (2, 5)
AGENDAMENTOS_POR_CONDOMINIO = (1, 2)
VISITAS_POR_AGENDAMENTO = (2, 5)


fk = FakerBR(seed=SEED)
rng = random.Random(SEED)


def popular_tipos_usuarios(cur):
    tipos = [
        ("Usuário Comum", "Não paga mensalidade, não pertence a condomínio. Acesso a ensino, mapa de pontos de coleta e notificações."),
        ("Síndico Residencial", "Gestor de condomínio residencial. Acesso a ranking, calendário, mapa, analytics (macro) e ensino."),
        ("Síndico Comercial", "Gestor de condomínio comercial. Fluxo corporativo: calendário, mapa, analytics (macro) e ensino."),
        ("Morador Residencial", "Ocupante de unidade em condomínio residencial. Ranking, analytics individual e ensino."),
        ("Usuário Comercial", "Ocupante/usuário de condomínio comercial. Analytics individual, calendário e ensino."),
        ("Cooperativa", "Conta de acesso da cooperativa de reciclagem parceira."),
        ("Administrador", "Administrador do sistema, com acesso a todas as funcionalidades de gestão e moderação."),
    ]
    ids = {}
    for nome, desc in tipos:
        cur.execute("SELECT id_tipo_usuario FROM tipos_usuarios WHERE nome_tipo = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            "INSERT INTO tipos_usuarios (nome_tipo, descricao) VALUES (%s, %s) RETURNING id_tipo_usuario",
            (nome, desc),
        )
    return ids

def popular_tipos_condominios(cur):
    tipos = [
        ("Residencial", "Condomínio residencial (torres/unidades habitacionais)."),
        ("Comercial", "Condomínio/edifício comercial."),
    ]
    ids = {}
    for nome, desc in tipos:
        cur.execute("SELECT id_tipo_condominio FROM tipos_condominios WHERE nome_tipo = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            "INSERT INTO tipos_condominios (nome_tipo, descricao) VALUES (%s, %s) RETURNING id_tipo_condominio",
            (nome, desc),
        )
    return ids


def popular_tipos_avisos(cur):
    tipos = [
        ("Comunicado", "Aviso geral do condomínio."),
        ("Manutenção", "Aviso de manutenção predial."),
        ("Evento", "Evento ou campanha do condomínio."),
        ("Campanha Ambiental", "Campanha de conscientização ambiental/reciclagem."),
        ("Segurança", "Aviso de segurança do condomínio."),
    ]
    ids = {}
    for nome, desc in tipos:
        cur.execute("SELECT id_tipo_aviso FROM tipos_avisos WHERE nome_tipo = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            "INSERT INTO tipos_avisos (nome_tipo, descricao) VALUES (%s, %s) RETURNING id_tipo_aviso",
            (nome, desc),
        )
    return ids


def popular_dias_semana(cur):
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo"]
    ids = {}
    for nome in dias:
        cur.execute("SELECT id_dia_semana FROM dias_semanas WHERE nome_dia = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            "INSERT INTO dias_semanas (nome_dia) VALUES (%s) RETURNING id_dia_semana",
            (nome,),
        )
    return ids


def popular_status_agendamentos(cur):
    # Mesmo seed mínimo já usado no script de objetos lógicos (idempotente).
    nomes = ["Agendado", "Confirmado", "Recusado", "Realizado", "Cancelado"]
    ids = {}
    for nome in nomes:
        cur.execute("SELECT id_status FROM status_agendamentos WHERE nome_status = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            "INSERT INTO status_agendamentos (nome_status) VALUES (%s) RETURNING id_status",
            (nome,),
        )
    return ids


def popular_categorias_residuos(cur):
    categorias = [
        ("Papel", "Papel e papelão em geral", True, "#1565C0"),
        ("Plástico", "Embalagens e materiais plásticos", True, "#F9A825"),
        ("Vidro", "Garrafas, potes e vidro em geral", True, "#2E7D32"),
        ("Metal", "Latas e metais recicláveis", True, "#757575"),
        ("Orgânico", "Resíduo orgânico / compostável", True, "#6D4C41"),
        ("Eletrônico", "Lixo eletrônico (e-waste)", True, "#512DA8"),
        ("Rejeito", "Resíduo não reciclável", False, "#212121"),
    ]
    ids = {}
    for nome, desc, permite, cor in categorias:
        cur.execute("SELECT id_categoria FROM categorias_residuos WHERE nome_categoria = %s", (nome,))
        row = cur.fetchone()
        if row:
            ids[nome] = row[0]
            continue
        ids[nome] = fetch_id(
            cur,
            """INSERT INTO categorias_residuos
                   (nome_categoria, descricao_material, permite_reciclagem, cor_identificacao)
               VALUES (%s, %s, %s, %s) RETURNING id_categoria""",
            (nome, desc, permite, cor),
        )
    return ids


def popular_regras_pontuacao(cur):
    regras = [
        ("postagem_reciclagem", 10, "Postagem de descarte validada pela cooperativa/síndico"),
        ("conclusao_aula", 5, "Conclusão de uma aula dentro de um curso"),
        ("coleta_realizada", 15, "Confirmação de coleta efetivamente realizada"),
        ("bonus", 0, "Bônus manual atribuído por administrador (valor definido no momento do lançamento)"),
    ]
    for tipo_evento, pontos, desc in regras:
        cur.execute("SELECT 1 FROM regras_pontuacao WHERE tipo_evento = %s", (tipo_evento,))
        if cur.fetchone():
            continue
        cur.execute(

            """INSERT INTO regras_pontuacao (tipo_evento, pontos, descricao, ativo)
               VALUES (%s, %s, %s, TRUE)""",
            (tipo_evento, pontos, desc),
        )





# ==============================================================================
# 2. USUÁRIOS E ENDEREÇOS
# ==============================================================================

def criar_endereco(cur):
    uf, cidade, cep, rua, numero, lat, lng = fk.address_tuple()
    return fetch_id(
        cur,
        """INSERT INTO enderecos (cep, estado, cidade, logradouro, numero, complemento, latitude, longitude)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_endereco""",
        (cep, uf, cidade, rua, numero, fk.secondary_address(), lat, lng),
    )


def criar_usuario(cur, tipo_usuario_id, n_telefones=(1, 1)):
    nome = fk.name()
    email = fk.email(nome)
    senha_hash = fk.password(email)
    nascimento = fk.date_of_birth(18, 75)
    cpf = fk.cpf()
    avatar = fk.url(path="avatares", ext="jpg") if fk.boolean(40) else None
    ativo = fk.boolean(95)
    registro_em = fk.date_time_between(900, 0)

    usuario_id = fetch_id(
        cur,
        """INSERT INTO usuarios
               (nome_usuario, email_usuario, senha_hash, data_nascimento, cpf_cnpj,
                url_avatar, ativo, registro_em, tipo_usuario_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id_usuario""",
        (nome, email, senha_hash, nascimento, cpf, avatar, ativo, registro_em, tipo_usuario_id),
    )

    qtd_tel = rng.randint(*n_telefones)
    for _ in range(qtd_tel):
        cur.execute(
            """INSERT INTO telefones (usuario_id, numero_contato, tipo_telefone, ativo)
               VALUES (%s, %s, %s, %s)""",
            (usuario_id, fk.phone(), fk.random_element(["celular", "fixo", "whatsapp"]), fk.boolean(90)),
        )

    return usuario_id, nome


# ==============================================================================
# 3. CONDOMÍNIOS, TORRES, UNIDADES, MORADORES
# ==============================================================================

_codigo_acesso_seq = 0


def proximo_codigo_acesso():
    global _codigo_acesso_seq
    _codigo_acesso_seq += 1
    return fk.codigo_acesso(_codigo_acesso_seq)


def criar_condominio(cur, tipo_condominio_id, sindico_usuario_id, nome_fantasia, comercial=False):
    endereco_id = criar_endereco(cur)
    cnpj = fk.cnpj() if comercial else (fk.cnpj() if fk.boolean(20) else None)
    codigo_acesso = proximo_codigo_acesso()
    ativo = fk.boolean(95)

    condominio_id = fetch_id(
        cur,
        """INSERT INTO condominios
               (nome_condominio, cnpj, codigo_acesso, ativo, tipo_condominio_id,
                sindico_usuario_id, endereco_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id_condominio""",
        (nome_fantasia, cnpj, codigo_acesso, ativo, tipo_condominio_id, sindico_usuario_id, endereco_id),
    )
    return condominio_id


def criar_torre(cur, condominio_id, nome_torre):
    return fetch_id(
        cur,
        "INSERT INTO torres (nome_torre, condominio_id) VALUES (%s, %s) RETURNING id_torre",
        (nome_torre, condominio_id),
    )

def criar_unidade(cur, numero, tipo_unidade, torre_id=None, condominio_id=None):
    return fetch_id(
        cur,
        """INSERT INTO unidades (numero_unidade, tipo_unidade, torre_id, condominio_id)
           VALUES (%s, %s, %s, %s) RETURNING id_unidade""",
        (numero, tipo_unidade, torre_id, condominio_id),
    )


def criar_morador(cur, usuario_id, unidade_id):
    return fetch_id(
        cur,
        """INSERT INTO moradores (usuario_id, unidade_id, pontuacao_acumulada)
           VALUES (%s, %s, 0) RETURNING id_morador""",
        (usuario_id, unidade_id),
    )


def criar_vinculo_condominio(cur, usuario_id, condominio_id, aprovado_por_usuario_id=None):
    data_entrada = fk.date_time_between(700, 30)
    aprovado = fk.boolean(92)
    saiu = fk.boolean(8)
    data_saida = fk.date_time_between(29, 0) if saiu else None
    return fetch_id(
        cur,
        """INSERT INTO usuarios_condominios
               (usuario_id, condominio_id, data_entrada, data_saida, aprovado, aprovado_por_usuario_id)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING id_usuario_condominio""",
        (usuario_id, condominio_id, data_entrada, data_saida, aprovado, aprovado_por_usuario_id),
    )


# ==============================================================================
# 4. COOPERATIVAS, PONTOS DE COLETA, CATEGORIAS
# ==============================================================================

def criar_cooperativa(cur, usuario_id):
    endereco_id = criar_endereco(cur)
    nome = fk.company()
    cooperativa_id = fetch_id(
        cur,
        """INSERT INTO cooperativas
               (cnpj_cooperativa, nome_cooperativa, email_cooperativa, telefone_cooperativa,
                data_cadastro, usuario_id, endereco_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id_cooperativa""",
        (fk.cnpj(), nome, fk.email(nome), fk.phone(), fk.date_time_between(900, 60), usuario_id, endereco_id),
    )
    return cooperativa_id, nome


def criar_ponto_coleta(cur, cooperativa_id, nome_cooperativa):
    endereco_id = criar_endereco(cur)
    nome_ponto = f"Ecoponto {nome_cooperativa} - {fk.street_name()}"
    return fetch_id(
        cur,
        """INSERT INTO pontos_coletas
               (nome_ponto, endereco_id, cooperativa_id, horario_abertura, horario_fechamento, ativo)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING id_ponto_coleta""",
        (nome_ponto, endereco_id, cooperativa_id, "08:00", "18:00", fk.boolean(95)),
    )


def vincular_categorias_cooperativa(cur, cooperativa_id, categoria_ids_recicláveis):
    escolhidas = fk.random_elements(categoria_ids_recicláveis, length=rng.randint(3, 5), unique=True)
    for cat_id in escolhidas:
        cur.execute(
            """INSERT INTO cooperativas_categorias_materiais (cooperativa_id, categoria_residuo_id)
               VALUES (%s, %s)""",
            (cooperativa_id, cat_id),
        )


def vincular_categorias_ponto_coleta(cur, ponto_coleta_id, categoria_ids_recicláveis):
    escolhidas = fk.random_elements(categoria_ids_recicláveis, length=rng.randint(2, 4), unique=True)
    for cat_id in escolhidas:
        cur.execute(
            """INSERT INTO pontos_coletas_categorias (ponto_coleta_id, categoria_residuo_id)
               VALUES (%s, %s)""",
            (ponto_coleta_id, cat_id),
        )


# ==============================================================================
# 5. POSTAGENS DE DESCARTE (usa sp_validar_postagem para aprovar/rejeitar)
# ==============================================================================

def criar_postagem(cur, usuario_id, condominio_id, categoria_id, data_postagem):
    return fetch_id(
        cur,
        """INSERT INTO postagens
               (usuario_id, condominio_id, categoria_id, url_foto, status_postagem, pontos_gerados, data_postagem)
           VALUES (%s, %s, %s, %s, 'P', NULL, %s)
           RETURNING id_postagem""",
        (usuario_id, condominio_id, categoria_id, fk.url(path="postagens", ext="jpg"), data_postagem),
    )


def validar_postagem(cur, postagem_id, novo_status, validado_por_usuario_id):
    call_procedure(
        cur,
        "CALL sp_validar_postagem(%s, %s, %s)",
        (postagem_id, novo_status, validado_por_usuario_id),
    )


# ==============================================================================
# 6. AVISOS
# ==============================================================================

def criar_aviso(cur, condominio_id, criado_por_usuario_id, tipo_aviso_id):
    cur.execute(
        """INSERT INTO avisos (titulo_mensagem, conteudo_mensagem, criado_em, condominio_id,
                                criado_por_usuario_id, tipo_aviso_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            fk.sentence(5).rstrip("."),
            fk.sentence(14),
            fk.date_time_between(365, 0),
            condominio_id,
            criado_por_usuario_id,
            tipo_aviso_id,
        ),
    )


# ==============================================================================
# 7. AGENDAMENTOS, VISITAS, RECORRÊNCIAS E AVALIAÇÕES
#    (usa sp_confirmar_passagem_cooperativa para confirmar visitas passadas)
# ==============================================================================

def criar_agendamento(cur, condominio_id, cooperativa_id, status_agendamento_id, recorrente):
    data_inicio = fk.date_time_between(180, 0)
    data_fim = data_inicio + timedelta(hours=2)
    # possui_recorrencia: se for avulso, já fixamos False (nenhuma trigger vai tocar essa
    # linha, pois não haverá INSERT em recorrencias_agendamentos). Se for recorrente,
    # deixamos a trigger trg_atualizar_recorrencia_insert setar TRUE quando inserirmos
    # a recorrência a seguir.
    return fetch_id(
        cur,
        """INSERT INTO agendamentos_coletas
               (condominio_id, cooperativa_id, status_agendamento_id, data_inicio, data_fim, possui_recorrencia)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING id_agendamento_coleta""",
        (condominio_id, cooperativa_id, status_agendamento_id, data_inicio, data_fim, False if not recorrente else None),
    )


def criar_recorrencia(cur, agendamento_coleta_id, dia_semana_id):
    cur.execute(
        """INSERT INTO recorrencias_agendamentos (agendamento_coleta_id, dia_semana_id)
           VALUES (%s, %s)""",
        (agendamento_coleta_id, dia_semana_id),
    )


def criar_visita(cur, agendamento_coleta_id, data_visita):
    return fetch_id(
        cur,
        """INSERT INTO visitas_coletas
               (agendamento_coleta_id, data_visita, foi_realizada, houve_confirmacao, confirmado_em, observacao)
           VALUES (%s, %s, NULL, NULL, NULL, NULL)
           RETURNING id_visita_coleta""",
        (agendamento_coleta_id, data_visita),
    )


def confirmar_visita(cur, visita_id, confirmou, observacao=None):
    call_procedure(cur, "CALL sp_confirmar_passagem_cooperativa(%s, %s, %s)", (visita_id, confirmou, observacao))
    # foi_realizada é um campo de fato consumado (a coleta de fato aconteceu),
    # distinto de houve_confirmacao (aviso prévio da cooperativa). Atualizamos
    # à parte, refletindo o desfecho real da visita.
    cur.execute(
        "UPDATE visitas_coletas SET foi_realizada = %s WHERE id_visita_coleta = %s",
        (confirmou, visita_id),
    )


def criar_avaliacao_visita(cur, visita_coleta_id, usuario_avaliador_id):
    cur.execute(
        """INSERT INTO avaliacoes_visitas_coletas
               (visita_coleta_id, usuario_avaliador_id, nota, comentario, avaliado_em)
           VALUES (%s, %s, %s, %s, %s)""",
        (
            visita_coleta_id,
            usuario_avaliador_id,
            rng.randint(1, 5),
            fk.sentence(6) if fk.boolean(60) else None,
            fk.date_time_between(30, 0),
        ),
    )


# ==============================================================================
# 8. CURSOS, AULAS E PROGRESSO (usuarios_cursos -> trigger de pontuação)
# ==============================================================================

def popular_cursos_e_aulas(cur):
    """
    Apenas 2 cursos existem no domínio do produto:
      1. Reciclagem de materiais
      2. Compostagem residencial e de apartamento (coletiva)
    """
    cursos_def = [
        (
            "Reciclagem de Materiais",
            "Explica os tipos de materiais recicláveis e onde/como reciclar cada um.",
            [
                "O que é reciclagem e por que ela importa",
                "Plásticos: tipos, símbolos e como separar",
                "Papel e papelão: o que pode e o que não pode reciclar",
                "Vidro e metal: cuidados no descarte",
                "Lixo eletrônico: pontos de coleta especializados",
                "Como montar a separação correta em casa",
            ],
        ),
        (
            "Compostagem Residencial e de Apartamento (Coletiva)",
            "Como reciclar resíduo orgânico através da compostagem doméstica e coletiva.",
            [
                "Introdução à compostagem: o que pode ir na composteira",
                "Montando uma composteira em apartamento",
                "Compostagem coletiva no condomínio: como organizar",
                "Resolvendo problemas comuns (odor, moscas, excesso de umidade)",
                "Usando o composto na horta e em vasos",
            ],
        ),
    ]

    cursos_ids = {}
    aulas_ids = {}  # curso_titulo -> [id_aula, ...]
    for titulo, descricao, aulas in cursos_def:
        cur.execute("SELECT id_curso FROM cursos WHERE titulo_curso = %s", (titulo,))
        row = cur.fetchone()
        if row:
            curso_id = row[0]
        else:
            curso_id = fetch_id(
                cur,
                """INSERT INTO cursos (titulo_curso, descricao_curso, esta_ativo)
                   VALUES (%s, %s, TRUE) RETURNING id_curso""",
                (titulo, descricao),
            )
        cursos_ids[titulo] = curso_id

        cur.execute("SELECT id_aula FROM aulas WHERE curso_id = %s ORDER BY ordem", (curso_id,))
        existentes = [r[0] for r in cur.fetchall()]
        if existentes:
            aulas_ids[titulo] = existentes
            continue

        ids_aula = []
        for ordem, titulo_aula in enumerate(aulas, start=1):
            aula_id = fetch_id(
                cur,
                """INSERT INTO aulas (curso_id, titulo_aula, conteudo_aula, ordem)
                   VALUES (%s, %s, %s, %s) RETURNING id_aula""",
                (curso_id, titulo_aula, fk.sentence(25), ordem),
            )
            ids_aula.append(aula_id)
        aulas_ids[titulo] = ids_aula

    return cursos_ids, aulas_ids


def matricular_usuario_em_aulas(cur, usuario_id, lista_aula_ids):
    """
    Cria o progresso do usuário aula a aula. Aulas concluídas são INSERIDAS já
    como concluido=False e então ATUALIZADAS para TRUE -- isso é proposital:
    é o UPDATE quem dispara a trigger trg_pontuar_conclusao_curso (AFTER UPDATE),
    então só inserir com concluido=TRUE direto NÃO geraria pontuação.
    """
    progresso_ids = []
    for aula_id in lista_aula_ids:
        vai_concluir = fk.boolean(55)
        data_inicio = fk.date_time_between(180, 1)
        usuario_curso_id = fetch_id(
            cur,
            """INSERT INTO usuarios_cursos (usuario_id, aula_id, concluido, data_inicio, data_conclusao)
               VALUES (%s, %s, FALSE, %s, NULL)
               RETURNING id_usuario_curso""",
            (usuario_id, aula_id, data_inicio),
        )
        progresso_ids.append((usuario_curso_id, vai_concluir, data_inicio))

    for usuario_curso_id, vai_concluir, data_inicio in progresso_ids:
        if not vai_concluir:
            continue
        data_conclusao = data_inicio + timedelta(days=rng.randint(1, 14))
        cur.execute(
            """UPDATE usuarios_cursos SET concluido = TRUE, data_conclusao = %s
               WHERE id_usuario_curso = %s""",
            (data_conclusao, usuario_curso_id),
        )


# ==============================================================================
# 9. NOTIFICAÇÕES E HISTÓRICO DE PONTUAÇÃO (bônus manual)
# ==============================================================================

def criar_notificacoes_usuario(cur, usuario_id, qtd):
    tipos = ["seguranca", "motivacional", "lembrete_coleta", "aviso_conta"]
    titulos = {
        "seguranca": "Alerta de segurança",
        "motivacional": "Continue reciclando!",
        "lembrete_coleta": "Coleta se aproximando",
        "aviso_conta": "Atualização da sua conta",
    }
    for _ in range(qtd):
        tipo = fk.random_element(tipos)
        foi_lida = fk.boolean(65)
        data_envio = fk.date_time_between(120, 0)
        data_leitura = data_envio + timedelta(hours=rng.randint(1, 48)) if foi_lida else None
        cur.execute(
            """INSERT INTO notificacoes
                   (usuario_id, titulo_mensagem, corpo_mensagem, tipo_notificacao, foi_lida, data_envio, data_leitura)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (usuario_id, titulos[tipo], fk.sentence(10), tipo, foi_lida, data_envio, data_leitura),
        )


def criar_bonus_pontuacao(cur, usuario_id, condominio_id, sindico_usuario_id):
    """
    Bônus manual (tipo_evento = 'bonus') lançado por um síndico/admin.
    Insere direto em historico_pontuacao -> a trigger trg_atualizar_pontuacao_morador
    atualiza moradores.pontuacao_acumulada automaticamente.
    """
    pontos = rng.choice([5, 10, 15, 20])
    cur.execute(
        """INSERT INTO historico_pontuacao
               (usuario_id, condominio_id, tipo_evento, pontos, referencia_id, referencia_tipo, criado_em)
           VALUES (%s, %s, 'bonus', %s, %s, 'bonus_manual', %s)""",
        (usuario_id, condominio_id, pontos, sindico_usuario_id, fk.date_time_between(60, 0)),
    )

