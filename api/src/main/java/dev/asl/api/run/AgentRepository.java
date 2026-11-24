package dev.asl.api.run;

import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

interface AgentRepository extends JpaRepository<Agent, AgentId> {

	List<Agent> findByRunId(UUID runId);
}
