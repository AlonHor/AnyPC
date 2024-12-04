__author__ = "Alon & K9"

from enum import Enum

class Events(Enum):
    Screenshot_Request = "SSRQ"
    FileContent_Request = "FLRQ"
    FileList_Request = "LSRQ"
    CopyFile_Request = "CPRQ"
    MoveFile_Request = "MVRQ"
    RemoveFile_Request = "RMRQ"
    ScreenControl_Request = "SCRQ"
    ScreenWatch_Request = "SWRQ"
    CommandRun_Request = "CMDR"

    ScreenControlInput_Action = "SCIN"
    ScreenControlDisconnect_Action = "DNSC"
    ScreenWatchDisconnect_Action = "DNSW"
    FileUpload_Action = "UPCK"
    ScreenFrame_Action = "SCFR"

    ScreenshotDone_Response = "SDON"
    FileDownload_Response = "DNCK"
    FileList_Response = "FOLL"
    AcceptScreenControl_Response = "ACSC"
    AcceptScreenWatch_Response = "ACSW"
    CommandRun_Response = "CMDO"

    OperationSuccess_Response = "SUCC"
    OperationFailed_Response = "ERRR"
    ConnectionClosed = "CLOS"
    UnknownEvent = "UNKNOWN_EVENT"

    @classmethod
    def from_value(cls, value: str) -> 'Events':
        for event in cls:
            if value == event.value:
                return event
        return cls.UnknownEvent

class Error(Enum):
    UnknownError = 0
    FileNotFound = 1
    BadPath = 2

    @classmethod
    def from_value(cls, value: int) -> 'Error':
        for event in cls:
            if value == event.value:
                return event
        return cls.UnknownError
