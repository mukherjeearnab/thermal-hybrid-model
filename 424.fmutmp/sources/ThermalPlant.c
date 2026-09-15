/* Main Simulation File */

#if defined(__cplusplus)
extern "C" {
#endif

#include "ThermalPlant_model.h"
#include "simulation/solver/events.h"
#include "simulation/arrayIndex.h"



/* dummy VARINFO and FILEINFO */
const VAR_INFO dummyVAR_INFO = omc_dummyVarInfo;

int ThermalPlant_input_function(DATA *data, threadData_t *threadData)
{
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* ambient variable */) = data->simulationInfo->inputVars[0];
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power variable */) = data->simulationInfo->inputVars[1];
  
  return 0;
}

int ThermalPlant_input_function_init(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->inputVars[0] = getStartFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 3);
  data->simulationInfo->inputVars[1] = getStartFromScalarIdx(data->simulationInfo, data->modelData, VAR_TYPE_REAL, VAR_KIND_VARIABLE, 4);
  
  return 0;
}

int ThermalPlant_input_function_updateStartValues(DATA *data, threadData_t *threadData)
{
  assertStreamPrint(threadData, data->modelData->realVarsData[3].dimension.numberOfDimensions == 0, "Handling of array variables not yet implemetned.");
  put_real_element(data->simulationInfo->inputVars[0], 0, &data->modelData->realVarsData[3].attribute.start);
  assertStreamPrint(threadData, data->modelData->realVarsData[4].dimension.numberOfDimensions == 0, "Handling of array variables not yet implemetned.");
  put_real_element(data->simulationInfo->inputVars[1], 0, &data->modelData->realVarsData[4].attribute.start);
  
  return 0;
}

int ThermalPlant_inputNames(DATA *data, char ** names){
  names[0] = (char *) data->modelData->realVarsData[3].info.name;
  names[1] = (char *) data->modelData->realVarsData[4].info.name;
  
  return 0;
}

int ThermalPlant_data_function(DATA *data, threadData_t *threadData)
{
  return 0;
}

int ThermalPlant_dataReconciliationInputNames(DATA *data, char ** names){
  
  return 0;
}

int ThermalPlant_dataReconciliationUnmeasuredVariables(DATA *data, char ** names)
{
  
  return 0;
}

int ThermalPlant_output_function(DATA *data, threadData_t *threadData)
{
  data->simulationInfo->outputVars[0] = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* temperature variable */);
  
  return 0;
}

int ThermalPlant_setc_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

int ThermalPlant_setb_function(DATA *data, threadData_t *threadData)
{
  
  return 0;
}


/*
equation index: 5
type: SIMPLE_ASSIGN
$temperature_der = (power + (ambient - $outputAlias_temperature) / R) / C
*/
void ThermalPlant_eqFunction_5(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,5};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* $temperature_der variable */) = DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[4]] /* power variable */) + DIVISION_SIM((data->localData[0]->realVars[data->simulationInfo->realVarsIndex[3]] /* ambient variable */) - (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* $outputAlias_temperature STATE(1,$temperature_der) */),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[1]] /* R PARAM */),"R",equationIndexes),(data->simulationInfo->realParameter[data->simulationInfo->realParamsIndex[0]] /* C PARAM */),"C",equationIndexes);
  threadData->lastEquationSolved = 5;
}

/*
equation index: 6
type: SIMPLE_ASSIGN
$DER.$outputAlias_temperature = $temperature_der
*/
void ThermalPlant_eqFunction_6(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,6};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[1]] /* der($outputAlias_temperature) STATE_DER */) = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[2]] /* $temperature_der variable */);
  threadData->lastEquationSolved = 6;
}

/*
equation index: 7
type: SIMPLE_ASSIGN
temperature = $outputAlias_temperature
*/
void ThermalPlant_eqFunction_7(DATA *data, threadData_t *threadData)
{
  const int equationIndexes[2] = {1,7};
  (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[5]] /* temperature variable */) = (data->localData[0]->realVars[data->simulationInfo->realVarsIndex[0]] /* $outputAlias_temperature STATE(1,$temperature_der) */);
  threadData->lastEquationSolved = 7;
}

OMC_DISABLE_OPT
int ThermalPlant_functionDAE(DATA *data, threadData_t *threadData)
{
  int equationIndexes[1] = {0};
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_DAE);
#endif

  data->simulationInfo->needToIterate = 0;
  data->simulationInfo->discreteCall = 1;
  ThermalPlant_functionLocalKnownVars(data, threadData);
  static void (*const eqFunctions[3])(DATA*, threadData_t*) = {
    ThermalPlant_eqFunction_5,
    ThermalPlant_eqFunction_6,
    ThermalPlant_eqFunction_7
  };
  
  for (int id = 0; id < 3; id++) {
    eqFunctions[id](data, threadData);
  }
  data->simulationInfo->discreteCall = 0;
  
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_DAE);
#endif
  return 0;
}


int ThermalPlant_functionLocalKnownVars(DATA *data, threadData_t *threadData)
{
  
  return 0;
}

