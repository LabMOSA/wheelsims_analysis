#include "ADCSensorTask.h"
#include "config/GlobalConfig.h"


namespace NextWheelInterrupts
{
    SemaphoreHandle_t g_adc_semaphore;
    void IRAM_ATTR adc_sensor_task_timer_interrupt()
    {
        xSemaphoreGiveFromISR(NextWheelInterrupts::g_adc_semaphore, NULL);
    }
}  // namespace NextWheel

ADCSensorTask::ADCSensorTask() : SensorTask("ADCSensorTask")
{
    NextWheelInterrupts::g_adc_semaphore = xSemaphoreCreateCounting(1, 0);
}


void ADCSensorTask::run(void* app)
{
    Serial.printf("ADCTask::run Priority: %li Core: %li \n", uxTaskPriorityGet(NULL), xPortGetCoreID());
    Serial.print("ADCSensorTask sample_rate: ");
    Serial.println(GlobalConfig::instance().get_imu_sample_rate());

    m_adc.begin();
    ADCDataFrame frame;

    auto adc_timer = timerBegin(3, 80, true);  // count up. 80 prescaler = 1us resolution
    timerAttachInterrupt(
        adc_timer,
        &NextWheelInterrupts::adc_sensor_task_timer_interrupt,
        false);  // Attach interrupt function
    timerAlarmWrite(adc_timer, 1000000 / GlobalConfig::instance().get_adc_sample_rate(), true);  // us timer calculation
    timerAlarmEnable(adc_timer);

    while (1)
    {
        // First empty the command queue (timeout=0, not waiting)
        // Loop while we have BASE_TASK_COMMAND_NONE --> 0
        while (Task::BaseTaskCommand command = dequeueBaseCommand(0))
        {
            switch (command)
            {
                case Task::BASE_TASK_COMMAND_NONE:
                    Serial.println("ADCSensorTask::run: BASE_TASK_COMMAND_NONE");
                    break;
                case Task::BASE_TASK_CONFIG_UPDATED:
                    Serial.println("ADCSensorTask::run: BASE_TASK_CONFIG_UPDATED");
                    Serial.print("ADCSensorTask::run Updating ADC sample rate to : ");
                    Serial.println(GlobalConfig::instance().get_adc_sample_rate());
                    // Update configuration
                    timerAlarmDisable(adc_timer);
                    timerAlarmWrite(
                        adc_timer,
                        1000000 / GlobalConfig::instance().get_adc_sample_rate(),
                        true);  // us timer calculation
                    timerAlarmEnable(adc_timer);
                    break;
                default:
                    Serial.print("ADCSensorTask::run: Unknown command: ");
                    Serial.println(command);
                    break;
            }
        }

        // ADC update will be triggered by timer interrupt
        xSemaphoreTake(NextWheelInterrupts::g_adc_semaphore, portMAX_DELAY);

        // Update values
        m_adc.update(frame);

        // Send data to registered queues
        sendData(frame);
    }

    timerAlarmDisable(adc_timer);
    timerEnd(adc_timer);
}
