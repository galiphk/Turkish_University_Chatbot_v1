# actions/actions.py
from rapidfuzz import process, fuzz
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
import json
import pandas as pd
import re
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os
import uuid
from .prompt_templates import SYSTEM_PROMPT, UNIVERSITY_INFO_PROMPT

FONT_PATH = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")
pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))

def add_logo_background(canvas, doc):
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.pagesizes import landscape, A4

    width, height = landscape(A4)
    try:
        logo_path = "./backend/static/logo.png"
        logo = ImageReader(logo_path)

        # 🎯 1. Ortada saydam filigran logo (biraz daha görünür)
        canvas.saveState()
        canvas.setFillAlpha(0.25)  # %25 opaklık

        filigran_width = 400
        filigran_height = 200
        x_center = (width - filigran_width) / 2
        y_center = (height - filigran_height) / 2

        canvas.drawImage(
            logo,
            x_center,
            y_center,
            width=filigran_width,
            height=filigran_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        canvas.restoreState()

        # 🎯 2. Sol üstte küçük ve opak logo (görünmeyen sorunu çözüldü)
        logo_width = 160
        logo_height = 80
        margin_top = 10
        margin_left = 40
        margin_bottom = 10

        canvas.drawImage(
            logo,
            x=margin_left,
            y=height - logo_height - margin_top - margin_bottom,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )

    except Exception as e:
        print(f"Logo çizilemedi: {e}")





def create_pdf(preferences, sender_id, output_dir="./backend/pdfs"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = f"{sender_id}tercih{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(output_dir, filename)


    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontName = "DejaVu"

    right_style = ParagraphStyle(
        name="RightAlign",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
        fontName="DejaVu"
    )

    today = datetime.today().strftime("%d.%m.%Y")
    elements.append(Paragraph(f"Tarih: {today}", right_style))
    elements.append(Paragraph("<b>Üniversite Tercih Listeniz</b>", styles["Title"]))

    data = [["#", "Program Kodu", "Üniversite", "Bölüm", "Başarı Sırası", "Puan", "Not"]]
    for i, pref in enumerate(preferences, start=1):
        def truncate(text, limit):
            return (text[:limit] + "...") if len(text) > limit else text

        row = [
            str(i),
            truncate(str(pref.get("code", "")), 20),
            truncate(pref.get("uni", ""), 32),
            truncate(pref.get("program", ""), 42),
            str(pref.get("ranking", "")),
            str(pref.get("score", "")),
            truncate(pref.get("note", ""), 40)
        ]
        data.append(row)

    table = Table(data, colWidths=[20, 75, 200, 200, 40, 40, 150])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    for row_num in range(1, len(data)):
        bg_color = colors.whitesmoke if row_num % 2 == 0 else colors.lightgrey
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, row_num), (-1, row_num), bg_color)
        ]))

    elements.append(table)

    doc.build(elements,
              onFirstPage=lambda canvas, doc: add_logo_background(canvas, doc),
              onLaterPages=lambda canvas, doc: add_logo_background(canvas, doc))

    return filename


def extract_pref_count(user_text):
    patterns = [
        r"(?:maksimum|en fazla|maks)?\s*(\d+)\s*(?:tercih|öneri|tane)?",
        r"(?:tercih|öneri)?\s*(\d+)\s*(?:adet|tane)?",
        r"(?:yaklaşık)?\s*(\d+)\s*(?:tercih|öneri)?"
    ]

    for pattern in patterns:
        match = re.search(pattern, user_text.lower())
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue

    return None
def extract_json_from_response(response_text):
    match = re.search(r"\{[\s\S]*\}", response_text)
    return match.group(0) if match else None

def fix_json_text(raw_text: str) -> str:
    # Markdown kalıntılarını temizle
    raw_text = raw_text.strip().strip("`").replace("json", "").replace("", "")

    # Çift çift tırnakları düzelt (""Ankara"" → "Ankara")
    raw_text = re.sub(r'""(.*?)""', r'"\1"', raw_text)

    # Akıllı tırnakları düzelt (“Ankara” → "Ankara")
    raw_text = raw_text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")

    # Tek tırnakları çift tırnağa çevir (ama key ve string'ler için dikkatli!)
    raw_text = re.sub(r"'([^']*)'", r'"\1"', raw_text)

    # NaN, Infinity gibi geçersiz şeyleri string'e çevir
    raw_text = re.sub(r'\bNaN\b', '"NaN"', raw_text)
    raw_text = re.sub(r'\bInfinity\b', '"Infinity"', raw_text)

    # Anahtarlar çift tırnaklı değilse düzelt: name: → "name":
    raw_text = re.sub(r'(?<=\{|\s)(\w+):', r'"\1":', raw_text)

    # true / false / null düzeltmesi (bazı modellerde boşluklu geliyor)
    raw_text = re.sub(r'\btrue\b', 'true', raw_text)
    raw_text = re.sub(r'\bfalse\b', 'false', raw_text)
    raw_text = re.sub(r'\bnull\b', 'null', raw_text)

    # Son elemandan sonra fazladan virgül varsa sil (özellikle listelerde/dictionary'de)
    raw_text = re.sub(r',\s*([\]}])', r'\1', raw_text)

    return raw_text

