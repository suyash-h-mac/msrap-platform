package com.msrap.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "regime_states")
@IdClass(RegimeStateId.class)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class RegimeState {

    @Id
    @Column(nullable = false, length = 32)
    private String symbol;

    @Id
    @Column(nullable = false)
    private Instant ts;

    @Column(nullable = false)
    private Short state;

    @Column(name = "state_label", length = 32)
    private String stateLabel;

    @Column(name = "prob_state0", precision = 8, scale = 6)
    private BigDecimal probState0;

    @Column(name = "prob_state1", precision = 8, scale = 6)
    private BigDecimal probState1;

    @Column(name = "prob_state2", precision = 8, scale = 6)
    private BigDecimal probState2;
}
