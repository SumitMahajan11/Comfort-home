"""
src/comfort/profile.py

User Comfort Profile and Questionnaire Engine.
Defines a comprehensive bilingual (English + Hindi) questionnaire schema
and maps practitioner/resident responses into structured user comfort profiles.

Honesty & Integrity Rule:
Never silently modifies the project's locked assumptions A-001..A-007.
Instead, operates in a clearly labeled 'user_override' mode that reuses
the same precomputed models and physics surrogates.
"""

from typing import Dict, Any, List, Optional

# 7-point ASHRAE thermal sensation scale mapped to 3-class target (D-003a)
SEVEN_POINT_SCALE = [
    {"value": -3, "label_en": "Cold (-3)", "label_hi": "बहुत ठंडा (-3)", "target_class": "cool"},
    {"value": -2, "label_en": "Cool (-2)", "label_hi": "ठंडा (-2)", "target_class": "cool"},
    {"value": -1, "label_en": "Slightly Cool (-1)", "label_hi": "हल्का ठंडा (-1)", "target_class": "cool"},
    {"value": 0, "label_en": "Neutral / Comfortable (0)", "label_hi": "आरामदायक / सामान्य (0)", "target_class": "neutral"},
    {"value": 1, "label_en": "Slightly Warm (+1)", "label_hi": "हल्का गर्म (+1)", "target_class": "warm"},
    {"value": 2, "label_en": "Warm (+2)", "label_hi": "गर्म (+2)", "target_class": "warm"},
    {"value": 3, "label_en": "Hot (+3)", "label_hi": "बहुत गर्म (+3)", "target_class": "warm"}
]