def format_slots_for_prompt(slot_memory: dict) -> dict:
    formatted = {}
    for key, value in slot_memory.items():
        if isinstance(value, list):
            formatted[key] = {"add": value, "remove": []}
        elif isinstance(value, str):
            formatted[key] = {"add": [value]} if value.strip() else {"add": [], "remove": []}
        else:
            formatted[key] = {"add": [], "remove": []}
    return formatted

# Excel dosyanızın tam yolunu buraya girin:
UNIV_DF = pd.read_excel(
    "C:/Users/Galip/Desktop/tercih_denm/Tercih_2.xlsx"
)

# Global slot hafızası - kullanıcı bazlı
SLOT_MEMORY = {}

class ActionLLMProxy(Action):
    def name(self) -> str:
        return "action_llm_proxy"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):
        
        user_id = tracker.sender_id

        # Başlangıç: tüm slotlar liste olacak şekilde
        if user_id not in SLOT_MEMORY:
            SLOT_MEMORY[user_id] = {
                "city": [],
                "major": [],
                "score": "",
                "ranking": "",
                "score_type": "", 
                "school": [],
                "school_type": "",
                "pref_count": "",
            }

        slot_memory = SLOT_MEMORY[user_id]

        user_input = tracker.latest_message.get('text')
        slots_for_prompt = format_slots_for_prompt(slot_memory)

        # Final prompt
        prompt = f"""
        {SYSTEM_PROMPT}

        Kullanıcının yeni mesajı:
        {user_input}

        Mevcut slot bilgileri (JSON formatında):
        {json.dumps(slots_for_prompt, ensure_ascii=False, indent=2)}

        Assistant:
        """

        try:
            print("LLM'den yanıt alınıyor...")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3:instruct",  # <-- model ismini burada değiştirdik
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0,
                    "num_predict": 700
                }
            )
            response.raise_for_status()
            json_text = response.json()["response"]
            json_text = json_text.strip("` \n").replace("json", "")
        except Exception as e:
            dispatcher.utter_message(text=f"❌ LLM yanıtı alınamadı: {e}")
            return []

        try:
            raw_response = response.json()["response"]
            raw_response = raw_response.strip("` \n").replace("json", "")  # varsa markdown temizle
            raw_response = fix_json_text(raw_response)  # JSON formatını düzelt
            json_text = extract_json_from_response(raw_response)
            if not json_text:
                raise ValueError("Geçerli JSON bulunamadı.")
            
            data = json.loads(json_text)
            reply = data.get("reply", "")
            slots_from_llm = data.get("slots", {})
            print(f"{user_id} için LLM'den gelen slotlar:", slots_from_llm)

        except Exception as e:
            dispatcher.utter_message("⚠ Bir şeyler ters gitti. Lütfen mesajınızı tekrar yazar mısınız? ")
            print(f"[JSON PARSE ERROR] Model cevabı:\n{raw_response}")
            return []

        dispatcher.utter_message(text=reply)

        def merge_lists(current: list, to_add: list, to_remove: list):
            current_set = set(current or [])
            current_set.update(to_add or [])
            current_set.difference_update(to_remove or [])
            return list(current_set)

        updated_slots = []    

        for key in slot_memory:
            if key == "pref_count":
                continue

            changes = slots_from_llm.get(key, {})
            if not isinstance(changes, dict):
                print(f"[UYARI] {key} için geçersiz slot formatı: {changes}")
                continue

            to_add = changes.get("add", [])
            to_remove = changes.get("remove", [])

            if key in ["score", "ranking", "score_type", "school_type"]:  # Tekil slotlar
                if to_remove:
                    slot_memory[key] = ""
                if isinstance(to_add, list) and to_add:
                    slot_memory[key] = to_add[-1]
                updated_slots.append(SlotSet(key, slot_memory[key]))
                continue

            # Liste slotları
            if isinstance(slot_memory[key], list):
                updated = merge_lists(slot_memory[key], to_add, to_remove)
                slot_memory[key] = updated
                updated_slots.append(SlotSet(key, updated))

        print(f"🎯 {user_id} için güncellenmiş slotlar:", slot_memory)
        return updated_slots

