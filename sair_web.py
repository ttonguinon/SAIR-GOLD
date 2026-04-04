# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import os
import re
import textwrap
import pandas as pd
from datetime import datetime
from deep_translator import GoogleTranslator
from fpdf import FPDF

# --- 0. CONEXIÓN DIRECTA (ARCHIVO OPTIMIZADO 10.5 MB) ---
@st.cache_resource
def conectar_db():
    db_path = "sair_data.db"
    if not os.path.exists(db_path):
        st.error("❌ Archivo de Base de Datos no encontrado en el repositorio.")
    return sqlite3.connect(db_path, check_same_thread=False)

# --- 1. MOTOR NORMATIVO (REGLA DE ORO: SIN ALTERACIONES) ---
traductor_en = GoogleTranslator(source='es', target='en')
traductor_es = GoogleTranslator(source='en', target='es')

def normalizar_texto(texto):
    if not texto: return ""
    texto = texto.upper()
    sustituciones = (('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'), ('Ü', 'U'))
    for a, b in sustituciones:
        texto = texto.replace(a, b)
    return texto

ALERGENOS_DB = {
    "TRIGO/GLUTEN": ["TRIGO", "WHEAT", "HARINA", "CEBADA", "CENTENO", "AVENA", "GLUTEN"],
    "LECHE/LÁCTEOS": ["LECHE", "MILK", "LACTEO", "SUERO", "QUESO", "MANTEQUILLA", "CASEINA", "LACTOSA"],
    "SOYA": ["SOYA", "SOY", "LECITINA", "PROTEINA VEGETAL"],
    "HUEVO": ["HUEVO", "EGG", "ALBUMINA", "YEMA"],
    "PESCADO/MARISCO": ["PESCADO", "FISH", "ATUN", "SALMON", "MERLUZA", "BAGRE", "TRUCHA", "SARDINA", "MARISCO", "CAMARON", "SHRIMP", "PULPO"],
    "MANÍ": ["MANI", "PEANUT", "CACAHUATE", "CACAHUETE"],
    "NUECES DE ÁRBOL/FRUTOS SECOS": ["NUEZ", "NUECES", "NUT", "ALMENDRA", "ALMOND", "AVELLANA", "HAZELNUT", "MARAÑON", "ANACARDO", "CASHEW", "MACADAMIA", "PECANA", "PECAN", "PISTACHO", "PISTACHIO", "BRASIL"],
    "SULFITOS (>= 10 mg/kg)": ["SULFITO", "SULFITE", "METABISULFITO", "BISULFITO", "DIOXIDO DE AZUFRE", "SO2", "E-220", "E-221", "E-222", "E-223", "E-224", "E-225", "E-226", "E-227", "E-228", "E220", "E221", "E222", "E223", "E224", "E225", "E226", "E227", "E228"]
}

ADVERTENCIAS_5109 = {
    "ASPARTAME": "FENILCETONÚRICOS: CONTIENE FENILALANINA (Res. 5109/2005)",
    "ASPARTAMO": "FENILCETONÚRICOS: CONTIENE FENILALANINA (Res. 5109/2005)",
    "TARTRAZINA": "CONTIENE TARTRAZINA (Res. 5109/2005)",
    "AMARILLO 5": "CONTIENE TARTRAZINA (Res. 5109/2005)",
    "CAFEINA": "CONTIENE CAFEÍNA (Res. 5109/2005)"
}

