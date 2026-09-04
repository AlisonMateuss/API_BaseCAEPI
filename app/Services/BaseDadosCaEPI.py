import csv
import ftplib
import io
import zipfile
import pandas as pd
import os
import re

class BaseDadosCaEPI:
    baseDadosDF = None 
    nomeArquivoBase = 'base-de-dados-do-CAEPI.csv'
    nomeArquivoConfigNomesColunas = 'config_nomes_colunas.csv'
    nomeArquivoErros = 'CAs_com_erros.txt'    
    urlBase = 'ftp.mtps.gov.br'
    caminho = 'portal/fiscalizacao/seguranca-e-saude-no-trabalho/caepi/'
    nColunas = 19


    nomeColunas = [
        "RegistroCA",
        "DataValidade",
        "Situacao",
        "NRProcesso",
        "CNPJ",
        "RazaoSocial",
        "Natureza",
        "NomeEquipamento",
        "DescricaoEquipamento",
        "MarcaCA",
        "Referencia",
        "Cor",
        "AprovadoParaLaudo",
        "RestricaoLaudo",
        "ObservacaoAnaliseLaudo",
        "CNPJLaboratorio",
        "RazaoSocialLaboratorio",
        "NRLaudo",
        "Norma"        
    ]

    def __init__(self):
        self = self

    def _baixarArquivoBaseCaEPI(self):
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    from requests.exceptions import ChunkedEncodingError
    import zlib

    print("Baixando base oficial do CAEPI...")

    url = "https://caepi.trabalho.gov.br/internet/ConsultaCAInternet.aspx"

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Encoding": "identity",
        "Connection": "close"
    }

    # =====================================================
    # 1. Acessar página do CAEPI
    # =====================================================

    resposta = session.get(
        url,
        headers=headers,
        timeout=30
    )

    resposta.raise_for_status()

    soup = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    form = soup.find("form")

    if not form:
        raise RuntimeError(
            "Formulário do CAEPI não foi encontrado."
        )

    # =====================================================
    # 2. Capturar campos hidden do ASP.NET
    # =====================================================

    dados = {}

    for input_tag in form.select('input[type="hidden"]'):
        nome = input_tag.get("name")

        if nome:
            dados[nome] = input_tag.get("value", "")

    dados["__EVENTTARGET"] = (
        "ctl00$PlaceHolderConteudo$LinkButton1"
    )

    dados["__EVENTARGUMENT"] = ""

    post_url = urljoin(
        resposta.url,
        form.get("action", "")
    )

    post_headers = headers.copy()
    post_headers["Referer"] = resposta.url

    # =====================================================
    # 3. Fazer POST do botão de download
    # =====================================================

    print("Solicitando arquivo ao servidor CAEPI...")

    download = session.post(
        post_url,
        data=dados,
        headers=post_headers,
        timeout=(30, 300),
        allow_redirects=True,
        stream=True
    )

    download.raise_for_status()

    # =====================================================
    # 4. Baixar GZIP temporário
    # =====================================================

    arquivo_gzip = self.nomeArquivoBase + ".gz.tmp"

    total_baixado = 0

    try:
        with open(arquivo_gzip, "wb") as arquivo:

            for bloco in download.iter_content(
                chunk_size=1024 * 1024
            ):

                if bloco:
                    arquivo.write(bloco)
                    total_baixado += len(bloco)

    except ChunkedEncodingError:

        print(
            "Aviso: servidor CAEPI encerrou "
            "a resposta antecipadamente."
        )

        print(
            "Tentando utilizar o conteúdo recebido."
        )

    if total_baixado == 0:
        raise RuntimeError(
            "Nenhum conteúdo foi recebido do CAEPI."
        )

    print(
        f"Download recebido: "
        f"{total_baixado / 1024 / 1024:.2f} MB"
    )

    # =====================================================
    # 5. Descompactar primeiro bloco GZIP válido
    # =====================================================

    arquivo_csv_temporario = (
        self.nomeArquivoBase + ".tmp"
    )

    descompactador = zlib.decompressobj(
        16 + zlib.MAX_WBITS
    )

    total_extraido = 0
    gzip_finalizado = False

    with open(arquivo_gzip, "rb") as origem:

        with open(
            arquivo_csv_temporario,
            "wb"
        ) as destino:

            while True:

                bloco = origem.read(
                    1024 * 1024
                )

                if not bloco:
                    break

                dados_extraidos = (
                    descompactador.decompress(
                        bloco
                    )
                )

                if dados_extraidos:
                    destino.write(
                        dados_extraidos
                    )

                    total_extraido += len(
                        dados_extraidos
                    )

                if descompactador.eof:
                    gzip_finalizado = True
                    break

    if not gzip_finalizado:
        raise RuntimeError(
            "O arquivo GZIP recebido do CAEPI "
            "não foi finalizado corretamente."
        )

    if total_extraido == 0:
        raise RuntimeError(
            "O arquivo CAEPI foi baixado, "
            "mas nenhum dado foi extraído."
        )

    print(
        f"Base extraída: "
        f"{total_extraido / 1024 / 1024:.2f} MB"
    )

    # =====================================================
    # 6. Validar início do CSV
    # =====================================================

    with open(
        arquivo_csv_temporario,
        "rb"
    ) as arquivo:

        inicio = arquivo.read(500)

    texto_inicio = inicio.decode(
        "utf-8-sig",
        errors="replace"
    )

    if "NR Registro CA" not in texto_inicio:
        raise RuntimeError(
            "O arquivo recebido não parece ser "
            "a base oficial do CAEPI."
        )

    # =====================================================
    # 7. Substituir base antiga somente após validar
    # =====================================================

    os.replace(
        arquivo_csv_temporario,
        self.nomeArquivoBase
    )

    # Remover GZIP temporário
    try:
        os.remove(arquivo_gzip)
    except OSError:
        pass

    print(
        "Download e atualização da base CAEPI "
        "concluídos com sucesso."
    )
    
    def _transformarEmDataFrame(self):
        print("Lendo base de dados CAEPI...")

        self.baseDadosDF = pd.read_csv(
            self.nomeArquivoBase,
            sep=None,
            engine='python',
            dtype=str,
            encoding='utf-8-sig'
        )

        if len(self.baseDadosDF.columns) != len(self.nomeColunas):
            raise ValueError(
                f"Formato inesperado da base CAEPI: "
                f"{len(self.baseDadosDF.columns)} colunas encontradas, "
                f"esperadas {len(self.nomeColunas)}."
            )

        self.baseDadosDF.columns = self.nomeColunas

        print(f"Base carregada: {len(self.baseDadosDF)} registros.")

    def __retornaNomesColunas(self):
        arquivo = open(self.nomeArquivoConfigNomesColunas, encoding='UTF-8')

        return arquivo.readline().split(',')

    def _retornarCAsSemErros(self) -> list:
        listaCAsValidos = []
        listaCAsInvalidos = []

        with open(self.nomeArquivoBase, encoding='UTF-8') as arquivo:
            reader = csv.reader(arquivo, delimiter='|', quotechar='"')
            
            for linhaDf in reader:
                if len(linhaDf) > self.nColunas:
                    # Reconstrói a linha original para tratamento
                    linha_original = '|'.join(linhaDf)
                    resul_tratamento = self._tratarCasComErros(linha_original)
                    if resul_tratamento['sucess']:
                        linhaDf = resul_tratamento['linha']
                    else:
                        listaCAsInvalidos.append(linha_original)
                        continue

                listaCAsValidos.append(linhaDf)

        if listaCAsInvalidos:
            self._criarArquivoComErros(listaCAsInvalidos)

        return listaCAsValidos
    
    def _tratarCasComErros(self, linha) -> dict:
        linhaDf = re.split(r'(?<! )\|', linha)
        if len(linhaDf) > self.nColunas: # Erro
            return {
                'sucess': False,
                'linha': linha
            }

        return    {
            'sucess': True,
            'linha': linhaDf
        }

    def _criarArquivoComErros(self, listaCAsInvalidos:list) -> None:
        with open(self.nomeArquivoErros, 'w') as f:
            f.writelines(listaCAsInvalidos)

    def atualizarBaseDados(self):
        print("Iniciando atualização da base CAEPI...")
    
        self._baixarArquivoBaseCaEPI()
    
        print("Base CAEPI atualizada com sucesso!")
    
        self._transformarEmDataFrame()
    
        return self.baseDadosDF
    
    def retornarBaseDados(self) -> pd.DataFrame:
        if not os.path.exists(self.nomeArquivoBase):
            print("Aguarde o download...")        
            self._baixarArquivoBaseCaEPI()
            print(f"Download concluido!")

        self._transformarEmDataFrame()
        return self.baseDadosDF

    


   
