#!/usr/bin/env python3
"""
Собирает отдельные GIF для упражнений из free-exercise-db (Unlicense / public domain).
https://github.com/yuhonas/free-exercise-db

Запуск:  pip install pillow requests
         python make_gifs.py            # подбор кандидатов + GIF по лучшему совпадению
Результат: папка gifs/<id>.gif и файл report.csv (id, лучший кандидат, ещё 2 варианта, оценка).
Совпадения с оценкой < 0.6 в report.csv помечены CHECK - проверьте их вручную
и при необходимости поправьте OVERRIDE ниже (id из free-exercise-db), затем запустите снова.
"""
import csv, difflib, io, os, re, sys
import requests
from PIL import Image

BASE = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main"
FRAME_MS = 700          # длительность каждого кадра, мс
SIZE = 480              # ширина GIF, px

# id из вашего файла -> английский поисковый запрос
QUERIES = {
 "bench_press_barbell": "Barbell Bench Press Medium Grip",
 "incline_barbell_press": "Barbell Incline Bench Press Medium Grip",
 "incline_dumbbell_press": "Incline Dumbbell Press",
 "bench_press_dumbbells": "Dumbbell Bench Press",
 "dips_chest": "Dips Chest Version",
 "pushups_floor": "Pushups",
 "pushups_weighted": "Weighted Pushup",
 "pushups_feet_elevated": "Decline Push-Up",
 "chest_press_machine": "Machine Bench Press",
 "low_to_high_cable_fly": "Low Cable Crossover",
 "overhead_press_barbell": "Standing Military Press",
 "seated_dumbbell_press": "Dumbbell Shoulder Press",
 "shoulder_press_machine": "Machine Shoulder Military Press",
 "pike_pushups": "Pike Push-Up",
 "lateral_raises_dumbbells": "Side Lateral Raise",
 "lateral_raises_cable": "Cable Seated Lateral Raise",
 "lateral_raises_resistance_band": "Band Lateral Raise",
 "rear_delt_cable_fly": "Cable Rear Delt Fly",
 "rear_delt_dumbbell_fly": "Bent Over Dumbbell Rear Delt Raise With Head On Bench",
 "face_pull_cable": "Face Pull",
 "lat_pulldown": "Wide-Grip Lat Pulldown",
 "lat_pulldown_band": "Band Assisted Pull-Up",
 "pullups": "Pullups",
 "seated_cable_row": "Seated Cable Rows",
 "barbell_row": "Bent Over Barbell Row",
 "dumbbell_row_bench": "One-Arm Dumbbell Row",
 "chest_supported_row": "Dumbbell Incline Row",
 "t_bar_row_supported": "Lying T-Bar Row",
 "inverted_rows": "Inverted Row",
 "back_squat": "Barbell Full Squat",
 "leg_press": "Leg Press",
 "hack_squat": "Hack Squat",
 "goblet_squat": "Goblet Squat",
 "bulgarian_split_squat": "Single Leg Split Squat Dumbbell Bulgarian",
 "leg_extension": "Leg Extensions",
 "romanian_deadlift_barbell": "Romanian Deadlift",
 "romanian_deadlift_dumbbells": "Romanian Deadlift With Dumbbells",
 "leg_curl_machine": "Lying Leg Curls",
 "glute_bridge": "Barbell Glute Bridge",
 "nordic_curl": "Natural Glute Ham Raise",
 "biceps_curl_barbell": "Barbell Curl",
 "biceps_curl_ez_bar": "EZ-Bar Curl",
 "biceps_curl_dumbbells": "Dumbbell Alternate Bicep Curl",
 "hammer_curls_dumbbells": "Hammer Curls",
 "biceps_curl_cable": "Standing Biceps Cable Curl",
 "triceps_pushdown_cable": "Triceps Pushdown",
 "triceps_pushdown_rope": "Triceps Pushdown Rope Attachment",
 "overhead_triceps_dumbbell": "Seated Triceps Press",
 "skull_crushers_dumbbells": "Lying Dumbbell Tricep Extension",
 "dips_bench": "Bench Dips",
 "cable_crunch_prayer": "Kneeling Cable Crunch With Alternating Oblique Twists",
 "hanging_leg_raises": "Hanging Leg Raise",
 "floor_crunches": "Crunches",
 "plank": "Plank",
}
# Ручные поправки: id вашего файла -> id папки в free-exercise-db
OVERRIDE = {
    "pushups_weighted": "Pushups",
    "lat_pulldown_band": "Wide-Grip_Lat_Pulldown",
    "pike_pushups": "Handstand_Push-Ups",
    "bulgarian_split_squat": "Split_Squat_with_Dumbbells",
    "cable_crunch_prayer": "Cable_Crunch",
    "glute_bridge": "Butt_Lift_Bridge",
}

def norm(s): return re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("_", " ")).split()

def score(q, name):
    a, b = " ".join(norm(q)), " ".join(norm(name))
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(norm(q)), set(norm(name))
    tok = len(ta & tb) / max(1, len(ta | tb))
    return 0.5 * seq + 0.5 * tok

def frame(url):
    r = requests.get(url, timeout=60); r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def main():
    db = requests.get(f"{BASE}/dist/exercises.json", timeout=60).json()
    by_id = {e["id"]: e for e in db}
    os.makedirs("gifs", exist_ok=True)
    rows = []
    for my_id, q in QUERIES.items():
        ranked = sorted(db, key=lambda e: -score(q, e["name"]))[:3]
        best = by_id.get(OVERRIDE.get(my_id)) or ranked[0]
        sc = score(q, best["name"])
        status = "ok" if sc >= 0.6 or my_id in OVERRIDE else "CHECK"
        try:
            frames = [frame(f"{BASE}/exercises/{best['id']}/{i}.jpg") for i in range(len(best["images"]))]
            h = int(frames[0].height * SIZE / frames[0].width)
            frames = [f.resize((SIZE, h)) for f in frames]
            # туда-обратно, чтобы движение выглядело плавным циклом
            seq = frames + frames[-2:0:-1] if len(frames) > 2 else frames + frames[::-1][1:-1]
            frames[0].save(f"gifs/{my_id}.gif", save_all=True, append_images=(seq[1:] or frames[1:]),
                           duration=FRAME_MS, loop=0, optimize=True)
        except Exception as ex:
            status = f"ERROR {ex}"
        rows.append([my_id, q, best["id"], round(sc, 2), status] + [r["id"] for r in ranked])
        print(my_id, "->", best["id"], round(sc, 2), status)
    with open("report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "query", "chosen", "score", "status", "cand1", "cand2", "cand3"])
        w.writerows(rows)

if __name__ == "__main__":
    main()