QUESTIONNAIRE_SCHEMA = {
    "version": "1.0.0",
    "description": "User Comfort Profile Questionnaire for ClimateAdapt-Comfort Decision Support",
    "questions": [
        {
            "id": "feel_summer",
            "number": 1,
            "title_en": "How do you usually feel in local buildings during summer?",
            "title_hi": "गर्मियों में स्थानीय इमारतों के अंदर आप आमतौर पर कैसा महसूस करते हैं?",
            "type": "select",
            "options": SEVEN_POINT_SCALE,
            "default": 2
        },
        {
            "id": "feel_winter",
            "number": 1,
            "title_en": "How do you usually feel in local buildings during winter?",
            "title_hi": "सर्दियों में स्थानीय इमारतों के अंदर आप आमतौर पर कैसा महसूस करते हैं?",
            "type": "select",
            "options": SEVEN_POINT_SCALE,
            "default": -1
        },
        {
            "id": "feel_monsoon",
            "number": 1,
            "title_en": "How do you usually feel in local buildings during the humid monsoon?",
            "title_hi": "मानसून / उमस के मौसम में आप आमतौर पर कैसा महसूस करते हैं?",
            "type": "select",
            "options": SEVEN_POINT_SCALE,
            "default": 1
        },
        {
            "id": "sensitivity",
            "number": 2,
            "title_en": "Which condition is more bothersome to you?",
            "title_hi": "आपके लिए कौन सा मौसम अधिक कष्टदायक या असहज है?",
            "type": "radio",
            "options": [
                {
                    "value": "heat_sensitive",
                    "label_en": "Excessive heat / stuffiness is much worse",
                    "label_hi": "अत्यधिक गर्मी और उमस बहुत अधिक परेशान करती है",
                    "warm_penalty": 1.35,
                    "cool_penalty": 0.75
                },
                {
                    "value": "balanced",
                    "label_en": "Heat and cold are equally bothersome",
                    "label_hi": "गर्मी और सर्दी दोनों समान रूप से परेशान करते हैं",
                    "warm_penalty": 1.0,
                    "cool_penalty": 1.0
                },
                {
                    "value": "cold_sensitive",
                    "label_en": "Cold drafts and chills are much worse",
                    "label_hi": "ठंड और शीतलहर बहुत अधिक परेशान करती है",
                    "warm_penalty": 0.75,
                    "cool_penalty": 1.35
                }
            ],
            "default": "heat_sensitive"
        },
        {
            "id": "clothing_summer",
            "number": 3,
            "title_en": "Usual indoor clothing in summer",
            "title_hi": "गर्मियों में सामान्य घरेलू पोशाक",
            "type": "select",
            "options": [
                {"value": "light", "clo": 0.45, "label_en": "Light shorts / thin cotton saree (0.45 clo)", "label_hi": "सूती हल्के कपड़े / हल्की साड़ी (0.45 clo)"},
                {"value": "normal", "clo": 0.60, "label_en": "Standard trousers & half-sleeve shirt (0.60 clo)", "label_hi": "सामान्य पैंट एवं हाफ शर्ट (0.60 clo)"},
                {"value": "heavy", "clo": 0.85, "label_en": "Formal clothing / multiple layers (0.85 clo)", "label_hi": "औपचारिक पूरे कपड़े / कई परतें (0.85 clo)"}
            ],
            "default": "light"
        },
        {
            "id": "clothing_winter",
            "number": 3,
            "title_en": "Usual indoor clothing in winter",
            "title_hi": "सर्दियों में सामान्य घरेलू पोशाक",
            "type": "select",
            "options": [
                {"value": "light", "clo": 0.75, "label_en": "Light full shirt / light shawl (0.75 clo)", "label_hi": "हल्की पूरी आस्तीन की कमीज / शॉल (0.75 clo)"},
                {"value": "normal", "clo": 1.00, "label_en": "Woolen sweater / cardigan (1.00 clo)", "label_hi": "ऊनी स्वेटर / कार्डिगन (1.00 clo)"},
                {"value": "heavy", "clo": 1.35, "label_en": "Heavy thermal innerwear + thick jacket (1.35 clo)", "label_hi": "थर्मल इनर + भारी जैकेट (1.35 clo)"}
            ],
            "default": "normal"
        },
        {
            "id": "activity_level",
            "number": 3,
            "title_en": "Primary indoor activity level",
            "title_hi": "घर के अंदर मुख्य गतिविधि स्तर",
            "type": "select",
            "options": [
                {"value": "sedentary", "met": 1.0, "label_en": "Seated resting / reading / desk work (1.0 met)", "label_hi": "बैठे रहना / पढ़ना / डेस्क कार्य (1.0 met)"},
                {"value": "light_active", "met": 1.2, "label_en": "Light domestic activity / walking around (1.2 met)", "label_hi": "हल्का घरेलू कार्य / चलना-फिरना (1.2 met)"},
                {"value": "moderate", "met": 1.6, "label_en": "Active housework / cooking / physical exercise (1.6 met)", "label_hi": "सक्रिय रसोई कार्य / शारीरिक व्यायाम (1.6 met)"}
            ],
            "default": "light_active"
        },
        {
            "id": "hours_occupied",
            "number": 3,
            "title_en": "Daily hours occupied in the building",
            "title_hi": "प्रतिदिन इमारत के अंदर बिताए जाने वाले घंटे",
            "type": "number",
            "min": 4,
            "max": 24,
            "default": 18
        },
        {
            "id": "cooling_equipment",
            "number": 4,
            "title_en": "Cooling / heating equipment available",
            "title_hi": "उपलब्ध शीतलन / हीटिंग उपकरण",
            "type": "radio",
            "options": [
                {"value": "none", "label_en": "No mechanical cooling (natural ventilation only)", "label_hi": "कोई उपकरण नहीं (केवल प्राकृतिक हवा)"},
                {"value": "fan", "label_en": "Ceiling / table fans only", "label_hi": "केवल छत या टेबल पंखा"},
                {"value": "cooler", "label_en": "Evaporative desert cooler + fans", "label_hi": "कूलर एवं पंखे"},
                {"value": "ac", "label_en": "Air conditioner (AC) available", "label_hi": "एयर कंडीशनर (AC) उपलब्ध"}
            ],
            "default": "fan"
        },
        {
            "id": "cooling_willingness",
            "number": 4,
            "title_en": "Willingness to run mechanical cooling (electricity bill tolerance)",
            "title_hi": "उपकरण चलाने की इच्छा (बिजली बिल सहनशीलता)",
            "type": "radio",
            "options": [
                {"value": "minimal", "label_en": "Minimal / avoid electricity costs whenever possible", "label_hi": "न्यूनतम / बिजली का बिल जितना संभव हो बचाना"},
                {"value": "moderate", "label_en": "Moderate / run during extreme afternoon or night hours", "label_hi": "मध्यम / केवल दोपहर की तेज गर्मी या रात में चलाना"},
                {"value": "frequent", "label_en": "Frequent / comfort is priority over electricity bills", "label_hi": "नियमित / बिजली बिल की तुलना में आराम प्राथमिकता है"}
            ],
            "default": "moderate"
        },
        {
            "id": "priorities",
            "number": 5,
            "title_en": "Design Priorities (Weights must sum to 100%)",
            "title_hi": "डिजाइन प्राथमिकताएं (कुल योग 100% होना चाहिए)",
            "type": "slider_group",
            "defaults": {
                "weight_comfort": 50,
                "weight_energy": 30,
                "weight_cost": 20
            }
        },
        {
            "id": "special_needs",
            "number": 6,
            "title_en": "Special occupant considerations",
            "title_hi": "विशेष पारिवारिक या स्वास्थ्य आवश्यकताएं",
            "type": "multiselect",
            "options": [
                {"value": "elderly", "label_en": "Elderly family members (higher cold/draft sensitivity)", "label_hi": "बुजुर्ग सदस्य (ठंड व तेज हवा के प्रति संवेदनशील)"},
                {"value": "infants", "label_en": "Infants or young children (narrower comfort band)", "label_hi": "छोटे बच्चे (संकीर्ण तापमान सहिष्णुता)"},
                {"value": "work_from_home", "label_en": "Occupants work from home full-time (continuous afternoon occupancy)", "label_hi": "घर से काम (दोपहर में निरंतर उपस्थिति)"}
            ],
            "default": []
        }
    ]
}

