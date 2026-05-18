package com.msrap.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "factor_loadings")
@IdClass(FactorLoadingId.class)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class FactorLoading {

    @Id
    @Column(nullable = false, length = 32)
    private String symbol;

    @Id
    @Column(nullable = false)
    private Instant ts;

    @Id
    @Column(name = "window_days", nullable = false)
    private Short windowDays;

    @Column(name = "beta_market",   precision = 10, scale = 6) private BigDecimal betaMarket;
    @Column(name = "beta_size",     precision = 10, scale = 6) private BigDecimal betaSize;
    @Column(name = "beta_value",    precision = 10, scale = 6) private BigDecimal betaValue;
    @Column(name = "beta_momentum", precision = 10, scale = 6) private BigDecimal betaMomentum;
    @Column(name = "beta_quality",  precision = 10, scale = 6) private BigDecimal betaQuality;
    @Column(name = "alpha",         precision = 10, scale = 6) private BigDecimal alpha;
    @Column(name = "r_squared",     precision = 8,  scale = 6) private BigDecimal rSquared;
    @Column(name = "residual_vol",  precision = 10, scale = 6) private BigDecimal residualVol;
}
