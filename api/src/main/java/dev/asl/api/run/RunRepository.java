package dev.asl.api.run;

import java.util.UUID;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

interface RunRepository extends JpaRepository<Run, UUID> {

	@Query("""
			select r from Run r
			where (cast(:scenario as string) is null or r.scenario = :scenario)
			  and (cast(:model as string) is null or r.model = :model)
			  and (cast(:condition as string) is null or r.condition = :condition)
			""")
	Page<Run> search(@Param("scenario") String scenario, @Param("model") String model,
			@Param("condition") String condition, Pageable pageable);
}
