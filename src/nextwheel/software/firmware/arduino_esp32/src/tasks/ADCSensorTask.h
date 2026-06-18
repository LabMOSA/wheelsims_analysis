#ifndef _ADC_SENSOR_TASK_H_
#define _ADC_SENSOR_TASK_H_

#include "tasks/SensorTask.h"
#include "data/ADCDataFrame.h"
#include "ADC.h"

class ADCSensorTask : public SensorTask
{
public:
    ADCSensorTask();
    virtual void run(void* app) override;

private:
    ADC m_adc;
};
#endif  // _ADC_TASK_H_
