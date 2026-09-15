/* Initialization */
#include "ThermalPlant_model.h"
#include "ThermalPlant_11mix.h"
#include "ThermalPlant_12jac.h"
#if defined(__cplusplus)
extern "C" {
#endif

void ThermalPlant_functionInitialEquations_0(DATA *data, threadData_t *threadData);

/*
equation index: 1
type: SIMPLE_ASSIGN
temperature = T_start
*/
void ThermalPlant_eqFunction_1(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,1};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* temperature variable */) = (data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[2]] /* T_start PARAM */);
  threadData->lastEquationSolved = 1;
}

/*
equation index: 2
type: SIMPLE_ASSIGN
$outputAlias_temperature = temperature
*/
void ThermalPlant_eqFunction_2(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,2};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* $outputAlias_temperature STATE(1,$temperature_der) */) = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* temperature variable */);
  threadData->lastEquationSolved = 2;
}
extern void ThermalPlant_eqFunction_5(DATA *data, threadData_t *threadData);

extern void ThermalPlant_eqFunction_6(DATA *data, threadData_t *threadData);

OMC_DISABLE_OPT
void ThermalPlant_functionInitialEquations_0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[4])(DATA*, threadData_t*) = {
    ThermalPlant_eqFunction_1,
    ThermalPlant_eqFunction_2,
    ThermalPlant_eqFunction_5,
    ThermalPlant_eqFunction_6
  };
  
  for (int id = 0; id < 4; id++) {
    eqFunctions[id](data, threadData);
  }
}

int ThermalPlant_functionInitialEquations(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->discreteCall = 1;
  ThermalPlant_functionInitialEquations_0(data, threadData);
  data->simulationInfo->discreteCall = 0;
  
  return 0;
}

/* No ThermalPlant_functionInitialEquations_lambda0 function */

int ThermalPlant_functionRemovedInitialEquations(DATA *data, threadData_t *threadData)
{
  const int *equationIndexes = NULL;
  double res = 0.0;

  
  return 0;
}


#if defined(__cplusplus)
}
#endif
