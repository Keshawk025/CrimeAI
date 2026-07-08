"""
app/services/explainability_service.py
──────────────────────────────────────
Service to construct evidence chains and explain AI-generated results in CrimeMind AI.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fir import FIR
from app.models.fir_entity import FIREntity
from app.models.fir_document_content import FIRDocumentContent

logger = logging.getLogger(__name__)


class ExplainabilityService:
    """
    Builds structured evidence chains, collects confidence metrics,
    reasoning steps, and limitation details for all AI modules.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def explain_similar_cases(self, fir_id: uuid.UUID, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explains Qdrant vector similarity retrieval.
        """
        matches = raw_results.get("matches", [])
        
        # Build supporting cases
        supporting_cases = [m["case_number"] for m in matches]
        
        # Collect supporting entities (extract from reasons strings)
        supporting_entities = []
        for m in matches:
            for reason in m.get("reasons", []):
                # Clean up reasons to find entities
                if "(" in reason and ")" in reason:
                    parts = reason.split("(")
                    if len(parts) > 1:
                        entity_part = parts[1].replace(")", "").strip()
                        for ent in entity_part.split(","):
                            val = ent.strip()
                            if val and val not in supporting_entities:
                                supporting_entities.append(val)

        # Compute average similarity score as confidence
        if matches:
            confidence = int(sum(m["similarity"] for m in matches) / len(matches))
            reasoning = f"Found {len(matches)} historical cases matching the semantic context of this FIR. " \
                        f"Top matching features include shared crime categories, weapons, or suspect profiles."
            limitations = [
                "Relies on the presence of semantic overlap in the text descriptions.",
                "Qdrant retrieval does not verify legal connection or physical evidence link."
            ]
        else:
            confidence = 50
            reasoning = "Limited supporting evidence available. No highly similar cases found in the repository."
            limitations = ["Vector database does not contain matches for the unique patterns of this case."]

        return {
            "result": raw_results,
            "confidence": confidence,
            "reasoning": reasoning,
            "supporting_cases": supporting_cases,
            "supporting_entities": supporting_entities,
            "limitations": limitations,
            # Backward compatibility fields:
            "query_fir": raw_results.get("query_fir"),
            "matches": matches,
        }

    async def explain_entity_extraction(self, fir_id: uuid.UUID, raw_entities: List[Any]) -> Dict[str, Any]:
        """
        Explains named entity extraction.
        """
        # Fetch original text length to assess confidence limits
        content_stmt = select(FIRDocumentContent).where(FIRDocumentContent.fir_id == fir_id)
        content_res = await self.db.execute(content_stmt)
        doc_content = content_res.scalar_one_or_none()
        fir_text = doc_content.extracted_text if doc_content else ""

        supporting_entities = []
        confidences = []
        
        for e in raw_entities:
            val = e.entity_value if hasattr(e, "entity_value") else e.get("entity_value", "")
            conf = e.confidence if hasattr(e, "confidence") else e.get("confidence", 0.0)
            if val:
                supporting_entities.append(f"{e.entity_type if hasattr(e, 'entity_type') else e.get('entity_type', '')}: {val}")
                confidences.append(int(conf * 100))

        confidence = int(sum(confidences) / len(confidences)) if confidences else 100
        
        if not fir_text.strip():
            confidence = 0
            reasoning = "Limited supporting evidence available."
            limitations = ["No text content is present in the document."]
        elif not raw_entities:
            reasoning = "Limited supporting evidence available. No prominent entities were identified in the text."
            limitations = ["The report text may be unstructured, empty, or contain zero standard entity keywords."]
        else:
            reasoning = f"Extracted {len(raw_entities)} structural entity nodes from the FIR plain text content. " \
                        f"Parsed entity types include suspects, victims, phone numbers, vehicles, and weapons."
            limitations = [
                "Named entity extraction is probabilistic and depends on grammar context.",
                "OCR misspellings or regional slang could lead to missed or misclassified entities."
            ]

        # Convert raw_entities to dict list for serialization
        serialized = []
        for e in raw_entities:
            if hasattr(e, "entity_type"):
                serialized.append({
                    "id": str(e.id),
                    "fir_id": str(e.fir_id),
                    "entity_type": e.entity_type,
                    "entity_value": e.entity_value,
                    "confidence": e.confidence,
                    "metadata_": e.metadata_,
                })
            else:
                serialized.append(e)

        return {
            "result": serialized,
            "confidence": confidence,
            "reasoning": reasoning,
            "supporting_cases": [],
            "supporting_entities": supporting_entities,
            "limitations": limitations,
        }

    async def explain_copilot(self, fir_id: uuid.UUID, raw_copilot_res: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explains AI copilot answers.
        """
        answer = raw_copilot_res.get("answer", "")
        sources = raw_copilot_res.get("sources", [])
        confidence = raw_copilot_res.get("confidence", 80)
        
        # Build supporting entities based on what exists in the database
        entities_stmt = select(FIREntity).where(FIREntity.fir_id == fir_id)
        entities_res = await self.db.execute(entities_stmt)
        entities = entities_res.scalars().all()
        
        supporting_entities = []
        supporting_cases = []
        
        # Analyze answer text to locate references to entities
        for ent in entities:
            if ent.entity_value.lower() in answer.lower():
                supporting_entities.append(f"{ent.entity_type}: {ent.entity_value}")
                
        # Analyze sources list for similar cases
        for s in sources:
            if s.startswith("CASE-") or s.startswith("FIR-"):
                supporting_cases.append(s)

        if answer == "I don't have enough evidence.":
            confidence = 30
            reasoning = "Limited supporting evidence available. The provided FIR text and indexed entities do not contain enough facts to answer this query."
            limitations = ["The request requires context or details that are not described in the uploaded FIR document."]
        else:
            reasoning = f"Answer compiled by synthesizing facts from: {', '.join(sources)}. " \
                        f"Facts matched directly with the case report file content and extracted entity markers."
            limitations = [
                "Synthesized using generative models; details should be cross-verified with the raw document.",
                "Does not pull data from live investigation files unless explicitly provided in the context."
            ]

        return {
            "result": answer,
            "confidence": confidence,
            "reasoning": reasoning,
            "supporting_cases": supporting_cases,
            "supporting_entities": supporting_entities,
            "limitations": limitations,
            # Backward compatibility fields:
            "answer": answer,
            "sources": sources,
            "workflow_steps": raw_copilot_res.get("workflow_steps", []),
        }

    async def explain_recommendations(self, fir_id: uuid.UUID, raw_rec_res: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explains investigation next steps.
        """
        recommendations = raw_rec_res.get("recommendations", [])
        message = raw_rec_res.get("message", "")
        
        supporting_entities = []
        supporting_cases = []
        
        # Fetch entities and similar cases to link as evidence
        entities_stmt = select(FIREntity).where(FIREntity.fir_id == fir_id)
        entities_res = await self.db.execute(entities_stmt)
        entities = entities_res.scalars().all()
        
        # Collect entities mentioned in recommendation reasons/titles
        for rec in recommendations:
            title = rec.get("title", "").lower()
            reason = rec.get("reason", "").lower()
            for ent in entities:
                val = ent.entity_value.lower()
                if val in title or val in reason:
                    desc = f"{ent.entity_type}: {ent.entity_value}"
                    if desc not in supporting_entities:
                        supporting_entities.append(desc)

        # Compute average confidence score
        if recommendations:
            confidences = [r.get("confidence", 80) for r in recommendations]
            confidence = int(sum(confidences) / len(confidences))
            reasoning = f"Generated {len(recommendations)} priority-scored actions based on crime category rules and active entity patterns. " \
                        f"Suggested actions link directly to physical evidence, suspect identities, or phone numbers."
            limitations = [
                "These steps are advisory patterns. Local warrant permissions and investigation protocols take precedence.",
                "Fails to consider external intelligence not stored in CrimeMind AI."
            ]
        else:
            confidence = 30
            reasoning = message or "Limited supporting evidence available."
            limitations = ["The uploaded case file is too short or lacks entities to form concrete investigation hypotheses."]

        return {
            "result": recommendations,
            "confidence": confidence,
            "reasoning": reasoning,
            "supporting_cases": supporting_cases,
            "supporting_entities": supporting_entities,
            "limitations": limitations,
            # Backward compatibility fields:
            "recommendations": recommendations,
            "message": message,
        }
