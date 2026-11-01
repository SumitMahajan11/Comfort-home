"""
src/app/answer_mapping.py

Simple, transparent rule-based mapping from questionnaire responses
to multi-objective optimization weights (O1_ml, O1_adapt, O2).
All mappings are plain dictionary lookups with one comment per line.
No machine learning or complex models.
"""

from typing import Dict, Any

# 1. Base weights determined by user's primary priority
PRIORITY_BASE_WEIGHTS = {
    # Heavy focus on thermal comfort; minimal weight on active energy
    "comfort": {"w_ml": 0.45, "w_adapt": 0.45, "w_o2": 0.10},
    # Heavy focus on minimizing heating/cooling energy demand
    "low energy": {"w_ml": 0.20, "w_adapt": 0.20, "w_o2": 0.60},
    # Balanced compromise between occupant comfort and energy demand
    "balanced": {"w_ml": 0.35, "w_adapt": 0.35, "w_o2": 0.30},
}

# 2. Adjustments based on how occupant usually feels
FEEL_ADJUSTMENTS = {
    # Feeling too hot shifts weight to ML model (sensitive to daytime radiant heat)
    "too hot": {"w_ml": +0.08, "w_adapt": -0.04, "w_o2": -0.04},
    # Feeling too cold shifts weight to adaptive model (sensitive to cold winter temps)
    "too cold": {"w_ml": -0.04, "w_adapt": +0.08, "w_o2": -0.04},
    # Balanced thermal sensation maintains current distribution
    "about right": {"w_ml": 0.00, "w_adapt": 0.00, "w_o2": 0.00},
}

# 3. Adjustments based on primary room usage
USE_ADJUSTMENTS = {
    # Sleeping requires overnight thermal comfort stability
    "sleeping": {"w_ml": -0.02, "w_adapt": +0.04, "w_o2": -0.02},
    # Working involves daytime metabolic heat and productivity focus
    "working": {"w_ml": +0.04, "w_adapt": -0.02, "w_o2": -0.02},
    # Cooking creates internal heat gains, prioritizing warm discomfort reduction
    "cooking": {"w_ml": +0.05, "w_adapt": -0.02, "w_o2": -0.03},
    # Mixed usage across day and night
    "mixed": {"w_ml": 0.00, "w_adapt": 0.00, "w_o2": 0.00},
}

# 4. Adjustments based on summer clothing habits
SUMMER_CLOTHING_ADJUSTMENTS = {
    # Light clothing aids heat dissipation; standard sensitivity
    "light": {"w_ml": 0.00, "w_adapt": 0.00, "w_o2": 0.00},
    # Normal clothing baseline
    "normal": {"w_ml": +0.02, "w_adapt": 0.00, "w_o2": -0.02},
    # Heavy clothing increases warm discomfort sensitivity
    "heavy": {"w_ml": +0.05, "w_adapt": 0.00, "w_o2": -0.05},
}

# 5. Adjustments based on winter clothing habits
WINTER_CLOTHING_ADJUSTMENTS = {
    # Light winter clothing makes occupant feel cold sooner; boost cold sensitivity
    "light": {"w_ml": 0.00, "w_adapt": +0.05, "w_o2": -0.05},
    # Normal winter clothing baseline
    "normal": {"w_ml": 0.00, "w_adapt": +0.02, "w_o2": -0.02},
    # Heavy winter clothing provides good passive warmth
    "heavy": {"w_ml": 0.00, "w_adapt": 0.00, "w_o2": 0.00},
}

# 6. Adjustments based on active cooling availability (Fan / AC)
COOLING_EQUIPMENT_ADJUSTMENTS = {
    # Purely passive shelter: comfort is entirely dependent on building envelope
    "none": {"w_ml": +0.05, "w_adapt": +0.05, "w_o2": -0.10},
    # Ceiling/table fan provides air movement; slight comfort support
    "fan": {"w_ml": 0.00, "w_adapt": 0.00, "w_o2": 0.00},
    # Active AC present: energy demand and operating cost become more significant
    "AC": {"w_ml": -0.05, "w_adapt": -0.05, "w_o2": +0.10},
}

