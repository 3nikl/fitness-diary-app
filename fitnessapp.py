import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from fpdf import FPDF

# ----------- Constants ------------

PASSCODE = "1512"
DATA_FILE = "fitness_diary_data.json"

# Food data with base units and nutrition info
FOOD_DATA = {
    # Meal 1
    "Oats": {"unit": "g", "base": 45, "cal": 170, "protein": 10, "carbs": 28, "fat": 0},
    "Whey Protein": {"unit": "g", "base": 34, "cal": 120, "protein": 25, "carbs": 2.5, "fat": 0},
    "Skim Milk Powder": {"unit": "g", "base": 40, "cal": 160, "protein": 16, "carbs": 18, "fat": 0},
    "PB Powder": {"unit": "g", "base": 16, "cal": 80, "protein": 7, "carbs": 6.2, "fat": 0},
    "Nuts": {"unit": "g", "base": 15, "cal": 95, "protein": 2, "carbs": 4, "fat": 9},
    # Meal 2
    "White Rice": {"unit": "g", "base": 150, "cal": 210, "protein": 5, "carbs": 72, "fat": 0.5},
    "Tomato": {"unit": "count", "cal": 20, "protein": 0, "carbs": 0, "fat": 0},
    "Onion": {"unit": "count", "cal": 35, "protein": 0, "carbs": 0, "fat": 0},
    "Yogurt": {"unit": "g", "base": 170, "cal": 90, "protein": 18, "carbs": 7, "fat": 0},
    "Tortilla": {"unit": "count", "cal": 70, "protein": 5, "carbs": 12, "fat": 2},
    "Soya Chunks": {"unit": "g", "base": 30, "cal": 140, "protein": 30, "carbs": 6, "fat": 1},
    # Meal 3
    "Whey Protein Shake": {"unit": "g", "base": 34, "cal": 120, "protein": 25, "carbs": 2, "fat": 0},
}

# Steps conversion
STEPS_PER_MILE = 1200
CAL_PER_MILE = 100


# ------------ Utility functions --------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def calculate_macros(food_inputs):
    """Calculate total macros from food input dict."""
    total = {"cal": 0, "protein": 0, "carbs": 0, "fat": 0}
    for food, qty in food_inputs.items():
        if qty is None or qty == 0:
            continue
        info = FOOD_DATA.get(food)
        if not info:
            continue
        if info["unit"] == "g":
            ratio = qty / info["base"]
            total["cal"] += info["cal"] * ratio
            total["protein"] += info["protein"] * ratio
            total["carbs"] += info["carbs"] * ratio
            total["fat"] += info["fat"] * ratio
        elif info["unit"] == "count":
            total["cal"] += info["cal"] * qty
            total["protein"] += info["protein"] * qty
            # carbs & fat are 0 for tomato/onion by design
    return total

def calculate_bmi(weight, height_cm):
    if weight <= 0 or height_cm <= 0:
        return None
    height_m = height_cm / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def steps_to_miles_calories(steps):
    miles = steps / STEPS_PER_MILE
    cal_burned = miles * CAL_PER_MILE
    return round(miles, 2), round(cal_burned, 1)

def get_today_date_str():
    return datetime.now().strftime("%Y-%m-%d")

