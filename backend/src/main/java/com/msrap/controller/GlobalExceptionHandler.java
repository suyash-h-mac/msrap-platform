package com.msrap.controller;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.net.URI;
import java.time.Instant;
import java.util.NoSuchElementException;

/**
 * Centralised exception handling for all REST controllers.
 *
 * <p>Uses RFC 9457 {@link ProblemDetail} (supported natively by Spring 6 / Boot 3)
 * so every error response has a consistent shape:</p>
 * <pre>
 * {
 *   "type":     "https://msrap.internal/errors/not-found",
 *   "title":    "Not Found",
 *   "status":   404,
 *   "detail":   "No regime data for symbol XYZ",
 *   "instance": "/api/analytics/regime/XYZ/current",
 *   "timestamp": "2025-05-18T12:00:00Z"
 * }
 * </pre>
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final String ERROR_BASE = "https://msrap.internal/errors/";

    // ── 404 ──────────────────────────────────────────────────────────────────

    @ExceptionHandler(NoSuchElementException.class)
    public ResponseEntity<ProblemDetail> handleNotFound(NoSuchElementException ex) {
        log.debug("Resource not found: {}", ex.getMessage());
        return problem(HttpStatus.NOT_FOUND, "not-found", ex.getMessage());
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ProblemDetail> handleNoResource(NoResourceFoundException ex) {
        log.debug("No resource found: {}", ex.getMessage());
        return problem(HttpStatus.NOT_FOUND, "not-found", ex.getMessage());
    }

    // ── 400 ──────────────────────────────────────────────────────────────────

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ProblemDetail> handleIllegalArgument(IllegalArgumentException ex) {
        log.warn("Bad request: {}", ex.getMessage());
        return problem(HttpStatus.BAD_REQUEST, "bad-request", ex.getMessage());
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ProblemDetail> handleMissingParam(
            MissingServletRequestParameterException ex) {
        String detail = String.format("Required parameter '%s' of type %s is missing",
                ex.getParameterName(), ex.getParameterType());
        log.warn("Missing request parameter: {}", detail);
        return problem(HttpStatus.BAD_REQUEST, "bad-request", detail);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ProblemDetail> handleTypeMismatch(
            MethodArgumentTypeMismatchException ex) {
        String detail = String.format("Parameter '%s' should be of type %s",
                ex.getName(),
                ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown");
        log.warn("Type mismatch: {}", detail);
        return problem(HttpStatus.BAD_REQUEST, "bad-request", detail);
    }

    // ── 500 ──────────────────────────────────────────────────────────────────

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleGeneric(Exception ex) {
        log.error("Unhandled exception: {}", ex.getMessage(), ex);
        return problem(HttpStatus.INTERNAL_SERVER_ERROR, "internal-error",
                "An unexpected error occurred. Please try again later.");
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    private ResponseEntity<ProblemDetail> problem(HttpStatus status, String errorType, String detail) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(status, detail);
        pd.setType(URI.create(ERROR_BASE + errorType));
        pd.setProperty("timestamp", Instant.now().toString());
        return ResponseEntity.status(status).body(pd);
    }
}
