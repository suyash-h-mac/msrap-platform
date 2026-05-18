package com.msrap;

import com.msrap.config.IngestionProperties;
import com.msrap.controller.GlobalExceptionHandler;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.SpringBootTest.WebEnvironment;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Smoke-test suite for the MSRAP Spring Boot application.
 *
 * <p>Uses {@code WebEnvironment.NONE} so the full HTTP server is not started —
 * these tests only verify that the application context loads and key beans are
 * wired up correctly. They run quickly in CI without needing a live database
 * (Spring Boot test autoconfiguration provides an in-memory H2 datasource when
 * the {@code test} profile is active and H2 is on the classpath).</p>
 *
 * <p>For a real integration test that exercises DB logic, see the {@code it/}
 * package (to be added when a Testcontainers PostgreSQL fixture is available).</p>
 */
@SpringBootTest(webEnvironment = WebEnvironment.NONE)
@ActiveProfiles("test")
@TestPropertySource(properties = {
        // Provide minimal ingestion config so IngestionProperties binds cleanly
        "msrap.ingestion.symbols=RELIANCE.NS,TCS.NS",
        "msrap.ingestion.history-days=365",
        // Point analytics python path at a safe no-op location for tests
        "msrap.analytics.python-path=/tmp",
        // Use a simple in-memory datasource — override in application-test.yml for full IT
        "spring.datasource.url=jdbc:h2:mem:msrap_test;DB_CLOSE_DELAY=-1;MODE=PostgreSQL",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa",
        "spring.datasource.password=",
        "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
        "spring.jpa.hibernate.ddl-auto=create-drop",
})
class MsrapApplicationTests {

    @Autowired
    private ApplicationContext context;

    @Autowired
    private IngestionProperties ingestionProperties;

    // ── Context loads ─────────────────────────────────────────────────────────

    @Test
    void contextLoads() {
        assertThat(context).isNotNull();
    }

    // ── IngestionProperties binding ────────────────────────────────────────────

    @Test
    void ingestionPropertiesBindsSymbolList() {
        assertThat(ingestionProperties.getSymbols())
                .isNotEmpty()
                .contains("RELIANCE.NS", "TCS.NS");
    }

    @Test
    void ingestionPropertiesHistoryDays() {
        assertThat(ingestionProperties.getHistoryDays()).isEqualTo(365);
    }

    // ── Key beans present ─────────────────────────────────────────────────────

    @Test
    void globalExceptionHandlerBeanPresent() {
        assertThat(context.getBean(GlobalExceptionHandler.class)).isNotNull();
    }

    @Test
    void ingestionPropertiesBeanPresent() {
        assertThat(context.getBean(IngestionProperties.class)).isNotNull();
    }
}
