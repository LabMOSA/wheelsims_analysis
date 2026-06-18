#ifndef _DAC_ACTUATOR_TASK_H_
#define _DAC_ACTUATOR_TASK_H_

#include "NextWheel.h"
#include <Arduino.h>
#include <freertos/queue.h>
#include "Task.h"

#ifdef _USE_INTERNAL_DAC_
#include "DAC.h"
#endif


class DACActuatorTask : public Task
{
    // For simplicity, we will create sound events of maxiumum 8 notes with pattern (frequency, duration_ms)
    // Adjust for your needs
    // If frequency == 0, then no sound will be played and will just wait for duration_ms
    static constexpr uint32_t SOUND_QUEUE_MESSAGE_SIZE = 16;

    // 2 fast beeps, [f Hz, duration ms, f Hz, duration ms, ...]
    static const uint32_t START_RECORDING_SOUND[SOUND_QUEUE_MESSAGE_SIZE];
    // 2 slower beeps  [f Hz, duration ms, f Hz, duration ms, ...]
    static const uint32_t STOP_RECORDING_SOUND[SOUND_QUEUE_MESSAGE_SIZE];
    // 2 beeps,  [f Hz, duration ms, f Hz, duration ms, ...]
    static const uint32_t START_STREAMING_SOUND[SOUND_QUEUE_MESSAGE_SIZE];
    // 2 slower beeps,  [f Hz, duration ms, f Hz, duration ms, ...]
    static const uint32_t STOP_STREAMING_SOUND[SOUND_QUEUE_MESSAGE_SIZE];
    // 4 faster beeps,  [f Hz, duration ms, f Hz, duration ms, ...]
    static const uint32_t LOW_BATTERY_SOUND[SOUND_QUEUE_MESSAGE_SIZE];


    // dequeue sounds with array reference
    bool dequeueSound(uint32_t* sound, unsigned long timeout = 10);

public:
    DACActuatorTask(
        const char* name = "DACActuatorTask",
        uint32_t stackSize = TASK_STACK_SIZE_DEFAULT * 10,
        uint8_t priority = TASK_PRIORITY_DEFAULT);
    virtual void run(void*);

    // Play sounds, will queue sound to be played
    void playStartRecordingSound(bool from_isr = false);
    void playStopRecordingSound(bool from_isr = false);
    void playStartStreamingSound(bool from_isr = false);
    void playStopStreamingSound(bool from_isr = false);
    void playLowBatterySound(bool from_isr = false);

private:
#ifdef _USE_INTERNAL_DAC_
    DAC m_dac;
#endif
    QueueHandle_t m_soundQueue;
};

#endif  // _DAC_ACTUATOR_TASK_H_