def map_tsv_to_target_class(tsv_value: int) -> str:
    """Maps 7-point ASHRAE scale (-3 to +3) to discrete class (cool, neutral, warm)."""
    if tsv_value < -0.5:
        return "cool"
    elif tsv_value > 0.5:
        return "warm"
    return "neutral"

def build_user_comfort_profile(responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses questionnaire responses into a validated User Comfort Profile.
    Outputs structured parameters and clearly labeled 'user_override' weights.

    Args:
        responses: dictionary containing answers matching QUESTIONNAIRE_SCHEMA

    Returns:
        Structured user profile dictionary
    """
    # 1. Seasonal feel
    feel_summer = int(responses.get("feel_summer", 2))
    feel_winter = int(responses.get("feel_winter", -1))
    feel_monsoon = int(responses.get("feel_monsoon", 1))

    # 2. Sensitivity factors
    sensitivity_key = str(responses.get("sensitivity", "heat_sensitive"))
    if sensitivity_key == "cold_sensitive":
        w_warm = 0.75
        w_cool = 1.35
    elif sensitivity_key == "balanced":
        w_warm = 1.0
        w_cool = 1.0
    else: # heat_sensitive (default)
        w_warm = 1.35
        w_cool = 0.75

    # 3. Special needs adjustment
    special_needs = list(responses.get("special_needs", []))
    if "elderly" in special_needs:
        w_cool += 0.20 # elderly require higher heating protection
    if "infants" in special_needs:
        w_warm += 0.15
        w_cool += 0.15

    # 4. Clothing and activity
    clo_summer_map = {"light": 0.45, "normal": 0.60, "heavy": 0.85}
    clo_winter_map = {"light": 0.75, "normal": 1.00, "heavy": 1.35}
    met_map = {"sedentary": 1.0, "light_active": 1.2, "moderate": 1.6}

    clothing_s_key = str(responses.get("clothing_summer", "light"))
    clothing_w_key = str(responses.get("clothing_winter", "normal"))
    activity_key = str(responses.get("activity_level", "light_active"))

    user_clo_summer = clo_summer_map.get(clothing_s_key, 0.45)
    user_clo_winter = clo_winter_map.get(clothing_w_key, 1.00)
    user_met = met_map.get(activity_key, 1.2)

    # Occupied hours
    base_hours = float(responses.get("hours_occupied", 18.0))
    if "work_from_home" in special_needs:
        base_hours = max(base_hours, 22.0)
    user_occupied_hours = min(24.0, max(4.0, base_hours))

    # 5. Priorities
    raw_p = responses.get("priorities", {})
    w_comf = float(raw_p.get("weight_comfort", 50.0))
    w_eng = float(raw_p.get("weight_energy", 30.0))
    w_cst = float(raw_p.get("weight_cost", 20.0))
    total_w = (w_comf + w_eng + w_cst) or 100.0

    norm_w_comf = w_comf / total_w
    norm_w_eng = w_eng / total_w
    norm_w_cst = w_cst / total_w

    return {
        "status": "VALID_PROFILE",
        "user_overrides_active": True,
        "note": "User overrides are applied strictly to the post-hoc Comfort Fit Score evaluation. Locked project assumptions A-001..A-007 are preserved in simulation baselines.",
        "seasonal_feel": {
            "summer": {
                "tsv_raw": feel_summer,
                "target_class": map_tsv_to_target_class(feel_summer)
            },
            "winter": {
                "tsv_raw": feel_winter,
                "target_class": map_tsv_to_target_class(feel_winter)
            },
            "monsoon": {
                "tsv_raw": feel_monsoon,
                "target_class": map_tsv_to_target_class(feel_monsoon)
            }
        },
        "sensitivity": {
            "profile_key": sensitivity_key,
            "warm_discomfort_penalty": round(w_warm, 2),
            "cool_discomfort_penalty": round(w_cool, 2)
        },
        "user_model_inputs": {
            "user_clo_summer": user_clo_summer,
            "user_clo_winter": user_clo_winter,
            "user_met": user_met,
            "user_occupied_hours_per_day": user_occupied_hours
        },
        "equipment": {
            "cooling_type": responses.get("cooling_equipment", "fan"),
            "willingness": responses.get("cooling_willingness", "moderate")
        },
        "normalized_weights": {
            "weight_comfort": round(norm_w_comf, 3),
            "weight_energy": round(norm_w_eng, 3),
            "weight_cost": round(norm_w_cst, 3)
        },
        "special_needs_flags": special_needs
    }