/* forwarded equations */
extern void ThermalPlant_eqFunction_5(DATA* data, threadData_t *threadData);
extern void ThermalPlant_eqFunction_6(DATA* data, threadData_t *threadData);

static void functionODE_system0(DATA *data, threadData_t *threadData)
{
  static void (*const eqFunctions[2])(DATA*, threadData_t*) = {
    ThermalPlant_eqFunction_5,
    ThermalPlant_eqFunction_6
  };
  
  if (data->simulationInfo->evalSelection) {
    for (int i = 0; i < data->simulationInfo->evalSelection->n; i++) {
      int id = data->simulationInfo->evalSelection->idx[i];
      eqFunctions[id](data, threadData);
    }
  } else {
    for (int id = 0; id < 2; id++) {
      eqFunctions[id](data, threadData);
    }
  }
}

int ThermalPlant_functionODE(DATA *data, threadData_t *threadData)
{
#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_tick(SIM_TIMER_FUNCTION_ODE);
#endif

  
  data->simulationInfo->callStatistics.functionODE++;
  
  ThermalPlant_functionLocalKnownVars(data, threadData);
  functionODE_system0(data, threadData);

#if !defined(OMC_MINIMAL_RUNTIME)
  if (measure_time_flag) rt_accumulate(SIM_TIMER_FUNCTION_ODE);
#endif

  return 0;
}

void ThermalPlant_ODE_DAG(DATA* data, threadData_t* threadData)
{
  const size_t eqMap[] = {5, 6};
  buildEvalDAG_ODE(data->modelData, sizeof(eqMap)/sizeof(size_t), eqMap);
}

/* forward the main in the simulation runtime */
extern int _main_SimulationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);
extern int _main_OptimizationRuntime(int argc, char **argv, DATA *data, threadData_t *threadData);

#include "ThermalPlant_12jac.h"
#include "ThermalPlant_13opt.h"

struct OpenModelicaGeneratedFunctionCallbacks ThermalPlant_callback = {
  NULL,    /* performSimulation */
  NULL,    /* performQSSSimulation */
  NULL,    /* updateContinuousSystem */
  ThermalPlant_callExternalObjectDestructors,    /* callExternalObjectDestructors */
  NULL,    /* initialNonLinearSystem */
  NULL,    /* initialLinearSystem */
  NULL,    /* initialMixedSystem */
  #if !defined(OMC_NO_STATESELECTION)
  ThermalPlant_initializeStateSets,
  #else
  NULL,
  #endif    /* initializeStateSets */
  ThermalPlant_initializeDAEmodeData,
  ThermalPlant_ODE_DAG,
  ThermalPlant_functionODE,
  ThermalPlant_functionAlgebraics,
  ThermalPlant_functionDAE,
  ThermalPlant_functionLocalKnownVars,
  ThermalPlant_input_function,
  ThermalPlant_input_function_init,
  ThermalPlant_input_function_updateStartValues,
  ThermalPlant_data_function,
  ThermalPlant_output_function,
  ThermalPlant_setc_function,
  ThermalPlant_setb_function,
  ThermalPlant_function_storeDelayed,
  ThermalPlant_function_storeSpatialDistribution,
  ThermalPlant_function_initSpatialDistribution,
  ThermalPlant_updateBoundVariableAttributes,
  ThermalPlant_functionInitialEquations,
  GLOBAL_EQUIDISTANT_HOMOTOPY,
  NULL,
  ThermalPlant_functionRemovedInitialEquations,
  ThermalPlant_updateBoundParameters,
  ThermalPlant_checkForAsserts,
  ThermalPlant_function_ZeroCrossingsEquations,
  ThermalPlant_function_ZeroCrossings,
  ThermalPlant_function_updateRelations,
  ThermalPlant_zeroCrossingDescription,
  ThermalPlant_relationDescription,
  ThermalPlant_function_initSample,
  ThermalPlant_INDEX_JAC_A,
  ThermalPlant_INDEX_JAC_ADJ,
  ThermalPlant_INDEX_JAC_B,
  ThermalPlant_INDEX_JAC_C,
  ThermalPlant_INDEX_JAC_D,
  ThermalPlant_INDEX_JAC_F,
  ThermalPlant_INDEX_JAC_H,
  ThermalPlant_initialAnalyticJacobianA,
  ThermalPlant_initialAnalyticJacobianADJ,
  ThermalPlant_initialAnalyticJacobianB,
  ThermalPlant_initialAnalyticJacobianC,
  ThermalPlant_initialAnalyticJacobianD,
  ThermalPlant_initialAnalyticJacobianF,
  ThermalPlant_initialAnalyticJacobianH,
  ThermalPlant_functionJacA_column,
  ThermalPlant_functionJacADJ_column,
  ThermalPlant_functionJacB_column,
  ThermalPlant_functionJacC_column,
  ThermalPlant_functionJacD_column,
  ThermalPlant_functionJacF_column,
  ThermalPlant_functionJacH_column,
  ThermalPlant_JacA_DAG,
  ThermalPlant_linear_model_frame,
  ThermalPlant_linear_model_datarecovery_frame,
  ThermalPlant_mayer,
  ThermalPlant_lagrange,
  ThermalPlant_getInputVarIndicesInOptimization,
  ThermalPlant_pickUpBoundsForInputsInOptimization,
  ThermalPlant_setInputData,
  ThermalPlant_getTimeGrid,
  ThermalPlant_symbolicInlineSystem,
  ThermalPlant_function_initSynchronous,
  ThermalPlant_function_updateSynchronous,
  ThermalPlant_function_equationsSynchronous,
  ThermalPlant_inputNames,
  ThermalPlant_dataReconciliationInputNames,
  ThermalPlant_dataReconciliationUnmeasuredVariables,
  ThermalPlant_read_simulation_info,
  ThermalPlant_read_input_fmu,
  NULL,
  NULL,
  -1,
  NULL,
  NULL,
  -1

};

