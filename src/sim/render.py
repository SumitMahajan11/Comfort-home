"""
IDF Template Generator and Renderer for ClimateAdapt-Comfort.
Generates fully validated EnergyPlus 26.2.0 building models across 4 building types:
- shelter_v1: single-zone passive shelter (20 m2, baseline)
- house: 3-zone detached house (60 m2, living/bedroom/kitchen)
- apartment: 2-zone apartment unit (55 m2, floor_position: ground, middle, top)
- commercial: 2-zone small office (80 m2, open office + meeting, weekday 09:00-18:00)

Parametrized by the 8 standard design variables:
- roof_insulation_thickness (m, 0.0 to 0.15)
- wall_insulation_thickness (m, 0.0 to 0.15)
- wall_mass_class ('light', 'medium', 'heavy')
- roof_solar_absorptance (0.3 to 0.9)
- wwr (0.05 to 0.40)
- orientation (0 to 359 degrees)
- shading_depth (m, 0.0 to 1.0)
- ventilation_ach (ACH, 1.0 to 15.0)
- mode ('free_running' or 'ideal_loads')
- floor_position ('ground', 'middle', 'top' - for apartment)
"""

import os

def _get_common_materials_idf(wall_mass_class, wall_ins_thick, roof_ins_thick, roof_abs):
    """Generates standard material and construction IDF definitions."""
    if wall_mass_class == 'heavy':
        wall_core_mat = 'HeavyConcrete_200mm'
    elif wall_mass_class == 'light':
        wall_core_mat = 'LightTimber_100mm'
    else:  # medium
        wall_core_mat = 'MediumBrick_200mm'

    return f"""!- ============================================================================
!- MATERIALS & CONSTRUCTIONS
!- ============================================================================

Material,
  HeavyConcrete_200mm,     !- Name
  Rough,                   !- Roughness
  0.200,                   !- Thickness {{m}}
  1.311,                   !- Conductivity {{W/m-K}}
  2240,                    !- Density {{kg/m3}}
  837;                     !- Specific Heat {{J/kg-K}}

Material,
  MediumBrick_200mm,       !- Name
  Rough,                   !- Roughness
  0.200,                   !- Thickness {{m}}
  0.890,                   !- Conductivity {{W/m-K}}
  1920,                    !- Density {{kg/m3}}
  790;                     !- Specific Heat {{J/kg-K}}

Material,
  LightTimber_100mm,       !- Name
  Smooth,                  !- Roughness
  0.100,                   !- Thickness {{m}}
  0.160,                   !- Conductivity {{W/m-K}}
  600,                     !- Density {{kg/m3}}
  1000;                    !- Specific Heat {{J/kg-K}}

Material,
  Wall_Insulation,         !- Name
  VerySmooth,              !- Roughness
  {wall_ins_thick:.4f},    !- Thickness {{m}}
  0.038,                   !- Conductivity {{W/m-K}}
  30,                      !- Density {{kg/m3}}
  1200;                    !- Specific Heat {{J/kg-K}}

Material,
  Plaster_15mm,            !- Name
  Smooth,                  !- Roughness
  0.015,                   !- Thickness {{m}}
  0.720,                   !- Conductivity {{W/m-K}}
  1600,                    !- Density {{kg/m3}}
  840;                     !- Specific Heat {{J/kg-K}}

Material,
  Roof_Concrete_100mm,     !- Name
  Rough,                   !- Roughness
  0.100,                   !- Thickness {{m}}
  1.130,                   !- Conductivity {{W/m-K}}
  2000,                    !- Density {{kg/m3}}
  1000;                    !- Specific Heat {{J/kg-K}}

Material,
  Roof_Insulation,         !- Name
  VerySmooth,              !- Roughness
  {roof_ins_thick:.4f},    !- Thickness {{m}}
  0.038,                   !- Conductivity {{W/m-K}}
  30,                      !- Density {{kg/m3}}
  1200;                    !- Specific Heat {{J/kg-K}}

Material,
  Roof_Outer_Finish,       !- Name
  Rough,                   !- Roughness
  0.010,                   !- Thickness {{m}}
  0.800,                   !- Conductivity {{W/m-K}}
  1800,                    !- Density {{kg/m3}}
  900,                     !- Specific Heat {{J/kg-K}}
  0.90,                    !- Thermal Absorptance
  {roof_abs:.2f},          !- Solar Absorptance
  0.90;                    !- Visible Absorptance

Material,
  Floor_Concrete_150mm,    !- Name
  Rough,                   !- Roughness
  0.150,                   !- Thickness {{m}}
  1.311,                   !- Conductivity {{W/m-K}}
  2240,                    !- Density {{kg/m3}}
  837;                     !- Specific Heat {{J/kg-K}}

Material,
  Partition_Gypsum_12mm,   !- Name
  Smooth,                  !- Roughness
  0.012,                   !- Thickness {{m}}
  0.160,                   !- Conductivity {{W/m-K}}
  800,                     !- Density {{kg/m3}}
  1090;                    !- Specific Heat {{J/kg-K}}

WindowMaterial:Glazing,
  Clear_6mm_Glass,         !- Name
  SpectralAverage,         !- Optical Data Type
  ,                        !- Window Glass Spectral Data Set Name
  0.006,                   !- Thickness {{m}}
  0.78,                    !- Solar Transmittance at Normal Incidence
  0.07,                    !- Front Side Solar Reflectance at Normal Incidence
  0.07,                    !- Back Side Solar Reflectance at Normal Incidence
  0.88,                    !- Visible Transmittance at Normal Incidence
  0.08,                    !- Front Side Visible Reflectance at Normal Incidence
  0.08,                    !- Back Side Visible Reflectance at Normal Incidence
  0.0,                     !- Infrared Transmittance at Normal Incidence
  0.84,                    !- Front Side Infrared Hemispherical Emissivity
  0.84,                    !- Back Side Infrared Hemispherical Emissivity
  0.90;                    !- Conductivity {{W/m-K}}

Construction,
  Exterior_Wall_Construction,
  Plaster_15mm,
  {wall_core_mat},
  Wall_Insulation,
  Plaster_15mm;

Construction,
  Roof_Construction,
  Roof_Outer_Finish,
  Roof_Insulation,
  Roof_Concrete_100mm,
  Plaster_15mm;

Construction,
  Floor_Construction,
  Floor_Concrete_150mm;

Construction,
  Adiabatic_Partition_Construction,
  Plaster_15mm,
  MediumBrick_200mm,
  Plaster_15mm;

Construction,
  Interior_Partition_Construction,
  Partition_Gypsum_12mm,
  Plaster_15mm,
  Partition_Gypsum_12mm;

Construction,
  Window_Construction,
  Clear_6mm_Glass;
"""

