import { LanguageCode } from "@/types";

export interface TranslationDictionary {
  appName: string;
  appSubtitle: string;
  tagline: string;
  disclaimerSimulation: string;
  disclaimerCost: string;
  simpleMode: string;
  expertMode: string;
  futureClimateToggle: string;
  futureClimateActiveNote: string;
  langSwitch: string;
  printReport: string;
  
  // Steps
  step1Title: string;
  step1Desc: string;
  step2Title: string;
  step2Desc: string;
  step3Title: string;
  step3Desc: string;
  step4Title: string;
  step4Desc: string;
  step5Title: string;
  step5Desc: string;

  // Step 1: Location
  selectCityPrompt: string;
  searchPlaceholder: string;
  searchBtn: string;
  nearestMatchWarning: string;
  distanceKm: string;
  simulatedStationsOnly: string;

  // Step 2: Climate Data
  climateZone: string;
  confidenceTier: string;
  adaptiveValidity: string;
  db2EnvelopePct: string;
  reasonsAndCaveats: string;

  // Step 3: Questionnaire
  buildingTypeLabel: string;
  bldgHouse: string;
  bldgApartment: string;
  bldgCommercial: string;
  usuallyFeelLabel: string;
  feelTooHot: string;
  feelAboutRight: string;
  feelTooCold: string;
  dailyOccupancyLabel: string;
  hoursPerDay: string;
  existingCoolingLabel: string;
  coolingNone: string;
  coolingFan: string;
  coolingAC: string;
  clothingHabitsLabel: string;
  clothingLight: string;
  clothingNormal: string;
  clothingHeavy: string;
  priorityLabel: string;
  priorityBudget: string;
  priorityBalanced: string;
  priorityComfort: string;
  typicalAreaAverageBadge: string;
  evaluatePackagesBtn: string;

  // Step 4: Comparison & Fit Score
  comfortFitScore: string;
  scoreExcellent: string;
  scoreGood: string;
  scoreModerate: string;
  userNeedsVsAreaAverage: string;
  yourPreference: string;
  areaSurveyAverage: string;

  // Step 5: Packages
  packagesHeading: string;
  packageBudget: string;
  packageBalanced: string;
  packageBestComfort: string;
  envelopeMaterials: string;
  costBreakdown: string;
  costScheduleSource: string;
  annualDiscomfortHours: string;
  annualEnergyDemand: string;
  comfortGain: string;
  energyReduction: string;
  monthlyPerformanceChart: string;
  outdoorTemp: string;
  baselineTemp: string;
  passiveTemp: string;
  viewDetails: string;
  exportPdf: string;
}

