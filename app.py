
import os
import json
import calendar
@@ -44,64 +45,185 @@
}

# --- HELPERS DE RASPAGEM ---
def obter_html(url: str) -> BeautifulSoup:
    print("Obtendo HTML de:", url)
    # timeout para evitar travar o worker; raise_for_status para falhas HTTP

def obter_dados_inpe():
    """
    Obtém o JSON utilizado pela nova página de estatísticas do INPE.
    O arquivo contém os dados dos seis biomas.
    """
    url = 'https://data.inpe.br/queimadas/estatisticas/media/estatistica/paises/brasil.json'

    print("Obtendo dados do INPE:", url)

req = requests.get(url, timeout=20)
req.raise_for_status()
    soup = BeautifulSoup(req.content, 'html.parser')
    return soup

def raspar_dados_bioma(soup: BeautifulSoup, row: int, col: int):
    # As classes na página seguem o padrão 'data row{row} col{col}'
    celulas_coluna = soup.findAll('td', {'class': f'data row{row} col{col}'})
    valores_coluna = [celula.text.strip() for celula in celulas_coluna]
    return valores_coluna[0] if valores_coluna else None
    dados = req.json()

    print("Dados obtidos com sucesso.")
    print("Última data disponível:", dados['meta']['data_limite'])

    return dados

def encontrar_media_e_recorde_mensal(soup: BeautifulSoup, mes_solicitado: str):

def extrair_dados_bioma(dados, bioma):
"""
    Retorna duas strings formatadas:
      - 'Média do mês - X focos'
      - 'Recorde do mês - Y focos (no ano Z)'
    Em caso de dados ausentes, retorna 'n/d'.
    Extrai as informações de um bioma:
      - Focos no último dia disponível
      - Acumulado do mês atual
      - Total do mesmo mês do ano passado
      - Média histórica mensal
      - Recorde histórico mensal
   """
    print("Encontrando média e recorde mensal...")
    quantidade_linhas = 29  # anos na tabela

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
@@ -176,52 +298,30 @@ def enviar_email_biomas(informacoes_biomas):
raise
print("E-mails enviados com sucesso via Brevo API.")


# --- PIPELINE PRINCIPAL ---

def run():
informacoes_biomas = []

    # Obtém os dados de todos os biomas em uma única requisição.
    dados = obter_dados_inpe()

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
        print(f"Obtendo informações para {bioma.capitalize()}...")

        informacoes = extrair_dados_bioma(dados, bioma)

        informacoes_biomas.append(informacoes)

print("Enviando e-mail para todos os biomas...")
enviar_email_biomas(informacoes_biomas)

return "E-mail enviado com sucesso!"


# --- FLASK APP ---

app = Flask(__name__)

@app.route('/biomas')
