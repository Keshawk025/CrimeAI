"""
app/services/similar_case_service.py
──────────────────────────────────────
Service for retrieving similar cases from Qdrant and generating comparative similarity reasons.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dateutil import parser as date_parser

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fir import FIR, FIRStatus
from app.models.fir_embedding import FIREmbedding
from app.models.fir_entity import FIREntity
from app.services.qdrant_index_service import QdrantIndexService, COLLECTION_NAME
from qdrant_client.http import models as qdrant_models
from app.core.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)


class SimilarCaseService:
    """
    Handles similarity queries, PostgreSQL metadata merging, and similarity explanation generation.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.qdrant_service = QdrantIndexService()

    async def get_similar_cases(
        self, fir_id: uuid.UUID, limit: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieves the top-K similar cases for a given FIR ID, matches metadata from PostgreSQL,
        and computes similarity reasons.
        """
        # 1. Fetch query FIR from DB
        fir_stmt = select(FIR).where(FIR.id == fir_id)
        fir_res = await self.db.execute(fir_stmt)
        query_fir = fir_res.scalar_one_or_none()
        if not query_fir:
            raise ValueError(f"FIR with ID {fir_id} not found.")

        # 2. Verify that embedding exists
        emb_stmt = select(FIREmbedding).where(FIREmbedding.fir_id == fir_id)
        emb_res = await self.db.execute(emb_stmt)
        query_emb = emb_res.scalar_one_or_none()
        if not query_emb:
            raise ValueError(f"FIR with ID {fir_id} has not been indexed yet. Please index it first.")

        # 3. Retrieve vector from Qdrant
        try:
            points = await self.qdrant_service.client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[str(fir_id)],
                with_vectors=True,
            )
        except Exception as exc:
            logger.error("Failed to connect to Qdrant for retrieving query vector: %s", exc)
            raise ServiceUnavailableException(f"Qdrant service is currently unavailable: {exc}")

        if not points:
            raise ValueError(f"Vector for FIR {fir_id} not found in Qdrant index.")

        query_vector = points[0].vector
        if not query_vector:
            raise ValueError(f"Vector data is missing for FIR {fir_id} in Qdrant index.")

        # 4. Search Qdrant for similar vectors (excluding query vector ID)
        try:
            response = await self.qdrant_service.client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=qdrant_models.Filter(
                    must_not=[
                        qdrant_models.HasIdCondition(has_id=[str(fir_id)])
                    ]
                ),
                limit=limit,
                with_payload=True,
            )
            search_results = response.points
        except Exception as exc:
            logger.error("Failed to query Qdrant for similar vectors: %s", exc)
            raise ServiceUnavailableException(f"Qdrant service is currently unavailable: {exc}")

        # 5. Fetch query FIR's entities for comparison
        query_entities_stmt = select(FIREntity).where(FIREntity.fir_id == fir_id)
        query_entities_res = await self.db.execute(query_entities_stmt)
        query_entities = query_entities_res.scalars().all()

        # Group query entities by type
        query_grouped = self._group_entities(query_entities)

        matches = []
        for result in search_results:
            cand_fir_id = uuid.UUID(result.id)
            score = result.score

            # Fetch candidate FIR metadata from PostgreSQL
            cand_stmt = select(FIR).where(FIR.id == cand_fir_id)
            cand_res = await self.db.execute(cand_stmt)
            cand_fir = cand_res.scalar_one_or_none()

            # Skip candidate if it is deleted or not found in PostgreSQL
            if not cand_fir:
                continue

            # Fetch candidate entities
            cand_entities_stmt = select(FIREntity).where(FIREntity.fir_id == cand_fir_id)
            cand_entities_res = await self.db.execute(cand_entities_stmt)
            cand_entities = cand_entities_res.scalars().all()
            cand_grouped = self._group_entities(cand_entities)

            # Calculate similarity percentage
            similarity_pct = max(0, min(100, round(score * 100)))

            # Generate explanations/reasons
            reasons = self._generate_reasons(query_grouped, cand_grouped)

            matches.append({
                "fir_id": str(cand_fir_id),
                "case_number": cand_fir.case_number,
                "crime_type": cand_grouped.get("crime_category", ["Unknown"])[0],
                "status": cand_fir.status,
                "similarity": similarity_pct,
                "reasons": reasons,
            })

        return {
            "query_fir": query_fir.case_number,
            "matches": matches,
        }

    def _group_entities(self, entities: List[FIREntity]) -> Dict[str, List[str]]:
        """Groups list of FIREntity objects by entity_type."""
        grouped = {}
        for ent in entities:
            t = ent.entity_type
            val = ent.entity_value.strip()
            if not val:
                continue
            if t not in grouped:
                grouped[t] = []
            if val not in grouped[t]:
                grouped[t].append(val)
        return grouped

    def _generate_reasons(
        self, query: Dict[str, List[str]], cand: Dict[str, List[str]]
    ) -> List[str]:
        """Compares two sets of grouped entities and returns similarity reasons."""
        reasons = []

        # 1. Crime Category
        q_cats = query.get("crime_category", [])
        c_cats = cand.get("crime_category", [])
        shared_cats = set(q_cats).intersection(set(c_cats))
        if shared_cats:
            reasons.append(f"Same crime category (both involve {', '.join(shared_cats)})")

        # 2. Weapons
        q_weapons = query.get("weapon", [])
        c_weapons = cand.get("weapon", [])
        shared_weapons = set(q_weapons).intersection(set(c_weapons))
        if shared_weapons:
            reasons.append(f"Same weapon type used ({', '.join(shared_weapons)})")

        # 3. Vehicles
        q_vehicles = query.get("vehicle", [])
        c_vehicles = cand.get("vehicle", [])
        shared_vehicles = set(q_vehicles).intersection(set(c_vehicles))
        if shared_vehicles:
            reasons.append(f"Same vehicle type/number identified ({', '.join(shared_vehicles)})")

        # 4. Locations & Addresses
        q_locs = query.get("location", []) + query.get("address", [])
        c_locs = cand.get("location", []) + cand.get("address", [])
        shared_locs = set(q_locs).intersection(set(c_locs))
        if shared_locs:
            reasons.append(f"Nearby location / same place ({', '.join(shared_locs)})")

        # 5. Suspects
        q_sus = query.get("suspect", [])
        c_sus = cand.get("suspect", [])
        shared_sus = set(q_sus).intersection(set(c_sus))
        if shared_sus:
            reasons.append(f"Involves same suspect ({', '.join(shared_sus)})")

        # 6. Victims
        q_vic = query.get("victim", [])
        c_vic = cand.get("victim", [])
        shared_vic = set(q_vic).intersection(set(c_vic))
        if shared_vic:
            reasons.append(f"Involves same victim ({', '.join(shared_vic)})")

        # 7. Evidence
        q_ev = query.get("evidence", [])
        c_ev = cand.get("evidence", [])
        shared_ev = set(q_ev).intersection(set(c_ev))
        if shared_ev:
            reasons.append(f"Similar evidence overlap ({', '.join(shared_ev)})")

        # 8. Dates / Timeline
        q_dates = query.get("date", [])
        c_dates = cand.get("date", [])
        parsed_q = []
        parsed_c = []
        for d in q_dates:
            try:
                parsed_q.append(date_parser.parse(d))
            except Exception:
                pass
        for d in c_dates:
            try:
                parsed_c.append(date_parser.parse(d))
            except Exception:
                pass
        
        timeline_match = False
        for q_dt in parsed_q:
            for c_dt in parsed_c:
                days_diff = abs((q_dt - c_dt).days)
                if days_diff <= 30:
                    timeline_match = True
                    break
            if timeline_match:
                break
        
        if timeline_match:
            reasons.append("Similar timeline (dates are within 30 days)")

        # 9. Fallback if no matching entity features found
        if not reasons:
            reasons.append("High semantic similarity in crime description")
            reasons.append("Similar modus operandi and case pattern")

        return reasons
