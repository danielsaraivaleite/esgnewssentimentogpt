'''
Módulo de rotinas de processamento textuais usadas para tratar as noticias capturadas
Autor: Daniel Saraiva Leite - 2023
Projeto Análise de sentimentos sobre notícias do tema ESG
'''

import numpy as np
import pandas as pd
import nltk
import re
from collections import Counter
import unidecode
import datetime as dt
import spacy
import string
import hashlib
from noticias_io import  le_termos_esg_para_df
nltk.download('rslp')
nltk.download('punkt')
nltk.download('stopwords')


stopwords = nltk.corpus.stopwords.words('portuguese')

nlp = spacy.load('pt_core_news_sm')

def remove_pontuacao(text,punct_list=list(string.punctuation)):
    '''
    Remove pontuação do texto
    usado no classificador ESG
    '''
    for punc in punct_list:
        if punc in text:
            text = text.replace(punc, ' ')
    return text.strip()

REPLACE_BY_SPACE_RE = re.compile('[/(){}\[\]\|@,;]')


def limpar_texto(text):
    '''
    Limpa o texto para fazer a classificação, retirando caracteres especiais, numeros, acentuacao e pontuacao
    '''
    text = re.sub(r'\d+', '', text)
    text = re.sub('\s+', ' ', text).strip()
    text = remove_pontuacao(text)
    text = text.lower() 
    text = text.replace('"', '')
    text = text.replace('+', '')
    text = text.replace('#', '')
    text = REPLACE_BY_SPACE_RE.sub(' ', text) 
    return text



def lematizador(text):
    '''
    Lematizador utilizando spacy
    '''
    sent = []
    doc = nlp(text)
    for word in doc:
        if word.pos_ == "VERB":
            sent.append(word.lemma_)
        else:
            sent.append(word.orth_)
    return " ".join(sent)



def remove_acentos(texto):
    '''
    Remove acentos
    '''
    return unidecode.unidecode(texto)



def trim_texto(texto):
    '''
    Retira espaços e tabs (trailing e dentro)
    '''
    texto = ''.join(filter(lambda character:ord(character) < 0xff,texto))
    texto = ' '.join(texto.split())
    return texto



def lista_stopwords_classificador_esg():
    '''
     Lista de stopwords para a classificação do ESG
    '''
    return list(spacy.lang.pt.stop_words.STOP_WORDS) + ['abc', 'xyz', 'def', 'caracteres', 'empresa']
    

def remove_termos_comuns(lista_empresas):
    '''
    Remove termos comuns para não pesquisar
    '''
    
    stopw = ['le', 'paulo','investimentos', 'brasil', 'carlos', 'rede', 'rio', 'ser', 'pao', 'time', 'joao', 'viver', 'rumo', 'oi', 'santos', 'porto', 'soma', 'construtora', 'transmissao', 'blue', 'pague', 'smart', 'log', 'nacional', 'siderurgica', 'mateus', 'cury', 'mundial', 'boa', 'caixa']
    result = lista_empresas
    
    for w in stopw:
        if w in result:
            result.remove(w)
    return result
    
    

def remove_nome_composto(nome_composto):
    '''
    Remove nomes compostos (ex Lojas Americanas > Americanas, Banco Itaú > Itaú)
    '''
    
    excecoes = [ 'banco do brasil', 'bb seguridade']
    
    termos_remover = ['são', 'do', 'de', 'da', 'das', 'dos', 'boa', 'indústria', 'indústrias', 'banco','grupo','consórcio', 'construtora', 'comércio', 'atacadista', 'varejista', 'lojas', 'conservas', 'energia', 'paulista','alimentos', 'alimentos','empresa','brasil', 's.a.', 's/a', 'participações', 'br', 'ltda', 'm.' ]
    
    nome = list(nome_composto.lower().split(' '))
    i = 0

    while i < len(termos_remover) and len(nome) > 1:
        if termos_remover[i] in nome:
            nome.remove(termos_remover[i])
        
        i = i+1
        
    if nome_composto.lower().strip() not in excecoes:   # excecoes
        return nome[0].split('-')[0]
    else:
        return nome_composto

        
    

def aplica_stemming_texto(texto):
    '''
    Faz o stemming de um texto
    '''
    stemmer = nltk.stem.RSLPStemmer()
    return remove_acentos(' '.join(stemmer.stem(token) for token in nltk.word_tokenize(texto)))



def remove_palavras_texto(texto, lista_palavras):
    '''
    Remove certas palavras de um texto
    '''
    query = texto
    stopwords = lista_palavras

    return ' '.join(  [word for word in re.split("\W+",query) if word.lower() not in stopwords])


