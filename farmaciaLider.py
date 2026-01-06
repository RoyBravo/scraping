import csv
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF  # IMPORTANTE: Librería para el PDF

BASE_URL = "https://farmaciaslider.pe/category/G5U78F1D42T6BQJ"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def limpiar_texto(texto):
    """Limpia saltos de línea y espacios extra."""
    if not texto:
        return "N/A"
    texto = texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return " ".join(texto.split())

def safe_encode(texto):
    """
    Convierte el texto a latin-1 para que FPDF no falle con tildes.
    Si hay un caracter muy raro (emoji, etc), lo reemplaza con '?'.
    """
    if not texto: return ""
    return texto.encode('latin-1', 'replace').decode('latin-1')

def obtener_html(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error conexión: {e}")
        return None

def extraer_detalles_producto(url_producto):
    if not url_producto: return "N/A", "N/A"
    html = obtener_html(url_producto)
    if not html: return "Error", "Error"
    
    soup = BeautifulSoup(html, 'html.parser')
    desc_div = soup.find('div', id='description')
    descripcion = desc_div.get_text(separator=' ', strip=True) if desc_div else "Sin descripción"
    
    spec_div = soup.find('div', id='specification')
    especificaciones = spec_div.get_text(separator=' ', strip=True) if spec_div else "Sin especificaciones"
    
    return limpiar_texto(descripcion), limpiar_texto(especificaciones)

def extraer_productos(html):
    soup = BeautifulSoup(html, 'html.parser')
    productos = []
    items = soup.select('div#productocatalogo') 

    for item in items:
        nombre_tag = item.select_one('h3.product-name a')
        nombre = limpiar_texto(nombre_tag.get_text(strip=True)) if nombre_tag else "Nombre no encontrado"

        precio_tag = item.select_one('div.preciocatalogo')
        precio = limpiar_texto(precio_tag.get_text(strip=True)) if precio_tag else "0.00"

        link_tag = item.select_one('a.product-img')
        link = link_tag['href'] if link_tag else ""
        if link and link.startswith('/'):
            link = "https://farmaciaslider.pe" + link

        print(f"   -> Extrayendo: {nombre[:30]}...")
        desc, specs = extraer_detalles_producto(link)

        productos.append({
            "nombre": nombre,
            "precio": precio,
            "descripcion": desc,
            "especificaciones": specs,
            "link": link
        })
        time.sleep(0.5)
    return productos

# --- FUNCIÓN NUEVA: GENERAR PDF ---
def generar_pdf(productos, filename="reporte_productos.pdf"):
    print(f"\n📄 Generando PDF: {filename}...")
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Título del documento
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Reporte de Farmacia Slider", ln=True, align='C')
    pdf.ln(10) # Espacio

    for p in productos:
        # 1. Nombre del Producto (Negrita, tamaño 12)
        pdf.set_font("Arial", "B", 12)
        # MultiCell permite que el texto baje de línea si es muy largo
        pdf.multi_cell(0, 6, safe_encode(f"Producto: {p['nombre']}"))
        
        # 2. Precio (Rojo oscuro para resaltar)
        pdf.set_text_color(200, 0, 0) 
        pdf.cell(0, 8, safe_encode(f"Precio: {p['precio']}"), ln=True)
        pdf.set_text_color(0, 0, 0) # Volver a negro
        
        # 3. Descripción (Texto normal, tamaño 10)
        pdf.set_font("Arial", "", 10)
        desc_corta = p['descripcion'][:600] + "..." if len(p['descripcion']) > 600 else p['descripcion']
        pdf.multi_cell(0, 5, safe_encode(f"Descripción: {desc_corta}"))
        
        # 4. Link (Azul y subrayado)
        pdf.set_text_color(0, 0, 255)
        pdf.set_font("Arial", "U", 9)
        pdf.cell(0, 6, "Ver Producto", ln=True, link=p['link'])
        
        # Línea separadora y volver a negro
        pdf.set_text_color(0, 0, 0)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    pdf.output(filename)
    print("✅ PDF Generado correctamente.")

def main():
    try:
        entrada = input("¿Cuántas páginas deseas scrapear? (ej. 1): ").strip()
        num_urls = int(entrada)
    except ValueError:
        print("Entrada inválida.")
        return

    all_products = []

    for i in range(num_urls):
        url = BASE_URL if i == 0 else f"{BASE_URL}/{i * 20}"
        print(f"\n🔍 Página {i + 1}: {url}")
        html = obtener_html(url)
        if html:
            all_products.extend(extraer_productos(html))

    if all_products:
        # 1. Guardar CSV (Formato Excel columnas separadas)
        csv_filename = "productos_farmacia.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
            campos = ["nombre", "precio", "descripcion", "especificaciones", "link"]
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(all_products)
        print(f"\n✅ CSV guardado: {csv_filename}")

        # 2. Guardar PDF
        generar_pdf(all_products, "reporte_farmacia.pdf")

if __name__ == "__main__":
    main()