CAT_RES_AUDITORIA = [
    "0. N.A. (No aplica)",
    "--- GRUPO 1: PANADERÍA (Metas: 360-460 mg) ---",
    "1.1 Pan blanco de molde (360mg)", "1.2 Pan integral de molde (400mg)", 
    "1.3 Pan tostado (400mg)", "1.4 Calados / Envueltos (400mg)", 
    "1.5 Galletas saladas (460mg)", "1.6 Galletas dulces con sal (460mg)", 
    "1.7 Ponqués/Tortas (400mg)", "1.8 Repostería fina (400mg)", 
    "1.9 Mezclas secas panadería (460mg)", "1.10 Masas refrigeradas (460mg)",
    "--- GRUPO 2: CÁRNICOS PROCESADOS (Metas: 740-840 mg) ---",
    "2.1 Chorizo (750mg)", "2.2 Jamón (840mg)", "2.3 Salchicha (810mg)", 
    "2.4 Salchichón (790mg)", "2.5 Mortadela (790mg)", "2.6 Carne de diablo (810mg)", 
    "2.7 Hamburguesas (740mg)", "2.8 Nugget de pollo (740mg)", "2.9 Albóndigas (740mg)", 
    "2.10 Carne molida proc. (740mg)", "2.11 Tocino procesado (790mg)", 
    "2.12 Butifarra (840mg)", "2.13 Longaniza (840mg)",
    "--- GRUPO 3: QUESOS (Metas: 450-720 mg) ---",
    "3.1 Queso fresco (450mg)", "3.2 Queso Doble Crema (540mg)", 
    "3.3 Queso Mozzarella (540mg)", "3.4 Queso Costeño (720mg)", 
    "3.5 Queso industrial (630mg)", "3.6 Queso crema (500mg)", 
    "3.7 Queso fundido (670mg)", "3.8 Queso madurado (670mg)", 
    "3.9 Queso Parmesano (720mg)", "3.10 Queso tipo Feta (720mg)", 
    "3.11 Queso Ricotta (450mg)", "3.12 Suero costeño (630mg)",
    "--- GRUPO 4: SALSAS Y GRASAS (Metas: 1080-1350 mg) ---",
    "4.1 Mayonesa (1080mg)", "4.2 Salsa de tomate (1170mg)", 
    "4.3 Mostaza (1260mg)", "4.4 Salsa de soya (1350mg)", 
    "4.5 Salsas emulsionadas (1120mg)", "4.6 Salsas de ají (1260mg)", 
    "4.7 Pastas de tomate (1080mg)", "4.8 Margarinas de mesa (1170mg)", 
    "4.9 Grasas para untar (1170mg)",
    "--- GRUPO 5: SNACKS (Metas: 540-720 mg) ---",
    "5.1 Papas fritas (540mg)", "5.2 Platanitos (540mg)", 
    "5.3 Chicharrones empacados (630mg)", "5.4 Extruidos (720mg)", 
    "5.5 Mezclas frutos secos (630mg)", "5.6 Maní con sal (630mg)", 
    "5.7 Rosquitas (630mg)", "5.8 Tortillas de maíz (670mg)", 
    "5.9 Pasabocas de yuca (630mg)",
    "--- GRUPO 6: SOPAS Y CALDOS (Metas: 270-360 mg) ---",
    "6.1 Sopas en polvo (270mg)", "6.2 Caldos deshidratados (310mg)", 
    "6.3 Cremas instantáneas (310mg)", "6.4 Sopas listas (360mg)", 
    "6.5 Bases deshidratadas (360mg)", "6.6 Sopas líquidas (360mg)", 
    "6.7 Caldos concentrados (360mg)"
]

def redondear_res810(valor, nutri):
    if valor is None or valor < 0: return "0"
    if nutri == 'energia' and valor < 5: return "0"
    if nutri == 'sodio' and valor < 5: return "0"
    if nutri == 'grasa_trans' and valor < 0.1: return "0"
    if nutri in ['proteina', 'grasa_total', 'grasa_sat', 'fibra', 'carbohidratos', 'azucares_totales', 'azucares_anadidos'] and valor < 0.5: return "0"
    def aproximar_estricto(n, dec):
        factor = 10 ** dec
        return int(n * factor + 0.5 + 1e-9) / factor
    if valor >= 10:
        val_f = aproximar_estricto(valor, 0)
        return str(int(val_f))
    elif valor >= 1:
        val_f = aproximar_estricto(valor, 1)
        return f"{val_f:.1f}"
    else: 
        if nutri in ['vit_a', 'vit_d', 'hierro', 'calcio', 'zinc']:
            val_f = aproximar_estricto(valor, 2)
            return f"{val_f:.2f}"
        else:
            val_f = aproximar_estricto(valor, 1)
            return f"{val_f:.1f}"