def conta_palavras_compostas(texto_stem, expressao):
    '''
    Conta palavras compostas 
    '''
    return len(re.findall(r'\b' + expressao.strip().lower() + r'\b' , texto_stem))



def conta_termos_esg(texto, termos):
    '''
     Conta os termos ESG num texto. A fonte dos termos é um Dataframe
    '''

    texto_stem = aplica_stemming_texto(remove_palavras_texto(texto.lower(), stopwords))

    termos['QtdeE'] = 0
    termos['QtdeS'] = 0
    termos['QtdeG'] = 0

    termos['QtdeE'] = termos['E'].apply(lambda x: conta_palavras_compostas(texto_stem, aplica_stemming_texto(x) ) if not pd.isna(x) else 0)
    termos['QtdeS'] = termos['S'].apply(lambda x: conta_palavras_compostas(texto_stem, aplica_stemming_texto(x) ) if not pd.isna(x) else 0)
    termos['QtdeG'] = termos['G'].apply(lambda x: conta_palavras_compostas(texto_stem, aplica_stemming_texto(x) ) if not pd.isna(x) else 0)
    
    r =  ( sum(termos['QtdeE']) , sum(termos['QtdeS']), sum(termos['QtdeG']) )
    
    return r



def classifica_texto(texto, termos):
    '''
     Verifica a qual categoria ESG o texto mais se relaciona pela soma de contagem dos termos
    '''
    df = pd.DataFrame({'Dimensão' : ['E', 'S', 'G'], 'Contagem': list(conta_termos_esg(texto,termos ))}).sort_values(by=['Contagem', 'Dimensão'], ascending=[False, False])
    
    if np.sum(df['Contagem']) == 0:
        return 'Outros'
    else:
        return df.iloc[0]['Dimensão']
    

def classifica_textos_coletados(noticias, apenas_titulos=False):
    '''
    Classifica todas as noticias
    '''
    dfTermos = le_termos_esg_para_df()
    
    noticias['classificacao'] = noticias['texto_completo'].apply(lambda x : classifica_texto(x, dfTermos ) )
    
    return noticias



def filtra_noticias_nao_relacionadas(noticias, empresa, apenas_titulos=False):
    '''
    Filtra notícias não relacionadas
    '''

    df = noticias
    emp_ajustada = remove_nome_composto(remove_acentos(empresa)).lower()
    
    if not apenas_titulos:
        df = df[ df['texto_completo'].apply(lambda x : remove_acentos(x.lower())).str.contains(emp_ajustada)   ]
    else:
        df = df[ df['titulo'].apply(lambda x : remove_acentos(x.lower())).str.contains(emp_ajustada)   ]
    return df



def filtra_noticias_sem_classificacao(noticias, empresa):
    '''
    Filtra notícias sem classificacao
    '''
    df = noticias
    df = df[df['classificacao'] != 'Outros' ]
    return df


def explode_lista_termos_lista_empresas(empresa, df_empresas, coluna):
    '''
     Explode as colunas que tem valores separador por , numa lista
    '''
    
    lista = []
    
    if len(df_empresas[df_empresas['empresa'] == empresa][coluna]) > 0 and  (not pd.isnull(df_empresas[df_empresas['empresa'] == empresa][coluna].iloc[0]) ):
        lista = df_empresas[df_empresas['empresa'] == empresa][coluna].iloc[0].split(',')
    
    
    return lista

    

