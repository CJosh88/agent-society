package dev.asl.api.run;

import java.util.List;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

interface EventRepository extends JpaRepository<Event, Long> {

	List<Event> findByRunIdOrderBySeq(UUID runId);
}