class ActionGeneratePreferences(Action):
    def name(self) -> str:
        return "action_generate_preferences"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: dict):
        df = UNIV_DF.copy()
        user_id = tracker.sender_id

        # Slotlar liste yapısı kullanıyor
        slot_keys = ["city", "major", "score", "ranking", "score_type", "school", "school_type"]

        user_slots = {}
        for key in slot_keys:
            val = tracker.get_slot(key)
            if key in ["score", "ranking", "score_type", "school_type"]:
                user_slots[key] = val or ""  # Tekil değer
            else:
                user_slots[key] = val or []  # Liste değeri

        if user_slots["city"]:
            all_cities = [c.strip().lower() for c in df["Şehir"].dropna().unique()]
            matched_cities = []

            for user_city in user_slots["city"]:
                match, score, _ = process.extractOne(user_city.lower().strip(), all_cities, scorer=fuzz.ratio)
                if score >= 85:
                    matched_cities.append(match)

            if matched_cities:
                df = df[df["Şehir"].str.lower().isin(matched_cities)]
            else:
                print("⚠ fuzzy city eşleşmesi bulunamadı")

        # --- Major filtresi (contains + fuzzy fallback, her major için ayrı) ---
        if user_slots["major"]:
            majors_lower = [m.lower() for m in user_slots["major"]]
            program_names = df["Program Adı"].dropna().str.lower().str.strip().unique()
            matched_rows = []

            for major in majors_lower:
                # A planı: contains
                contains_matches = df[df["Program Adı"].str.lower().str.contains(major)]
                if not contains_matches.empty:
                    matched_rows.append(contains_matches)
                else:
                    # B planı: fuzzy eşleşme
                    fuzzy_results = process.extract(major, program_names, scorer=fuzz.token_set_ratio, limit=5)
                    close_matches = [res[0] for res in fuzzy_results if res[1] >= 85]

                    if close_matches:
                        fuzzy_df = df[df["Program Adı"].str.lower().isin(close_matches)]
                        matched_rows.append(fuzzy_df)
                    else:
                        print(f"❌ '{major}' için eşleşme bulunamadı.")

            # Hepsini birleştir
            if matched_rows:
                df = pd.concat(matched_rows).drop_duplicates().reset_index(drop=True)
            else:
                print("⚠ Hiçbir major eşleşmesi bulunamadı.")

        # school_type
        if user_slots["school_type"]:
            sct_value = user_slots["school_type"][-1].lower()
            df = df[df["Üniversite Türü"].str.lower().str.contains(sct_value, na=False)]

        # --- School eşleşmesi ---
        if user_slots["school"]:
            school_names = df["Üniversite Adı"].dropna().unique()
            matched_schools = []
            for sc in user_slots["school"]:
                match, score, _ = process.extractOne(sc, school_names, scorer=fuzz.ratio)
                if score >= 80:
                    matched_schools.append(match.lower())

            if matched_schools:
                df = df[df["Üniversite Adı"].str.lower().isin(matched_schools)]
            else:
                print("⚠ fuzzy school eşleşmesi bulunamadı")

        if user_slots["score_type"]:
            sct_value = user_slots["score_type"].lower()
            df = df[df["Puan Türü"].str.lower().str.contains(sct_value, na=False)]

        ranking = user_slots.get("ranking")
        score = user_slots.get("score")

        # Sayısal hale getir
        df["Başarı Sırası"] = pd.to_numeric(df["Başarı Sırası"], errors="coerce")
        df["En Küçük Puan (Genel)"] = pd.to_numeric(df["En Küçük Puan (Genel)"], errors="coerce")

        if ranking:
            try:
                user_rank = float(ranking)
                lower_limit = user_rank * 0.95

                df_below = df[df["Başarı Sırası"] >= user_rank].copy()
                df_below["Etiket"] = "✅ Uygun"

                df_above = df[
                    (df["Başarı Sırası"] < user_rank) &
                    (df["Başarı Sırası"] >= lower_limit)
                ].copy()
                df_above["Etiket"] = "⚠ Sıralamanın biraz altında"

                df = pd.concat([df_below, df_above])
                df = df.sort_values("Başarı Sırası", ascending=True)

            except ValueError:
                pass

        elif score:
            try:
                user_score = float(score)
                upper_limit = user_score * 1.05

                df_below = df[df["En Küçük Puan (Genel)"] <= user_score].copy()
                df_below["Etiket"] = "✅ Uygun"

                df_above = df[
                    (df["En Küçük Puan (Genel)"] > user_score) &
                    (df["En Küçük Puan (Genel)"] <= upper_limit)
                ].copy()
                df_above["Etiket"] = "⚠ Puanın %5 kadar üzerinde"

                df = pd.concat([df_below, df_above])
                df = df.sort_values("En Küçük Puan (Genel)", ascending=False)

            except ValueError:
                pass
        
        else:
            # Kullanıcıdan sıralama bilgisi gelmemişse, veriye göre otomatik sırala
            if df["Başarı Sırası"].notnull().any():
                df = df[df["Başarı Sırası"].notnull()]
                df = df.sort_values("Başarı Sırası", ascending=True)
                df["Etiket"] = ""
            elif df["En Küçük Puan (Genel)"].notnull().any():
                df = df[df["En Küçük Puan (Genel)"].notnull()]
                df = df.sort_values("En Küçük Puan (Genel)", ascending=False)
                df["Etiket"] = ""
            else:
                print("⚠ Hem başarı sırası hem puan verisi eksik, sıralama yapılamıyor.")
                df["Etiket"] = "ℹ Sıralama yapılmadı"
                dispatcher.utter_message(
                            text="📌 Sıralama bilgisi vermediğiniz için ilk bulunan uygun bölümler listeleniyor. Daha iyi sonuçlar için puanınızı veya başarı sıranızı yazabilirsiniz. 🎯"
                        )

        # Kullanıcının mesajından tercih sayısı çıkar
        pref_count_value = extract_pref_count(tracker.latest_message.get("text", ""))

        # SLOT_MEMORY'ye yaz (tek değer!)
        if pref_count_value:
            SLOT_MEMORY[user_id]["pref_count"] = str(pref_count_value)  # Tekil string

        # tracker'dan gelen slotu oku
        pref_count_raw = tracker.get_slot("pref_count")

        # int'e çevir
        try:
            pref_count = int(pref_count_raw) if pref_count_raw else None
        except (ValueError, TypeError):
            pref_count = None

        max_limit = 24

        if pref_count is not None and pref_count > 0:
            top_n = df.iloc[:pref_count]
        else:
            top_n = df.iloc[:max_limit]

        if top_n.empty:
            dispatcher.utter_message("Maalesef kriterlerinize uyan tercih bulunamadı.")
            return []
        
        lines = []
        for i, (idx, row) in enumerate(top_n.iterrows(), start=0):
            program_kodu = row["Program Kodu"]
            uni = row["Üniversite Adı"]
            program = row["Program Adı"]
            sira = int(row["Başarı Sırası"]) if pd.notnull(row["Başarı Sırası"]) else "–"
            puan = f"{row['En Küçük Puan (Genel)']:.2f}" if pd.notnull(row["En Küçük Puan (Genel)"]) else "–"
            puan_turu = row["Puan Türü"]
            etiket = row["Etiket"]

            line = f"{i+1}. {program_kodu} - {uni} - {program} - {sira} sıralama - {puan} {puan_turu} - {etiket}"
            lines.append(line)

        prefs = [
            {
                "code": str(r["Program Kodu"]),
                "uni": r["Üniversite Adı"],
                "program": r["Program Adı"],
                "ranking": str(r["Başarı Sırası"]) if pd.notnull(r["Başarı Sırası"]) else "",
                "score": f"{r['En Küçük Puan (Genel)']:.2f}" if pd.notnull(r["En Küçük Puan (Genel)"]) else "",
                "note": r["Etiket"]
            }
            for _, r in top_n.iterrows()
        ]

        # PDF oluştur
        pdf_name = create_pdf(prefs,sender_id=user_id)

        dispatcher.utter_message(custom={
                                        "text": f"Toplam {len(df)} eşleşme bulundu. {len(top_n)} tanesi listeleniyor:\n" + "\n".join(lines),
                                        "pdf": pdf_name
                                    })
        return [SlotSet("pref_list", prefs)]


class ActionProvideInfo(Action):
    def name(self) -> str:
        return "action_provide_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict):

        user_input = tracker.latest_message.get("text")

        prompt = f"{UNIVERSITY_INFO_PROMPT}\nKullanıcının sorusu:\n{user_input}\nCevabın:"

        try:
            print("-get_info- LLM'den bilgi alınıyor...")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3:instruct",
                    "prompt": prompt,
                    "temperature": 0.8,
                    "stream": False
                }
            )
            response.raise_for_status()
            answer = response.json()["response"]
        except Exception as e:
            dispatcher.utter_message(text=f"❌ LLM'den bilgi alınamadı: {e}")
            return []

        dispatcher.utter_message(text=answer.strip())
        return []