package com.msrap.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "equity_ohlcv")
@IdClass(EquityOhlcvId.class)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class EquityOhlcv {

    @Id
    @Column(nullable = false, length = 32)
    private String symbol;

    @Id
    @Column(nullable = false)
    private Instant ts;

    @Id
    @Column(nullable = false, length = 8)
    private String interval;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal open;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal high;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal low;

    @Column(nullable = false, precision = 18, scale = 4)
    private BigDecimal close;

    @Column(nullable = false)
    private Long volume;

    @Column(name = "adj_close", precision = 18, scale = 4)
    private BigDecimal adjClose;
}
