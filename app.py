import requests
from bs4 import BeautifulSoup
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

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

# Função para obter o HTML de uma URL
def obter_html(url):
    print("Obtendo HTML de:", url)
    req = requests.get(url)
    html = req.content
    soup = BeautifulSoup(html, 'html.parser')
    return soup

# Função para raspar os dados de uma célula específica
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
        valores_mensal = [int(celula.text.strip()) for celula in celulas_mensal if celula.text.strip().isdigit()]  
        
        # Calcular a média
        if valores_mensal:
            media_mensal = sum(valores_mensal) / len(valores_mensal)
            resultado_media = f'Média do mês - {int(media_mensal)} focos\n'

        # Encontrar o recorde de focos para o mês solicitado
        lista_mensal = []
        for y in range(quantidade_linhas):
            # Procurando, em todas as linhas, quais células da coluna têm o valor do recorde
            celulas_mensal = soup.findAll('td', {'class': f'data row{y} col{mes_index}'})
            valores_mensal = [int(celula.text.strip()) for celula in celulas_mensal if celula.text.strip().isdigit()]
            lista_mensal.extend(valores_mensal)

        # Calcular o recorde
        if lista_mensal:
            maior_valor_mensal = max(lista_mensal)
            ano_do_recorde_mensal = 1999 + lista_mensal.index(maior_valor_mensal)
            if mes_index >= 5:  
                ano_do_recorde_mensal = ano_do_recorde_mensal - 1
            resultado_recorde = f'Recorde do mês - {maior_valor_mensal} focos (no ano {ano_do_recorde_mensal})\n'

        # Retornar tanto a média quanto o recorde
        return resultado_media, resultado_recorde

# Função para enviar o e-mail
def enviar_email(focos_24h_amazonia, acumulado_mes_atual_amazonia, total_mesmo_mes_ano_passado_amazonia, media_amazonia, recorde_amazonia, 
                 focos_24h_cerrado, acumulado_mes_atual_cerrado, total_mesmo_mes_ano_passado_cerrado, media_cerrado, recorde_cerrado):
    smtp_server = "smtp-relay.brevo.com"
    port = 587
    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    remetente = "marcoscony@gmail.com"
    destinatarios = ["marcoscony@gmail.com", 'marcos.acony@g.globo']
    titulo = "Teste de email"

    texto = f"""
    AMAZÔNIA - FOCOS DE INCÊNDIO

    24h - {focos_24h_amazonia} focos
    Acumulado do mês atual - {acumulado_mes_atual_amazonia} focos (vs {total_mesmo_mes_ano_passado_amazonia} focos totais no mesmo mês do ano passado)
    {media_amazonia}
    {recorde_amazonia}

    CERRADO - FOCOS DE INCÊNDIO

    24h - {focos_24h_cerrado} focos
    Acumulado do mês atual - {acumulado_mes_atual_cerrado} focos (vs {total_mesmo_mes_ano_passado_cerrado} focos totais no mesmo mês do ano passado)
    {media_cerrado}
    {recorde_cerrado}
    """

    html = f"""
    <html>
      <body>
        <ul>
          <h2 style="color: #8B0000;"><b>AMAZÔNIA - FOCOS DE INCÊNDIO</b></h2>
          <li><b style="color: #555555;">24h</b> - {focos_24h_amazonia} focos<br></li>
          <li><b style="color: #555555;">Acumulado do mês atual</b> - {acumulado_mes_atual_amazonia} focos (vs {total_mesmo_mes_ano_passado_amazonia} focos totais no mesmo mês do ano passado)<br></li>
          <li><b style="color: orange;">{media_amazonia}</b><br></li>
          <li><b style="color: red;">{recorde_amazonia}</b><br></li>
          
          <h2 style="color: #8B0000;"><b>CERRADO - FOCOS DE INCÊNDIO</b></h2>
          <li><b style="color: #555555;">24h</b> - {focos_24h_cerrado} focos<br></li>
          <li><b style="color: #555555;">Acumulado do mês atual</b> - {acumulado_mes_atual_cerrado} focos (vs {total_mesmo_mes_ano_passado_cerrado} focos totais no mesmo mês do ano passado)<br></li>
          <li><b style="color: orange;">{media_cerrado}</b><br></li>
          <li><b style="color: red;">{recorde_cerrado}</b><br></li>
        </ul>
      </body>
    </html>
    """

    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(email, password)

    mensagem = MIMEMultipart("alternative")
    mensagem["From"] = remetente
    mensagem["To"] = ",".join(destinatarios)
    mensagem["Subject"] = '🔎 FOCO NOS FOCOS 🔥'
    conteudo_texto = MIMEText(texto, "plain")
    conteudo_html = MIMEText(html, "html")
    mensagem.attach(conteudo_texto)
    mensagem.attach(conteudo_html)

    print('Enviando e-mail')
    server.sendmail(remetente, destinatarios, mensagem.as_string())
    server.quit()

    print("E-mail enviado com sucesso.")