def get_date_obj(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")

def generate_weekly_report(data, start_date, end_date):
    # Filter entries between start_date and end_date inclusive
    entries = [v for k, v in data.items() if start_date <= k <= end_date]
    if not entries:
        return None

    # Prepare summary data
    dates = []
    weights = []
    calories = []
    proteins = []
    net_calories = []
    bmis = []
    for e in entries:
        dates.append(e['date'])
        weights.append(e.get('weight', None))
        calories.append(e.get('total_calories', 0))
        proteins.append(e.get('total_protein', 0))
        net_calories.append(e.get('net_calories', 0))
        bmis.append(e.get('bmi', None))

    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(0, 10, "Weekly Fitness Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Week: {start_date} to {end_date}", ln=True)
    pdf.ln(5)

    # Summary table
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(30, 10, "Weight (kg)", 1)
    pdf.cell(40, 10, "Calories", 1)
    pdf.cell(30, 10, "Protein (g)", 1)
    pdf.cell(30, 10, "Net Cal", 1)
    pdf.cell(20, 10, "BMI", 1)
    pdf.ln()

    for i in range(len(dates)):
        pdf.cell(40, 10, dates[i], 1)
        pdf.cell(30, 10, str(weights[i]) if weights[i] else "-", 1)
        pdf.cell(40, 10, str(round(calories[i],1)) if calories[i] else "0", 1)
        pdf.cell(30, 10, str(round(proteins[i],1)) if proteins[i] else "0", 1)
        pdf.cell(30, 10, str(round(net_calories[i],1)) if net_calories[i] else "0", 1)
        pdf.cell(20, 10, str(bmis[i]) if bmis[i] else "-", 1)
        pdf.ln()

    # Save PDF temporarily
    filename = f"weekly_report_{start_date}_to_{end_date}.pdf"
    pdf.output(filename)
    return filename

def plot_trends(data, key, title, ylabel):
    dates = sorted(data.keys())
    values = [data[d].get(key, None) for d in dates]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, mode='lines+markers', name=title))
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title=ylabel, height=300)
    return fig

# ----------- Streamlit App -----------------

st.set_page_config(page_title="Advanced Fitness Diary", layout="wide")

# Password input
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Enter Passcode to Access Your Fitness Diary")
    password_input = st.text_input("Passcode", type="password")
    if st.button("Unlock"):
        if password_input == PASSCODE:
            st.session_state.authenticated = True
            import streamlit.runtime.scriptrunner.script_runner as script_runner
            raise script_runner.RerunException(script_runner.RerunData())
        else:
            st.error("Incorrect passcode!")
    st.stop()

# Load data
data = load_data()

st.sidebar.title("Fitness Diary")
page = st.sidebar.radio("Navigate", ["Enter Daily Data", "Weight & BMI", "History", "Weekly Report"])

# --- Date selector ---
if "selected_date" not in st.session_state:
    st.session_state.selected_date = get_today_date_str()

selected_date = st.sidebar.date_input("Select date", datetime.strptime(st.session_state.selected_date, "%Y-%m-%d"))
selected_date_str = selected_date.strftime("%Y-%m-%d")
st.session_state.selected_date = selected_date_str

# Helper to get or create entry for selected date
def get_entry(date_str):
    return data.get(date_str, {
        "date": date_str,
        "weight": None,
        "height": None,
        "age": None,
        "bmi": None,
        "steps": 0,
        "workout_notes": "",
        "food": {},
        "extra_food": [],
        "total_calories": 0,
        "total_protein": 0,
        "net_calories": 0,
    })

entry = get_entry(selected_date_str)