def conta_mencoes_empresas(noticias, empresa, listagem_empresas):
    '''
     Conta a quatidade de empresas citadas em cada noticia (empresa selecionada x demais)
     importante para nao considerar noticias que falam de muitas empresas
    '''

    df2 = noticias
    df = noticias
    
    emp_ajustada = remove_acentos(remove_nome_composto(empresa.lower()))
    empresas_ajust = list(listagem_empresas['Nome'])
    empresas_ajust = remove_termos_comuns(list(set([remove_acentos(remove_nome_composto(i).lower()) for i in empresas_ajust])))

    df2['texto_completo_orig'] = df2['texto_completo']
    
    # trata empresas com espaços no nome
    if ' ' in emp_ajustada:
        df2['texto_completo'] = df2['texto_completo'].apply(lambda x : re.sub(emp_ajustada,emp_ajustada.replace(' ', '_') , x, flags=re.IGNORECASE))   
        emp_ajustada = emp_ajustada.replace(' ', '_') 
        
    # trata empresas com & no nome
    if '&' in emp_ajustada:
        df2['texto_completo'] = df2['texto_completo'].apply(lambda x : re.sub(emp_ajustada,emp_ajustada.replace('&', 'e') , x, flags=re.IGNORECASE))   
        emp_ajustada = emp_ajustada.replace('&', 'e') 
    
    if emp_ajustada not in empresas_ajust:
        empresas_ajust.append(emp_ajustada)
        
    # trata empresas com apelidos

    for apelido in explode_lista_termos_lista_empresas(empresa, listagem_empresas, 'apelidos'):
        df2['texto_completo'] = df2['texto_completo'].apply(lambda x : re.sub(r"\b" + apelido +  r"\b", emp_ajustada , x, flags=re.IGNORECASE))

    wordlist = list(map(str.lower, empresas_ajust))
    wordlist = list(set(wordlist))
    
    
    counters = df2['texto_completo'].apply(lambda t : Counter(re.findall(r'\b[a-z0-9_]+\b', remove_palavras_texto(remove_acentos(t.lower()), list(noticias.columns)))))
    
    df2 = pd.concat([df2, counters.apply(pd.Series).fillna(0).astype(int)], axis=1)
    
    # remove palavras que nao sao empresas
    other_words = list(set(df2.columns) - set(wordlist) - set(noticias.columns))
    df2 = df2.drop(other_words, axis=1)

    demais_empresas = list( set(wordlist).intersection(df2.columns))
    
    if emp_ajustada in demais_empresas:
        demais_empresas.remove(emp_ajustada)

    df2['demais_citacoes'] = df2[demais_empresas].sum(axis=1)

    df2 = df2.drop(demais_empresas, axis=1)

    if 'citacoes_empresa' in df2.columns and emp_ajustada in df2.columns:
        df2['citacoes_empresa'] = df2[emp_ajustada]
        del df2[emp_ajustada]
    else:
        df2.rename(columns = {emp_ajustada:'citacoes_empresa'}, inplace = True)
    
    del df2['texto_completo']
    
    df2.rename(columns = {'texto_completo_orig':'texto_completo'}, inplace = True)
    
    return df2




def filtra_citacao_relevante(noticias, empresa, listagem_empresas, threshold=1.0, aceitar_titulo=True, recalcular_contagem=True):
    '''
    Verifica se a citação a empresa é relevante (> soma das demais ou aparecer no titulo)
    '''
    df2 = noticias
    if recalcular_contagem:    
        df2 = conta_mencoes_empresas(noticias, empresa, listagem_empresas)
        
    if aceitar_titulo:
        df2['relevante'] = df2.apply(lambda row : 
                                     1 if ( (row['citacoes_empresa'] > threshold*row['demais_citacoes'])  or (remove_acentos(empresa).lower() in remove_acentos(row['titulo'].lower()))   )
                                     else 0, axis=1)
    else:
        df2['relevante'] = df2.apply(lambda row : 
                                     1 if ( row['citacoes_empresa'] > threshold*row['demais_citacoes']   )
                                     else 0, axis=1)
    
    
    return df2[ df2['relevante'] == 1 ]


def trata_nome_fontes(fonte):
    fonte  = fonte.lower()
    fonte = fonte.replace('istoé dinheiro', 'istoé')
    fonte = fonte.replace('época negócios', 'época')
    fonte = fonte.replace(' dinheiro', '').replace(' online', '').replace(' notícias', '').replace(' brasil', '')
    
    return fonte.strip().capitalize()

    

