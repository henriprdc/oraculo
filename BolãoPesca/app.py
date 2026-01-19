from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'bolao_pescadores_secret_key'

# Arquivos para armazenar dados
PARTICIPANTS_FILE = 'participants.json'
GAMES_FILE = 'games.json'
ROUNDS_FILE = 'rounds.json'

# Times do Brasileirão
TIMES_BRASILEIRAO = [
    "Athletico-PR",
    "Atlético-MG",
    "Bahia",
    "Botafogo",
    "Bragantino",
    "Chapecoense",
    "Corinthians",
    "Coritiba",
    "Cruzeiro",
    "Flamengo",
    "Fluminense",
    "Grêmio",
    "Internacional",
    "Mirassol",
    "Palmeiras",
    "Remo",
    "Santos",
    "São Paulo",
    "Vasco",
    "Vitória"
]


# ========== FUNÇÕES AUXILIARES ==========

def load_participants():
    if os.path.exists(PARTICIPANTS_FILE):
        with open(PARTICIPANTS_FILE, 'r', encoding='utf-8') as f:
            try:
                participants = json.load(f)
                # Garantir que cada participante tenha a estrutura de palpites
                for p in participants:
                    if 'palpites' not in p:
                        p['palpites'] = {}
                return participants
            except json.JSONDecodeError:
                return []
    return []


def simular_palpites(participants, games):
    """Simula palpites para teste do ranking"""
    import random

    for participante in participants:
        palpites = {}
        for rodada_numero, jogos_rodada in games.items():
            for jogo in jogos_rodada:
                if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                    # 70% de chance de ter palpite
                    if random.random() < 0.7:
                        # Simular palpite (pode ser correto ou não)
                        placar_casa_real = jogo['placar_casa']
                        placar_visitante_real = jogo['placar_visitante']

                        # 30% de chance de palpite exato
                        if random.random() < 0.3:
                            palpites[str(jogo['id'])] = {
                                'placar_casa': placar_casa_real,
                                'placar_visitante': placar_visitante_real,
                                'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M')
                            }
                        else:
                            # Palpite aleatório
                            resultado_real = 'C' if placar_casa_real > placar_visitante_real else \
                                'V' if placar_casa_real < placar_visitante_real else 'E'

                            # Garantir que o palpite tenha o mesmo resultado (para PTE)
                            if resultado_real == 'C':
                                palpites[str(jogo['id'])] = {
                                    'placar_casa': random.randint(1, 3),
                                    'placar_visitante': random.randint(0, 2),
                                    'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M')
                                }
                            elif resultado_real == 'V':
                                palpites[str(jogo['id'])] = {
                                    'placar_casa': random.randint(0, 2),
                                    'placar_visitante': random.randint(1, 3),
                                    'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M')
                                }
                            else:
                                palpites[str(jogo['id'])] = {
                                    'placar_casa': random.randint(0, 2),
                                    'placar_visitante': random.randint(0, 2),
                                    'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M')
                                }

        participante['palpites'] = palpites

    return participants