# ----- PAGE: Enter Daily Data -----
if page == "Enter Daily Data":
    st.header(f"Enter Daily Data for {selected_date_str}")

    # Meal inputs in collapsible sections
    with st.expander("Meal 1 (Oatmeal + Protein Combo)"):
        m1 = {}
        m1["Oats"] = st.number_input("Oats (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Oats", 0.0), key="m1_oats")
        m1["Whey Protein"] = st.number_input("Whey Protein (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Whey Protein", 0.0), key="m1_whey")
        m1["Skim Milk Powder"] = st.number_input("Skim Milk Powder (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Skim Milk Powder", 0.0), key="m1_skim")
        m1["PB Powder"] = st.number_input("Peanut Butter Powder (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("PB Powder", 0.0), key="m1_pb")
        m1["Nuts"] = st.number_input("Nuts (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Nuts", 0.0), key="m1_nuts")

    with st.expander("Meal 2 (Rice + Tofu + Yogurt + Others)"):
        m2 = {}
        m2["White Rice"] = st.number_input("White Rice (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("White Rice", 0.0), key="m2_rice")
        m2["Tomato"] = st.number_input("Tomatoes (count)", min_value=0, max_value=50, step=1, value=int(entry["food"].get("Tomato", 0)), key="m2_tomato")
        m2["Onion"] = st.number_input("Onions (count)", min_value=0, max_value=50, step=1, value=int(entry["food"].get("Onion", 0)), key="m2_onion")
        m2["Yogurt"] = st.number_input("Yogurt (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Yogurt", 0.0), key="m2_yogurt")
        m2["Tortilla"] = st.number_input("Tortillas (count)", min_value=0, max_value=10, step=1, value=int(entry["food"].get("Tortilla", 0)), key="m2_tortilla")
        m2["Soya Chunks"] = st.number_input("Soya Chunks (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Soya Chunks", 0.0), key="m2_soya")

    with st.expander("Meal 3 (Protein Shake)"):
        m3 = {}
        m3["Whey Protein Shake"] = st.number_input("Whey Protein Shake (grams)", min_value=0.0, max_value=1000.0, step=1.0, value=entry["food"].get("Whey Protein Shake", 0.0), key="m3_whey")

    with st.expander("Extra Foods (manual calories & protein input)"):
        extra_foods = entry.get("extra_food", [])
        extra_foods_count = len(extra_foods)
        new_extra_foods = []
        for i in range(extra_foods_count):
            c1, c2, c3 = st.columns([4, 2, 2])
            with c1:
                name = st.text_input(f"Extra food name #{i+1}", value=extra_foods[i].get("name", ""), key=f"extra_name_{i}")
            with c2:
                cal = st.number_input(f"Calories #{i+1}", min_value=0.0, max_value=5000.0, value=extra_foods[i].get("calories", 0.0), step=1.0, key=f"extra_cal_{i}")
            with c3:
                prot = st.number_input(f"Protein #{i+1}", min_value=0.0, max_value=500.0, value=extra_foods[i].get("protein", 0.0), step=0.1, key=f"extra_prot_{i}")
            new_extra_foods.append({"name": name, "calories": cal, "protein": prot})
        if st.button("Add Extra Food"):
            new_extra_foods.append({"name": "", "calories": 0.0, "protein": 0.0})
        extra_foods = new_extra_foods

    st.markdown("---")
    st.header("Other Inputs")
    weight = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, step=0.1, value=entry.get("weight", 70.0), key="weight_input")
    height = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, step=0.1, value=entry.get("height", 170.0), key="height_input")
    age = st.number_input("Age (years)", min_value=1, max_value=120, step=1, value=entry.get("age", 30), key="age_input")
    steps = st.number_input("Steps walked", min_value=0, max_value=100000, step=100, value=entry.get("steps", 0), key="steps_input")
    workout_notes = st.text_area("Workout notes", value=entry.get("workout_notes", ""), key="workout_notes")

    if st.button("Save Entry"):
        # Combine all food inputs
        combined_food = {}
        combined_food.update(m1)
        combined_food.update(m2)
        combined_food.update(m3)
        # Save all food inputs
        entry["food"] = combined_food
        entry["extra_food"] = extra_foods
        entry["weight"] = weight
        entry["height"] = height
        entry["age"] = age
        entry["steps"] = steps
        entry["workout_notes"] = workout_notes

        # Calculate BMI
        bmi = calculate_bmi(weight, height)
        entry["bmi"] = bmi

        # Calculate macros
        macros = calculate_macros(combined_food)
        # Add extra foods calories & protein
        extra_cal = sum(item.get("calories", 0) for item in extra_foods)
        extra_prot = sum(item.get("protein", 0) for item in extra_foods)

        total_calories = macros["cal"] + extra_cal
        total_protein = macros["protein"] + extra_prot

        # Steps to miles & calories burned
        miles, cal_burned = steps_to_miles_calories(steps)

        net_calories = total_calories - cal_burned

        entry["total_calories"] = round(total_calories, 1)
        entry["total_protein"] = round(total_protein, 1)
        entry["miles_walked"] = miles
        entry["calories_burned"] = round(cal_burned, 1)
        entry["net_calories"] = round(net_calories, 1)
        entry["date"] = selected_date_str

        # Save to data
        data[selected_date_str] = entry
        save_data(data)
        st.success(f"Entry saved for {selected_date_str}!")

