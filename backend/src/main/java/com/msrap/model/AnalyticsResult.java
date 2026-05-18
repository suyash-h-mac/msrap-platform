package com.msrap.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "analytics_results")
@IdClass(AnalyticsResultId.class)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class AnalyticsResult {

    @Id
    @Column(nullable = false, length = 32)
    private String symbol;

    @Id
    @Column(nullable = false)
    private Instant ts;

    @Id
    @Column(nullable = false, length = 32)
    private String module;

    @Id
    @Column(nullable = false, length = 64)
    private String metric;

    @Column(precision = 24, scale = 8)
    private BigDecimal value;

    @Column(name = "value_str")
    private String valueStr;
}
