package com.msrap.model;

import lombok.*;
import java.io.Serializable;
import java.time.Instant;

@Getter @Setter @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode
public class AnalyticsResultId implements Serializable {
    private String symbol;
    private Instant ts;
    private String module;
    private String metric;
}
