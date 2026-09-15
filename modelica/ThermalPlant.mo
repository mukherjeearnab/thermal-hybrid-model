model ThermalPlant
  "Simple first-order lumped thermal model: C*dT/dt = P - (T-Ta)/R"

  parameter Real R = 0.5
    "Thermal resistance [K/W]";

  parameter Real C = 100.0
    "Thermal capacitance [J/K]";

  parameter Real T_start = 25.0
    "Initial temperature [degC]";

  input Real power
    "Applied power [W]";

  input Real ambient
    "Ambient temperature [degC]";

  output Real temperature
    "Simulated temperature [degC]";

initial equation
  temperature = T_start;

equation
  C * der(temperature) = power - (temperature - ambient) / R;

end ThermalPlant;