def _get_ideal_loads_hvac_idf(zone_name):
    """Generates IdealLoadsAirSystem and DualSetpoint thermostat for a zone."""
    return f"""
ZoneHVAC:IdealLoadsAirSystem,
  {zone_name}_IdealLoads,
  ,
  {zone_name}_ZoneAirInletNode,
  ,
  ,
  50,
  13,
  0.0156,
  0.0077,
  NoLimit,
  ,
  ,
  NoLimit,
  ,
  ,
  ,
  ,
  ConstantSensibleHeatRatio,
  0.7,
  None,
  ,
  ,
  None,
  NoEconomizer,
  None,
  0.7,
  0.65;

ZoneHVAC:EquipmentList,
  {zone_name}_Equipment,
  SequentialLoad,
  ZoneHVAC:IdealLoadsAirSystem,
  {zone_name}_IdealLoads,
  1,
  1,
  ,
  ;

ZoneHVAC:EquipmentConnections,
  {zone_name},
  {zone_name}_Equipment,
  {zone_name}_ZoneInletNodes,
  ,
  {zone_name}_ZoneAirNode,
  {zone_name}_ZoneReturnNode;

NodeList,
  {zone_name}_ZoneInletNodes,
  {zone_name}_ZoneAirInletNode;

ThermostatSetpoint:DualSetpoint,
  {zone_name}_DualSetpoint,
  Heating_Setpoint_Schedule,
  Cooling_Setpoint_Schedule;

ZoneControl:Thermostat,
  {zone_name}_Thermostat,
  {zone_name},
  Zone_Control_Type_Sched,
  ThermostatSetpoint:DualSetpoint,
  {zone_name}_DualSetpoint;
"""

def _get_run_period_idf(run_period_days):
    if run_period_days is not None:
        sm, sd, em, ed = run_period_days
        return f"""
RunPeriod,
  Custom_Period,           !- Name
  {sm},                    !- Begin Month
  {sd},                    !- Begin Day of Month
  ,                        !- Begin Year
  {em},                    !- End Month
  {ed},                    !- End Day of Month
  ,                        !- End Year
  Tuesday,                 !- Day of Week for Start Day
  Yes,                     !- Use Weather File Holidays and Special Days
  Yes,                     !- Use Weather File Daylight Saving Period
  No,                      !- Apply Weekend Holiday Rule
  Yes,                     !- Use Weather File Rain Indicators
  Yes;                     !- Use Weather File Snow Indicators
"""
    return """
RunPeriod,
  Annual,                  !- Name
  1,                       !- Begin Month
  1,                       !- Begin Day of Month
  ,                        !- Begin Year
  12,                      !- End Month
  31,                      !- End Day of Month
  ,                        !- End Year
  Tuesday,                 !- Day of Week for Start Day
  Yes,                     !- Use Weather File Holidays and Special Days
  Yes,                     !- Use Weather File Daylight Saving Period
  No,                      !- Apply Weekend Holiday Rule
  Yes,                     !- Use Weather File Rain Indicators
  Yes;                     !- Use Weather File Snow Indicators
"""


