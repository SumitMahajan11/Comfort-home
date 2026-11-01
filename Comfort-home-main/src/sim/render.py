"""
IDF Template Generator and Renderer for ClimateAdapt-Comfort.
Generates fully validated EnergyPlus 26.2.0 single-zone shelter models
parametrized by design variables:
- roof_insulation_thickness (m, 0.0 to 0.15)
- wall_insulation_thickness (m, 0.0 to 0.15)
- wall_mass_class ('light', 'medium', 'heavy')
- roof_solar_absorptance (0.3 to 0.9)
- wwr (0.05 to 0.40)
- orientation (0 to 359 degrees)
- shading_depth (m, 0.0 to 1.0)
- ventilation_ach (ACH, 1.0 to 15.0)
- mode ('free_running' or 'ideal_loads')
"""

import os

def render_shelter_idf(
    params,
    output_idf_path,
    mode='free_running',
    run_period_days=None # None for annual, or tuple (start_month, start_day, end_month, end_day)
):
    """
    Renders a parametrized single-zone passive shelter IDF.
    Geometry: 5m (X) x 4m (Y) x 3m (Z) = 20 m2 floor area, 60 m3 volume.
    """
    roof_ins_thick = max(0.001, float(params.get('roof_insulation_thickness', 0.0)))
    wall_ins_thick = max(0.001, float(params.get('wall_insulation_thickness', 0.0)))
    wall_mass = str(params.get('wall_mass_class', 'medium')).lower()
    roof_abs = float(params.get('roof_solar_absorptance', 0.7))
    wwr = float(params.get('wwr', 0.20))
    orientation = float(params.get('orientation', 0.0))
    shading_depth = float(params.get('shading_depth', 0.0))
    vent_ach = float(params.get('ventilation_ach', 5.0))
    
    # Wall mass layer mapping
    if wall_mass == 'heavy':
        wall_core_mat = 'HeavyConcrete_200mm'
    elif wall_mass == 'light':
        wall_core_mat = 'LightTimber_100mm'
    else: # medium
        wall_core_mat = 'MediumBrick_200mm'
        
    # Window dimensions based on WWR:
    # South wall is 5.0m wide x 3.0m high = 15.0 m2
    # North wall is 5.0m wide x 3.0m high = 15.0 m2
    # East/West walls are 4.0m wide x 3.0m high = 12.0 m2
    # Total wall area = 54.0 m2
    # Distribute window evenly across walls or primary south/north
    # Window on 5m wall: height 1.2m, width = (15.0 * wwr) / 1.2
    win_h = 1.2
    win_w_5m = min(4.6, max(0.4, (15.0 * wwr) / win_h))
    x_start_5m = (5.0 - win_w_5m) / 2.0
    x_end_5m = x_start_5m + win_w_5m
    
    win_w_4m = min(3.6, max(0.4, (12.0 * wwr) / win_h))
    y_start_4m = (4.0 - win_w_4m) / 2.0
    y_end_4m = y_start_4m + win_w_4m
    
    z_win_bottom = 0.9
    z_win_top = z_win_bottom + win_h
    
    # Shading overhang geometry if shading_depth > 0
    shading_objects = ""
    if shading_depth > 0.02:
        # South window overhang
        shading_objects += f"""
Shading:Overhang,
  SouthWindow_Overhang,    !- Name
  South_Window,            !- Window or Door Name
  0.1,                     !- Height above Window or Door {{m}}
  90,                      !- Tilt Angle from Window/Door {{deg}}
  0.2,                     !- Left Extension from Window/Door Width {{m}}
  0.2,                     !- Right Extension from Window/Door Width {{m}}
  {shading_depth:.3f};              !- Depth {{m}}

Shading:Overhang,
  NorthWindow_Overhang,    !- Name
  North_Window,            !- Window or Door Name
  0.1,                     !- Height above Window or Door {{m}}
  90,                      !- Tilt Angle from Window/Door {{deg}}
  0.2,                     !- Left Extension from Window/Door Width {{m}}
  0.2,                     !- Right Extension from Window/Door Width {{m}}
  {shading_depth:.3f};              !- Depth {{m}}
"""

    # Conditioning mode objects
    hvac_objects = ""
    if mode == 'ideal_loads':
        hvac_objects = """
ZoneHVAC:IdealLoadsAirSystem,
  Shelter_IdealLoads,      !- Name
  ,                        !- Availability Schedule Name
  Shelter_ZoneAirInletNode,!- Zone Supply Air Node Name
  ,                        !- Zone Exhaust Air Node Name
  ,                        !- System Inlet Air Node Name
  50,                      !- Maximum Heating Supply Air Temperature {C}
  13,                      !- Minimum Cooling Supply Air Temperature {C}
  0.0156,                  !- Maximum Heating Supply Air Humidity Ratio {kgWater/kgDryAir}
  0.0077,                  !- Minimum Cooling Supply Air Humidity Ratio {kgWater/kgDryAir}
  NoLimit,                 !- Heating Limit
  ,                        !- Maximum Heating Air Flow Rate {m3/s}
  ,                        !- Maximum Sensible Heating Capacity {W}
  NoLimit,                 !- Cooling Limit
  ,                        !- Maximum Cooling Air Flow Rate {m3/s}
  ,                        !- Maximum Total Cooling Capacity {W}
  ,                        !- Heating Availability Schedule Name
  ,                        !- Cooling Availability Schedule Name
  ConstantSensibleHeatRatio,!- Dehumidification Control Type
  0.7,                     !- Cooling Sensible Heat Ratio {dimensionless}
  None,                    !- Humidification Control Type
  ,                        !- Design Specification Outdoor Air Object Name
  ,                        !- Outdoor Air Inlet Node Name
  None,                    !- Demand Controlled Ventilation Type
  NoEconomizer,            !- Outdoor Air Economizer Type
  None,                    !- Heat Recovery Type
  0.7,                     !- Sensible Heat Recovery Effectiveness {dimensionless}
  0.65;                    !- Latent Heat Recovery Effectiveness {dimensionless}

ZoneHVAC:EquipmentList,
  Shelter_Equipment,       !- Name
  SequentialLoad,          !- Load Distribution Scheme
  ZoneHVAC:IdealLoadsAirSystem, !- Zone Equipment 1 Object Type
  Shelter_IdealLoads,      !- Zone Equipment 1 Name
  1,                       !- Zone Equipment 1 Cooling Sequence
  1,                       !- Zone Equipment 1 Heating or No-Load Sequence
  ,                        !- Zone Equipment 1 Sequential Cooling Fraction Schedule Name
  ;                        !- Zone Equipment 1 Sequential Heating Fraction Schedule Name

ZoneHVAC:EquipmentConnections,
  Main_Zone,               !- Zone Name
  Shelter_Equipment,       !- Zone Conditioning Equipment List Name
  Shelter_ZoneInletNodes,  !- Zone Air Inlet Node or NodeList Name
  ,                        !- Zone Air Exhaust Node or NodeList Name
  Shelter_ZoneAirNode,     !- Zone Air Node Name
  Shelter_ZoneReturnNode;  !- Zone Return Air Node or NodeList Name

NodeList,
  Shelter_ZoneInletNodes,  !- Name
  Shelter_ZoneAirInletNode;!- Node 1 Name

ThermostatSetpoint:DualSetpoint,
  Shelter_DualSetpoint,    !- Name
  Heating_Setpoint_Schedule, !- Heating Setpoint Temperature Schedule Name
  Cooling_Setpoint_Schedule; !- Cooling Setpoint Temperature Schedule Name

ZoneControl:Thermostat,
  Shelter_Thermostat,      !- Name
  Main_Zone,               !- Zone Name
  Zone_Control_Type_Sched, !- Control Type Schedule Name
  ThermostatSetpoint:DualSetpoint, !- Control 1 Object Type
  Shelter_DualSetpoint;    !- Control 1 Name

Schedule:Constant,
  Heating_Setpoint_Schedule, !- Name
  Temperature,             !- Schedule Type Limits Name
  20.0;                    !- Hourly Value {C}

Schedule:Constant,
  Cooling_Setpoint_Schedule, !- Name
  Temperature,             !- Schedule Type Limits Name
  26.0;                    !- Hourly Value {C}

Schedule:Constant,
  Zone_Control_Type_Sched, !- Name
  Control_Type,            !- Schedule Type Limits Name
  4;                       !- 4 is Dual Setpoint with Deadband
"""

    # Run period
    if run_period_days is not None:
        sm, sd, em, ed = run_period_days
        run_period_str = f"""
RunPeriod,
  Custom_Period,           !- Name
  {sm},                     !- Begin Month
  {sd},                     !- Begin Day of Month
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
    else:
        run_period_str = """
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

    idf_text = f"""!- EnergyPlus Single Zone Parametric Shelter Model
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
  Passive_Shelter,         !- Name
  {orientation:.1f},                     !- North Axis {{deg}}
  Suburbs,                 !- Terrain
  0.04,                    !- Loads Convergence Tolerance Value {{W}}
  0.4,                     !- Temperature Convergence Tolerance Value {{deltaC}}
  FullExterior,            !- Solar Distribution
  25,                      !- Maximum Number of Warmup Days
  6;                       !- Minimum Number of Warmup Days

GlobalGeometryRules,
  UpperLeftCorner,         !- Starting Vertex Position
  Counterclockwise,        !- Vertex Entry Direction
  World,                   !- Coordinate System
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

!- ============================================================================
!- MATERIALS & CONSTRUCTIONS
!- ============================================================================

!- 1. Heavy Concrete (200mm)
Material,
  HeavyConcrete_200mm,     !- Name
  Rough,                   !- Roughness
  0.200,                   !- Thickness {{m}}
  1.311,                   !- Conductivity {{W/m-K}}
  2240,                    !- Density {{kg/m3}}
  837;                     !- Specific Heat {{J/kg-K}}

!- 2. Medium Clay Brick (200mm)
Material,
  MediumBrick_200mm,       !- Name
  Rough,                   !- Roughness
  0.200,                   !- Thickness {{m}}
  0.890,                   !- Conductivity {{W/m-K}}
  1920,                    !- Density {{kg/m3}}
  790;                     !- Specific Heat {{J/kg-K}}

!- 3. Light Timber Stud / Board (100mm)
Material,
  LightTimber_100mm,       !- Name
  Smooth,                  !- Roughness
  0.100,                   !- Thickness {{m}}
  0.160,                   !- Conductivity {{W/m-K}}
  600,                     !- Density {{kg/m3}}
  1000;                    !- Specific Heat {{J/kg-K}}

!- 4. Wall Insulation (Parametric)
Material,
  Wall_Insulation,         !- Name
  VerySmooth,              !- Roughness
  {wall_ins_thick:.4f},                 !- Thickness {{m}}
  0.038,                   !- Conductivity {{W/m-K}}
  30,                      !- Density {{kg/m3}}
  1200;                    !- Specific Heat {{J/kg-K}}

!- 5. Plaster Finish (15mm)
Material,
  Plaster_15mm,            !- Name
  Smooth,                  !- Roughness
  0.015,                   !- Thickness {{m}}
  0.720,                   !- Conductivity {{W/m-K}}
  1600,                    !- Density {{kg/m3}}
  840;                     !- Specific Heat {{J/kg-K}}

!- 6. Concrete Roof Slab (100mm)
Material,
  Roof_Concrete_100mm,     !- Name
  Rough,                   !- Roughness
  0.100,                   !- Thickness {{m}}
  1.130,                   !- Conductivity {{W/m-K}}
  2000,                    !- Density {{kg/m3}}
  1000;                    !- Specific Heat {{J/kg-K}}

!- 7. Roof Insulation (Parametric)
Material,
  Roof_Insulation,         !- Name
  VerySmooth,              !- Roughness
  {roof_ins_thick:.4f},                 !- Thickness {{m}}
  0.038,                   !- Conductivity {{W/m-K}}
  30,                      !- Density {{kg/m3}}
  1200;                    !- Specific Heat {{J/kg-K}}

!- 8. Roof Outer Surface with Parametric Solar Absorptance
Material,
  Roof_Outer_Finish,       !- Name
  Rough,                   !- Roughness
  0.010,                   !- Thickness {{m}}
  0.800,                   !- Conductivity {{W/m-K}}
  1800,                    !- Density {{kg/m3}}
  900,                     !- Specific Heat {{J/kg-K}}
  0.90,                    !- Thermal Absorptance
  {roof_abs:.2f},                    !- Solar Absorptance
  0.90;                    !- Visible Absorptance

!- 9. Floor Slab (150mm)
Material,
  Floor_Concrete_150mm,    !- Name
  Rough,                   !- Roughness
  0.150,                   !- Thickness {{m}}
  1.311,                   !- Conductivity {{W/m-K}}
  2240,                    !- Density {{kg/m3}}
  837;                     !- Specific Heat {{J/kg-K}}

!- 10. Clear Window Glass (6mm)
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
  Window_Construction,
  Clear_6mm_Glass;

!- ============================================================================
!- ZONE GEOMETRY (5m x 4m x 3m)
!- ============================================================================

Zone,
  Main_Zone,               !- Name
  0.0,                     !- Direction of Relative North {{deg}}
  0.0, 0.0, 0.0,           !- X, Y, Z Origin {{m}}
  1,                       !- Type
  1,                       !- Multiplier
  3.0,                     !- Ceiling Height {{m}}
  60.0;                    !- Volume {{m3}}

!- Floor Surface (Z = 0)
BuildingSurface:Detailed,
  Floor_Surface,           !- Name
  Floor,                   !- Surface Type
  Floor_Construction,      !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Ground,                  !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  NoSun,                   !- Sun Exposure
  NoWind,                  !- Wind Exposure
  0.0,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  0.0, 0.0, 0.0,           !- Vertex 1
  0.0, 4.0, 0.0,           !- Vertex 2
  5.0, 4.0, 0.0,           !- Vertex 3
  5.0, 0.0, 0.0;           !- Vertex 4

!- Roof Surface (Z = 3.0)
BuildingSurface:Detailed,
  Roof_Surface,            !- Name
  Roof,                    !- Surface Type
  Roof_Construction,       !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Outdoors,                !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  SunExposed,              !- Sun Exposure
  WindExposed,             !- Wind Exposure
  0.0,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  0.0, 4.0, 3.0,           !- Vertex 1
  0.0, 0.0, 3.0,           !- Vertex 2
  5.0, 0.0, 3.0,           !- Vertex 3
  5.0, 4.0, 3.0;           !- Vertex 4

!- South Wall (Y = 0)
BuildingSurface:Detailed,
  South_Wall,              !- Name
  Wall,                    !- Surface Type
  Exterior_Wall_Construction, !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Outdoors,                !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  SunExposed,              !- Sun Exposure
  WindExposed,             !- Wind Exposure
  0.5,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  0.0, 0.0, 3.0,           !- Vertex 1
  0.0, 0.0, 0.0,           !- Vertex 2
  5.0, 0.0, 0.0,           !- Vertex 3
  5.0, 0.0, 3.0;           !- Vertex 4

!- South Window
FenestrationSurface:Detailed,
  South_Window,            !- Name
  Window,                  !- Surface Type
  Window_Construction,     !- Construction Name
  South_Wall,              !- Building Surface Name
  ,                        !- Outside Boundary Condition Object
  0.5,                     !- View Factor to Ground
  ,                        !- Frame and Divider Name
  1.0,                     !- Multiplier
  4,                       !- Number of Vertices
  {x_start_5m:.3f}, 0.0, {z_win_top:.3f},
  {x_start_5m:.3f}, 0.0, {z_win_bottom:.3f},
  {x_end_5m:.3f}, 0.0, {z_win_bottom:.3f},
  {x_end_5m:.3f}, 0.0, {z_win_top:.3f};

!- North Wall (Y = 4.0)
BuildingSurface:Detailed,
  North_Wall,              !- Name
  Wall,                    !- Surface Type
  Exterior_Wall_Construction, !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Outdoors,                !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  SunExposed,              !- Sun Exposure
  WindExposed,             !- Wind Exposure
  0.5,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  5.0, 4.0, 3.0,           !- Vertex 1
  5.0, 4.0, 0.0,           !- Vertex 2
  0.0, 4.0, 0.0,           !- Vertex 3
  0.0, 4.0, 3.0;           !- Vertex 4

!- North Window
FenestrationSurface:Detailed,
  North_Window,            !- Name
  Window,                  !- Surface Type
  Window_Construction,     !- Construction Name
  North_Wall,              !- Building Surface Name
  ,                        !- Outside Boundary Condition Object
  0.5,                     !- View Factor to Ground
  ,                        !- Frame and Divider Name
  1.0,                     !- Multiplier
  4,                       !- Number of Vertices
  {5.0 - x_start_5m:.3f}, 4.0, {z_win_top:.3f},
  {5.0 - x_start_5m:.3f}, 4.0, {z_win_bottom:.3f},
  {5.0 - x_end_5m:.3f}, 4.0, {z_win_bottom:.3f},
  {5.0 - x_end_5m:.3f}, 4.0, {z_win_top:.3f};

!- East Wall (X = 5.0)
BuildingSurface:Detailed,
  East_Wall,               !- Name
  Wall,                    !- Surface Type
  Exterior_Wall_Construction, !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Outdoors,                !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  SunExposed,              !- Sun Exposure
  WindExposed,             !- Wind Exposure
  0.5,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  5.0, 0.0, 3.0,           !- Vertex 1
  5.0, 0.0, 0.0,           !- Vertex 2
  5.0, 4.0, 0.0,           !- Vertex 3
  5.0, 4.0, 3.0;           !- Vertex 4

!- West Wall (X = 0.0)
BuildingSurface:Detailed,
  West_Wall,               !- Name
  Wall,                    !- Surface Type
  Exterior_Wall_Construction, !- Construction Name
  Main_Zone,               !- Zone Name
  ,                        !- Space Name
  Outdoors,                !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  SunExposed,              !- Sun Exposure
  WindExposed,             !- Wind Exposure
  0.5,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  0.0, 4.0, 3.0,           !- Vertex 1
  0.0, 4.0, 0.0,           !- Vertex 2
  0.0, 0.0, 0.0,           !- Vertex 3
  0.0, 0.0, 3.0;           !- Vertex 4

{shading_objects}

!- ============================================================================
!- INTERNAL LOADS & VENTILATION
!- ============================================================================

!- 2 Occupants (Assumption A-001: 24h occupancy, A-002: 1.1 met = 125 W/person)
People,
  Shelter_Occupants,       !- Name
  Main_Zone,               !- Zone or ZoneList Name
  Always_On,               !- Number of People Schedule Name
  People,                  !- Number of People Calculation Method
  2.0,                     !- Number of People
  ,                        !- People per Floor Area {{person/m2}}
  ,                        !- Floor Area per Person {{m2/person}}
  0.3,                     !- Fraction Radiant
  ,                        !- Sensible Heat Fraction
  Shelter_Activity_Sched;  !- Activity Level Schedule Name

Schedule:Constant,
  Shelter_Activity_Sched,
  AnyNumber,
  125.0;                   !- Activity level in Watts

!- Natural Ventilation (ACH) with natural cooling control (ventilate when indoor > 20C and outdoor is cooler)
ZoneVentilation:DesignFlowRate,
  Natural_Ventilation,     !- Name
  Main_Zone,               !- Zone or ZoneList Name
  Always_On,               !- Schedule Name
  AirChanges/Hour,         !- Design Volume Flow Rate Calculation Method
  ,                        !- Design Volume Flow Rate {{m3/s}}
  ,                        !- Flow Rate per Zone Floor Area {{m3/s-m2}}
  ,                        !- Flow Rate per Person {{m3/s-person}}
  {vent_ach:.2f},                    !- Air Changes per Hour {{1/hr}}
  Natural,                 !- Ventilation Type
  0.0,                     !- Fan Pressure Rise {{Pa}}
  1.0,                     !- Fan Total Efficiency
  1.0,                     !- Constant Term Coefficient
  0.0,                     !- Temperature Term Coefficient
  0.0,                     !- Velocity Term Coefficient
  0.0,                     !- Velocity Squared Term Coefficient
  20.0,                    !- Minimum Indoor Temperature {{C}}
  ,                        !- Minimum Indoor Temperature Schedule Name
  ,                        !- Maximum Indoor Temperature {{C}}
  ,                        !- Maximum Indoor Temperature Schedule Name
  1.0;                     !- Delta Temperature {{deltaC}}

!- Infiltration (0.5 ACH baseline)
ZoneInfiltration:DesignFlowRate,
  Infiltration_0p5ACH,     !- Name
  Main_Zone,               !- Zone or ZoneList Name
  Always_On,               !- Schedule Name
  AirChanges/Hour,         !- Design Volume Flow Rate Calculation Method
  ,                        !- Design Volume Flow Rate {{m3/s}}
  ,                        !- Flow Rate per Zone Floor Area {{m3/s-m2}}
  ,                        !- Flow Rate per Person {{m3/s-person}}
  0.5;                     !- Air Changes per Hour {{1/hr}}

{hvac_objects}

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
    os.makedirs(os.path.dirname(output_idf_path), exist_ok=True)
    with open(output_idf_path, 'w', encoding='utf-8') as f:
        f.write(idf_text)
    return output_idf_path
