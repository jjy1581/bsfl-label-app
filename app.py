from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# --- Constants ---
EGG_WEIGHT_EACH = 0.0000276  # grams per egg
HATCH_RATE = 0.90
DRY_FOOD_PER_LARVA = 0.22  # grams
DRY_FOOD_RATIO = 0.30  # dry food is 30% of total wet mix (70% water, 30% dry)

# Feeding schedule: (day_offset, percentage_of_total)
FEED_SCHEDULE = [
    (0, 0.02, "Hatch day feed"),
    (6, 0.20, "Growth feed 1"),
    (7, 0.28, "Growth feed 2"),
    (9, 0.50, "Final feed"),
]
HARVEST_DAY = 11


def calculate_schedule(egg_weight_g, start_date):
    num_eggs = egg_weight_g / EGG_WEIGHT_EACH
    expected_larvae = num_eggs * HATCH_RATE
    total_dry_food = expected_larvae * DRY_FOOD_PER_LARVA
    total_wet_food = total_dry_food / DRY_FOOD_RATIO  # dry is 30% of total

    feeds = []
    for day_offset, pct, stage in FEED_SCHEDULE:
        feed_date = start_date + timedelta(days=day_offset)
        dry = total_dry_food * pct
        wet = total_wet_food * pct
        # Hatch day: add extra water equal to wet feed so substrate doesn't dry out
        extra_water = round(wet, 1) if day_offset == 0 else 0
        feeds.append({
            "feed_num": len(feeds) + 1,
            "day": day_offset,
            "date": feed_date.strftime("%a %m/%d"),
            "date_full": feed_date.strftime("%Y-%m-%d"),
            "stage": stage,
            "dry_g": round(dry, 1),
            "wet_g": round(wet, 1),
            "extra_water_g": extra_water,
            "total_place_g": round(wet + extra_water, 1),
        })

    harvest_date = start_date + timedelta(days=HARVEST_DAY)

    return {
        "num_eggs": round(num_eggs),
        "expected_larvae": round(expected_larvae),
        "total_dry_g": round(total_dry_food, 1),
        "total_wet_g": round(total_wet_food, 1),
        "feeds": feeds,
        "harvest_date": harvest_date.strftime("%a %m/%d"),
        "harvest_day": HARVEST_DAY,
        "scale_margin_eggs": 362,
        "scale_margin_pct": round(362 / num_eggs * 100, 1) if num_eggs > 0 else 0,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    egg_weight = float(data["egg_weight"])
    bin_number = data["bin_number"]
    start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")

    schedule = calculate_schedule(egg_weight, start_date)
    schedule["egg_weight"] = egg_weight
    schedule["bin_number"] = bin_number
    schedule["start_date"] = start_date.strftime("%a %m/%d/%Y")

    return jsonify(schedule)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
