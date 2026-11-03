
import os
import json
import calendar
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from flask import Flask
from dotenv import load_dotenv

# --- ENV ---
# Em produção no Render, as env vars vêm do painel; load_dotenv() só ajuda localmente.
load_dotenv()

# --- TIMEZONE ---
tz_brasilia = pytz.timezone('America/Sao_Paulo')

# --- CONSTANTES ---
nomes_biomas = ['amazonia', 'cerrado', 'pantanal', 'mata_atlantica', 'caatinga', 'pampa']

mapping_meses = {
    'janeiro': 0,
    'fevereiro': 1,
    'março': 2,
    'abril': 3,
    'maio': 4,
    'junho': 5,
    'julho': 6,
    'agosto': 7,
    'setembro': 8,
    'outubro': 9,
    'novembro': 10,
    'dezembro': 11
}

mapeamento_biomas = {
    'amazonia': 'AMAZÔNIA',
    'cerrado': 'CERRADO',
    'pantanal': 'PANTANAL',
    'mata_atlantica': 'MATA ATLÂNTICA',
    'caatinga': 'CAATINGA',
    'pampa': 'PAMPA'
}

# --- HELPERS DE RASPAGEM ---

def obter_dados_inpe():
    """
    Obtém o JSON utilizado pela nova página de estatísticas do INPE.
    O arquivo contém os dados dos seis biomas.
    """
    url = 'https://data.inpe.br/queimadas/estatisticas/media/estatistica/paises/brasil.json'

    print("Obtendo dados do INPE:", url)

    req = requests.get(url, timeout=20)
    req.raise_for_status()

    dados = req.json()

    print("Dados obtidos com sucesso.")
    print("Última data disponível:", dados['meta']['data_limite'])

    return dados


def extrair_dados_bioma(dados, bioma):
    """
    Extrai as informações de um bioma:
      - Focos no último dia disponível
      - Acumulado do mês atual
      - Total do mesmo mês do ano passado
      - Média histórica mensal
      - Recorde histórico mensal
    """

    print(f"Processando dados do bioma: {bioma}")

    data_atual = datetime.now(tz_brasilia)
    mes_atual = data_atual.month
    ano_atual = data_atual.year

    nome_bioma = mapeamento_biomas[bioma]

    # Identifica o bioma pelo nome, ignorando diferenças de caixa.
    def corresponde_bioma(registro):
        nome = (registro.get('bioma') or {}).get('nome_bioma')

        return (
            isinstance(nome, str)
            and nome.upper() == nome_bioma
        )

    # --- HISTÓRICO MENSAL ---

    historico = dados['historico_mensal']
    totais_por_ano = {}

    for registro in historico:
        if not corresponde_bioma(registro):
            continue

        ano = registro['ano']
        valor = registro['meses'].get(str(mes_atual))

        if valor is not None:
            totais_por_ano[ano] = (
                totais_por_ano.get(ano, 0) + valor
            )

    # --- COMPARATIVO DIÁRIO ---

    diario = dados['comparativo_diario']['registros']
    diarios_por_data = {}

    for registro in diario:
        if not corresponde_bioma(registro):
            continue

        data = registro['data']
        valor = registro.get('quantidade_focos')

        # Ignora dados ainda não disponíveis.
        if valor is None:
            continue

        diarios_por_data[data] = (
            diarios_por_data.get(data, 0) + valor
        )

    # Utiliza a data limite informada pelo INPE.
    data_limite = dados['meta']['data_limite']

    # Identifica os dias disponíveis do mês atual.
    datas_validas = [
        data for data in diarios_por_data
        if data.startswith(f"{ano_atual}-{mes_atual:02d}-")
        and data <= data_limite
    ]

    if not datas_validas:
        raise ValueError(
            f"Não foram encontrados dados diários atuais para {bioma}"
        )

    # --- FOCOS NAS ÚLTIMAS 24H ---

    ultima_data = max(datas_validas)

    focos_24h = diarios_por_data[ultima_data]

    print(f"Último dia disponível para {bioma}: {ultima_data}")
    print(f"Focos no último dia: {focos_24h}")

    # --- ACUMULADO DO MÊS ATUAL ---

    acumulado_mes_atual_bioma = sum(
        valor
        for data, valor in diarios_por_data.items()
        if data.startswith(f"{ano_atual}-{mes_atual:02d}-")
        and data <= ultima_data
    )

    # --- MESMO MÊS DO ANO PASSADO ---

    ano_passado = ano_atual - 1

    total_mesmo_mes_ano_passado_bioma = (
        totais_por_ano.get(ano_passado)
    )

    if total_mesmo_mes_ano_passado_bioma is None:
        total_mesmo_mes_ano_passado_bioma = 'n/d'

    # --- MÉDIA E RECORDE HISTÓRICO ---

    # Exclui o ano corrente dos cálculos históricos.
    historicos = {
        ano: valor
        for ano, valor in totais_por_ano.items()
        if ano < ano_atual
    }

    resultado_media = 'Média do mês - n/d'
    resultado_recorde = 'Recorde do mês - n/d'

    if historicos:
        valores = list(historicos.values())

        media_mensal = sum(valores) / len(valores)

        resultado_media = (
            f'Média do mês - {int(media_mensal)} focos'
        )

        ano_recorde = max(
            historicos,
            key=historicos.get
        )

        maior_valor = historicos[ano_recorde]

        resultado_recorde = (
            f'Recorde do mês - {maior_valor} focos '
            f'(no ano {ano_recorde})'
        )

    print(f"Acumulado mensal: {acumulado_mes_atual_bioma}")
    print(f"Mesmo mês do ano passado: {total_mesmo_mes_ano_passado_bioma}")
    print(resultado_media)
    print(resultado_recorde)

    return {
        'bioma': bioma,
        'focos_24h': focos_24h,
        'acumulado_mes_atual_bioma': acumulado_mes_atual_bioma,
        'total_mesmo_mes_ano_passado_bioma': total_mesmo_mes_ano_passado_bioma,
        'media': resultado_media,
        'recorde': resultado_recorde
    }