def render_building_idf(
    params,
    output_idf_path,
    building_type='shelter_v1',
    mode='free_running',
    run_period_days=None,
    floor_position='middle'
):
    """
    Renders a parametrized EnergyPlus 26.2.0 IDF file.
    Supports building_type in ['shelter_v1', 'house', 'apartment', 'commercial'].
    """
    roof_ins_thick = max(0.001, float(params.get('roof_insulation_thickness', 0.0)))
    wall_ins_thick = max(0.001, float(params.get('wall_insulation_thickness', 0.0)))
    wall_mass = str(params.get('wall_mass_class', 'medium')).lower()
    roof_abs = float(params.get('roof_solar_absorptance', 0.7))
    wwr = min(0.50, max(0.05, float(params.get('wwr', 0.20))))
    orientation = float(params.get('orientation', 0.0))
    shading_depth = float(params.get('shading_depth', 0.0))
    vent_ach = max(0.5, float(params.get('ventilation_ach', 5.0)))
    
    # Header & SimulationControl
    run_period_str = _get_run_period_idf(run_period_days)
    materials_str = _get_common_materials_idf(wall_mass, wall_ins_thick, roof_ins_thick, roof_abs)
    
    header = f"""!- EnergyPlus Parametric Model ({building_type})
!- ClimateAdapt-Comfort Automated Model Pipeline
Version, 26.2;

SimulationControl,
  No,                      !- Do Zone Sizing Calculation
  No,                      !- Do System Sizing Calculation
  No,                      !- Do Plant Sizing Calculation
  No,                      !- Run Simulation for Sizing Periods
  Yes,                     !- Run Simulation for Weather File Run Periods
  No;                      !- Do HVAC System Sizing Simulation for Sizing Periods

Building,
  Building_{building_type},!- Name
  {orientation:.1f},       !- North Axis {{deg}}
  Suburbs,                 !- Terrain
  0.04,                    !- Loads Convergence Tolerance Value {{W}}
  0.4,                     !- Temperature Convergence Tolerance Value {{deltaC}}
  FullExterior,            !- Solar Distribution
  25,                      !- Maximum Number of Warmup Days
  6;                       !- Minimum Number of Warmup Days

GlobalGeometryRules,
  UpperLeftCorner,         !- Starting Vertex Position
  Counterclockwise,        !- Vertex Entry Direction
  Relative,                !- Coordinate System
  Relative,                !- Daylighting Reference Point Coordinate System
  Relative;                !- Rectangular Surface Coordinate System

ShadowCalculation,
  PolygonClipping,         !- Shading Calculation Method
  Periodic,                !- Shading Calculation Update Frequency Method
  20;                      !- Shading Calculation Update Frequency {{days}}

SurfaceConvectionAlgorithm:Inside, TARP;
SurfaceConvectionAlgorithm:Outside, DOE-2;
HeatBalanceAlgorithm, ConductionTransferFunction;
Timestep, 4;

{run_period_str}

ScheduleTypeLimits, AnyNumber;
ScheduleTypeLimits, Fraction, 0.0, 1.0, Continuous;
ScheduleTypeLimits, Temperature, -60.0, 200.0, Continuous;
ScheduleTypeLimits, Control_Type, 0, 4, Discrete;

Schedule:Constant, Always_On, Fraction, 1.0;
Schedule:Constant, Heating_Setpoint_Schedule, Temperature, 20.0;
Schedule:Constant, Cooling_Setpoint_Schedule, Temperature, 26.0;
Schedule:Constant, Zone_Control_Type_Sched, Control_Type, 4;

{materials_str}
"""

    outputs_str = """
!- ============================================================================
!- OUTPUT VARIABLES (Hourly)
!- ============================================================================
Output:Variable, *, Zone Mean Air Temperature, Hourly;
Output:Variable, *, Zone Mean Radiant Temperature, Hourly;
Output:Variable, *, Zone Air Relative Humidity, Hourly;
Output:Variable, *, Site Outdoor Air Drybulb Temperature, Hourly;
Output:Variable, *, Zone Ideal Loads Zone Total Heating Rate, Hourly;
Output:Variable, *, Zone Ideal Loads Zone Total Cooling Rate, Hourly;
Output:Table:SummaryReports, AllSummary;
OutputControl:Table:Style, Comma;
"""

    # Build geometry and systems based on building_type
    if building_type == 'shelter_v1':
        # 5m x 4m x 3m single-zone
        win_h = 1.2
        win_w_5m = min(4.6, max(0.4, (15.0 * wwr) / win_h))
        x_start_5m = (5.0 - win_w_5m) / 2.0
        x_end_5m = x_start_5m + win_w_5m
        z_win_bottom = 0.9
        z_win_top = z_win_bottom + win_h
        
        shading_str = ""
        if shading_depth > 0.02:
            shading_str = f"""
Shading:Overhang, SouthWindow_Overhang, South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, NorthWindow_Overhang, North_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
"""
        hvac_str = _get_ideal_loads_hvac_idf("Main_Zone") if mode == 'ideal_loads' else ""
        
        body = f"""
Zone, Main_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 60.0;

BuildingSurface:Detailed, Floor_Surface, Floor, Floor_Construction, Main_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  0.0, 0.0, 0.0,  0.0, 4.0, 0.0,  5.0, 4.0, 0.0,  5.0, 0.0, 0.0;

BuildingSurface:Detailed, Roof_Surface, Roof, Roof_Construction, Main_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  0.0, 4.0, 3.0,  0.0, 0.0, 3.0,  5.0, 0.0, 3.0,  5.0, 4.0, 3.0;

BuildingSurface:Detailed, South_Wall, Wall, Exterior_Wall_Construction, Main_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 0.0, 3.0,  0.0, 0.0, 0.0,  5.0, 0.0, 0.0,  5.0, 0.0, 3.0;

FenestrationSurface:Detailed, South_Window, Window, Window_Construction, South_Wall, , 0.5, , 1.0, 4,
  {x_start_5m:.3f}, 0.0, {z_win_top:.3f},
  {x_start_5m:.3f}, 0.0, {z_win_bottom:.3f},
  {x_end_5m:.3f}, 0.0, {z_win_bottom:.3f},
  {x_end_5m:.3f}, 0.0, {z_win_top:.3f};

BuildingSurface:Detailed, North_Wall, Wall, Exterior_Wall_Construction, Main_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  5.0, 4.0, 3.0,  5.0, 4.0, 0.0,  0.0, 4.0, 0.0,  0.0, 4.0, 3.0;

FenestrationSurface:Detailed, North_Window, Window, Window_Construction, North_Wall, , 0.5, , 1.0, 4,
  {5.0 - x_start_5m:.3f}, 4.0, {z_win_top:.3f},
  {5.0 - x_start_5m:.3f}, 4.0, {z_win_bottom:.3f},
  {5.0 - x_end_5m:.3f}, 4.0, {z_win_bottom:.3f},
  {5.0 - x_end_5m:.3f}, 4.0, {z_win_top:.3f};

BuildingSurface:Detailed, East_Wall, Wall, Exterior_Wall_Construction, Main_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  5.0, 0.0, 3.0,  5.0, 0.0, 0.0,  5.0, 4.0, 0.0,  5.0, 4.0, 3.0;

BuildingSurface:Detailed, West_Wall, Wall, Exterior_Wall_Construction, Main_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 4.0, 3.0,  0.0, 4.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 3.0;

{shading_str}

People, Shelter_Occupants, Main_Zone, Always_On, People, 2.0, , , 0.3, , Shelter_Activity_Sched;
Schedule:Constant, Shelter_Activity_Sched, AnyNumber, 125.0;

ZoneVentilation:DesignFlowRate, Natural_Ventilation, Main_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;
ZoneInfiltration:DesignFlowRate, Infiltration_0p5ACH, Main_Zone, Always_On, AirChanges/Hour, , , , 0.5;

{hvac_str}
"""

    elif building_type == 'house':
        # 3 Zones: Living (36m2), Bedroom (14m2), Kitchen (10m2) = 60 m2
        # Living South wall 6m x 3m = 18 m2
        # Bedroom South wall 4m x 3m = 12 m2
        # Living North wall 6m x 3m = 18 m2
        # Kitchen North wall 4m x 3m = 12 m2
        win_h = 1.2
        win_w_liv = min(5.4, max(0.4, (18.0 * wwr) / win_h))
        x_start_liv_s = (6.0 - win_w_liv) / 2.0
        x_end_liv_s = x_start_liv_s + win_w_liv
        
        win_w_bed = min(3.6, max(0.4, (12.0 * wwr) / win_h))
        x_start_bed_s = 6.0 + (4.0 - win_w_bed) / 2.0
        x_end_bed_s = x_start_bed_s + win_w_bed

        win_w_kit = min(3.6, max(0.4, (12.0 * wwr) / win_h))
        x_start_kit_n = 6.0 + (4.0 - win_w_kit) / 2.0
        x_end_kit_n = x_start_kit_n + win_w_kit

        z_b = 0.9
        z_t = z_b + win_h

        shading_str = ""
        if shading_depth > 0.02:
            shading_str = f"""
Shading:Overhang, Living_South_Overhang, Living_South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, Bedroom_South_Overhang, Bedroom_South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, Living_North_Overhang, Living_North_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, Kitchen_North_Overhang, Kitchen_North_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
"""
        hvac_str = ""
        if mode == 'ideal_loads':
            hvac_str = _get_ideal_loads_hvac_idf("Living_Zone") + \
                       _get_ideal_loads_hvac_idf("Bedroom_Zone") + \
                       _get_ideal_loads_hvac_idf("Kitchen_Zone")

        body = f"""
Zone, Living_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 108.0;
Zone, Bedroom_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 42.0;
Zone, Kitchen_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 30.0;

BuildingSurface:Detailed, Living_Floor, Floor, Floor_Construction, Living_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  0.0, 0.0, 0.0,  0.0, 6.0, 0.0,  6.0, 6.0, 0.0,  6.0, 0.0, 0.0;
BuildingSurface:Detailed, Bedroom_Floor, Floor, Floor_Construction, Bedroom_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  6.0, 0.0, 0.0,  6.0, 3.5, 0.0,  10.0, 3.5, 0.0,  10.0, 0.0, 0.0;
BuildingSurface:Detailed, Kitchen_Floor, Floor, Floor_Construction, Kitchen_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  6.0, 3.5, 0.0,  6.0, 6.0, 0.0,  10.0, 6.0, 0.0,  10.0, 3.5, 0.0;

BuildingSurface:Detailed, Living_Roof, Roof, Roof_Construction, Living_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  0.0, 6.0, 3.0,  0.0, 0.0, 3.0,  6.0, 0.0, 3.0,  6.0, 6.0, 3.0;
BuildingSurface:Detailed, Bedroom_Roof, Roof, Roof_Construction, Bedroom_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  6.0, 3.5, 3.0,  6.0, 0.0, 3.0,  10.0, 0.0, 3.0,  10.0, 3.5, 3.0;
BuildingSurface:Detailed, Kitchen_Roof, Roof, Roof_Construction, Kitchen_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  6.0, 6.0, 3.0,  6.0, 3.5, 3.0,  10.0, 3.5, 3.0,  10.0, 6.0, 3.0;

BuildingSurface:Detailed, Living_South_Wall, Wall, Exterior_Wall_Construction, Living_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 0.0, 3.0,  0.0, 0.0, 0.0,  6.0, 0.0, 0.0,  6.0, 0.0, 3.0;
FenestrationSurface:Detailed, Living_South_Window, Window, Window_Construction, Living_South_Wall, , 0.5, , 1.0, 4,
  {x_start_liv_s:.3f}, 0.0, {z_t:.3f},  {x_start_liv_s:.3f}, 0.0, {z_b:.3f},  {x_end_liv_s:.3f}, 0.0, {z_b:.3f},  {x_end_liv_s:.3f}, 0.0, {z_t:.3f};

BuildingSurface:Detailed, Bedroom_South_Wall, Wall, Exterior_Wall_Construction, Bedroom_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  6.0, 0.0, 3.0,  6.0, 0.0, 0.0,  10.0, 0.0, 0.0,  10.0, 0.0, 3.0;
FenestrationSurface:Detailed, Bedroom_South_Window, Window, Window_Construction, Bedroom_South_Wall, , 0.5, , 1.0, 4,
  {x_start_bed_s:.3f}, 0.0, {z_t:.3f},  {x_start_bed_s:.3f}, 0.0, {z_b:.3f},  {x_end_bed_s:.3f}, 0.0, {z_b:.3f},  {x_end_bed_s:.3f}, 0.0, {z_t:.3f};

BuildingSurface:Detailed, Living_North_Wall, Wall, Exterior_Wall_Construction, Living_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  6.0, 6.0, 3.0,  6.0, 6.0, 0.0,  0.0, 6.0, 0.0,  0.0, 6.0, 3.0;
FenestrationSurface:Detailed, Living_North_Window, Window, Window_Construction, Living_North_Wall, , 0.5, , 1.0, 4,
  {6.0 - x_start_liv_s:.3f}, 6.0, {z_t:.3f},  {6.0 - x_start_liv_s:.3f}, 6.0, {z_b:.3f},  {6.0 - x_end_liv_s:.3f}, 6.0, {z_b:.3f},  {6.0 - x_end_liv_s:.3f}, 6.0, {z_t:.3f};

BuildingSurface:Detailed, Kitchen_North_Wall, Wall, Exterior_Wall_Construction, Kitchen_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 6.0, 3.0,  10.0, 6.0, 0.0,  6.0, 6.0, 0.0,  6.0, 6.0, 3.0;
FenestrationSurface:Detailed, Kitchen_North_Window, Window, Window_Construction, Kitchen_North_Wall, , 0.5, , 1.0, 4,
  {16.0 - x_start_kit_n:.3f}, 6.0, {z_t:.3f},  {16.0 - x_start_kit_n:.3f}, 6.0, {z_b:.3f},  {16.0 - x_end_kit_n:.3f}, 6.0, {z_b:.3f},  {16.0 - x_end_kit_n:.3f}, 6.0, {z_t:.3f};

BuildingSurface:Detailed, Bedroom_East_Wall, Wall, Exterior_Wall_Construction, Bedroom_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 0.0, 3.0,  10.0, 0.0, 0.0,  10.0, 3.5, 0.0,  10.0, 3.5, 3.0;
BuildingSurface:Detailed, Kitchen_East_Wall, Wall, Exterior_Wall_Construction, Kitchen_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 3.5, 3.0,  10.0, 3.5, 0.0,  10.0, 6.0, 0.0,  10.0, 6.0, 3.0;
BuildingSurface:Detailed, Living_West_Wall, Wall, Exterior_Wall_Construction, Living_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 6.0, 3.0,  0.0, 6.0, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 3.0;

BuildingSurface:Detailed, Living_Bed_Part_Living, Wall, Interior_Partition_Construction, Living_Zone, , Surface, Living_Bed_Part_Bed, NoSun, NoWind, 0.0, 4,
  6.0, 3.5, 3.0,  6.0, 3.5, 0.0,  6.0, 0.0, 0.0,  6.0, 0.0, 3.0;
BuildingSurface:Detailed, Living_Bed_Part_Bed, Wall, Interior_Partition_Construction, Bedroom_Zone, , Surface, Living_Bed_Part_Living, NoSun, NoWind, 0.0, 4,
  6.0, 0.0, 3.0,  6.0, 0.0, 0.0,  6.0, 3.5, 0.0,  6.0, 3.5, 3.0;

BuildingSurface:Detailed, Living_Kit_Part_Living, Wall, Interior_Partition_Construction, Living_Zone, , Surface, Living_Kit_Part_Kit, NoSun, NoWind, 0.0, 4,
  6.0, 6.0, 3.0,  6.0, 6.0, 0.0,  6.0, 3.5, 0.0,  6.0, 3.5, 3.0;
BuildingSurface:Detailed, Living_Kit_Part_Kit, Wall, Interior_Partition_Construction, Kitchen_Zone, , Surface, Living_Kit_Part_Living, NoSun, NoWind, 0.0, 4,
  6.0, 3.5, 3.0,  6.0, 3.5, 0.0,  6.0, 6.0, 0.0,  6.0, 6.0, 3.0;

BuildingSurface:Detailed, Bed_Kit_Part_Bed, Wall, Interior_Partition_Construction, Bedroom_Zone, , Surface, Bed_Kit_Part_Kit, NoSun, NoWind, 0.0, 4,
  10.0, 3.5, 3.0,  10.0, 3.5, 0.0,  6.0, 3.5, 0.0,  6.0, 3.5, 3.0;
BuildingSurface:Detailed, Bed_Kit_Part_Kit, Wall, Interior_Partition_Construction, Kitchen_Zone, , Surface, Bed_Kit_Part_Bed, NoSun, NoWind, 0.0, 4,
  6.0, 3.5, 3.0,  6.0, 3.5, 0.0,  10.0, 3.5, 0.0,  10.0, 3.5, 3.0;

{shading_str}

People, Living_Occupants, Living_Zone, Always_On, People, 2.0, , , 0.3, , House_Activity_Sched;
People, Bedroom_Occupants, Bedroom_Zone, Always_On, People, 2.0, , , 0.3, , House_Activity_Sched;
Schedule:Constant, House_Activity_Sched, AnyNumber, 125.0;

ZoneVentilation:DesignFlowRate, Living_Ventilation, Living_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;
ZoneVentilation:DesignFlowRate, Bed_Ventilation, Bedroom_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;
ZoneVentilation:DesignFlowRate, Kit_Ventilation, Kitchen_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;

ZoneInfiltration:DesignFlowRate, Living_Infiltration, Living_Zone, Always_On, AirChanges/Hour, , , , 0.5;
ZoneInfiltration:DesignFlowRate, Bed_Infiltration, Bedroom_Zone, Always_On, AirChanges/Hour, , , , 0.5;
ZoneInfiltration:DesignFlowRate, Kit_Infiltration, Kitchen_Zone, Always_On, AirChanges/Hour, , , , 0.5;

{hvac_str}
"""

    elif building_type == 'apartment':
        # 2 Zones: Apt_Living (33m2: 6x5.5), Apt_Bedroom (22m2: 4x5.5) = 55 m2
        # South and East walls: exterior. North and West walls: adiabatic party walls.
        # Floor position: 'ground', 'middle', 'top'
        pos = floor_position.lower()
        if pos == 'top':
            roof_bc = "Outdoors"
            roof_sun = "SunExposed"
            roof_wind = "WindExposed"
            roof_constr = "Roof_Construction"
            floor_bc = "Adiabatic"
        elif pos == 'ground':
            roof_bc = "Adiabatic"
            roof_sun = "NoSun"
            roof_wind = "NoWind"
            roof_constr = "Adiabatic_Partition_Construction"
            floor_bc = "Ground"
        else:  # middle
            roof_bc = "Adiabatic"
            roof_sun = "NoSun"
            roof_wind = "NoWind"
            roof_constr = "Adiabatic_Partition_Construction"
            floor_bc = "Adiabatic"

        win_h = 1.2
        win_w_liv = min(5.4, max(0.4, (18.0 * wwr) / win_h))
        x_s_liv = (6.0 - win_w_liv) / 2.0
        x_e_liv = x_s_liv + win_w_liv

        win_w_bed = min(3.6, max(0.4, (12.0 * wwr) / win_h))
        x_s_bed = 6.0 + (4.0 - win_w_bed) / 2.0
        x_e_bed = x_s_bed + win_w_bed

        z_b = 0.9
        z_t = z_b + win_h

        shading_str = ""
        if shading_depth > 0.02:
            shading_str = f"""
Shading:Overhang, Apt_Liv_South_Overhang, Apt_Liv_South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, Apt_Bed_South_Overhang, Apt_Bed_South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
"""
        hvac_str = ""
        if mode == 'ideal_loads':
            hvac_str = _get_ideal_loads_hvac_idf("Apt_Living_Zone") + \
                       _get_ideal_loads_hvac_idf("Apt_Bedroom_Zone")

        body = f"""
Zone, Apt_Living_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 99.0;
Zone, Apt_Bedroom_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.0, 66.0;

BuildingSurface:Detailed, Apt_Living_Floor, Floor, Floor_Construction, Apt_Living_Zone, , {floor_bc}, , NoSun, NoWind, 0.0, 4,
  0.0, 0.0, 0.0,  0.0, 5.5, 0.0,  6.0, 5.5, 0.0,  6.0, 0.0, 0.0;
BuildingSurface:Detailed, Apt_Bedroom_Floor, Floor, Floor_Construction, Apt_Bedroom_Zone, , {floor_bc}, , NoSun, NoWind, 0.0, 4,
  6.0, 0.0, 0.0,  6.0, 5.5, 0.0,  10.0, 5.5, 0.0,  10.0, 0.0, 0.0;

BuildingSurface:Detailed, Apt_Living_Roof, Roof, {roof_constr}, Apt_Living_Zone, , {roof_bc}, , {roof_sun}, {roof_wind}, 0.0, 4,
  0.0, 5.5, 3.0,  0.0, 0.0, 3.0,  6.0, 0.0, 3.0,  6.0, 5.5, 3.0;
BuildingSurface:Detailed, Apt_Bedroom_Roof, Roof, {roof_constr}, Apt_Bedroom_Zone, , {roof_bc}, , {roof_sun}, {roof_wind}, 0.0, 4,
  6.0, 5.5, 3.0,  6.0, 0.0, 3.0,  10.0, 0.0, 3.0,  10.0, 5.5, 3.0;

BuildingSurface:Detailed, Apt_Liv_South_Wall, Wall, Exterior_Wall_Construction, Apt_Living_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 0.0, 3.0,  0.0, 0.0, 0.0,  6.0, 0.0, 0.0,  6.0, 0.0, 3.0;
FenestrationSurface:Detailed, Apt_Liv_South_Window, Window, Window_Construction, Apt_Liv_South_Wall, , 0.5, , 1.0, 4,
  {x_s_liv:.3f}, 0.0, {z_t:.3f},  {x_s_liv:.3f}, 0.0, {z_b:.3f},  {x_e_liv:.3f}, 0.0, {z_b:.3f},  {x_e_liv:.3f}, 0.0, {z_t:.3f};

BuildingSurface:Detailed, Apt_Bed_South_Wall, Wall, Exterior_Wall_Construction, Apt_Bedroom_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  6.0, 0.0, 3.0,  6.0, 0.0, 0.0,  10.0, 0.0, 0.0,  10.0, 0.0, 3.0;
FenestrationSurface:Detailed, Apt_Bed_South_Window, Window, Window_Construction, Apt_Bed_South_Wall, , 0.5, , 1.0, 4,
  {x_s_bed:.3f}, 0.0, {z_t:.3f},  {x_s_bed:.3f}, 0.0, {z_b:.3f},  {x_e_bed:.3f}, 0.0, {z_b:.3f},  {x_e_bed:.3f}, 0.0, {z_t:.3f};

BuildingSurface:Detailed, Apt_Bed_East_Wall, Wall, Exterior_Wall_Construction, Apt_Bedroom_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 0.0, 3.0,  10.0, 0.0, 0.0,  10.0, 5.5, 0.0,  10.0, 5.5, 3.0;

BuildingSurface:Detailed, Apt_Liv_North_Wall, Wall, Adiabatic_Partition_Construction, Apt_Living_Zone, , Adiabatic, , NoSun, NoWind, 0.0, 4,
  6.0, 5.5, 3.0,  6.0, 5.5, 0.0,  0.0, 5.5, 0.0,  0.0, 5.5, 3.0;
BuildingSurface:Detailed, Apt_Bed_North_Wall, Wall, Adiabatic_Partition_Construction, Apt_Bedroom_Zone, , Adiabatic, , NoSun, NoWind, 0.0, 4,
  10.0, 5.5, 3.0,  10.0, 5.5, 0.0,  6.0, 5.5, 0.0,  6.0, 5.5, 3.0;

BuildingSurface:Detailed, Apt_Liv_West_Wall, Wall, Adiabatic_Partition_Construction, Apt_Living_Zone, , Adiabatic, , NoSun, NoWind, 0.0, 4,
  0.0, 5.5, 3.0,  0.0, 5.5, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 3.0;

BuildingSurface:Detailed, Apt_Liv_Bed_Part_Liv, Wall, Interior_Partition_Construction, Apt_Living_Zone, , Surface, Apt_Liv_Bed_Part_Bed, NoSun, NoWind, 0.0, 4,
  6.0, 5.5, 3.0,  6.0, 5.5, 0.0,  6.0, 0.0, 0.0,  6.0, 0.0, 3.0;
BuildingSurface:Detailed, Apt_Liv_Bed_Part_Bed, Wall, Interior_Partition_Construction, Apt_Bedroom_Zone, , Surface, Apt_Liv_Bed_Part_Liv, NoSun, NoWind, 0.0, 4,
  6.0, 0.0, 3.0,  6.0, 0.0, 0.0,  6.0, 5.5, 0.0,  6.0, 5.5, 3.0;

{shading_str}

People, Apt_Living_Occupants, Apt_Living_Zone, Always_On, People, 2.0, , , 0.3, , Apt_Activity_Sched;
People, Apt_Bedroom_Occupants, Apt_Bedroom_Zone, Always_On, People, 2.0, , , 0.3, , Apt_Activity_Sched;
Schedule:Constant, Apt_Activity_Sched, AnyNumber, 125.0;

ZoneVentilation:DesignFlowRate, Apt_Liv_Ventilation, Apt_Living_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;
ZoneVentilation:DesignFlowRate, Apt_Bed_Ventilation, Apt_Bedroom_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;

ZoneInfiltration:DesignFlowRate, Apt_Liv_Infiltration, Apt_Living_Zone, Always_On, AirChanges/Hour, , , , 0.5;
ZoneInfiltration:DesignFlowRate, Apt_Bed_Infiltration, Apt_Bedroom_Zone, Always_On, AirChanges/Hour, , , , 0.5;

{hvac_str}
"""

    elif building_type == 'commercial':
        # 2 Zones: Open_Office (55m2: 10x5.5), Meeting_Room (25m2: 10x2.5) = 80 m2, Height 3.2m
        # Commercial Occupancy, Lighting & Equipment Schedules per A-008, A-009, A-010, A-011
        win_h = 1.4
        win_w_s = min(9.0, max(0.5, (32.0 * wwr) / win_h))
        x_s = (10.0 - win_w_s) / 2.0
        x_e = x_s + win_w_s
        z_b = 0.9
        z_t = z_b + win_h

        shading_str = ""
        if shading_depth > 0.02:
            shading_str = f"""
Shading:Overhang, Office_South_Overhang, Office_South_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
Shading:Overhang, Meeting_North_Overhang, Meeting_North_Window, 0.1, 90, 0.2, 0.2, {shading_depth:.3f};
"""
        hvac_str = ""
        if mode == 'ideal_loads':
            hvac_str = _get_ideal_loads_hvac_idf("Open_Office_Zone") + \
                       _get_ideal_loads_hvac_idf("Meeting_Room_Zone")

        body = f"""
Schedule:Compact, Office_Occupancy_Schedule, Fraction,
  Through: 12/31, For: Weekdays, Until: 09:00, 0.0, Until: 18:00, 1.0, Until: 24:00, 0.0,
  For: Weekends Holidays AllOtherDays, Until: 24:00, 0.0;

Schedule:Compact, Office_Lighting_Schedule, Fraction,
  Through: 12/31, For: Weekdays, Until: 08:00, 0.05, Until: 19:00, 1.0, Until: 24:00, 0.05,
  For: Weekends Holidays AllOtherDays, Until: 24:00, 0.05;

Schedule:Compact, Office_Equipment_Schedule, Fraction,
  Through: 12/31, For: Weekdays, Until: 08:00, 0.20, Until: 19:00, 1.0, Until: 24:00, 0.20,
  For: Weekends Holidays AllOtherDays, Until: 24:00, 0.20;

Zone, Open_Office_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.2, 176.0;
Zone, Meeting_Room_Zone, 0.0, 0.0, 0.0, 0.0, 1, 1, 3.2, 80.0;

BuildingSurface:Detailed, Office_Floor, Floor, Floor_Construction, Open_Office_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  0.0, 0.0, 0.0,  0.0, 5.5, 0.0,  10.0, 5.5, 0.0,  10.0, 0.0, 0.0;
BuildingSurface:Detailed, Meeting_Floor, Floor, Floor_Construction, Meeting_Room_Zone, , Ground, , NoSun, NoWind, 0.0, 4,
  0.0, 5.5, 0.0,  0.0, 8.0, 0.0,  10.0, 8.0, 0.0,  10.0, 5.5, 0.0;

BuildingSurface:Detailed, Office_Roof, Roof, Roof_Construction, Open_Office_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  0.0, 5.5, 3.2,  0.0, 0.0, 3.2,  10.0, 0.0, 3.2,  10.0, 5.5, 3.2;
BuildingSurface:Detailed, Meeting_Roof, Roof, Roof_Construction, Meeting_Room_Zone, , Outdoors, , SunExposed, WindExposed, 0.0, 4,
  0.0, 8.0, 3.2,  0.0, 5.5, 3.2,  10.0, 5.5, 3.2,  10.0, 8.0, 3.2;

BuildingSurface:Detailed, Office_South_Wall, Wall, Exterior_Wall_Construction, Open_Office_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 0.0, 3.2,  0.0, 0.0, 0.0,  10.0, 0.0, 0.0,  10.0, 0.0, 3.2;
FenestrationSurface:Detailed, Office_South_Window, Window, Window_Construction, Office_South_Wall, , 0.5, , 1.0, 4,
  {x_s:.3f}, 0.0, {z_t:.3f},  {x_s:.3f}, 0.0, {z_b:.3f},  {x_e:.3f}, 0.0, {z_b:.3f},  {x_e:.3f}, 0.0, {z_t:.3f};

BuildingSurface:Detailed, Meeting_North_Wall, Wall, Exterior_Wall_Construction, Meeting_Room_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 8.0, 3.2,  10.0, 8.0, 0.0,  0.0, 8.0, 0.0,  0.0, 8.0, 3.2;
FenestrationSurface:Detailed, Meeting_North_Window, Window, Window_Construction, Meeting_North_Wall, , 0.5, , 1.0, 4,
  {10.0 - x_s:.3f}, 8.0, {z_t:.3f},  {10.0 - x_s:.3f}, 8.0, {z_b:.3f},  {10.0 - x_e:.3f}, 8.0, {z_b:.3f},  {10.0 - x_e:.3f}, 8.0, {z_t:.3f};

BuildingSurface:Detailed, Office_East_Wall, Wall, Exterior_Wall_Construction, Open_Office_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 0.0, 3.2,  10.0, 0.0, 0.0,  10.0, 5.5, 0.0,  10.0, 5.5, 3.2;
BuildingSurface:Detailed, Meeting_East_Wall, Wall, Exterior_Wall_Construction, Meeting_Room_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  10.0, 5.5, 3.2,  10.0, 5.5, 0.0,  10.0, 8.0, 0.0,  10.0, 8.0, 3.2;

BuildingSurface:Detailed, Office_West_Wall, Wall, Exterior_Wall_Construction, Open_Office_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 5.5, 3.2,  0.0, 5.5, 0.0,  0.0, 0.0, 0.0,  0.0, 0.0, 3.2;
BuildingSurface:Detailed, Meeting_West_Wall, Wall, Exterior_Wall_Construction, Meeting_Room_Zone, , Outdoors, , SunExposed, WindExposed, 0.5, 4,
  0.0, 8.0, 3.2,  0.0, 8.0, 0.0,  0.0, 5.5, 0.0,  0.0, 5.5, 3.2;

BuildingSurface:Detailed, Office_Meeting_Part_Off, Wall, Interior_Partition_Construction, Open_Office_Zone, , Surface, Office_Meeting_Part_Meet, NoSun, NoWind, 0.0, 4,
  10.0, 5.5, 3.2,  10.0, 5.5, 0.0,  0.0, 5.5, 0.0,  0.0, 5.5, 3.2;
BuildingSurface:Detailed, Office_Meeting_Part_Meet, Wall, Interior_Partition_Construction, Meeting_Room_Zone, , Surface, Office_Meeting_Part_Off, NoSun, NoWind, 0.0, 4,
  0.0, 5.5, 3.2,  0.0, 5.5, 0.0,  10.0, 5.5, 0.0,  10.0, 5.5, 3.2;

{shading_str}

People, Office_Occupants, Open_Office_Zone, Office_Occupancy_Schedule, People, 6.0, , , 0.3, , Office_Activity_Sched;
People, Meeting_Occupants, Meeting_Room_Zone, Office_Occupancy_Schedule, People, 4.0, , , 0.3, , Office_Activity_Sched;
Schedule:Constant, Office_Activity_Sched, AnyNumber, 130.0;

Lights, Office_Lights, Open_Office_Zone, Office_Lighting_Schedule, LightingLevel, 467.5, , , 0.2, 0.2, 0.6;
Lights, Meeting_Lights, Meeting_Room_Zone, Office_Lighting_Schedule, LightingLevel, 212.5, , , 0.2, 0.2, 0.6;

ElectricEquipment, Office_Equipment, Open_Office_Zone, Office_Equipment_Schedule, EquipmentLevel, 440.0, , , 0.3, 0.0, 0.5;
ElectricEquipment, Meeting_Equipment, Meeting_Room_Zone, Office_Equipment_Schedule, EquipmentLevel, 200.0, , , 0.3, 0.0, 0.5;

ZoneVentilation:DesignFlowRate, Office_Ventilation, Open_Office_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;
ZoneVentilation:DesignFlowRate, Meeting_Ventilation, Meeting_Room_Zone, Always_On, AirChanges/Hour, , , , {vent_ach:.2f}, Natural, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 20.0, , , , 1.0;

ZoneInfiltration:DesignFlowRate, Office_Infiltration, Open_Office_Zone, Always_On, AirChanges/Hour, , , , 0.5;
ZoneInfiltration:DesignFlowRate, Meeting_Infiltration, Meeting_Room_Zone, Always_On, AirChanges/Hour, , , , 0.5;

{hvac_str}
"""
    else:
        raise ValueError(f"Unknown building_type: {building_type}")

    idf_text = header + body + outputs_str

    os.makedirs(os.path.dirname(output_idf_path), exist_ok=True)
    with open(output_idf_path, 'w', encoding='utf-8') as f:
        f.write(idf_text)
    return output_idf_path


def render_shelter_idf(
    params,
    output_idf_path,
    mode='free_running',
    run_period_days=None
):
    """Backwards-compatible wrapper for shelter_v1."""
    return render_building_idf(
        params=params,
        output_idf_path=output_idf_path,
        building_type='shelter_v1',
        mode=mode,
        run_period_days=run_period_days
    )
