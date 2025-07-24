import requests
import math

def obter_coordenadas(local):
    """Obtém as coordenadas e nome oficial de um local usando a API Nominatim"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={local}"
        headers = {'User-Agent': 'CalculadorDistancia/1.0'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        dados = response.json()
        
        if dados:
            resultado = dados[0]
            nome = resultado.get('display_name', local).split(',')[0]
            return float(resultado['lat']), float(resultado['lon']), nome
        return None, None, local
    
    except Exception as e:
        print(f"Erro ao buscar {local}: {e}")
        return None, None, local

def distancia_circulo_maximo(lat1, lon1, lat2, lon2):
    """
    Calcula a distância pelo círculo máximo usando a fórmula de Haversine
    Ref: https://en.wikipedia.org/wiki/Great-circle_distance
    """
    # Raio médio da Terra em km
    R = 6371.0
    
    # Converter graus para radianos
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)
    
    # Fórmula do círculo máximo
    Δσ = math.acos(
        math.sin(φ1) * math.sin(φ2) + 
        math.cos(φ1) * math.cos(φ2) * math.cos(Δλ)
    )
    
    return R * Δσ

def main():
    print("\n" + "="*50)
    print("  CALCULADORA DE DISTÂNCIA - CÍRCULO MÁXIMO")
    print("="*50 + "\n")
    
    cidade1 = input("Digite a origem (cidade/endereço): ").strip()
    cidade2 = input("Digite o destino (cidade/endereço): ").strip()
    
    if not cidade1 or not cidade2:
        print("\nErro: Você deve informar ambas as localidades")
        return
    
    lat1, lon1, nome1 = obter_coordenadas(cidade1)
    lat2, lon2, nome2 = obter_coordenadas(cidade2)
    
    if None in [lat1, lon1, lat2, lon2]:
        print("\nNão foi possível obter coordenadas para uma ou ambas localidades")
        return
    
    distancia = distancia_circulo_maximo(lat1, lon1, lat2, lon2)
    
    # Resultado formatado
    print("\n" + "═"*50)
    print(f"📍 ORIGEM:    {nome1}")
    print(f"   Coordenadas: {lat1:.6f}°N, {lon1:.6f}°E")
    print(f"\n🏁 DESTINO:   {nome2}")
    print(f"   Coordenadas: {lat2:.6f}°N, {lon2:.6f}°E")
    print("\n" + "─"*50)
    print(f"📏 DISTÂNCIA PELO CÍRCULO MÁXIMO: {distancia:.2f} km")
    print("═"*50)
    
    # Links para mapas
    print("\n🔗 Links para visualização:")
    print(f"• Mapa com rota: https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}")
    print(f"• Origem: https://www.google.com/maps?q={lat1},{lon1}")
    print(f"• Destino: https://www.google.com/maps?q={lat2},{lon2}")

if __name__ == "__main__":
    main()