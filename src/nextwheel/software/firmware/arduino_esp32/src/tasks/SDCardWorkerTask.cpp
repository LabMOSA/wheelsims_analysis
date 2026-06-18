#include "SDCardWorkerTask.h"
#include "NextWheelApp.h"
#include "data/ConfigDataFrame.h"
#include "config/GlobalConfig.h"
#include "state/SystemState.h"


SDCardWorkerTask::SDCardWorkerTask()
    : WorkerTask("SDCardWorkerTask", SDCARD_WORKER_TASK_STACK_SIZE),
      m_file(nullptr),
      m_bytesWritten(0)
{
    m_commandQueue = xQueueCreate(10, sizeof(SDCardWorkerTaskCommand));
}

bool SDCardWorkerTask::sendCommandEvent(SDCardWorkerTaskCommand command, bool from_isr)
{
    if (from_isr)
    {
        return xQueueSendFromISR(m_commandQueue, &command, nullptr) == pdTRUE;
    }
    else
    {
        return xQueueSend(m_commandQueue, &command, 0) == pdTRUE;
    }
}


String SDCardWorkerTask::currentFileName()
{
    return m_filename;
}

bool SDCardWorkerTask::isRecording()
{
    if (m_file)
    {
        return true;
    }

    return false;
}

void SDCardWorkerTask::run(void* app)
{
    Serial.printf("SDCardWorkerTask::run Priority: %li Core: %li \n", uxTaskPriorityGet(NULL), xPortGetCoreID());

    TickType_t lastGeneration = xTaskGetTickCount();

    // Init SD CARD
    m_sdCard.begin();

    while (1)
    {
        // First empty the command queue (timeout=0, not waiting)
        // Loop while we have BASE_TASK_COMMAND_NONE --> 0
        while (Task::BaseTaskCommand command = dequeueBaseCommand(0))
        {
            switch (command)
            {
                case Task::BASE_TASK_COMMAND_NONE:
                    Serial.println("SDCardWorkerTask::run: BASE_TASK_COMMAND_NONE");
                    break;
                case Task::BASE_TASK_CONFIG_UPDATED:
                    Serial.println("SDCardWorkerTask::run: BASE_TASK_CONFIG_UPDATED");

                    // If file is not null means we are recording. We should update the configuration info from now.
                    if (m_file)
                    {
                        ConfigDataFrame configDataFrame(GlobalConfig::instance().get());
                        m_bytesWritten += m_sdCard.writeToLogFile(m_file, configDataFrame);

                        // Empty the queue (with old config!)
                        while (DataFramePtr dataPtr = dequeue(0))
                        {
                            delete dataPtr;
                        }
                    }
                    break;

                default:
                    Serial.print("SDCardWorkerTask::run: Unknown command: ");
                    Serial.println(command);
                    break;
            }
        }

        // Dequeue all data values (one shot), no timeout
        while (DataFramePtr dataPtr = dequeue(0))
        {
            if (m_file)
            {
                m_bytesWritten += m_sdCard.writeToLogFile(m_file, *dataPtr);
            }

            // Make sure we delete the data object
            delete dataPtr;
        }
        // Make sure write is complete
        if (m_file)
        {
            // Make sure we flush the file to SDCard
            m_file.flush();
        }

        // Dequeue commands
        while (SDCardWorkerTaskCommand command = dequeueCommand(0))
        {
            switch (command)
            {
                case SDCARD_WORKER_TASK_COMMAND_NONE:
                    Serial.println("SDCardWorkerTask::run: SDCARD_WORKER_TASK_COMMAND_NONE");
                    break;
                case SDCARD_WORKER_TASK_COMMAND_START_RECORDING:
                    Serial.println("SDCardWorkerTask::run: SDCARD_WORKER_TASK_COMMAND_START_RECORDING");

                    // Already recording
                    if (isRecording())
                        continue;

                    // Make sure we close the file if we were already recording
                    resetLog();

                    m_filename = generateFileName();
                    m_file = m_sdCard.openNewLogFile(m_filename.c_str());
                    if (!m_file)
                    {
                        Serial.print("SDCardWorkerTask::run: Failed to open log file : ");
                        Serial.println(m_filename);
                        resetLog();
                    }
                    else
                    {
                        Serial.print("SDCardWorkerTask::run: File opened: ");
                        Serial.println(m_file.name());

                        SystemState::instance().getState().recording = true;
                        SystemState::instance().getState().filename = m_file.name();

                        // Write config (first data object in the file)
                        ConfigDataFrame configDataFrame(GlobalConfig::instance().get());
                        m_bytesWritten += m_sdCard.writeToLogFile(m_file, configDataFrame);

                        // Allowing messages only if file opened successfully
                        NextWheelApp::instance()->registerSensorTasksToSDCardWorker();
                    }
                    break;
                case SDCARD_WORKER_TASK_COMMAND_STOP_RECORDING:

                    Serial.println("SDCardWorkerTask::run: SDCARD_WORKER_TASK_COMMAND_STOP_RECORDING");
                    if (!isRecording())
                        continue;

                    NextWheelApp::instance()->unregisterSensorTasksFromSDCardWorker();

                    if (m_file)
                    {
                        SystemState::instance().getState().recording = false;
                        SystemState::instance().getState().filename = String();

                        Serial.print("SDCardWorkerTask::run: File closed: ");
                        Serial.println(m_file.name());
                        Serial.print("SDCardWorkerTask::run: File size: ");
                        Serial.println(m_bytesWritten);
                    }
                    resetLog();
                    break;
                default:
                    Serial.println("SDCardWorkerTask::run: Unknown command");
                    break;
            }
        }  // end while (SDCardWorkerTaskCommand command = dequeueCommand(0))


        // 50 ms task
        vTaskDelayUntil(&lastGeneration, 50 / portTICK_RATE_MS);

    }  // while(1)
}

SDCardWorkerTask::SDCardWorkerTaskCommand SDCardWorkerTask::dequeueCommand(unsigned long timeout)
{
    SDCardWorkerTaskCommand command = SDCARD_WORKER_TASK_COMMAND_NONE;
    if (xQueueReceive(m_commandQueue, &command, timeout) != pdTRUE)
    {
        return SDCARD_WORKER_TASK_COMMAND_NONE;
    }
    return command;
}

String SDCardWorkerTask::generateFileName()
{
    time_t now;
    struct tm* timeInfo;
    time(&now);
    timeInfo = localtime(&now);
    char fileName[64];
    sprintf(
        fileName,
        "/log_%04d-%02d-%02d_%02d-%02d-%02d.dat",
        timeInfo->tm_year + 1900,
        timeInfo->tm_mon + 1,
        timeInfo->tm_mday,
        timeInfo->tm_hour,
        timeInfo->tm_min,
        timeInfo->tm_sec);
    return String(fileName);
}

void SDCardWorkerTask::resetLog()
{
    if (m_file)
    {
        m_file.close();
    }
    m_file = File(nullptr);
    m_filename = String();
    m_bytesWritten = 0;
}