def buscar_en_db(term, fuente):
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        tn = normalizar_texto(term)
        p = tn.split()
        cn = "REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(nombre, 'Á', 'A'), 'É', 'E'), 'Í', 'I'), 'Ó', 'O'), 'Ú', 'U')"
        if fuente == "ICBF":
            c = " AND ".join([f"{cn} LIKE ?" for _ in p]); v = [f"%{x}%" for x in p]
            cur.execute(f"SELECT * FROM ingredientes WHERE {c} AND fuente LIKE 'ICBF%' LIMIT 50", v)
            return [dict(row) for row in cur.fetchall()], "ICBF"
        else:
            te = traductor_en.translate(term).upper()
            pe = normalizar_texto(te).split()
            c = " AND ".join([f"{cn} LIKE ?" for _ in pe]); v = [f"%{x}%" for x in pe]
            cur.execute(f"SELECT * FROM ingredientes WHERE {c} AND fuente LIKE 'USDA%' LIMIT 50", v)
            r = [dict(row) for row in cur.fetchall()]
            if r:
                tu = " ||| ".join([item['nombre'] for item in r])
                try:
                    tr = traductor_es.translate(tu).upper()
                    ne = tr.split(" ||| ")
                    if len(ne) == len(r):
                        for j, it in enumerate(r): it['nombre'] = ne[j].strip()
                except: pass
            return r, "USDA"
    except: return [], "ERROR"

# --- 2. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="SAIR - INVIMA 2026", layout="wide")
st.title("SAIR v17.5 GOLD DEFINITIVA")
st.markdown("### SISTEMA AUTOMATIZADO DE INSPECCIÓN DEL ROTULADO (NUTRICIONAL)")

with st.sidebar:
    st.markdown("### Estado del Sistema")
    if os.path.exists("sair_data.db"):
        peso_mb = os.path.getsize("sair_data.db") / (1024 * 1024)
        st.success(f"✅ DB Conectada ({peso_mb:.2f} MB)")
    else:
        st.error("❌ Archivo DB no encontrado.")

st.divider()

if 'receta' not in st.session_state: st.session_state.receta = []
if 'resultados_actuales' not in st.session_state: st.session_state.resultados_actuales = []
if 'fuente_busqueda' not in st.session_state: st.session_state.fuente_busqueda = "ICBF"
if 'reporte_texto' not in st.session_state: st.session_state.reporte_texto = ""

# --- 1. DATOS DEL PRODUCTO ---
col_p1, col_p2 = st.columns(2)
with col_p1:
    st.header("1. DATOS DEL PRODUCTO")
    var_prod = st.text_input("Nombre Comercial:").upper()
    cmb_matriz = st.selectbox("Matriz (Sólido/Líquido):", ["SÓLIDO (g)", "LÍQUIDO (ml)"])
    var_peso = st.number_input("Contenido Neto Declarado:", min_value=0.0, format="%.2f")
    cmb_res2056 = st.selectbox("Categoría (Res. 2056/2023):", CAT_RES_AUDITORIA)

with col_p2:
    st.header("2. INGREDIENTES")
    col_i1, col_i2 = st.columns([2, 1])
    with col_i1: var_ing = st.text_input("Nombre del Ingrediente:").upper()
    with col_i2: cant_ing = st.number_input("Cantidad (g/ml):", min_value=0.0, format="%.2f")
    
    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("BUSCAR EN ICBF", type="primary", use_container_width=True):
            if var_ing:
                res, f = buscar_en_db(var_ing, "ICBF")
                st.session_state.resultados_actuales = res; st.session_state.fuente_busqueda = f
    with cb2:
        if st.button("BUSCAR EN USDA", use_container_width=True):
            if var_ing:
                with st.spinner("Traduciendo y buscando en USDA..."):
                    res, f = buscar_en_db(var_ing, "USDA")
                    st.session_state.resultados_actuales = res; st.session_state.fuente_busqueda = f

    if st.session_state.resultados_actuales:
        opciones = [f"{r['nombre']} ({st.session_state.fuente_busqueda})" for r in st.session_state.resultados_actuales]
        seleccion = st.selectbox("Seleccione el ingrediente exacto:", opciones)
        if st.button("ADICIONAR A LA FORMULACIÓN", type="primary", use_container_width=True):
            idx = opciones.index(seleccion)
            item = st.session_state.resultados_actuales[idx]
            st.session_state.receta.append({"info": item, "peso": cant_ing, "nombre_es": item['nombre'].upper(), "origen": st.session_state.fuente_busqueda})
            st.success(f"Añadido: {item['nombre']}")
            st.session_state.resultados_actuales = []; st.rerun()

