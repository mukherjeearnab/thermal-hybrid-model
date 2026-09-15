model ThermalPlantTest
  "Validation model: applies a power step to ThermalPlant and checks the
   expected steady-state temperature and time constant.

   ambient = 25 degC (constant)
   power   = 0 W  for t <  20 s
   power   = 50 W for t >= 20 s
   simulation interval: 0 to 100 s

   Expected steady state:
     T_steady = T_ambient + P*R = 25 + 50*0.5 = 50 degC
   Expected time constant:
     tau = R*C = 0.5*100 = 50 s"

  ThermalPlant plant(
    R = 0.5,
    C = 100.0,
    T_start = 25.0);

  parameter Real ambientValue = 25.0 "Constant ambient temperature [degC]";
  parameter Real powerStepTime = 20.0 "Time at which power steps up [s]";
  parameter Real powerAfterStep = 50.0 "Applied power after step [W]";

equation
  plant.ambient = ambientValue;
  plant.power = if time < powerStepTime then 0.0 else powerAfterStep;

  annotation(experiment(StartTime = 0, StopTime = 100, Tolerance = 1e-6));
end ThermalPlantTest;
