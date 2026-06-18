#ifndef _IMU_SENSOR_TASK_H_
#define _IMU_SENSOR_TASK_H_

#include "tasks/SensorTask.h"
#include "data/IMUDataFrame.h"
#include "IMU.h"

class IMUSensorTask : public SensorTask
{
public:
    IMUSensorTask();
    virtual void run(void* app) override;
};

#endif  // _IMU_SENSOR_TASK_H_