def map_answers_to_weights(answers: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes normalized objective weights (O1_ml, O1_adapt, O2) from user responses.
    
    Parameters:
        answers: dict with keys:
            - priority: 'comfort' | 'low energy' | 'balanced'
            - usually_feel: 'too hot' | 'too cold' | 'about right'
            - main_use: 'sleeping' | 'working' | 'cooking' | 'mixed'
            - hours_occupied: int between 1 and 24
            - summer_clothing: 'light' | 'normal' | 'heavy'
            - winter_clothing: 'light' | 'normal' | 'heavy'
            - has_fan_ac: 'none' | 'fan' | 'AC'
            
    Returns:
        Dict with 'O1_ml', 'O1_adapt', 'O2' summing to 1.0.
    """
    priority = answers.get("priority", "balanced").lower()
    feel = answers.get("usually_feel", "about right").lower()
    use = answers.get("main_use", "mixed").lower()
    hours = float(answers.get("hours_occupied", 24))
    summer_clo = answers.get("summer_clothing", "light").lower()
    winter_clo = answers.get("winter_clothing", "normal").lower()
    cooling = answers.get("has_fan_ac", "none")
    if cooling.upper() == "AC":
        cooling = "AC"
    else:
        cooling = cooling.lower()

    # 1. Base weights from Priority
    base = PRIORITY_BASE_WEIGHTS.get(priority, PRIORITY_BASE_WEIGHTS["balanced"])
    w_ml = base["w_ml"]
    w_adapt = base["w_adapt"]
    w_o2 = base["w_o2"]

    # 2. Feel adjustment
    adj_feel = FEEL_ADJUSTMENTS.get(feel, FEEL_ADJUSTMENTS["about right"])
    w_ml += adj_feel["w_ml"]
    w_adapt += adj_feel["w_adapt"]
    w_o2 += adj_feel["w_o2"]

    # 3. Usage adjustment
    adj_use = USE_ADJUSTMENTS.get(use, USE_ADJUSTMENTS["mixed"])
    w_ml += adj_use["w_ml"]
    w_adapt += adj_use["w_adapt"]
    w_o2 += adj_use["w_o2"]

    # 4. Hours occupied adjustment (more occupied hours = greater value of comfort)
    if hours >= 18:
        w_ml += 0.03
        w_adapt += 0.03
        w_o2 -= 0.06
    elif hours <= 8:
        w_ml -= 0.03
        w_adapt -= 0.03
        w_o2 += 0.06

    # 5. Clothing adjustments
    adj_sum = SUMMER_CLOTHING_ADJUSTMENTS.get(summer_clo, SUMMER_CLOTHING_ADJUSTMENTS["light"])
    w_ml += adj_sum["w_ml"]
    w_adapt += adj_sum["w_adapt"]
    w_o2 += adj_sum["w_o2"]

    adj_win = WINTER_CLOTHING_ADJUSTMENTS.get(winter_clo, WINTER_CLOTHING_ADJUSTMENTS["normal"])
    w_ml += adj_win["w_ml"]
    w_adapt += adj_win["w_adapt"]
    w_o2 += adj_win["w_o2"]

    # 6. Equipment adjustment
    adj_cool = COOLING_EQUIPMENT_ADJUSTMENTS.get(cooling, COOLING_EQUIPMENT_ADJUSTMENTS["none"])
    w_ml += adj_cool["w_ml"]
    w_adapt += adj_cool["w_adapt"]
    w_o2 += adj_cool["w_o2"]

    # Ensure strictly positive weights
    w_ml = max(0.05, w_ml)
    w_adapt = max(0.05, w_adapt)
    w_o2 = max(0.05, w_o2)

    # Normalize to 1.0
    total = w_ml + w_adapt + w_o2
    return {
        "O1_ml": round(w_ml / total, 4),
        "O1_adapt": round(w_adapt / total, 4),
        "O2": round(w_o2 / total, 4)
    }
