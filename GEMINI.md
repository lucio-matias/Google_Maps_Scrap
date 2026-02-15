# Visão geral do projeto

Você está ajudando a criar um Web Scraping para automatizar a captura de informação de empresas a partir do Google Maps. O objetivo será capturar as informações das empresas apresentadas na página para salvar em um arquivo CSV na pasta Output no diretório do projeto.

1. Considerar o plano de trabalho detalhado no item abaixo em destaque.
2. Gerar uma aplicação em Python que implemente o plano de trabalho solicitado.
3. Utilizar o gerenciador de pacotes **`uv`** para criar e gerenciar um ambiente virtual.
4. Aceitar instruções adicionais para modificar a aplicação em execução.

# Plano de Trabalho

1. Buscar no Google Maps empresas do tipo "Confecção" localizadas na cidade de Nova Friburgo/RJ. Utilizar o MCP disponivel.

2. Extrair para cada empresa separadamente: Name, Full Address, EMAIL. Format: Address as "Street, City, State/Province, Postal Code, Country"; EMAIL, URL

3. Exportar os dados coletados em um arquivo em formato CSV

# Detalhes do fluxo de trabalho

* Nome do ambiente virtual: **`.venv`**, criado utilizando **`uv init`**.
* Instalar as dependências necessárias
* Utilizar **Python 3.14.2**, salvo indicação em contrário.
* Escrever a estrutura central do código no arquivo **`app.py`** no diretório atual

# Preferências de estilo

* O código deve ser limpo e modular, seguindo a formatação **PEP 8**.
* Manter os imports agrupados no topo do arquivo.
* Adicionar comentários inline claros explicando cada etapa principal.

