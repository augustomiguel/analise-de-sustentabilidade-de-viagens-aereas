# testar_lattes.py
import os
from lattes.extrator import ExtratorLattes

# 1. Vamos criar um XML falso simulando a estrutura do CNPq
xml_mock = """<?xml version="1.0" encoding="UTF-8"?>
<CURRICULO-VITAE>
    <DADOS-GERAIS NOME-COMPLETO="Diego">
        <ATUACOES-PROFISSIONAIS>
            <ATUACAO-PROFISSIONAL NOME-INSTITUICAO="Universidade Federal da Paraíba"/>
        </ATUACOES-PROFISSIONAIS>
    </DADOS-GERAIS>
    <PRODUCAO-BIBLIOGRAFICA>
        <ARTIGOS-PUBLICADOS>
            <ARTIGO-PUBLICADO TITULO-DO-ARTIGO="Revisão Sistemática sobre Sustentabilidade e Descarbonização" ANO-DO-ARTIGO="2024"/>
            <ARTIGO-PUBLICADO TITULO-DO-ARTIGO="Análise de Viagens em IES" ANO-DO-ARTIGO="2025"/>
        </ARTIGOS-PUBLICADOS>
    </PRODUCAO-BIBLIOGRAFICA>
    <DADOS-COMPLEMENTARES>
        <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
            <PARTICIPACAO-EM-CONGRESSO NOME-DO-EVENTO="Congresso Nacional de Gestão Ambiental" ANO="2025"/>
        </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
    </DADOS-COMPLEMENTARES>
</CURRICULO-VITAE>
"""

# 2. Salva esse XML na pasta que o extrator vai ler
pasta_destino = 'dadosLattes'
os.makedirs(pasta_destino, exist_ok=True)

caminho_mock = os.path.join(pasta_destino, 'curriculo_teste.xml')
with open(caminho_mock, 'w', encoding='utf-8') as f:
    f.write(xml_mock)

print(f"Simulação: Arquivo '{caminho_mock}' criado com sucesso!\n")

# 3. Roda o nosso novo extrator
extrator = ExtratorLattes(pasta_xmls=pasta_destino)
df_resultado = extrator.processar_todos()

# 4. Mostra o resultado na tela
print("\n--- VISUALIZAÇÃO DA PLANILHA GERADA ---")
print(df_resultado.to_string())