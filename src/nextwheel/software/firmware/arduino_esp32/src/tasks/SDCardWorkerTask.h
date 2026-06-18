#ifndef _SDCARD_WORKER_TASK_H_
#define _SDCARD_WORKER_TASK_H_

#include "tasks/WorkerTask.h"
#include "SDCard.h"


class SDCardWorkerTask : public WorkerTask
{
    static const size_t SDCARD_WORKER_TASK_STACK_SIZE = 8000;

public:
    enum SDCardWorkerTaskCommand
    {
        SDCARD_WORKER_TASK_COMMAND_NONE = 0,
        SDCARD_WORKER_TASK_COMMAND_START_RECORDING = 1,
        SDCARD_WORKER_TASK_COMMAND_STOP_RECORDING = 2
    };

    SDCardWorkerTask();
    bool sendCommandEvent(SDCardWorkerTaskCommand command, bool from_isr = false);

    String currentFileName();
    bool isRecording();

    virtual void run(void* app) override;

private:
    SDCard m_sdCard;
    File m_file;
    String m_filename;
    size_t m_bytesWritten;
    QueueHandle_t m_commandQueue;

    SDCardWorkerTaskCommand dequeueCommand(unsigned long timeout = 10);

    String generateFileName();

    void resetLog();
};

#endif  // _SDCARD_WORKER_TASK_H_
