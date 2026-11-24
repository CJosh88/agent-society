package dev.asl.api.run;

import java.util.Map;
import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "events")
class Event {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	Long id;
	UUID runId;
	int seq;
	int tick;
	String type;
	String agentId;
	@JdbcTypeCode(SqlTypes.JSON)
	Map<String, Object> payload;
}