def save_participants(participants):
    with open(PARTICIPANTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(participants, f, ensure_ascii=False, indent=2)


def get_next_participant_id():
    participants = load_participants()
    if participants:
        return max(p['id'] for p in participants) + 1
    return 1


def resetar_jogos_concluidos():
    """Reseta todos os jogos concluídos para status Agendado"""
    games = load_games()

    jogos_resetados = 0
    for rodada_numero, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo.get('status') == 'Concluído':
                jogo['status'] = 'Agendado'
                jogo['placar_casa'] = None
                jogo['placar_visitante'] = None
                if 'data_conclusao' in jogo:
                    del jogo['data_conclusao']
                jogos_resetados += 1

    save_games(games)

    # Também resetar status das rodadas
    rounds = load_rounds()
    rodadas_alteradas = 0
    for rodada in rounds:
        if rodada.get('status') == 'Concluída':
            rodada['status'] = 'Em andamento'
            if 'data_conclusao' in rodada:
                del rodada['data_conclusao']
            rodadas_alteradas += 1

    save_rounds(rounds)

    return jogos_resetados, rodadas_alteradas

def load_games():
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_games(games):
    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(games, f, ensure_ascii=False, indent=2)


def load_rounds():
    if os.path.exists(ROUNDS_FILE):
        with open(ROUNDS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_rounds(rounds):
    with open(ROUNDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rounds, f, ensure_ascii=False, indent=2)


def get_next_game_id():
    games = load_games()
    max_id = 0
    for rodada_games in games.values():
        for jogo in rodada_games:
            if jogo['id'] > max_id:
                max_id = jogo['id']
    return max_id + 1



def obter_rodada_atual():
    """Obtém informações da rodada atual"""
    rounds = load_rounds()
    games = load_games()

    rodada_atual = {
        "numero": 1,
        "nome": "Rodada 1",
        "status": "Não iniciada",
        "data_inicio": "A definir",
        "data_fim": "A definir",
        "jogos": []
    }

    for rodada in sorted(rounds, key=lambda x: x['numero']):
        if rodada['status'] != 'Concluída':
            rodada_atual = {
                "numero": rodada['numero'],
                "nome": rodada['nome'],
                "status": rodada['status'],
                "data_inicio": rodada['data_inicio'] if rodada['data_inicio'] else "A definir",
                "data_fim": rodada['data_fim'] if rodada['data_fim'] else "A definir",
                "jogos": games.get(str(rodada['numero']), [])
            }
            break

    return rodada_atual


def calcular_ranking():
    """Calcula o ranking com as novas métricas"""
    participants = load_participants()
    ativos = [p for p in participants if p.get('ativo', True)]
    games = load_games()

    # Para cada participante, calcular as métricas
    for participante in ativos:
        total_pontos = 0
        placares_exatos = 0  # PE
        pontos_time = 0  # PTE
        total_pontos_possiveis = 0

        # Garantir que o participante tenha a estrutura de palpites
        if 'palpites' not in participante:
            participante['palpites'] = {}

        # Calcular baseado nos jogos concluídos
        for rodada_numero, jogos_rodada in games.items():
            for jogo in jogos_rodada:
                if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                    # Cada jogo tem 3 pontos possíveis (3 PE ou 1 PTE)
                    total_pontos_possiveis += 3

                    # Verificar se participante tem palpite para este jogo
                    palpite = participante['palpites'].get(str(jogo['id']))
                    if palpite:
                        palpite_casa = palpite.get('placar_casa')
                        palpite_visitante = palpite.get('placar_visitante')
                        resultado_casa = jogo['placar_casa']
                        resultado_visitante = jogo['placar_visitante']

                        # Verificar placar exato (PE) - 3 pontos
                        if palpite_casa == resultado_casa and palpite_visitante == resultado_visitante:
                            placares_exatos += 1
                            total_pontos += 2

                        # Verificar acerto de time (PTE) - 1 ponto
                        elif (palpite_casa > palpite_visitante and resultado_casa > resultado_visitante) or \
                                (palpite_casa < palpite_visitante and resultado_casa < resultado_visitante) or \
                                (palpite_casa == palpite_visitante and resultado_casa == resultado_visitante):
                            pontos_time += 1
                            total_pontos += 1

        # Calcular aproveitamento
        aproveitamento = 0
        if total_pontos_possiveis > 0:
            aproveitamento = (total_pontos / total_pontos_possiveis) * 100

        # Atualizar dados do participante
        participante['pontos'] = total_pontos
        participante['placares_exatos'] = placares_exatos  # PE
        participante['pontos_time'] = pontos_time  # PTE
        participante['aproveitamento'] = round(aproveitamento, 1)
        participante['jogos_com_palpite'] = len([p for p in participante['palpites'].values()])

    # Ordenar por: 1. Pontos (decrescente), 2. PE (decrescente), 3. PTE (decrescente), 4. Aproveitamento (decrescente)
    ranking_ordenado = sorted(
        ativos,
        key=lambda x: (
            x.get('pontos', 0),
            x.get('placares_exatos', 0),
            x.get('pontos_time', 0),
            x.get('aproveitamento', 0)
        ),
        reverse=True
    )

    # Adicionar posição no ranking
    for i, participante in enumerate(ranking_ordenado, 1):
        participante['posicao'] = i

    # Retornar top 10 para a página inicial
    return ranking_ordenado[:10]


# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    participants = load_participants()
    ativos = [p for p in participants if p.get('ativo', True)]

    # Calcular ranking
    ranking_ordenado = calcular_ranking()

    # Obter rodada atual
    rounds = load_rounds()
    games = load_games()

    rodada_atual = {
        "numero": 1,
        "nome": "Rodada 1",
        "status": "Não iniciada",
        "data_inicio": "A definir",
        "data_fim": "A definir",
        "jogos": []
    }

    for rodada in sorted(rounds, key=lambda x: x['numero']):
        if rodada['status'] != 'Concluída':
            rodada_atual = {
                "numero": rodada['numero'],
                "nome": rodada['nome'],
                "status": rodada['status'],
                "data_inicio": rodada['data_inicio'] if rodada['data_inicio'] else "A definir",
                "data_fim": rodada['data_fim'] if rodada['data_fim'] else "A definir",
                "jogos": games.get(str(rodada['numero']), [])
            }
            break

    # Estatísticas
    camisas_entregues = len(ativos) // 5
    total_jogos = sum(len(rodada_games) for rodada_games in games.values())

    # Calcular precisão média
    if ativos:
        precisao_total = sum(p.get('aproveitamento', 0) for p in ativos)
        precisao_media = f"{round(precisao_total / len(ativos), 1)}%"
    else:
        precisao_media = "0%"

    estatisticas = {
        "total_participantes": len(ativos),
        "camisas_entregues": camisas_entregues,
        "precisao_media": "0%",
        "rodada_atual": rodada_atual['numero'],
        "total_rodadas": len(rounds),
        "jogos_cadastrados": total_jogos
    }

    return render_template('index.html',
                           ranking=ranking_ordenado,
                           rodada=rodada_atual,
                           estatisticas=estatisticas,
                           times=TIMES_BRASILEIRAO,
                           min=min)


# ========== ROTAS DE PARTICIPANTES ==========

@app.route('/cadastro-participantes')
def cadastro_participantes():
    participants = load_participants()
    return render_template('cadastro_participantes.html',
                           participants=participants,
                           total=len(participants))


@app.route('/cadastro-participantes/novo')
def novo_participante():
    """Exibe formulário para novo participante"""
    return render_template('form_participante.html')


@app.route('/cadastro-participantes/adicionar', methods=['POST'])
def adicionar_participante():
    """Adiciona novo participante"""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    telefone = request.form.get('telefone', '').strip()
    apelido = request.form.get('apelido', '').strip()

    # Validações básicas
    if not nome:
        flash('Nome é obrigatório!', 'error')
        return redirect(url_for('novo_participante'))

    # Carrega participantes existentes
    participants = load_participants()

    # Verifica se email já existe
    if any(p['email'] == email for p in participants if email):
        flash('Email já cadastrado!', 'error')
        return redirect(url_for('novo_participante'))

    # Cria novo participante
    novo_participante = {
        'id': get_next_participant_id(),
        'nome': nome,
        'email': email,
        'telefone': telefone,
        'apelido': apelido,
        'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'pontos': 0,
        'acertos': 0,
        'ativo': True
    }

    participants.append(novo_participante)
    save_participants(participants)

    flash(f'Participante {nome} cadastrado com sucesso!', 'success')
    return redirect(url_for('cadastro_participantes'))


@app.route('/cadastro-participantes/editar/<int:id>')
def editar_participante(id):
    """Exibe formulário para editar participante"""
    participants = load_participants()
    participante = next((p for p in participants if p['id'] == id), None)

    if not participante:
        flash('Participante não encontrado!', 'error')
        return redirect(url_for('cadastro_participantes'))

    return render_template('form_participante.html', participante=participante)


@app.route('/cadastro-participantes/atualizar/<int:id>', methods=['POST'])
def atualizar_participante(id):
    """Atualiza participante existente"""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    telefone = request.form.get('telefone', '').strip()
    apelido = request.form.get('apelido', '').strip()
    ativo = request.form.get('ativo') == 'on'

    if not nome:
        flash('Nome é obrigatório!', 'error')
        return redirect(url_for('editar_participante', id=id))

    participants = load_participants()

    for i, p in enumerate(participants):
        if p['id'] == id:
            # Verifica se email foi alterado e se já existe
            if email != p['email'] and any(part['email'] == email for part in participants if email):
                flash('Email já cadastrado!', 'error')
                return redirect(url_for('editar_participante', id=id))

            # Atualiza dados
            participants[i]['nome'] = nome
            participants[i]['email'] = email
            participants[i]['telefone'] = telefone
            participants[i]['apelido'] = apelido
            participants[i]['ativo'] = ativo
            participants[i]['data_atualizacao'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            break

    save_participants(participants)
    flash(f'Participante {nome} atualizado com sucesso!', 'success')
    return redirect(url_for('cadastro_participantes'))


@app.route('/cadastro-participantes/excluir/<int:id>')
def excluir_participante(id):
    """Exclui participante"""
    participants = load_participants()
    participants = [p for p in participants if p['id'] != id]
    save_participants(participants)

    flash('Participante excluído com sucesso!', 'success')
    return redirect(url_for('cadastro_participantes'))


# ========== ROTAS DE JOGOS ==========

@app.route('/cadastro-jogos', methods=['GET', 'POST'])
def cadastro_jogos():
    """Página principal de cadastro de jogos"""
    if request.method == 'POST':
        # Processar criação de rodada
        numero = request.form.get('numero', type=int)
        nome = request.form.get('nome', '').strip()

        if not numero or not nome:
            flash('Número e nome da rodada são obrigatórios!', 'error')
            return redirect(url_for('cadastro_jogos'))

        rounds = load_rounds()

        if any(r['numero'] == numero for r in rounds):
            flash(f'Rodada {numero} já existe!', 'error')
            return redirect(url_for('cadastro_jogos'))

        nova_rodada = {
            'id': len(rounds) + 1,
            'numero': numero,
            'nome': nome,
            'data_inicio': request.form.get('data_inicio', ''),
            'data_fim': request.form.get('data_fim', ''),
            'status': 'Não iniciada',
            'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        rounds.append(nova_rodada)
        save_rounds(rounds)
        flash(f'Rodada {numero} criada com sucesso!', 'success')
        return redirect(url_for('cadastro_jogos'))

    # GET request - mostrar página
    rounds = load_rounds()
    games = load_games()

    total_jogos = sum(len(rodada_games) for rodada_games in games.values())

    estatisticas = {
        "total_rodadas": len(rounds),
        "jogos_cadastrados": total_jogos
    }

    return render_template('cadastro_jogos.html',
                           rounds=rounds,
                           games=games,
                           estatisticas=estatisticas,
                           times=TIMES_BRASILEIRAO)


@app.route('/cadastro-jogos/salvar-jogo', methods=['POST'])
def salvar_jogo():
    """Salva um novo jogo ou edita um existente"""
    jogo_id = request.form.get('jogo_id', type=int)
    rodada_numero = request.form.get('rodada_numero', type=int)
    time_casa = request.form.get('time_casa', '').strip()
    time_visitante = request.form.get('time_visitante', '').strip()
    data = request.form.get('data', '')
    horario = request.form.get('horario', '')

    # Validações
    if not rodada_numero:
        flash('Rodada é obrigatória!', 'error')
        return redirect(url_for('cadastro_jogos'))

    if not time_casa or not time_visitante:
        flash('Times são obrigatórios!', 'error')
        return redirect(url_for('cadastro_jogos'))

    if time_casa == time_visitante:
        flash('Times não podem ser iguais!', 'error')
        return redirect(url_for('cadastro_jogos'))

    games = load_games()

    if not horario:
        horario = '16:00'

    if jogo_id:
        # Modo edição
        encontrado = False

        for rodada_str, jogos_rodada in games.items():
            for i, jogo in enumerate(jogos_rodada):
                if jogo['id'] == jogo_id:
                    # Atualiza o jogo
                    games[rodada_str][i]['time_casa'] = time_casa
                    games[rodada_str][i]['time_visitante'] = time_visitante
                    games[rodada_str][i]['data'] = data
                    games[rodada_str][i]['horario'] = horario
                    games[rodada_str][i]['estadio'] = request.form.get('estadio', 'A definir')
                    games[rodada_str][i]['data_atualizacao'] = datetime.now().strftime('%Y-%m-%d %H:%M')

                    encontrado = True
                    flash(f'Jogo atualizado com sucesso!', 'success')
                    break
            if encontrado:
                break

        if not encontrado:
            flash('Jogo não encontrado para edição!', 'error')
    else:
        # Modo adição
        if str(rodada_numero) not in games:
            games[str(rodada_numero)] = []

        novo_jogo = {
            'id': get_next_game_id(),
            'rodada': rodada_numero,
            'time_casa': time_casa,
            'time_visitante': time_visitante,
            'data': data,
            'horario': horario,
            'estadio': request.form.get('estadio', 'A definir'),
            'placar_casa': None,
            'placar_visitante': None,
            'status': 'Agendado',
            'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        games[str(rodada_numero)].append(novo_jogo)
        flash(f'Jogo {time_casa} x {time_visitante} adicionado à rodada {rodada_numero}!', 'success')

    save_games(games)
    return redirect(url_for('cadastro_jogos'))


@app.route('/cadastro-jogos/excluir/<int:jogo_id>')
def excluir_jogo(jogo_id):
    """Exclui um jogo"""
    games = load_games()

    jogo_excluido = False
    for rodada_numero, jogos_rodada in games.items():
        original_length = len(jogos_rodada)
        games[rodada_numero] = [j for j in jogos_rodada if j['id'] != jogo_id]

        if len(games[rodada_numero]) < original_length:
            jogo_excluido = True
            break

    if jogo_excluido:
        save_games(games)
        flash('Jogo excluído com sucesso!', 'success')
    else:
        flash('Jogo não encontrado!', 'error')

    return redirect(request.referrer or url_for('cadastro_jogos'))

@app.route('/cadastro-jogos/status/<int:rodada_numero>', methods=['POST'])
def atualizar_status_rodada(rodada_numero):
    """Atualiza o status de uma rodada"""
    status = request.form.get('status')

    if not status:
        flash('Status é obrigatório!', 'error')
        return redirect(url_for('cadastro_jogos'))

    rounds = load_rounds()

    for rodada in rounds:
        if rodada['numero'] == rodada_numero:
            rodada['status'] = status
            if status == 'Concluída':
                rodada['data_conclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            break

    save_rounds(rounds)
    flash(f'Status da rodada {rodada_numero} atualizado para {status}!', 'success')
    return redirect(url_for('cadastro_jogos'))


@app.route('/cadastro-jogos/placar/<int:jogo_id>', methods=['POST'])
def registrar_placar(jogo_id):
    """Registrar o placar de um jogo"""
    placar_casa = request.form.get('placar_casa', type=int)
    placar_visitante = request.form.get('placar_visitante', type=int)

    if placar_casa is None or placar_visitante is None:
        flash('Placar é obrigatório!', 'error')
        return redirect(url_for('cadastro_jogos'))

    games = load_games()

    for rodada_numero, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo['id'] == jogo_id:
                jogo['placar_casa'] = placar_casa
                jogo['placar_visitante'] = placar_visitante
                jogo['status'] = 'Concluído'
                jogo['data_conclusao'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                flash('Placar registrado com sucesso!', 'success')
                break

    save_games(games)
    return redirect(url_for('cadastro_jogos'))


@app.route('/cadastro-jogos/resetar-jogo/<int:jogo_id>', methods=['POST'])
def resetar_jogo(jogo_id):
    """Reseta um jogo específico para status Agendado"""
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'message': 'Apenas administradores podem resetar jogos!'}), 403

    games = load_games()
    jogo_encontrado = False
    rodada_numero = None

    for rodada_numero_str, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo['id'] == jogo_id:
                if jogo.get('status') == 'Concluído':
                    # Salvar informações para retorno
                    time_casa = jogo['time_casa']
                    time_visitante = jogo['time_visitante']
                    rodada_numero = int(rodada_numero_str)

                    # Resetar o jogo
                    jogo['status'] = 'Agendado'
                    jogo['placar_casa'] = None
                    jogo['placar_visitante'] = None

                    # Remover campos de conclusão
                    if 'data_conclusao' in jogo:
                        del jogo['data_conclusao']

                    jogo_encontrado = True
                else:
                    return jsonify({'success': False, 'message': 'Este jogo não está concluído!'}), 400
                break
        if jogo_encontrado:
            break

    if jogo_encontrado:
        save_games(games)
        return jsonify({
            'success': True,
            'message': f'Jogo {time_casa} x {time_visitante} resetado para Agendado!',
            'rodada': rodada_numero
        })

    return jsonify({'success': False, 'message': 'Jogo não encontrado!'}), 404

# Adicionar função para registrar palpites (será usada depois)
@app.route('/palpites')
def palpites():
    """Página principal de palpites"""
    # Verificar se há participante selecionado
    if 'user_id' not in session:
        flash('Selecione um participante para fazer palpites!', 'warning')
        return redirect(url_for('selecionar_participante'))

    user_id = session['user_id']
    participants = load_participants()

    # Encontrar participante atual
    participante_atual = next((p for p in participants if p['id'] == user_id), None)

    if not participante_atual:
        flash('Participante não encontrado!', 'error')
        session.clear()
        return redirect(url_for('selecionar_participante'))

    # Obter rodada atual
    rodada_atual = obter_rodada_atual()
    games = load_games()

    # Obter jogos da rodada atual
    jogos_rodada = games.get(str(rodada_atual['numero']), [])

    # Ordenar jogos por data
    jogos_ordenados = sorted(jogos_rodada, key=lambda x: (
        x.get('data', '9999-99-99'),
        x.get('horario', '99:99')
    ))

    # Preparar dados para template
    jogos_com_palpites = []
    for jogo in jogos_ordenados:
        jogo_completo = jogo.copy()

        # Verificar se já tem palpite DESTE participante
        palpite = participante_atual.get('palpites', {}).get(str(jogo['id']))
        if palpite:
            jogo_completo['palpite_casa'] = palpite.get('placar_casa')
            jogo_completo['palpite_visitante'] = palpite.get('placar_visitante')
            jogo_completo['tem_palpite'] = True
        else:
            jogo_completo['palpite_casa'] = ''
            jogo_completo['palpite_visitante'] = ''
            jogo_completo['tem_palpite'] = False

        # Verificar se jogo já ocorreu
        if jogo.get('status') == 'Concluído':
            jogo_completo['pode_palpitar'] = False
            jogo_completo['placar_final'] = f"{jogo['placar_casa']} x {jogo['placar_visitante']}"

            # Calcular pontos deste jogo
            if palpite:
                pontos = calcular_pontos_palpite(
                    palpite.get('placar_casa'),
                    palpite.get('placar_visitante'),
                    jogo['placar_casa'],
                    jogo['placar_visitante']
                )
                jogo_completo['pontos_obtidos'] = pontos
        else:
            jogo_completo['pode_palpitar'] = True
            jogo_completo['placar_final'] = None

        jogos_com_palpites.append(jogo_completo)

    # Calcular estatísticas
    total_palpites = sum(1 for j in jogos_com_palpites if j['tem_palpite'])
    palpites_restantes = len(jogos_com_palpites) - total_palpites

    estatisticas_palpites = {
        'total_jogos': len(jogos_com_palpites),
        'palpites_feitos': total_palpites,
        'palpites_restantes': palpites_restantes,
        'rodada_numero': rodada_atual['numero'],
        'rodada_nome': rodada_atual['nome'],
        'data_limite': rodada_atual['data_fim']
    }

    return render_template('palpites.html',
                           jogos=jogos_com_palpites,
                           estatisticas=estatisticas_palpites,
                           participante=participante_atual,
                           rodada=rodada_atual)


@app.route('/palpite/registrar', methods=['POST'])
def registrar_palpite():
    """Registra ou atualiza um palpite"""
    if 'user_id' not in session:
        flash('Faça login para registrar palpites!', 'error')
        return redirect(url_for('palpites'))

    user_id = session['user_id']
    jogo_id = request.form.get('jogo_id', type=int)
    placar_casa = request.form.get('placar_casa', type=int)
    placar_visitante = request.form.get('placar_visitante', type=int)
    rodada_numero = request.form.get('rodada_numero', type=int)

    print(f"DEBUG: Registrando palpite - User: {user_id}, Jogo: {jogo_id}, Placar: {placar_casa}x{placar_visitante}")

    # Validações
    if jogo_id is None or placar_casa is None or placar_visitante is None:
        flash('Todos os campos são obrigatórios!', 'error')
        return redirect(url_for('palpites'))

    if placar_casa < 0 or placar_visitante < 0:
        flash('Placar não pode ser negativo!', 'error')
        return redirect(url_for('palpites'))

    # Verificar se jogo ainda permite palpites
    games = load_games()
    jogo_encontrado = None

    for rodada_str, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo['id'] == jogo_id:
                jogo_encontrado = jogo
                break
        if jogo_encontrado:
            break

    if not jogo_encontrado:
        flash('Jogo não encontrado!', 'error')
        return redirect(url_for('palpites'))

    if jogo_encontrado.get('status') == 'Concluído':
        flash('Este jogo já foi realizado! Não é possível alterar o palpite.', 'error')
        return redirect(url_for('palpites'))

    # Carregar e atualizar participantes
    participants = load_participants()
    participante_encontrado = False

    for i, participante in enumerate(participants):
        if participante['id'] == user_id:
            # Inicializar dicionário de palpites se não existir
            if 'palpites' not in participante:
                participante['palpites'] = {}

            # Registrar/atualizar palpite
            participante['palpites'][str(jogo_id)] = {
                'placar_casa': placar_casa,
                'placar_visitante': placar_visitante,
                'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'rodada': rodada_numero
            }

            # Atualizar timestamp
            participante['ultimo_palpite'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            participante_encontrado = True
            break

    # Se não encontrou o participante, criar um novo
    if not participante_encontrado:
        novo_participante = {
            'id': user_id,
            'nome': session.get('user_name', 'Participante'),
            'email': '',
            'telefone': '',
            'apelido': '',
            'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'pontos': 0,
            'acertos': 0,
            'ativo': True,
            'palpites': {
                str(jogo_id): {
                    'placar_casa': placar_casa,
                    'placar_visitante': placar_visitante,
                    'data_palpite': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'rodada': rodada_numero
                }
            },
            'ultimo_palpite': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        participants.append(novo_participante)

    save_participants(participants)

    flash(f'Palpite registrado: {placar_casa} x {placar_visitante}', 'success')
    return redirect(url_for('palpites'))


@app.route('/palpite/excluir/<int:jogo_id>')
def excluir_palpite(jogo_id):
    """Exclui um palpite"""
    if 'user_id' not in session:
        flash('Faça login para excluir palpites!', 'error')
        return redirect(url_for('palpites'))

    user_id = session['user_id']

    # Verificar se jogo já ocorreu
    games = load_games()
    jogo_concluido = False

    for rodada_str, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo['id'] == jogo_id and jogo.get('status') == 'Concluído':
                jogo_concluido = True
                break
        if jogo_concluido:
            break

    if jogo_concluido:
        flash('Não é possível excluir palpite de jogo concluído!', 'error')
        return redirect(url_for('palpites'))

    # Carregar e atualizar participantes
    participants = load_participants()
    palpite_excluido = False

    for i, participante in enumerate(participants):
        if participante['id'] == user_id:
            if 'palpites' in participante and str(jogo_id) in participante['palpites']:
                del participante['palpites'][str(jogo_id)]
                palpite_excluido = True
                flash('Palpite excluído com sucesso!', 'success')
                break

    if not palpite_excluido:
        flash('Palpite não encontrado!', 'error')

    save_participants(participants)
    return redirect(url_for('palpites'))


@app.route('/meus-palpites')
def meus_palpites():
    """Mostra todos os palpites do usuário"""
    if 'user_id' not in session:
        flash('Faça login para ver seus palpites!', 'error')
        return redirect(url_for('index'))

    user_id = session['user_id']
    participants = load_participants()

    # Encontrar participante atual
    participante_atual = None
    for p in participants:
        if p['id'] == user_id:
            participante_atual = p
            break

    if not participante_atual:
        flash('Participante não encontrado!', 'error')
        return redirect(url_for('index'))

    # Carregar todos os jogos
    games = load_games()
    all_games = []

    for rodada_numero, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            jogo_completo = jogo.copy()
            jogo_completo['rodada_numero'] = rodada_numero
            all_games.append(jogo_completo)

    # Filtrar jogos com palpites
    palpites_do_usuario = []
    total_pontos = 0
    total_pe = 0
    total_pte = 0

    # Obter palpites do participante
    palpites_participante = participante_atual.get('palpites', {})

    for jogo in all_games:
        jogo_id_str = str(jogo['id'])
        if jogo_id_str in palpites_participante:
            palpite = palpites_participante[jogo_id_str]

            jogo_completo = jogo.copy()
            jogo_completo['palpite_casa'] = palpite.get('placar_casa')
            jogo_completo['palpite_visitante'] = palpite.get('placar_visitante')
            jogo_completo['data_palpite'] = palpite.get('data_palpite')
            jogo_completo['rodada'] = palpite.get('rodada', jogo.get('rodada_numero', 0))

            if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                pontos, pe, pte = calcular_pontos_detalhados(
                    palpite.get('placar_casa'),
                    palpite.get('placar_visitante'),
                    jogo['placar_casa'],
                    jogo['placar_visitante']
                )
                jogo_completo['pontos'] = pontos
                jogo_completo['pe'] = pe
                jogo_completo['pte'] = pte

                total_pontos += pontos
                total_pe += pe
                total_pte += pte
            else:
                jogo_completo['pontos'] = None
                jogo_completo['pe'] = None
                jogo_completo['pte'] = None

            palpites_do_usuario.append(jogo_completo)

    # Ordenar por rodada e data
    palpites_ordenados = sorted(palpites_do_usuario,
                                key=lambda x: (x.get('rodada', 0), x.get('data', ''), x.get('horario', '')),
                                reverse=True)

    # Calcular aproveitamento
    aproveitamento = calcular_aproveitamento(participante_atual, games)

    estatisticas = {
        'total_palpites': len(palpites_ordenados),
        'total_pontos': total_pontos,
        'total_pe': total_pe,
        'total_pte': total_pte,
        'aproveitamento': aproveitamento
    }

    return render_template('meus_palpites.html',
                           palpites=palpites_ordenados,
                           estatisticas=estatisticas,
                           participante=participante_atual)


@app.route('/todos-os-palpites')
def todos_os_palpites():
    """Página para ver e gerenciar palpites de todos os participantes"""
    # Verificar se é admin (simulação)
    if not session.get('is_admin', False):
        flash('Acesso restrito!', 'error')
        return redirect(url_for('index'))

    participants = load_participants()
    rodada_atual = obter_rodada_atual()
    games = load_games()

    # Obter jogos da rodada atual
    jogos_rodada = games.get(str(rodada_atual['numero']), [])

    # Preparar dados
    dados = []
    for jogo in jogos_rodada:
        jogo_data = {
            'id': jogo['id'],
            'time_casa': jogo['time_casa'],
            'time_visitante': jogo['time_visitante'],
            'data': jogo.get('data'),
            'horario': jogo.get('horario'),
            'status': jogo.get('status'),
            'placar_casa': jogo.get('placar_casa'),
            'placar_visitante': jogo.get('placar_visitante'),
            'palpites': []
        }

        # Coletar palpites de todos os participantes para este jogo
        for participante in participants:
            if participante.get('ativo', True):
                palpite = participante.get('palpites', {}).get(str(jogo['id']))
                if palpite:
                    jogo_data['palpites'].append({
                        'participante_id': participante['id'],
                        'participante_nome': participante['nome'],
                        'participante_apelido': participante.get('apelido', ''),
                        'palpite_casa': palpite.get('placar_casa'),
                        'palpite_visitante': palpite.get('placar_visitante'),
                        'data_palpite': palpite.get('data_palpite'),
                        'pontos': calcular_pontos_palpite(
                            palpite.get('placar_casa'),
                            palpite.get('placar_visitante'),
                            jogo.get('placar_casa'),
                            jogo.get('placar_visitante')
                        ) if jogo.get('status') == 'Concluído' else None
                    })

        dados.append(jogo_data)

    return render_template('todos_palpites.html',
                           jogos=dados,
                           rodada=rodada_atual,
                           total_participantes=len([p for p in participants if p.get('ativo', True)]))


# ========== ADICIONE ROTA PARA PALPITE RÁPIDO ==========

@app.route('/palpite-rapido/<int:participante_id>')
def palpite_rapido(participante_id):
    """Redireciona para fazer palpites rapidamente para um participante"""
    participants = load_participants()

    participante = next((p for p in participants if p['id'] == participante_id), None)

    if not participante:
        flash('Participante não encontrado!', 'error')
        return redirect(url_for('selecionar_participante'))

    # Login rápido
    session['user_id'] = participante['id']
    session['user_name'] = participante['nome']
    session['user_apelido'] = participante.get('apelido', '')

    flash(f'Fazendo palpites como {participante["nome"]}', 'info')
    return redirect(url_for('palpites'))


# ========== ADICIONE MODO ADMIN PARA TESTE ==========

@app.route('/modo-admin')
def modo_admin():
    """Ativa modo admin para testes"""
    session['is_admin'] = True
    flash('Modo administrador ativado!', 'success')
    return redirect(url_for('index'))

# ========== FUNÇÕES AUXILIARES PARA PALPITES ==========

def calcular_pontos_palpite(palpite_casa, palpite_visitante, resultado_casa, resultado_visitante):
    """Calcula pontos de um palpite"""
    if palpite_casa is None or palpite_visitante is None:
        return 0

    pontos = 0

    # Verificar placar exato (PE) - 3 pontos
    if palpite_casa == resultado_casa and palpite_visitante == resultado_visitante:
        pontos += 3  # 3 pontos para placar exato
    # Verificar acerto do resultado (vitória/empate/derrota) - 1 ponto
    else:
        # Determinar resultado do palpite
        if palpite_casa > palpite_visitante:
            resultado_palpite = 'C'  # Vitória do time da casa
        elif palpite_casa < palpite_visitante:
            resultado_palpite = 'V'  # Vitória do time visitante
        else:
            resultado_palpite = 'E'  # Empate

        # Determinar resultado real
        if resultado_casa > resultado_visitante:
            resultado_real = 'C'
        elif resultado_casa < resultado_visitante:
            resultado_real = 'V'
        else:
            resultado_real = 'E'

        # Se acertou o resultado
        if resultado_palpite == resultado_real:
            pontos += 1

    return pontos


def calcular_pontos_detalhados(palpite_casa, palpite_visitante, resultado_casa, resultado_visitante):
    """Calcula pontos detalhados (PE e PTE separados)"""
    pe = 0
    pte = 0
    pontos = 0

    if palpite_casa is None or palpite_visitante is None:
        return 0, pe, pte

    # Verificar placar exato (PE) - 3 pontos + 2 PTE
    if palpite_casa == resultado_casa and palpite_visitante == resultado_visitante:
        pe = 1
        pte = 2  # Acertou gols de ambos os times
        pontos = 3  # 3 pontos para placar exato
    else:
        # Verificar acerto do resultado (vitória/empate/derrota) - 1 ponto
        # Determinar resultado do palpite
        if palpite_casa > palpite_visitante:
            resultado_palpite = 'C'  # Vitória do time da casa
        elif palpite_casa < palpite_visitante:
            resultado_palpite = 'V'  # Vitória do time visitante
        else:
            resultado_palpite = 'E'  # Empate

        # Determinar resultado real
        if resultado_casa > resultado_visitante:
            resultado_real = 'C'
        elif resultado_casa < resultado_visitante:
            resultado_real = 'V'
        else:
            resultado_real = 'E'

        # Se acertou o resultado
        if resultado_palpite == resultado_real:
            pontos = 1

        # Calcular PTE - apenas acertos de gols de times específicos
        if palpite_casa == resultado_casa:
            pte += 1
        if palpite_visitante == resultado_visitante:
            pte += 1

    return pontos, pe, pte


def calcular_aproveitamento(participante, games):
    """Calcula o aproveitamento de um participante"""
    if 'palpites' not in participante:
        return 0

    total_pontos = 0
    total_jogos_com_palpite = 0
    palpites_participante = participante.get('palpites', {})

    for rodada_numero, jogos_rodada in games.items():
        for jogo in jogos_rodada:
            if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                jogo_id_str = str(jogo['id'])
                if jogo_id_str in palpites_participante:
                    total_jogos_com_palpite += 1
                    palpite = palpites_participante[jogo_id_str]

                    pontos = calcular_pontos_palpite(
                        palpite.get('placar_casa'),
                        palpite.get('placar_visitante'),
                        jogo['placar_casa'],
                        jogo['placar_visitante']
                    )
                    total_pontos += pontos

    # Calcular aproveitamento (pontuação máxima por jogo: 3 pontos)
    if total_jogos_com_palpite > 0:
        pontuacao_maxima = total_jogos_com_palpite * 3
        aproveitamento = (total_pontos / pontuacao_maxima) * 100
        return round(aproveitamento, 2)

    return 0

def calcular_ranking():
    """Calcula o ranking com as novas métricas"""
    participants = load_participants()
    ativos = [p for p in participants if p.get('ativo', True)]
    games = load_games()

    # Para cada participante, calcular as métricas
    for participante in ativos:
        total_pontos = 0
        placares_exatos = 0  # PE
        pontos_time = 0  # PTE (apenas acertos de gols)
        total_pontos_possiveis = 0

        # Garantir que o participante tenha a estrutura de palpites
        if 'palpites' not in participante:
            participante['palpites'] = {}

        # Calcular baseado nos jogos concluídos
        for rodada_numero, jogos_rodada in games.items():
            for jogo in jogos_rodada:
                if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                    # Cada jogo tem 3 pontos possíveis (3 PE ou 1 PTE máximo para resultado)
                    total_pontos_possiveis += 3

                    # Verificar se participante tem palpite para este jogo
                    palpite = participante['palpites'].get(str(jogo['id']))
                    if palpite:
                        palpite_casa = palpite.get('placar_casa')
                        palpite_visitante = palpite.get('placar_visitante')
                        resultado_casa = jogo['placar_casa']
                        resultado_visitante = jogo['placar_visitante']

                        # Verificar placar exato (PE) - 3 pontos + 2 PTE
                        if palpite_casa == resultado_casa and palpite_visitante == resultado_visitante:
                            placares_exatos += 1
                            pontos_time += 2  # Acertou gols de ambos os times
                            total_pontos += 3
                        else:
                            # Verificar acerto do resultado (vitória/empate/derrota) - 1 ponto
                            # Determinar resultado do palpite
                            if palpite_casa > palpite_visitante:
                                resultado_palpite = 'C'
                            elif palpite_casa < palpite_visitante:
                                resultado_palpite = 'V'
                            else:
                                resultado_palpite = 'E'

                            # Determinar resultado real
                            if resultado_casa > resultado_visitante:
                                resultado_real = 'C'
                            elif resultado_casa < resultado_visitante:
                                resultado_real = 'V'
                            else:
                                resultado_real = 'E'

                            # Se acertou o resultado
                            if resultado_palpite == resultado_real:
                                total_pontos += 1

                            # Calcular PTE - apenas acertos de gols de times específicos
                            if palpite_casa == resultado_casa:
                                pontos_time += 1
                            if palpite_visitante == resultado_visitante:
                                pontos_time += 1

        # Calcular aproveitamento
        aproveitamento = 0
        if total_pontos_possiveis > 0:
            aproveitamento = (total_pontos / total_pontos_possiveis) * 100

        # Atualizar dados do participante
        participante['pontos'] = total_pontos
        participante['placares_exatos'] = placares_exatos  # PE
        participante['pontos_time'] = pontos_time  # PTE (acertos de gols)
        participante['aproveitamento'] = round(aproveitamento, 1)
        participante['jogos_com_palpite'] = len([p for p in participante['palpites'].values()])

    # Ordenar por: 1. Pontos (decrescente), 2. PE (decrescente), 3. PTE (decrescente), 4. Aproveitamento (decrescente)
    ranking_ordenado = sorted(
        ativos,
        key=lambda x: (
            x.get('pontos', 0),
            x.get('placares_exatos', 0),
            x.get('pontos_time', 0),
            x.get('aproveitamento', 0)
        ),
        reverse=True
    )

    # Adicionar posição no ranking
    for i, participante in enumerate(ranking_ordenado, 1):
        participante['posicao'] = i

    # Retornar top 10 para a página inicial
    return ranking_ordenado[:10]


@app.route('/selecionar-participante')
def selecionar_participante():
    """Página para selecionar qual participante está fazendo palpites"""
    participants = load_participants()
    ativos = [p for p in participants if p.get('ativo', True)]

    # Participante atual da sessão
    participante_atual_id = session.get('user_id')
    participante_atual = None

    if participante_atual_id:
        participante_atual = next((p for p in ativos if p['id'] == participante_atual_id), None)

    return render_template('selecionar_participante.html',
                           participants=ativos,
                           participante_atual=participante_atual)


@app.route('/login-participante/<int:participante_id>')
def login_participante(participante_id):
    """Define qual participante está fazendo palpites"""
    participants = load_participants()

    # Encontrar o participante
    participante = next((p for p in participants if p['id'] == participante_id), None)

    if not participante:
        flash('Participante não encontrado!', 'error')
        return redirect(url_for('selecionar_participante'))

    if not participante.get('ativo', True):
        flash('Participante inativo!', 'error')
        return redirect(url_for('selecionar_participante'))

    # Salvar na sessão
    session['user_id'] = participante['id']
    session['user_name'] = participante['nome']
    session['user_apelido'] = participante.get('apelido', '')

    flash(f'Bem-vindo, {participante["nome"]}!', 'success')
    return redirect(url_for('palpites'))


@app.route('/logout-participante')
def logout_participante():
    """Desconecta o participante atual"""
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_apelido', None)

    flash('Você saiu do sistema de palpites.', 'info')
    return redirect(url_for('index'))


# ========== APIs para AJAX ==========

@app.route('/api/rodada/<int:numero>/jogos')
def api_jogos_rodada(numero):
    """Retorna jogos de uma rodada específica"""
    games = load_games()
    jogos_rodada = games.get(str(numero), [])
    return jsonify(jogos_rodada)


@app.route('/api/times')
def api_times():
    """Retorna lista de times"""
    return jsonify(TIMES_BRASILEIRAO)


@app.route('/api/participantes')
def api_participantes():
    """API para participantes"""
    participants = load_participants()
    return jsonify(participants)


@app.route('/atualizar-ranking')
def atualizar_ranking():
    """Força a atualização do ranking (para testes)"""
    participants = load_participants()
    games = load_games()

    print("DEBUG: Atualizando ranking...")
    print(f"DEBUG: Total de participantes: {len(participants)}")
    print(f"DEBUG: Total de jogos: {sum(len(j) for j in games.values())}")

    # Recalcular ranking para todos os participantes
    for participante in participants:
        total_pontos = 0
        placares_exatos = 0
        pontos_time = 0
        total_pontos_possiveis = 0

        if 'palpites' not in participante:
            participante['palpites'] = {}
            continue

        print(f"DEBUG: Participante {participante['nome']} tem {len(participante['palpites'])} palpites")

        for rodada_numero, jogos_rodada in games.items():
            for jogo in jogos_rodada:
                if jogo.get('status') == 'Concluído' and jogo.get('placar_casa') is not None:
                    total_pontos_possiveis += 3

                    palpite = participante['palpites'].get(str(jogo['id']))
                    if palpite:
                        print(
                            f"DEBUG: Jogo {jogo['id']}: Palpite {palpite.get('placar_casa')}x{palpite.get('placar_visitante')} vs Resultado {jogo['placar_casa']}x{jogo['placar_visitante']}")

                        pontos = calcular_pontos_palpite(
                            palpite.get('placar_casa'),
                            palpite.get('placar_visitante'),
                            jogo['placar_casa'],
                            jogo['placar_visitante']
                        )

                        if pontos == 3:
                            placares_exatos += 1
                        elif pontos == 1:
                            pontos_time += 1

                        total_pontos += pontos

        # Atualizar dados
        participante['pontos'] = total_pontos
        participante['placares_exatos'] = placares_exatos
        participante['pontos_time'] = pontos_time

        if total_pontos_possiveis > 0:
            participante['aproveitamento'] = round((total_pontos / total_pontos_possiveis) * 100, 1)
        else:
            participante['aproveitamento'] = 0

        print(
            f"DEBUG: {participante['nome']}: {total_pontos} pontos, {placares_exatos} PE, {pontos_time} PTE, {participante['aproveitamento']}%")

    save_participants(participants)
    flash('Ranking atualizado com sucesso!', 'success')
    return redirect(url_for('index'))

# ========== INICIALIZAÇÃO ==========

def inicializar_dados():
    """Inicializa dados padrão"""
    if not os.path.exists(GAMES_FILE):
        save_games({})

    if not os.path.exists(ROUNDS_FILE):
        rounds = []
        for i in range(1, 39):
            rounds.append({
                'id': i,
                'numero': i,
                'nome': f'Rodada {i}',
                'data_inicio': '',
                'data_fim': '',
                'status': 'Não iniciada',
                'data_criacao': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
        save_rounds(rounds)


if __name__ == '__main__':
    if not os.path.exists(PARTICIPANTS_FILE):
        save_participants([])

    inicializar_dados()
    app.run(debug=True, port=5000)