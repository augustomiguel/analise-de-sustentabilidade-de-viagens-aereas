import requests

def obter_coordenadas(endereco):
    """
    Função para obter latitude e longitude de um endereço utilizando a API do Nominatim (OpenStreetMap)
    """
    try:
        # URL da API Nominatim
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={endereco}"
        
        # Headers para identificar o aplicativo (obrigatório pela política de uso)
        headers = {
            'User-Agent': 'MeuAplicativoDeGeolocalizacao/1.0 (seu@email.com)'
        }
        
        # Fazendo a requisição
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Verifica se houve erro na requisição
        
        dados = response.json()
        
        if dados:
            # Pegando o primeiro resultado
            primeiro_resultado = dados[0]
            lat = primeiro_resultado['lat']
            lon = primeiro_resultado['lon']
            return float(lat), float(lon)
        else:
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API: {e}")
        return None
    except (KeyError, IndexError):
        print("Local não encontrado ou dados incompletos.")
        return None

def main():
    print("Obter coordenadas geográficas de um local")
    print("----------------------------------------")
    
    endereco = input("Digite o endereço (ex: 'Avenida Paulista, 1000, São Paulo'): ")
    
    if not endereco.strip():
        print("Por favor, digite um endereço válido.")
        return
    
    coordenadas = obter_coordenadas(endereco)
    
    if coordenadas:
        latitude, longitude = coordenadas
        print(f"\nCoordenadas encontradas:")
        print(f"Latitude: {latitude}")
        print(f"Longitude: {longitude}")
        
        # Link para o Google Maps
        print(f"\nLink para o Google Maps: https://www.google.com/maps?q={latitude},{longitude}")
    else:
        print("Não foi possível obter as coordenadas para o endereço informado.")

if __name__ == "__main__":
    main()