import requests
import math

class Distancia:
    def __init__(self, user_agent='CalculadorDistancia/1.0'):
        self.user_agent = user_agent
    
    def _obter_coordenadas(self, local):
        """Método privado para obter coordenadas de um local"""
        try:
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={local}"
            headers = {'User-Agent': self.user_agent}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            dados = response.json()
            
            if dados:
                resultado = dados[0]
                return {
                    'latitude': float(resultado['lat']),
                    'longitude': float(resultado['lon']),
                    'nome': resultado.get('display_name', local).split(',')[0]
                }
            return None
            
        except Exception as e:
            print(f"Erro ao buscar {local}: {e}")
            return None

    def _calcular_distancia_haversine(self, coord1, coord2):
        """Método privado para cálculo usando fórmula de Haversine"""
        # Raio médio da Terra em km
        R = 6371.0
        
        # Converter graus para radianos
        φ1 = math.radians(coord1['latitude'])
        φ2 = math.radians(coord2['latitude'])
        Δλ = math.radians(coord2['longitude'] - coord1['longitude'])
        
        # Fórmula de Haversine
        Δσ = math.acos(
            math.sin(φ1) * math.sin(φ2) + 
            math.cos(φ1) * math.cos(φ2) * math.cos(Δλ)
        )
        
        return R * Δσ

    def calcular(self, origem, destino):
        """
        Calcula a distância entre dois locais
        
        Args:
            origem (str): Local de origem
            destino (str): Local de destino
            
        Returns:
            dict: Dicionário com resultados ou None em caso de erro
        """
        if not origem or not destino:
            return None
            
        coord_origem = self._obter_coordenadas(origem)
        coord_destino = self._obter_coordenadas(destino)
        
        if not coord_origem or not coord_destino:
            return None
        
        distancia = self._calcular_distancia_haversine(coord_origem, coord_destino)
        
        return {
            'origem': coord_origem,
            'destino': coord_destino,
            'distancia_km': distancia,
            'mapa_url': self.gerar_url_mapa(coord_origem, coord_destino)
        }
    
    def gerar_url_mapa(self, coord_origem, coord_destino):
        """Gera URL do Google Maps com a rota"""
        return (f"https://www.google.com/maps/dir/"
                f"{coord_origem['latitude']},{coord_origem['longitude']}/"
                f"{coord_destino['latitude']},{coord_destino['longitude']}")

    def mostrar_resultados(self, resultado):
        """Exibe os resultados formatados"""
        if not resultado:
            print("Não foi possível calcular a distância.")
            return
        
        print("\n" + "═"*50)
        print(f"📍 ORIGEM:    {resultado['origem']['nome']}")
        print(f"   Coordenadas: {resultado['origem']['latitude']:.6f}°N, "
              f"{resultado['origem']['longitude']:.6f}°E")
        print(f"\n🏁 DESTINO:   {resultado['destino']['nome']}")
        print(f"   Coordenadas: {resultado['destino']['latitude']:.6f}°N, "
              f"{resultado['destino']['longitude']:.6f}°E")
        print("\n" + "─"*50)
        print(f"📏 DISTÂNCIA: {resultado['distancia_km']:.2f} km")
        print("═"*50)
        print(f"\n🔗 Mapa: {resultado['mapa_url']}")


if __name__ == "__main__":
    # Exemplo de uso direto
    print("\n" + "="*50)
    print("  CALCULADORA DE DISTÂNCIA - CLASSE")
    print("="*50 + "\n")
    
    calculadora = Distancia()
    origem = input("Digite a origem (cidade/endereço): ").strip()
    destino = input("Digite o destino (cidade/endereço): ").strip()
    
    resultado = calculadora.calcular(origem, destino)
    calculadora.mostrar_resultados(resultado)