def filtrar_noticias_pos_coleta_modelo_simplificado(dfNoticias, df_empresas, filtrar_termos_especificos=False):
    '''
    Filtros pos processamento (exclusoes) 
    O filtro serve para classificar fontes incorretas, empresas que tem termos comuns no seu nome
    e tambem noticias nao relacionadas aos temas E S ou G
    '''

    dfFiltrado = dfNoticias

    # filtra noticias nao relacionadas a ESG
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Partido Comunista Brasileiro'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'JDV - Jornal do Vale do Itapocu'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'TJDFT'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Hotelier News'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Rede Brasil Atual'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'MPF'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'braskem.com.br'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'braskem'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'taurus'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'PT'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Engeplus'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Gerdau'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Boatos.org'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'Revista Hotéis'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'PANROTAS'.lower()] 
    dfFiltrado = dfFiltrado[dfFiltrado['fonte'].str.lower() != 'bomdia.eu'] 
    
    
    if filtrar_termos_especificos:
        # termos a excluir
        termos_excluir = []#'nesta entrevista exclusiva', 'as ações que são apostas', 'morre o empresário', 
                         # 'morre o ex-', 'morre aos', 'você pode assistir aqui', 'black friday', 
                         #'loja em metaverso', 'loja no metaverso', 'inaugura loja em', 'rock in rio',
                         #'confira as vagas de emprego', 'frases de luiz barsi', 
                         #'e mais empresas com vagas abertas', 'confira mais vagas em', 'veja mais vagas abertas em', 
                         #'quarta-feira de cinzas', 'carnaval', 'o que abre e o que fecha']
        for t in termos_excluir:
            dfFiltrado = dfFiltrado[~dfFiltrado['texto_completo'].str.lower().str.contains(t)]

        for t in termos_excluir:
            dfFiltrado = dfFiltrado[~dfFiltrado['titulo'].str.lower().str.contains(t)]
    
   

    # trata empresas que estao associadas a termos genericos sem relacao com ela
    dfPadroesExcluir = df_empresas[ ~ pd.isnull(df_empresas['termos_excluir_pesquisa']) ]
    dfFiltrado['excluir_texto'] = False
    dfFiltrado['excluir_titulo'] = False

    padrao = ''
    for emp in dfPadroesExcluir['empresa'].unique():
        lista_termos = explode_lista_termos_lista_empresas(emp, dfPadroesExcluir, 'termos_excluir_pesquisa')
        lista_termos = [remove_acentos(t).lower() for t in lista_termos]
        padrao = '|'.join(  lista_termos  ) 
        
        # filtra termos que sao associados incorretamente com uma empresa e sao falsos relevantes no texto
        dfFiltrado['excluir_texto'] =  ((dfFiltrado['excluir_texto']) | ((dfFiltrado['empresa'] == emp) & (dfFiltrado['texto_completo'].apply(remove_acentos).str.lower().str.contains(padrao, regex=True))))

        # filtra termos que sao associados incorretamente com uma empresa e sao falsos relevantes no titulo
        dfFiltrado['excluir_titulo'] =  ((dfFiltrado['excluir_titulo']) | ((dfFiltrado['empresa'] == emp) & (dfFiltrado['titulo'].apply(remove_acentos).str.lower().str.contains(padrao, regex=True))))
        
    
    dfFiltrado = dfFiltrado[~ dfFiltrado['excluir_texto'] ] 
    del dfFiltrado['excluir_texto']
    
    dfFiltrado = dfFiltrado[~ dfFiltrado['excluir_titulo'] ] 
    del dfFiltrado['excluir_titulo']

    # trata empresas que estao associadas a termos genericos, e que precisam de lista de palavras pra detecta-las
    # exemplo azul linhas aereas, ao buscar apenas por azul retorna-se muitas noticias nao relacionadas

    dfPadroesExcluir = df_empresas[ ~ pd.isnull(df_empresas['termos_obrigatorios_pesquisa']) ]
    
    dfFiltrado['excluir_texto'] = False

    padrao = ''
    for emp in dfPadroesExcluir['empresa'].unique():
        lista_termos = explode_lista_termos_lista_empresas(emp, dfPadroesExcluir, 'termos_obrigatorios_pesquisa')
        lista_termos = [remove_acentos(t).lower() for t in lista_termos]
        padrao = "|".join(  [r'\b' + x + r'\b' for x in lista_termos] )

            
        dfFiltrado['excluir_texto'] =  ((dfFiltrado['excluir_texto']) | ((dfFiltrado['empresa'] == emp) & (~dfFiltrado['texto_completo'].apply(remove_acentos).str.lower().str.contains(padrao, regex=True))))
    
    dfFiltrado = dfFiltrado[~ dfFiltrado['excluir_texto'] ] 
    del dfFiltrado['excluir_texto']
    
    dfFiltrado = dfFiltrado.reset_index(drop=True).drop_duplicates().reset_index(drop=True)
    
    
    return dfFiltrado



def criar_hash_noticia(texto, empresa, titulo='', data=None, pergunta=''):
    '''Criar um identificador unico para o texto da noticia'''
    
    if pergunta != '':
        texto_codificar = texto.strip() + empresa.strip() + pergunta.strip()
        
    else:
        texto_codificar = data.strftime("%Y%m%d") + remove_acentos(empresa).upper().strip()[:8] + remove_acentos(titulo).upper().strip()[:15]
        
        
    hash_texto = hashlib.sha256(texto_codificar.encode('UTF-8')).hexdigest()
        
    return hash_texto


def ajusta_nomes_empresas_dataframe(df):
    '''ajusta nome das empresas na base coletada'''
    df['empresa'] = df['empresa'].str.replace(' s.a.', '')
    return df

