package dev.asl.api.run;

import org.springframework.data.jpa.repository.JpaRepository;

interface LlmCallRepository extends JpaRepository<LlmCall, Long> {
}
