#  "[{"key":"chave-api-dados","value":"9b8e00db8253945fc8e90aa1cd4423be"}]

import requests

def listar_orgaos(pagina=1):
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/orgaos-siape?pagina=1"
    params = {"pagina": pagina}
    headers = {'chave-api-dados': "9b8e00db8253945fc8e90aa1cd4423be"}
    
    try:
        response = requests.get(url,verify=True, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"Erro: {err}")
        return None

# Uso:
orgaos_pagina_1 = listar_orgaos(pagina=1)
if orgaos_pagina_1:
    for i in orgaos_pagina_1:
        print(i['descricao'], i['codigo'])
    #print(orgaos_pagina_1)