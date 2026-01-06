import csv
import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "https://farmaciaslider.pe/category/G5U78F1D42T6BQJ"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def obtener_html(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error al acceder a {url}. Código: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error al obtener {url}: {e}")
        return None

def extraer_detalles_producto(url_producto):
    """Entra al link del producto para obtener descripción y especificaciones"""
    if not url_producto:
        return "N/A", "N/A"
    
    html = obtener_html(url_producto)
    if not html:
        return "Error al cargar", "Error al cargar"
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Buscar Descripción dentro de id="description"
    desc_div = soup.find('div', id='description')
    descripcion = desc_div.get_text(strip=True) if desc_div else "Sin descripción"
    
    # 2. Buscar Especificaciones dentro de id="specification"
    # Según tu imagen, los detalles están en un div clase 'specs-details' dentro de 'specification'
    spec_div = soup.find('div', id='specification')
    especificaciones = spec_div.get_text(strip=True) if spec_div else "Sin especificaciones"
    
    return descripcion, especificaciones

def extraer_productos(html):
    soup = BeautifulSoup(html, 'html.parser')
    productos = []
    # Usamos select para buscar los contenedores de productos
    items = soup.select('div#productocatalogo') 

    for item in items:
        nombre_tag = item.select_one('h3.product-name a')
        nombre = nombre_tag.get_text(strip=True) if nombre_tag else "Nombre no encontrado"

        precio_tag = item.select_one('div.preciocatalogo')
        precio = precio_tag.get_text(strip=True) if precio_tag else "Precio no encontrado"

        link_tag = item.select_one('a.product-img')
        link = link_tag['href'] if link_tag else ""
        if link and link.startswith('/'):
            link = "https://farmaciaslider.pe" + link

        # --- NUEVA LÓGICA: Entrar al producto ---
        print(f"   -> Obteniendo detalles de: {nombre[:30]}...")
        desc, specs = extraer_detalles_producto(link)
        # ----------------------------------------

        productos.append({
            "nombre": nombre,
            "precio": precio,
            "descripcion": desc,
            "especificaciones": specs,
            "link": link
        })
        # Pequeña pausa entre productos para no saturar el servidor
        time.sleep(0.5)
        
    return productos

def main():
    try:
        num_urls = int(input("¿Cuántas páginas deseas scrapear? (ej. 1): ").strip())
    except ValueError:
        print("Entrada no válida.")
        return

    all_products = []

    for i in range(num_urls):
        url = BASE_URL if i == 0 else f"{BASE_URL}/{i * 20}"
        print(f"\n🔍 Procesando página {i + 1}: {url}")
        
        html = obtener_html(url)
        if html:
            productos = extraer_productos(html)
            all_products.extend(productos)

    if all_products:
        filename = "productos_detallados.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            # Añadimos las nuevas columnas al CSV
            campos = ["nombre", "precio", "descripcion", "especificaciones", "link"]
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(all_products)
        print(f"\n✅ Proceso terminado. Total: {len(all_products)} productos en '{filename}'")

if __name__ == "__main__":
    main()