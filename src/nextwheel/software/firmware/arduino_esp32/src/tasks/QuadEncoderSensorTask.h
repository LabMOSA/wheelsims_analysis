#ifndef _QUAD_ENCODER_SENSOR_TASK_H_
#define _QUAD_ENCODER_SENSOR_TASK_H_

#include "tasks/SensorTask.h"
#include <ESP32Encoder.h>
#include "NextWheel.h"

class QuadEncoderSensorTask : public SensorTask
{
public:
    QuadEncoderSensorTask();
    virtual void run(void* app) override;

private:
    ESP32Encoder m_encoder;
};
#endif  // _QUAD_ENCODER_SENSOR_TASK_H_