st.divider()

# --- 3. REPORTE TÉCNICO ---
st.header("3. REPORTE TÉCNICO")
if st.session_state.receta:
    c_r1, c_r2 = st.columns([2, 1])
    with c_r1:
        st.dataframe(pd.DataFrame(st.session_state.receta)[["nombre_es", "peso", "origen"]], use_container_width=True)
        st.write(f"**TOTAL MASA:** {sum(i['peso'] for i in st.session_state.receta):.2f}")
    with c_r2:
        if st.button("LIMPIAR DATOS", type="secondary", use_container_width=True):
            st.session_state.receta = []; st.session_state.reporte_texto = ""; st.rerun()

if st.button("GENERAR ANÁLISIS INTEGRAL", type="primary"):
    if not st.session_state.receta or var_peso <= 0:
        st.error("Datos insuficientes.")
    else:
        peso_f = float(var_peso); matriz = cmb_matriz
        mapa_forense = {'energia': ['energia', 'energy', 'energy_kcal'], 'proteina': ['proteina', 'protein'], 'grasa_total': ['grasa_total', 'fat', 'total_lipid'], 'grasa_sat': ['grasa_sat', 'fatty_acids_total_saturated'], 'grasa_trans': ['grasa_trans', 'fatty_acids_total_trans'], 'carbohidratos': ['carbohidratos', 'carbohydrate'], 'azucares_totales': ['azucares_totales', 'sugars', 'sugars_total'], 'azucares_anadidos': ['azucares_anadidos', 'added_sugars', 'sugars_added'], 'fibra': ['fibra', 'fiber'], 'sodio': ['sodio', 'sodium'], 'vit_a': ['vit_a', 'vitamin_a'], 'vit_d': ['vit_d', 'vitamin_d'], 'hierro': ['hierro', 'iron'], 'calcio': ['calcio', 'calcium'], 'zinc': ['zinc']}
        nombres_display = {'energia': 'Energía (kcal)', 'proteina': 'Proteína (g)', 'grasa_total': 'Grasa Total (g)', 'grasa_sat': 'Grasa Saturada (g)', 'grasa_trans': 'Grasa Trans (g)', 'carbohidratos': 'Carbohidratos Tot. (g)', 'azucares_totales': 'Azúcares Totales (g)', 'azucares_anadidos': 'Azúcares Añadidos (g)', 'fibra': 'Fibra Dietaria (g)', 'sodio': 'Sodio (mg)', 'vit_a': 'Vitamina A (ug)', 'vit_d': 'Vitamina D (ug)', 'hierro': 'Hierro (mg)', 'calcio': 'Calcio (mg)', 'zinc': 'Zinc (mg)'}
        
        texto_reporte = f"SISTEMA AUTOMATIZADO DE INSPECCIÓN DEL ROTULADO (NUTRICIONAL) - {var_prod}\n" + "="*85 + "\n"
        texto_reporte += "1. COMPOSICIÓN DE LA FORMULACIÓN (Trazabilidad):\n"
        texto_reporte += f"{'INGREDIENTE':<35} | {'ORIGEN':<8} | {'CANT.':<8} | {'%'}\n" + "-"*75 + "\n"
        
        s_adic, g_adic, az_adic = False, False, False
        ts = ["SAL", "SODIO", "CITRATO", "GLUTAMATO", "BENZOATO", "SECO", "SALMUERA", "CLORURO", "BICARBONATO", "CONSERVANTE", "NITRITO", "NITRATO", "FOSFATO", "PROPIONATO", "SORBATO", "AJINOMOTO", "SAZONADOR", "CONSOME", "CALDO"]
        tg = ["ACEITE", "MANTECA", "MANTEQUILLA", "MARGARINA", "TOCINO", "CREMA", "GRASA", "SEBO", "GORDO", "GORDA", "EMPELLA", "LARDO", "NATA", "HIDROGENAD", "SHORTENING", "GHEE"]
        t_az = ["AZUCAR", "PANELA", "MIEL", "JARABE", "FRUCTOSA", "GLUCOSA", "SACAROSA", "MALTODEXTRINA", "ALMIBAR", "JUGO", "ZUMO", "CONCENTRADO", "EXTRACTO", "MELAZA", "AGAVE", "DEXTROSA", "MALTOSA", "NECTAR", "CHANCACA", "CARAMELO", "ALFENIQUE"]

        for i in st.session_state.receta:
            pct = (i['peso'] / peso_f) * 100; ne = normalizar_texto(i['nombre_es'])
            texto_reporte += f"{i['nombre_es'][:35]:<35} | {i['origen']:<8} | {i['peso']:>6.1f} | {pct:>5.2f}%\n"
            if any(x in ne for x in ts): s_adic = True
            if any(x in ne for x in tg): g_adic = True
            if any(x in ne for x in t_az): az_adic = True
            
        texto_reporte += "\n2. TABLA NUTRICIONAL (Por cada 100 (g) o (ml))\n"
        nut_g = {}; nut_str = {}
        for k, var in mapa_forense.items():
            s_n = 0
            for i in st.session_state.receta:
                val = next((float(i['info'][v]) for v in var if v in i['info'] and i['info'][v] is not None and str(i['info'][v]).strip() != ''), 0)
                if k == 'azucares_anadidos' and val == 0:
                    if any(x in normalizar_texto(i['nombre_es']) for x in t_az):
                        val = next((float(i['info'][vt]) for vt in mapa_forense['azucares_totales'] if vt in i['info'] and i['info'][vt] is not None and str(i['info'][vt]).strip() != ''), 0)
                s_n += (val * i['peso'] / 100)
            vl = redondear_res810((s_n / peso_f) * 100, k)
            texto_reporte += f"  {nombres_display.get(k, k):<25}: {vl}\n"
            nut_g[k] = float(vl); nut_str[k] = vl
            
        texto_reporte += "\n3. SELLOS FRONTALES (Res. 2492/2022 y Res. 254/2023):\n"
        en_t = nut_g.get('energia', 0)
        k_az = nut_g.get('azucares_totales', 0) * 4 if az_adic else 0
        k_gs = nut_g.get('grasa_sat', 0) * 9; k_gt = nut_g.get('grasa_trans', 0) * 9
        p_az = (k_az / en_t * 100) if en_t > 0 else 0; p_gs = (k_gs / en_t * 100) if en_t > 0 else 0; p_gt = (k_gt / en_t * 100) if en_t > 0 else 0
        r_so = (nut_g.get('sodio', 0) / en_t) if en_t > 0 else 0
        es_sol = "SÓLIDO" in matriz.upper()
        ex_so = (es_sol and (r_so >= 1 or nut_g.get('sodio',0) >= 300)) or (not es_sol and ((en_t > 0 and r_so >= 1) or (en_t == 0 and nut_g.get('sodio',0) >= 40)))
        ed = any(x in normalizar_texto(str(st.session_state.receta)) for x in ["SUCRALOSA", "STEVIA", "ASPARTAME", "ACESULFAME", "ERITRITOL", "ASPARTAMO"])
        hs = False
        def po(t1, t2): return f"      .-------.\n     / {t1:^7} \\\n    |  {t2:^7}  |\n    | MINSALUD |\n     \\       /\n      '-------'\n"
        if ex_so and s_adic: texto_reporte += po("EXCESO", "SODIO"); hs = True
        if p_az >= 10 and az_adic: texto_reporte += po("EXCESO", "AZÚCAR"); hs = True
        if p_gs >= 10 and g_adic: texto_reporte += po("EXCESO", "G.SAT"); hs = True
        if p_gt >= 1 and g_adic: texto_reporte += po("EXCESO", "G.TRAN"); hs = True
        if ed: texto_reporte += po("CONTIENE", "EDULCO"); hs = True
        if not hs: texto_reporte += "  >>> PRODUCTO LIBRE DE SELLOS FRONTALES.\n"
        m_s = re.findall(r'\((\d+)mg\)', cmb_res2056)
        if m_s:
            lim = int(m_s[0]); rs = "CUMPLE" if nut_g['sodio'] <= lim else "NO CUMPLE"
            texto_reporte += f"\n  META SODIO RES. 2056/2023 ({lim}mg): {rs}\n"
            
        texto_reporte += "\n" + "-"*40 + "\n4. ALERTAS DE SEGURIDAD (Res. 5109/2005 y 810/2021):\n"
        al_t = set()
        for i in st.session_state.receta:
            tc = normalizar_texto(f"{i['nombre_es']} {str(i['info'])}")
            for al, keys in ALERGENOS_DB.items():
                kn = [normalizar_texto(k) for k in keys]
                if any(k in tc for k in kn): al_t.add(f" [!] ALÉRGENO: {al} (Res. 810/2021)")
            for k, ley in ADVERTENCIAS_5109.items():
                if normalizar_texto(k) in tc: al_t.add(f" [!] {ley}")
        for msg in sorted(al_t): texto_reporte += f"{msg}\n"
        
        texto_reporte += "\n" + "="*85 + "\n5. COMPOSICIÓN CENTESIMAL CRUZADA (% APORTE)\n\n"
        h = f"{'INGREDIENTE':<16}|ENE |PRO |GRA |G.S |G.T |CHO |AZU |A.A |FIB |SOD |V.A |V.D |HIE |CAL |ZIN "; texto_reporte += h + "\n" + "-"*95 + "\n"
        for i in st.session_state.receta:
            f = i['nombre_es'][:15].ljust(16)
            for k, v_map in mapa_forense.items():
                val = next((float(i['info'][v]) for v in v_map if v in i['info'] and i['info'][v] is not None and str(i['info'][v]).strip() != ''), 0)
                if k == 'azucares_anadidos' and val == 0:
                    if any(x in normalizar_texto(i['nombre_es']) for x in t_az):
                        val = next((float(i['info'][vt]) for vt in mapa_forense['azucares_totales'] if vt in i['info'] and i['info'][vt] is not None and str(i['info'][vt]).strip() != ''), 0)
                f += f"|{( (val * i['peso'] / 100) / peso_f * 100):4.1f}"
            texto_reporte += f + "\n"
        ing_o = sorted(st.session_state.receta, key=lambda x: x['peso'], reverse=True); l_i = f"INGREDIENTES: {'; '.join([ing['nombre_es'] for ing in ing_o])}."; texto_reporte += f"\n{textwrap.fill(l_i, width=75)}\n"
        texto_reporte += "\n" + "="*85 + "\n TABLA NUTRICIONAL SUGERIDA EN FORMATO LINEAL:\n\n"; lin_str = "Información Nutricional por 100(g/ml): " + ", ".join([f"{nombres_display.get(k,k)}: {nut_str.get(k,'0')}" for k in mapa_forense.keys()]) + "."; texto_reporte += f"{textwrap.fill(lin_str, width=75)}\n\nFIN DE AUDITORÍA TÉCNICA"
        st.session_state.reporte_texto = texto_reporte

# --- MOSTRAR REPORTE Y DESCARGA PDF ---
if st.session_state.reporte_texto:
    st.markdown(f"```text\n{st.session_state.reporte_texto}\n```")
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Courier", size=8)
    for l in st.session_state.reporte_texto.split('\n'): pdf.cell(200, 3.5, txt=l.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    st.download_button(label="📥 DESCARGAR ACTA PDF", data=pdf.output(dest='S').encode('latin-1'), file_name=f"Acta_SAIR_{var_prod}.pdf", mime="application/pdf", type="primary")
    