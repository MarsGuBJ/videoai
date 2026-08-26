package com.videoai.monitoring.common.enums;

/**
 * Standard result/error codes. Codes 0/400/404/500 mirror HTTP semantics;
 * 1xxx codes are generic business errors.
 */
public enum ErrorCode {
    SUCCESS(0, "success"),
    BAD_REQUEST(400, "bad request"),
    NOT_FOUND(404, "not found"),
    INTERNAL_ERROR(500, "internal error"),
    CONFLICT(409, "conflict"),
    BUSINESS_ERROR(1000, "business error"),
    REMOTE_SERVICE_ERROR(1001, "remote service error");

    private final int code;
    private final String message;

    ErrorCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
