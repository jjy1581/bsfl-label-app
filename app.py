from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# ============================================================
# BSFL Feeding Formula — Constants & Logic
# ============================================================
#
# CORE PRINCIPLE:
# Everything is derived from dry food per larva. We start with
# how much dry food each larva needs over its full grow-out,
# then calculate total dry food for the bin, then convert to
# wet mix using the water-to-dry ratio.
#
# WHY 0.22g dry food per larva?
# This is our current working estimate for total dry feed intake
# per larva across the full ~11 day grow-out. Will be calibrated
# over time by tracking input feed vs. harvest weight.
#
# WHY 60/40 water-to-dry ratio?
# The wet mix is 60% water and 40% dry feed by weight.
# This gives us a moist but not soupy substrate. The mix needs
# to hold together and not pool water at the bottom.
# To get total wet mix from dry: wet_mix = dry / 0.40
#
# WHY these schedule percentages (2/20/28/50)?
# Mimics the larval growth curve — tiny neonates eat almost
# nothing at first, then ramp up as they grow exponentially.
# Day 0 is just enough to keep them alive after hatching.
# The bulk of feed (50%) comes at day 9 when larvae are largest.
#
# WHY extra water on hatch day?
# Neonates are extremely sensitive to drying out. We add 20%
# extra water (based on wet mix weight) on top of the day 0
# wet mix to keep the substrate moist until the next feed.
# ============================================================

EGG_WEIGHT_EACH = 0.0000276  # grams per single BSFL egg
HATCH_RATE = 0.90             # expect ~90% of eggs to hatch
DRY_FOOD_PER_LARVA = 0.22    # grams of dry feed per larva over full grow-out
DRY_FOOD_RATIO = 0.40        # dry food is 40% of total wet mix weight (60% water)
HATCH_DAY_EXTRA_WATER = 0.20 # 20% extra water on hatch day (as % of wet mix weight)

# Feeding schedule: (day_offset, percentage_of_total_feed, stage_label)
# Percentages must sum to 1.0
FEED_SCHEDULE = [
    (0,  0.02, "Hatch day feed"),   # Just enough for neonates
    (6,  0.20, "Growth feed 1"),    # Larvae starting to grow
    (7,  0.28, "Growth feed 2"),    # Rapid growth phase
    (9,  0.50, "Final feed"),       # Larvae at peak size, biggest feed
]
HARVEST_DAY = 11  # Expected harvest day from egg placement


def calculate_schedule(egg_weight_g, start_date):
    # Step 1: How many larvae are we feeding?
    # Egg weight from scale / weight per egg = number of eggs
    num_eggs = egg_weight_g / EGG_WEIGHT_EACH
    expected_larvae = num_eggs * HATCH_RATE

    # Step 2: Total dry food for the entire bin
    # This is our anchor — everything else derives from this
    total_dry_food = expected_larvae * DRY_FOOD_PER_LARVA

    # Step 3: Convert to total wet mix
    # If dry is 40% of wet mix, then wet_mix = dry / 0.40
    total_wet_food = total_dry_food / DRY_FOOD_RATIO

    feeds = []
    for day_offset, pct, stage in FEED_SCHEDULE:
        feed_date = start_date + timedelta(days=day_offset)

        # This feed's portion of total dry and wet
        dry = total_dry_food * pct
        wet = total_wet_food * pct

        # Hatch day gets extra water to prevent substrate drying out
        # Extra water = 20% of this feed's wet mix weight
        extra_water = round(wet * HATCH_DAY_EXTRA_WATER, 1) if day_offset == 0 else 0

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
