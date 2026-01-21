import csv
import time
from datetime import datetime # Nueva importación para la fecha
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fpdf import FPDF
from fpdf.enums import XPos, YPos

def configurar_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def safe_encode(texto):
    if not texto or texto.strip() == "": return "N/A"
    return texto.encode('latin-1', 'replace').decode('latin-1')

def cerrar_anuncios(driver):
    try:
        selectores_cerrar = [
            "button[class*='closeButton']", "div[class*='close']",
            "span[class*='close']", "button[aria-label='Close']"
        ]
        for selector in selectores_cerrar:
            botones = driver.find_elements(By.CSS_SELECTOR, selector)
            for boton in botones:
                if boton.is_displayed():
                    boton.click()
                    time.sleep(1)
    except:
        pass

def scroll_suave(driver, pixeles):
    paso = 200
    actual = 0
    while actual < pixeles:
        driver.execute_script(f"window.scrollBy(0, {paso});")
        actual += paso
        time.sleep(0.3)

def extraer_rango_paginas(inicio, fin):
    driver = configurar_driver()
    driver.maximize_window()
    todos_los_datos = []
    enlaces_procesados = set()

    try:
        for pagina in range(inicio, fin + 1):
            url = f"https://farmaciaisis.com.pe/products?page={pagina}"
            driver.get(url)
            time.sleep(4)
            cerrar_anuncios(driver)
            scroll_suave(driver, 1500)

            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[class*='productCard']")))
            articulos = driver.find_elements(By.CSS_SELECTOR, "article[class*='productCard']")

            temp_list = []
            for art in articulos:
                try:
                    nombre = art.find_element(By.TAG_NAME, "span").text.strip()
                    if not nombre or "stock" in nombre.lower():
                        nombre = art.find_element(By.TAG_NAME, "img").get_attribute("alt")

                    precio = art.find_element(By.TAG_NAME, "p").text.strip()
                    link = art.find_element(By.TAG_NAME, "a").get_attribute("href")
                    html = art.get_attribute("innerHTML").lower()
                    dispo = "sin stock" if ("agotado" in html or "sin stock" in html) else "con stock"

                    if link not in enlaces_procesados:
                        temp_list.append({"nombre": nombre, "dispo": dispo, "precio": precio, "link": link})
                        enlaces_procesados.add(link)
                except:
                    continue

            for item in temp_list:
                driver.get(item['link'])
                time.sleep(3)
                cerrar_anuncios(driver)
                scroll_suave(driver, 800)
                descripcion = "Descripción no disponible."

                try:
                    secciones = driver.find_elements(By.CSS_SELECTOR, "section[class*='wrapper']")
                    for seccion in secciones:
                        try:
                            titulo = seccion.find_element(By.TAG_NAME, "h3").text.strip().lower()
                            if "descripción" in titulo or "descripcion" in titulo:
                                div_contenido = seccion.find_element(By.CSS_SELECTOR, "div[class*='contentWrap']")
                                texto_extraido = driver.execute_script("return arguments[0].innerText;", div_contenido)
                                if texto_extraido and len(texto_extraido.strip()) > 10:
                                    descripcion = texto_extraido.strip()
                                    break
                        except:
                            continue
                except:
                    pass

                todos_los_datos.append({
                    "nombre": item['nombre'],
                    "disponibilidad": item['dispo'],
                    "precio": item['precio'],
                    "descripcion": descripcion
                })
                estado_log = "[OK]" if descripcion != "Descripción no disponible." else "[VACÍO]"
                print(f"    ✔ {item['nombre'][:30]}... {estado_log}")

    finally:
        driver.quit()
    return todos_los_datos

def guardar_reportes(lista, nombre_archivo):
    if not lista: return

    # Obtener fecha y hora actual formateada
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Guardado en CSV con fecha al inicio
    with open(f"{nombre_archivo}.csv", "w", newline="", encoding="utf-8-sig") as f:
        # Escribimos la fecha como un comentario o primera línea
        f.write(f"Fecha de registro: {fecha_actual}\n")
        writer = csv.DictWriter(f, fieldnames=["nombre", "disponibilidad", "precio", "descripcion"], delimiter=';')
        writer.writeheader()
        writer.writerows(lista)

    # Generación de PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Título Principal
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Reporte Inventario Farmacia Isis", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Fecha del registro
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 8, f"Fecha de registro: {fecha_actual}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    for p in lista:
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(0, 6, safe_encode(f"PRODUCTO: {p['nombre']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", "I", 9)
        info = f"ESTADO: {p['disponibilidad'].upper()} | PRECIO: {p['precio']}"
        pdf.multi_cell(190, 6, safe_encode(info), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", "", 9)
        pdf.multi_cell(190, 5, safe_encode(f"DESCRIPCIÓN: {p['descripcion']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    pdf.output(f"{nombre_archivo}.pdf")
    print(f"\n✨ Proceso terminado. Archivos creados el {fecha_actual}.")

if __name__ == "__main__":
    try:
        p_i = int(input("Página de inicio (número): "))
        p_f = int(input("Página de fin (número): "))
        nombre_file = input("Nombre de archivo (ej: mi_inventario): ")

        res = extraer_rango_paginas(p_i, p_f)

        if res:
            guardar_reportes(res, nombre_file)
        else:
            print("❌ No se obtuvieron datos para procesar.")
    except ValueError:
        print("❌ Error: Por favor ingresa solo números para las páginas.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