export const TRANSLATIONS: Record<LanguageCode, TranslationDictionary> = {
  en: {
    appName: "Plan my shelter",
    appSubtitle: "Passive Shelter Decision-Support System",
    tagline: "Evidence-gated passive building envelopes for Indian climate zones",
    disclaimerSimulation: "Simulation-based estimate, not a measured result or a construction quote.",
    disclaimerCost: "Rough indicative ranges from CPWD Delhi Schedule of Rates (DSR 2021) with ±15% regional variance. For academic decision-support only; never present as an official contractor quote or tender.",
    simpleMode: "Simple Mode",
    expertMode: "Expert Physics Mode",
    futureClimateToggle: "Future-Climate (+1.5°C Warmer)",
    futureClimateActiveNote: "Scenario: +1.5°C mean warming applied across all 8,760 hours.",
    langSwitch: "हिंदी",
    printReport: "Export Builder PDF",

    // Steps
    step1Title: "1. Select Location",
    step1Desc: "Pick one of the 5 simulated reference stations or search any Indian location.",
    step2Title: "2. Climate & Comfort Profile",
    step2Desc: "Precomputed EnergyPlus climate characteristics and empirical DB II comfort boundary.",
    step3Title: "3. Occupant Comfort Questionnaire",
    step3Desc: "Specify building type and comfort habits alongside verified typical-area averages.",
    step4Title: "4. Area Comparison & Comfort Fit Score",
    step4Desc: "Deterministic score (0–100) calibrating your envelope fit against regional norms.",
    step5Title: "5. Passive Packages & CPWD DSR Costs",
    step5Desc: "Precomputed Pareto envelope specifications, itemized DSR rates, and 12-month performance.",

    // Step 1
    selectCityPrompt: "Choose one of 5 simulated climate stations:",
    searchPlaceholder: "Search city or state",
    searchBtn: "Match Nearest Station",
    nearestMatchWarning: "Nearest Simulated Climate Station",
    distanceKm: "km away",
    simulatedStationsOnly: "Only 5 representative stations have been simulated in EnergyPlus. Other locations match to the nearest station with explicit distance tracking.",

    // Step 2
    climateZone: "Climate Zone",
    confidenceTier: "Confidence Tier",
    adaptiveValidity: "Adaptive 90% Validity",
    db2EnvelopePct: "ASHRAE DB II Coverage",
    reasonsAndCaveats: "Confidence Basis & Research Caveat",

    // Step 3
    buildingTypeLabel: "Building Typology",
    bldgHouse: "Detached House (Single Zone)",
    bldgApartment: "Apartment (Intermediate Floor)",
    bldgCommercial: "Small Commercial / Office",
    usuallyFeelLabel: "How does your indoor space usually feel?",
    feelTooHot: "Too hot & stuffy",
    feelAboutRight: "About right / comfortable",
    feelTooCold: "Too chilly & cold",
    dailyOccupancyLabel: "Daily Occupancy Duration",
    hoursPerDay: "hours/day",
    existingCoolingLabel: "Existing Cooling Available",
    coolingNone: "No active cooling (free-running)",
    coolingFan: "Ceiling fan only",
    coolingAC: "Air Conditioner (intermittent/regular)",
    clothingHabitsLabel: "Typical Indoor Clothing",
    clothingLight: "Light breathable cotton (0.5 clo)",
    clothingNormal: "Standard everyday casual (0.7 clo)",
    clothingHeavy: "Warm layers / woolens (1.0 clo)",
    priorityLabel: "Design Optimization Priority",
    priorityBudget: "Lowest Energy Interventions",
    priorityBalanced: "Balanced (Cost vs Comfort Knee-Point)",
    priorityComfort: "Maximum Comfort (Minimum Discomfort Hours)",
    typicalAreaAverageBadge: "Regional Area Average",
    evaluatePackagesBtn: "Compute Comfort Fit & Generate Packages",

    // Step 4
    comfortFitScore: "Comfort Fit Score",
    scoreExcellent: "High Passive Potential",
    scoreGood: "Balanced Passive Suitability",
    scoreModerate: "Challenging Thermal Regime",
    userNeedsVsAreaAverage: "Your Needs vs Typical Regional Profile",
    yourPreference: "Your Input",
    areaSurveyAverage: "Regional Baseline",

    // Step 5
    packagesHeading: "Recommended Passive Envelope Packages",
    packageBudget: "Lowest energy",
    packageBalanced: "Balanced",
    packageBestComfort: "Lowest discomfort",
    envelopeMaterials: "Bill of Materials & Specifications",
    costBreakdown: "CPWD DSR 2021 Estimated Cost Range",
    costScheduleSource: "Based on official CPWD Delhi Schedule of Rates (DSR 2021)",
    annualDiscomfortHours: "Discomfort Hours",
    annualEnergyDemand: "HVAC Energy Burden",
    comfortGain: "Comfort Gain vs Baseline",
    energyReduction: "Energy Reduction",
    monthlyPerformanceChart: "12-Month Indoor vs Outdoor Temperature Profile (°C)",
    outdoorTemp: "Outdoor Ambient",
    baselineTemp: "Uninsulated Baseline (R2)",
    passiveTemp: "Recommended Passive Package",
    viewDetails: "View Full Envelope Details",
    exportPdf: "Download Builder-Ready PDF Spec"
  },
  hi: {
    appName: "अपने शेल्टर की योजना बनाएं",
    appSubtitle: "पैसिव भवन डिज़ाइन निर्णय-समर्थन प्रणाली",
    tagline: "भारतीय जलवायु क्षेत्रों के लिए साक्ष्य-आधारित पैसिव भवन आवरण",
    disclaimerSimulation: "यह सिमुलेशन-आधारित अनुमान है, कोई मापा गया परिणाम या निर्माण उद्धरण (कोटेशन) नहीं।",
    disclaimerCost: "सीपीडब्ल्यूडी दिल्ली दर अनुसूची (डीएसआर 2021) के अनुसार अनुमानित दरें (±15% क्षेत्रीय भिन्नता)। केवल शैक्षणिक निर्णय-समर्थन हेतु; इसे कभी भी आधिकारिक ठेकेदार का कोटेशन न मानें।",
    simpleMode: "सरल मोड",
    expertMode: "विशेषज्ञ भौतिकी मोड",
    futureClimateToggle: "भविष्य की जलवायु (+1.5°C अधिक गर्म)",
    futureClimateActiveNote: "परिदृश्य: पूरे 8,760 घंटों में +1.5°C औसत तापमान वृद्धि लागू।",
    langSwitch: "English",
    printReport: "बिल्डर PDF डाउनलोड",

    // Steps
    step1Title: "1. स्थान का चयन",
    step1Desc: "5 सिमुलेटेड संदर्भ स्टेशनों में से चुनें या भारत के किसी भी स्थान को खोजें।",
    step2Title: "2. जलवायु एवं कम्फर्ट प्रोफाइल",
    step2Desc: "एनर्जीप्लस जलवायु विशेषताएं एवं अनुभवजन्य DB II कम्फर्ट सीमा।",
    step3Title: "3. अधिभोगी कम्फर्ट प्रश्नावली",
    step3Desc: "क्षेत्रीय औसत के साथ अपने भवन का प्रकार और कम्फर्ट आवश्यकताएं बताएं।",
    step4Title: "4. क्षेत्रीय तुलना एवं कम्फर्ट फिट स्कोर",
    step4Desc: "निश्चयात्मक स्कोर (0–100) जो क्षेत्रीय मानकों के अनुरूप आपके भवन आवरण का आकलन करता है।",
    step5Title: "5. पैसिव पैकेज एवं सीपीडब्ल्यूडी लागत",
    step5Desc: "पूर्व-गणना किए गए परेतो डिज़ाइन, सीपीडब्ल्यूडी दरें और 12 महीने का प्रदर्शन।",

    // Step 1
    selectCityPrompt: "5 सिमुलेटेड जलवायु स्टेशनों में से एक चुनें:",
    searchPlaceholder: "शहर या राज्य खोजें",
    searchBtn: "निकटतम स्टेशन खोजें",
    nearestMatchWarning: "निकटतम सिमुलेटेड जलवायु स्टेशन",
    distanceKm: "किमी दूर",
    simulatedStationsOnly: "एनर्जीप्लस में केवल 5 प्रतिनिधि स्टेशनों का सिमुलेशन किया गया है। अन्य स्थान निकटतम स्टेशन से मेल खाते हैं।",

    // Step 2
    climateZone: "जलवायु क्षेत्र",
    confidenceTier: "विश्वसनीयता स्तर (Confidence Tier)",
    adaptiveValidity: "अडैप्टिव 90% वैधता",
    db2EnvelopePct: "ASHRAE DB II कवरेज",
    reasonsAndCaveats: "विश्वसनीयता का आधार एवं शोध चेतावनी",

    // Step 3
    buildingTypeLabel: "भवन का प्रकार (Typology)",
    bldgHouse: "स्वतंत्र घर (सिंगल ज़ोन)",
    bldgApartment: "अपार्टमेंट (मध्यम तल)",
    bldgCommercial: "छोटा व्यावसायिक / कार्यालय",
    usuallyFeelLabel: "अंदर का तापमान सामान्यतः कैसा महसूस होता है?",
    feelTooHot: "बहुत अधिक गर्म एवं उमस भरा",
    feelAboutRight: "बिल्कुल ठीक / आरामदायक",
    feelTooCold: "बहुत ठंडा एवं ठिठुरन भरा",
    dailyOccupancyLabel: "दैनिक उपयोग की अवधि",
    hoursPerDay: "घंटे/दिन",
    existingCoolingLabel: "उपलब्ध कूलिंग सुविधा",
    coolingNone: "कोई कूलिंग नहीं (प्राकृतिक हवा)",
    coolingFan: "केवल छत का पंखा",
    coolingAC: "एयर कंडीशनर (एसी)",
    clothingHabitsLabel: "घर के अंदर पहने जाने वाले कपड़े",
    clothingLight: "हल्के सूती कपड़े (0.5 clo)",
    clothingNormal: "सामान्य कैजुअल कपड़े (0.7 clo)",
    clothingHeavy: "गर्म ऊनी कपड़े (1.0 clo)",
    priorityLabel: "डिज़ाइन प्राथमिकता",
    priorityBudget: "न्यूनतम ऊर्जा (Lowest Energy)",
    priorityBalanced: "संतुलित (लागत बनाम कम्फर्ट)",
    priorityComfort: "अधिकतम कम्फर्ट (न्यूनतम असुविधा घंटे)",
    typicalAreaAverageBadge: "क्षेत्रीय औसत",
    evaluatePackagesBtn: "कम्फर्ट फिट गणना करें और पैकेज प्राप्त करें",

    // Step 4
    comfortFitScore: "कम्फर्ट फिट स्कोर",
    scoreExcellent: "उत्कृष्ट पैसिव क्षमता",
    scoreGood: "संतुलित पैसिव उपयुक्तता",
    scoreModerate: "चुनौतीपूर्ण तापीय स्थिति",
    userNeedsVsAreaAverage: "आपकी आवश्यकता बनाम क्षेत्रीय औसत प्रोफाइल",
    yourPreference: "आपकी पसंद",
    areaSurveyAverage: "क्षेत्रीय आधारभूत आंकड़ा",

    // Step 5
    packagesHeading: "अनुशंसित पैसिव भवन पैकेज",
    packageBudget: "न्यूनतम ऊर्जा (Lowest energy)",
    packageBalanced: "संतुलित (Balanced)",
    packageBestComfort: "न्यूनतम असुविधा (Lowest discomfort)",
    envelopeMaterials: "सामग्री सूची एवं तकनीकी विनिर्देश",
    costBreakdown: "सीपीडब्ल्यूडी डीएसआर 2021 अनुमानित लागत सीमा",
    costScheduleSource: "आधिकारिक सीपीडब्ल्यूडी दिल्ली दर अनुसूची (DSR 2021) पर आधारित",
    annualDiscomfortHours: "असुविधा के घंटे",
    annualEnergyDemand: "एचवीएसी ऊर्जा भार",
    comfortGain: "कम्फर्ट में सुधार (बेसलाइन की तुलना में)",
    energyReduction: "ऊर्जा की बचत",
    monthlyPerformanceChart: "12 महीने का आंतरिक बनाम बाह्य तापमान प्रोफाइल (°C)",
    outdoorTemp: "बाहरी तापमान",
    baselineTemp: "असंरक्षित बेसलाइन (R2)",
    passiveTemp: "अनुशंसित पैसिव पैकेज",
    viewDetails: "विस्तृत विवरण देखें",
    exportPdf: "बिल्डर PDF विनिर्देश डाउनलोड करें"
  }
};