# ----- PAGE: Weight & BMI -----
elif page == "Weight & BMI":
    st.header("Weight & BMI Tracker")

    if entry.get("weight") is not None:
        st.write(f"**Date:** {selected_date_str}")
        st.write(f"Weight: {entry['weight']} kg")
        st.write(f"Height: {entry['height']} cm")
        st.write(f"Age: {entry['age']} years")
        st.write(f"Calculated BMI: {entry.get('bmi', 'N/A')}")

    else:
        st.info("No weight data available for the selected date.")

# ----- PAGE: History -----
elif page == "History":
    st.header("History & Past Entries")

    if not data:
        st.info("No data saved yet.")
    else:
        # Show all dates saved, sorted descending
        dates_sorted = sorted(data.keys(), reverse=True)
        date_select = st.selectbox("Select Date to View/Edit", dates_sorted, index=dates_sorted.index(selected_date_str) if selected_date_str in dates_sorted else 0)

        entry_hist = data[date_select]

        st.subheader(f"Data for {date_select}")
        st.write("**Weight (kg):**", entry_hist.get("weight", "N/A"))
        st.write("**Height (cm):**", entry_hist.get("height", "N/A"))
        st.write("**Age:**", entry_hist.get("age", "N/A"))
        st.write("**BMI:**", entry_hist.get("bmi", "N/A"))
        st.write("**Steps:**", entry_hist.get("steps", 0))
        st.write("**Miles Walked:**", entry_hist.get("miles_walked", 0))
        st.write("**Calories Burned (steps):**", entry_hist.get("calories_burned", 0))
        st.write("**Workout Notes:**", entry_hist.get("workout_notes", ""))

        st.write("### Food Intake")
        food_hist = entry_hist.get("food", {})
        if food_hist:
            df_food = pd.DataFrame.from_dict(food_hist, orient='index', columns=['Quantity'])
            st.table(df_food)
        else:
            st.write("No food intake data.")

        st.write("### Extra Foods")
        extra_hist = entry_hist.get("extra_food", [])
        if extra_hist:
            df_extra = pd.DataFrame(extra_hist)
            st.table(df_extra)
        else:
            st.write("No extra foods data.")

# ----- PAGE: Weekly Report -----
elif page == "Weekly Report":
    st.header("Weekly Summary Report")
    st.write("This report summarizes your last 7 days of data with charts and totals.")

    if len(data) == 0:
        st.info("No data available to generate report.")
    else:
        today = datetime.now()
        seven_days_ago = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")

        # Filter data for last 7 days
        filtered_dates = sorted([d for d in data.keys() if seven_days_ago <= d <= today_str])

        if not filtered_dates:
            st.info("No data in last 7 days.")
        else:
            filtered_data = {d: data[d] for d in filtered_dates}

            # Plot weight trend
            weight_fig = plot_trends(filtered_data, "weight", "Weight (kg) over Last 7 Days", "Weight (kg)")
            st.plotly_chart(weight_fig, use_container_width=True)

            # Plot calories trend
            cal_fig = plot_trends(filtered_data, "total_calories", "Calories Intake over Last 7 Days", "Calories")
            st.plotly_chart(cal_fig, use_container_width=True)

            # Plot protein trend
            prot_fig = plot_trends(filtered_data, "total_protein", "Protein Intake over Last 7 Days", "Protein (g)")
            st.plotly_chart(prot_fig, use_container_width=True)

            # Plot net calories trend
            net_cal_fig = plot_trends(filtered_data, "net_calories", "Net Calories over Last 7 Days", "Calories")
            st.plotly_chart(net_cal_fig, use_container_width=True)

            # Show summary table
            st.write("### Summary Table (Last 7 Days)")
            df_report = pd.DataFrame.from_dict(filtered_data, orient='index')
            st.dataframe(df_report[["weight", "total_calories", "total_protein", "net_calories", "bmi"]])

            # Button to download PDF report
            if st.button("Download Weekly PDF Report"):
                start_date = filtered_dates[0]
                end_date = filtered_dates[-1]
                pdf_file = generate_weekly_report(data, start_date, end_date)
                if pdf_file:
                    with open(pdf_file, "rb") as f:
                        st.download_button(label="Download PDF", data=f, file_name=pdf_file, mime="application/pdf")
                else:
                    st.error("Failed to generate PDF report.")

