import csv
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_URL = "https://farmaciaslider.pe/category/G5U78F1D42T6BQJ"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# --- UTILIDADES ---
def limpiar_texto(texto):
    if not texto: return "Sin datos"
    texto = texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return " ".join(texto.split())

def safe_encode(texto):
    if not texto: return ""
    replacements = {
        'ü': 'u', 'Ü': 'U', 'ñ': 'n', 'Ñ': 'N',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U'
    }
    for char, rep in replacements.items():
        texto = texto.replace(char, rep)
    return texto.encode('latin-1', 'replace').decode('latin-1')

# --- SCRAPING ---
def obtener_html(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        return response.text if response.status_code == 200 else None
    except: return None

def extraer_detalles_producto(url_producto):
    if not url_producto or url_producto == "Sin datos": return "Sin descripción"
    html = obtener_html(url_producto)
    if not html: return "Error al acceder al detalle"
    
    soup = BeautifulSoup(html, 'html.parser')
    # Selector específico para la descripción en la ficha del producto
    desc_div = soup.find('div', id='description')
    if not desc_div:
        desc_div = soup.select_one('.product-description') # Selector alternativo
        
    descripcion = desc_div.get_text(separator=' ', strip=True) if desc_div else "Descripción no disponible"
    return limpiar_texto(descripcion)

def extraer_productos(html):
    soup = BeautifulSoup(html, 'html.parser')
    productos = []
    items = soup.select('div#productocatalogo') 

    for item in items:
        try:
            nombre_tag = item.select_one('h3.product-name a')
            nombre = limpiar_texto(nombre_tag.get_text(strip=True)) if nombre_tag else "N/A"
            
            precio_tag = item.select_one('div.preciocatalogo')
            precio = limpiar_texto(precio_tag.get_text(strip=True)) if precio_tag else "0.00"
            
            link_tag = item.select_one('a.product-img') or item.select_one('h3.product-name a')
            link = ""
            if link_tag and link_tag.has_attr('href'):
                link = link_tag['href']
                if link.startswith('/'):
                    link = "https://farmaciaslider.pe" + link
            
            print(f" -> Extrayendo: {nombre[:30]}...")
            # Llamada para obtener la descripción real entrando al link
            desc_completa = extraer_detalles_producto(link)
            
            productos.append({
                "nombre": nombre,
                "precio": precio,
                "descripcion": desc_completa,
                "link": link
            })
            time.sleep(0.3)
        except Exception as e:
            print(f"Error en producto: {e}")
            continue
    return productos

# --- GENERACIÓN DE PDF ---
def generar_pdf(productos, fecha_hoy, filename="reporte_farmacia.pdf"):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORTE DE PRODUCTOS - FARMACIAS LIDER", ln=True, align='C')
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Fecha de extraccion: {fecha_hoy}", ln=True, align='C')
    pdf.ln(10)

    for p in productos:
        if pdf.get_y() > 240: pdf.add_page()
        
        pdf.set_x(15)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, safe_encode(f"PRODUCTO: {p['nombre']}"), border=0, align='L', fill=True)
        
        pdf.set_x(15)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(200, 0, 0) 
        pdf.cell(0, 8, safe_encode(f"PRECIO: {p['precio']}"), ln=True, align='L')
        
        pdf.set_x(15)
        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, safe_encode(f"Descripcion: {p['descripcion']}"), align='L')
        
        pdf.set_x(15)
        pdf.set_text_color(0, 0, 255)
        pdf.set_font("Arial", "U", 8)
        pdf.cell(0, 6, "Ver producto en la web >", ln=True, link=p['link'], align='L')
        pdf.ln(6)

    pdf.output(filename)
    print(f"✅ PDF generado correctamente.")

# --- FLUJO PRINCIPAL ---
def main():
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    try:
        num = int(input("¿Cuantas paginas deseas scrapear?: "))
        all_prods = []
        for i in range(num):
            url = BASE_URL if i == 0 else f"{BASE_URL}/{i*20}"
            html = obtener_html(url)
            if html:
                all_prods.extend(extraer_productos(html))
        
        if all_prods:
            # 1. Guardar en Excel con Fecha ARRIBA una sola vez
            csv_fn = "productos_farmacia.csv"
            with open(csv_fn, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=';')
                # Fila de fecha única al inicio
                writer.writerow(["FECHA DE EXTRACCION", fecha_hoy])
                writer.writerow([]) # Fila en blanco para separar
                # Cabezales normales
                writer.writerow(["nombre", "precio", "descripcion", "link"])
                # Datos de productos
                for p in all_prods:
                    writer.writerow([p['nombre'], p['precio'], p['descripcion'], p['link']])
            
            print(f"\n✅ Excel guardado (Fecha solo en la primera fila).")
            generar_pdf(all_prods, fecha_hoy)
            
    except Exception as e: print(f"Error general: {e}")

if __name__ == "__main__":
    main()
