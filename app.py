import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, render_template
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

nomes_biomas = ['amazonia', 'cerrado', 'pantanal', 'mata_atlantica', 'caatinga', 'pampa']  # Renomeado de 'biomas' para 'nomes_biomas'

# Mapeamento dos meses
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

# função para pegar a "sopa", dado um html
def obter_html(url):
    print("Obtendo HTML de:", url)
    req = requests.get(url)
    html = req.content
    soup = BeautifulSoup(html, 'html.parser')
    return soup


# Dado um html, raspa os dados de uma célula específica
def raspar_dados_bioma(soup, row, col):
    print("Raspando dados do bioma...")
    celulas_coluna = soup.findAll('td', {'class': f'data row{row} col{col}'})
    valores_coluna = [celula.text.strip() for celula in celulas_coluna]
    return valores_coluna[0] if valores_coluna else None


# Função para encontrar a média e o recorde mensal
def encontrar_media_e_recorde_mensal(soup, mes_solicitado):
    print("Encontrando média e recorde mensal...")
    quantidade_linhas = 27
    
    if mes_solicitado.lower() in mapping_meses:
        mes_index = mapping_meses[mes_solicitado.lower()]

        # Encontrar as células da coluna específica do mês solicitado para calcular a média
        celulas_mensal = soup.findAll('td', {'class': f'data row28 col{mes_index}'})
        valores_mensal = [int(celula.text.strip()) for celula in celulas_mensal if celula.text.strip().isdigit()]  # Convertendo e filtrando valores inteiros

        # Calcular a média
        if valores_mensal:
            media_mensal = sum(valores_mensal) / len(valores_mensal)
            resultado_media = f'Média do mês - {int(media_mensal)} focos\n'

        # Encontrar o recorde de focos para o mês solicitado
        lista_mensal = []
        for y in range(quantidade_linhas):
            # Procurando, em todas as linhas, quais células da coluna têm o valor do recorde
            celulas_mensal = soup.findAll('td', {'class': f'data row{y} col{mes_index}'})
            valores_mensal = [int(celula.text.strip()) for celula in celulas_mensal if celula.text.strip().isdigit()]  # Convertendo e filtrando valores inteiros
            lista_mensal.extend(valores_mensal)

        # Calcular o recorde
        if lista_mensal:
            maior_valor_mensal = max(lista_mensal)
            ano_do_recorde_mensal = 1999 + lista_mensal.index(maior_valor_mensal)
            if mes_index >= 5:  # Se o mês for junho ou posterior, subtrai 1 do ano do recorde
                ano_do_recorde_mensal = ano_do_recorde_mensal - 1
            resultado_recorde = f'Recorde do mês - {maior_valor_mensal} focos (no ano {ano_do_recorde_mensal})\n'

        # Retornar tanto a média quanto o recorde
        return resultado_media, resultado_recorde

#parte do código que vai enviar o e-mail do bioma específico
def enviar_email_biomas(informacoes_biomas):
    smtp_server = "smtp-relay.brevo.com"
    port = 587
    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    remetente = "marcoscony@gmail.com"
    destinatarios = ["marcoscony@gmail.com", 'marcos.acony@g.globo']
    titulo = "Teste de email"

    mensagem = MIMEMultipart("alternative")
    mensagem["From"] = remetente
    mensagem["To"] = ",".join(destinatarios)
    mensagem["Subject"] = '🔎 FOCO NOS FOCOS 🔥'

    texto = ""
    html = """
    <html>
      <body>
        <h1 style="color: #8B0000;">🔎 FOCO NOS FOCOS 🔥</h1>
    """

    for bioma_info in informacoes_biomas:
        bioma = bioma_info['bioma']
        focos_24h = bioma_info['focos_24h']
        acumulado_mes_atual_bioma = bioma_info['acumulado_mes_atual_bioma']
        total_mesmo_mes_ano_passado_bioma = bioma_info['total_mesmo_mes_ano_passado_bioma']
        media = bioma_info['media']
        recorde = bioma_info['recorde']

        texto += f"""
        {bioma.upper()}

        24h - {focos_24h} focos
        Acumulado do mês atual - {acumulado_mes_atual_bioma} focos (vs {total_mesmo_mes_ano_passado_bioma} focos totais no mesmo mês do ano passado)
        {media}
        {recorde}

        """

        html += f"""
        <h2 style="color: #8B0000;"><b>{bioma.upper()}</b></h2>
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

    conteudo_texto = MIMEText(texto, "plain")
    conteudo_html = MIMEText(html, "html")
    mensagem.attach(conteudo_texto)
    mensagem.attach(conteudo_html)

    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(email, password)

    print("Enviando e-mail para os biomas...")
    server.sendmail(remetente, destinatarios, mensagem.as_string())
    server.quit()

    print("E-mails para os biomas enviados com sucesso.")

# Código que roda tudo
# Mapeamento dos nomes dos biomas com acento
mapeamento_biomas = {
    'amazonia': 'AMAZÔNIA',
    'cerrado': 'CERRADO',
    'pantanal': 'PANTANAL',
    'mata_atlantica': 'MATA ATLÂNTICA',
    'caatinga': 'CAATINGA',
    'pampa': 'PAMPA'
}

def run():
    informacoes_biomas = []

    for bioma in nomes_biomas:  # Iterando sobre nomes_biomas
        bioma_capitalizado = mapeamento_biomas.get(bioma, bioma.replace("_", " ").capitalize())  # Capitaliza e substitui "_" por espaço
        print(f"Obtendo HTML da URL para {bioma_capitalizado}...")
        url_dados = f'http://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/bioma/grafico_historico_mes_atual_estado_{bioma}.html'
        soup = obter_html(url_dados)
        data_atual = datetime.now()
        dia_do_mes = data_atual.day
        focos_24h = raspar_dados_bioma(soup, 1, dia_do_mes - 2)
        acumulado_mes_atual_bioma = raspar_dados_bioma(soup, 1, 30)
        total_mesmo_mes_ano_passado_bioma = raspar_dados_bioma(soup, 0, 30)
        mes_atual = data_atual.month

        # Encontrar o nome do mês correspondente ao número do mês atual
        nome_mes_atual = None
        for mes, numero in mapping_meses.items():
            if numero == mes_atual - 1:  # Subtraímos 1 porque os meses em Python vão de 1 a 12
                nome_mes_atual = mes

        print(f"Obtendo HTML da URL para média e recorde do {bioma_capitalizado}...")
        url_media_recorde = f'http://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media//bioma/grafico_historico_estado_{bioma}.html'
        soup_media_recorde = obter_html(url_media_recorde)

        print(f'Executando função de média e recorde mensal para {bioma_capitalizado}')
        media, recorde = encontrar_media_e_recorde_mensal(soup_media_recorde, nome_mes_atual)
        
        # Armazenar informações do bioma em uma lista
        informacoes_biomas.append({
            'bioma': bioma_capitalizado,
            'focos_24h': focos_24h,
            'acumulado_mes_atual_bioma': acumulado_mes_atual_bioma,
            'total_mesmo_mes_ano_passado_bioma': total_mesmo_mes_ano_passado_bioma,
            'media': media,
            'recorde': recorde
        })

    print("Enviando e-mail para todos os biomas...")
    enviar_email_biomas(informacoes_biomas)
    
    return "E-mail enviado com sucesso!"



app = Flask(__name__)

@app.route('/biomas')
def biomas():
    # Chama a função run, que tem como objetivo disparar o e-mail
    return run()

if __name__ == '__main__':
    app.run(debug=True)