# Função para obter o HTML e raspar dados dos biomas especificados
def obter_e_raspar_biomas(url_amazonia, url_cerrado):
    # Obter dados da Amazônia
    print("Obtendo HTML da URL para Amazônia")
    soup_amazonia = obter_html(url_amazonia)
    data_atual = datetime.now()
    dia_do_mes = data_atual.day
    focos_24h_amazonia = raspar_dados_bioma(soup_amazonia, 1, dia_do_mes - 2)
    acumulado_mes_atual_amazonia = raspar_dados_bioma(soup_amazonia, 1, 30)
    total_mesmo_mes_ano_passado_amazonia = raspar_dados_bioma(soup_amazonia, 0, 30)
    mes_atual = data_atual.month

    # Encontrar o nome do mês correspondente ao número do mês atual
    nome_mes_atual = None
    for mes, numero in mapping_meses.items():
        if numero == mes_atual - 1: 
            nome_mes_atual = mes

    print("Obtendo HTML da URL para Cerrado")
    soup_cerrado = obter_html(url_cerrado)
    focos_24h_cerrado = raspar_dados_bioma(soup_cerrado, 1, dia_do_mes - 2)
    acumulado_mes_atual_cerrado = raspar_dados_bioma(soup_cerrado, 1, 30)
    total_mesmo_mes_ano_passado_cerrado = raspar_dados_bioma(soup_cerrado, 0, 30)

    print('Executando função de média e recorde mensal para Amazônia')
    media_amazonia, recorde_amazonia = encontrar_media_e_recorde_mensal(soup_amazonia, nome_mes_atual)

    print('Executando função de média e recorde mensal para Cerrado')
    media_cerrado, recorde_cerrado = encontrar_media_e_recorde_mensal(soup_cerrado, nome_mes_atual)

    print("Enviando e-mail com informações sobre Amazônia e Cerrado")
    enviar_email(focos_24h_amazonia, acumulado_mes_atual_amazonia, total_mesmo_mes_ano_passado_amazonia, media_amazonia, recorde_amazonia,
                 focos_24h_cerrado, acumulado_mes_atual_cerrado, total_mesmo_mes_ano_passado_cerrado, media_cerrado, recorde_cerrado)

    return "E-mail enviado com sucesso com informações sobre Amazônia e Cerrado!"

app = Flask(__name__)

# Rota para enviar e-mail com dados da Amazônia e do Cerrado
@app.route('/biomas')
def biomas():
    # URL da Amazônia
    url_amazonia = 'http://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/bioma/grafico_historico_mes_atual_estado_amazonia.html'
    # URL do Cerrado
    url_cerrado = 'http://terrabrasilis.dpi.inpe.br/queimadas/situacao-atual/media/bioma/grafico_historico_mes_atual_estado_cerrado.html'
    return obter_e_raspar_biomas(url_amazonia, url_cerrado)

if __name__ == '__main__':
    app.run(debug=True)