#define _OMC_LIT_RESOURCE_0_name_data "ThermalPlant"
#define _OMC_LIT_RESOURCE_0_dir_data "/home/arnab/Projects/openmodelica-pytorch-hybrid/modelica"
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_name,12,_OMC_LIT_RESOURCE_0_name_data);
static const MMC_DEFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir,57,_OMC_LIT_RESOURCE_0_dir_data);

static const MMC_DEFSTRUCTLIT(_OMC_LIT_RESOURCES,2,MMC_ARRAY_TAG) {MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_name), MMC_REFSTRINGLIT(_OMC_LIT_RESOURCE_0_dir)}};
void ThermalPlant_setupDataStruc(DATA *data, threadData_t *threadData)
{
  assertStreamPrint(threadData,0!=data, "Error while initialize Data");
  threadData->localRoots[LOCAL_ROOT_SIMULATION_DATA] = data;
  data->callback = &ThermalPlant_callback;
  OpenModelica_updateUriMapping(threadData, MMC_REFSTRUCTLIT(_OMC_LIT_RESOURCES));
  data->modelData->modelName = "ThermalPlant";
  data->modelData->modelFilePrefix = "ThermalPlant";
  data->modelData->modelFileName = "ThermalPlant.mo";
  data->modelData->resultFileName = NULL;
  data->modelData->modelDir = "/home/arnab/Projects/openmodelica-pytorch-hybrid/modelica";
  data->modelData->modelGUID = "{9e3c718c-420b-4862-b399-421672c2ed21}";
  data->modelData->initXMLData = NULL;
  data->modelData->modelDataXml.infoXMLData = NULL;
  GC_asprintf(&data->modelData->modelDataXml.fileName, "%s/ThermalPlant_info.json", data->modelData->resourcesDir);
  data->modelData->runTestsuite = 0;
  data->modelData->nStatesArray = 1;
  data->modelData->nDiscreteReal = 0;
  data->modelData->nVariablesRealArray = 6;
  data->modelData->nVariablesIntegerArray = 0;
  data->modelData->nVariablesBooleanArray = 0;
  data->modelData->nVariablesStringArray = 0;
  data->modelData->nParametersRealArray = 3;
  data->modelData->nParametersIntegerArray = 0;
  data->modelData->nParametersBooleanArray = 0;
  data->modelData->nParametersStringArray = 0;
  data->modelData->nParametersReal = 3;
  data->modelData->nParametersInteger = 0;
  data->modelData->nParametersBoolean = 0;
  data->modelData->nParametersString = 0;
  data->modelData->nAliasRealArray = 0;
  data->modelData->nAliasIntegerArray = 0;
  data->modelData->nAliasBooleanArray = 0;
  data->modelData->nAliasStringArray = 0;
  data->modelData->nInputVars = 2;
  data->modelData->nOutputVars = 1;
  data->modelData->nZeroCrossings = 0;
  data->modelData->nSamples = 0;
  data->modelData->nRelations = 0;
  data->modelData->nMathEvents = 0;
  data->modelData->nExtObjs = 0;
  data->modelData->modelDataXml.modelInfoXmlLength = 0;
  data->modelData->modelDataXml.nFunctions = 0;
  data->modelData->modelDataXml.nProfileBlocks = 0;
  data->modelData->modelDataXml.nEquations = 8;
  data->modelData->nMixedSystems = 0;
  data->modelData->nLinearSystems = 0;
  data->modelData->nNonLinearSystems = 0;
  data->modelData->nStateSets = 0;
  data->modelData->nJacobians = 7;
  data->modelData->nOptimizeConstraints = 0;
  data->modelData->nOptimizeFinalConstraints = 0;
  data->modelData->nDelayExpressions = 0;
  data->modelData->nBaseClocks = 0;
  data->modelData->nSpatialDistributions = 0;
  data->modelData->nSensitivityVars = 0;
  data->modelData->nSensitivityParamVars = 0;
  data->modelData->nSetcVars = 0;
  data->modelData->ndataReconVars = 0;
  data->modelData->nSetbVars = 0;
  data->modelData->nRelatedBoundaryConditions = 0;
  data->modelData->linearizationDumpLanguage = OMC_LINEARIZE_DUMP_LANGUAGE_MODELICA;
}

static int rml_execution_failed()
{
  fflush(NULL);
  fprintf(stderr, "Execution failed!\n");
  fflush(NULL);
  return 1;
}

