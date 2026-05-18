package com.msrap.model;

import lombok.*;
import java.io.Serializable;
import java.time.Instant;

@Getter @Setter @NoArgsConstructor @AllArgsConstructor @EqualsAndHashCode
public class RegimeStateId implements Serializable {
    private String symbol;
    private Instant ts;
}
