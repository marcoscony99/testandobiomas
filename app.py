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
def obter_html(url: str) -> BeautifulSoup:
    print("Obtendo HTML de:", url)
    # timeout para evitar travar o worker; raise_for_status para falhas HTTP
    req = requests.get(url, timeout=20)
    req.raise_for_status()
    soup = BeautifulSoup(req.content, 'html.parser')
    return soup

def raspar_dados_bioma(soup: BeautifulSoup, row: int, col: int):
    # As classes na página seguem o padrão 'data row{row} col{col}'
    celulas_coluna = soup.findAll('td', {'class': f'data row{row} col{col}'})
    valores_coluna = [celula.text.strip() for celula in celulas_coluna]
    return valores_coluna[0] if valores_coluna else None

def encontrar_media_e_recorde_mensal(soup: BeautifulSoup, mes_solicitado: str):
    """
    Retorna duas strings formatadas:
      - 'Média do mês - X focos'
      - 'Recorde do mês - Y focos (no ano Z)'
    Em caso de dados ausentes, retorna 'n/d'.
    """
    print("Encontrando média e recorde mensal...")
    quantidade_linhas = 29  # anos na tabela
    resultado_media = 'Média do mês - n/d'
    resultado_recorde = 'Recorde do mês - n/d'

    if not mes_solicitado:
        return resultado_media, resultado_recorde

    mes_idx = mapping_meses.get(mes_solicitado.lower())
    if mes_idx is None:
        return resultado_media, resultado_recorde

    # Média na linha 30 (índice 29 no HTML)
    celulas_mensal = soup.findAll('td', {'class': f'data row30 col{mes_idx}'})
    valores_mensal = [int(cel.text.strip()) for cel in celulas_mensal if cel.text.strip().isdigit()]
    if valores_mensal:
        media_mensal = sum(valores_mensal) / len(valores_mensal)
        resultado_media = f'Média do mês - {int(media_mensal)} focos'

    # Recorde: percorre linhas por ano
    lista_mensal = []
    for y in range(quantidade_linhas):
        cel_y = soup.findAll('td', {'class': f'data row{y} col{mes_idx}'})
        vals_y = [int(cel.text.strip()) for cel in cel_y if cel.text.strip().isdigit()]
        lista_mensal.extend(vals_y)

    if lista_mensal:
        maior_valor = max(lista_mensal)
        ano_recorde = 1999 + lista_mensal.index(maior_valor)
        # Ajuste de ano se a coluna for >= junho (copiado da sua lógica original)
        if mes_idx >= 5:
            ano_recorde = ano_recorde - 1
        resultado_recorde = f'Recorde do mês - {maior_valor} focos (no ano {ano_recorde})'

    return resultado_media, resultado_recorde

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

    for bioma in nomes_biomas:
        print(f"Obtendo HTML da URL para {bioma.capitalize()}...")
        url_dados = f'https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/bioma/grafico_historico_mes_atual_estado_{bioma}.html'
        soup = obter_html(url_dados)

        data_atual = datetime.now(tz_brasilia)
        dia_do_mes = data_atual.day
        numero_dias_mes = calendar.monthrange(data_atual.year, data_atual.month)[1]

        # Colunas no HTML parecem 0-based; mantém sua lógica original
        focos_24h = raspar_dados_bioma(soup, 1, dia_do_mes - 1)
        acumulado_mes_atual_bioma = raspar_dados_bioma(soup, 1, numero_dias_mes)
        total_mesmo_mes_ano_passado_bioma = raspar_dados_bioma(soup, 0, numero_dias_mes)

        mes_atual = data_atual.month
        nome_mes_atual = None
        for mes, numero in mapping_meses.items():
            if numero == mes_atual - 1:
                nome_mes_atual = mes

        print(f"Obtendo HTML da URL para média e recorde do {bioma.capitalize()}...")
        url_media_recorde = f'https://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media//bioma/grafico_historico_estado_{bioma}.html'
        soup_media_recorde = obter_html(url_media_recorde)

        print(f'Executando função de média e recorde mensal para {bioma.capitalize()}')
        media, recorde = encontrar_media_e_recorde_mensal(soup_media_recorde, nome_mes_atual)

        informacoes_biomas.append({
            'bioma': bioma,
            'focos_24h': focos_24h,
            'acumulado_mes_atual_bioma': acumulado_mes_atual_bioma,
            'total_mesmo_mes_ano_passado_bioma': total_mesmo_mes_ano_passado_bioma,
            'media': media,
            'recorde': recorde
        })

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