# --- ENVIO DE E-MAIL VIA API DO BREVO (sem SMTP) ---

def enviar_email_biomas(informacoes_biomas):
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY não configurada nas variáveis de ambiente.")

    remetente = os.environ.get("SENDER_EMAIL", "marcoscony@gmail.com")
    destinatarios = ["marcoscony@gmail.com", "marcos.acony@g.globo"]
    assunto = "🔎 FOCO NOS FOCOS 🔥"

    # Monta conteúdo de texto e HTML
    texto = ""
    html = """
    <html>
      <body>
        <h1 style="color: #8B0000;">🔎 FOCO NOS FOCOS 🔥</h1>
    """

    for bioma_info in informacoes_biomas:
        bioma = bioma_info['bioma']
        nome_bioma_com_acento = mapeamento_biomas.get(bioma, bioma.upper())
        focos_24h = bioma_info['focos_24h']
        acumulado_mes_atual_bioma = bioma_info['acumulado_mes_atual_bioma']
        total_mesmo_mes_ano_passado_bioma = bioma_info['total_mesmo_mes_ano_passado_bioma']
        media = bioma_info['media']
        recorde = bioma_info['recorde']

        texto += f"""
{nome_bioma_com_acento}

24h - {focos_24h} focos
Acumulado do mês atual - {acumulado_mes_atual_bioma} focos (vs {total_mesmo_mes_ano_passado_bioma} focos totais no mesmo mês do ano passado)
{media}
{recorde}

"""

        html += f"""
        <h2 style="color: #8B0000;"><b>{nome_bioma_com_acento}</b></h2>
        <ul>
          <li><b style="color: #555555;">24h</b> - {focos_24h} focos</li>
          <li><b style="color: #555555;">Acumulado do mês atual</b> - {acumulado_mes_atual_bioma} focos (vs {total_mesmo_mes_ano_passado_bioma} focos totais no mesmo mês do ano passado)</li>
          <li><b style="color: orange;">{media}</b></li>
          <li><b style="color: red;">{recorde}</b></li>
        </ul>
        """

    html += """
      </body>
    </html>
    """

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }
    payload = {
        "sender": {"email": remetente, "name": "Foco nos Focos"},
        "to": [{"email": e} for e in destinatarios],
        "subject": assunto,
        "textContent": texto,
        "htmlContent": html,
    }

    print("Enviando e-mail via Brevo API...")
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    try:
        resp.raise_for_status()
    except Exception:
        print("Erro no envio:", resp.status_code, resp.text)
        raise
    print("E-mails enviados com sucesso via Brevo API.")


# --- PIPELINE PRINCIPAL ---

def run():
    informacoes_biomas = []

    # Obtém os dados de todos os biomas em uma única requisição.
    dados = obter_dados_inpe()

    for bioma in nomes_biomas:
        print(f"Obtendo informações para {bioma.capitalize()}...")

        informacoes = extrair_dados_bioma(dados, bioma)

        informacoes_biomas.append(informacoes)

    print("Enviando e-mail para todos os biomas...")
    enviar_email_biomas(informacoes_biomas)

    return "E-mail enviado com sucesso!"


# --- FLASK APP ---

app = Flask(__name__)

@app.route('/biomas')
def biomas():
    return run()

if __name__ == '__main__':
    # Em ambientes locais, o debug ajuda. No Render, use o start command padrão.
    app.run(debug=True)
