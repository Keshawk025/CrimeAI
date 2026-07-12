"use client";

import { useMemo, useRef, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

interface KnowledgeGraphProps {
  entities: any[];
  caseNumber: string;
}

export default function KnowledgeGraph({ entities, caseNumber }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  useEffect(() => {
    if (containerRef.current) {
      setDimensions({
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
      });
    }
    const handleResize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const graphData = useMemo(() => {
    const nodes: any[] = [];
    const links: any[] = [];

    // Central Node (FIR)
    nodes.push({
      id: "FIR",
      name: caseNumber || "FIR Case",
      group: "FIR",
      val: 25,
      color: "#ef4444", // Red for FIR
    });

    const categories = new Set<string>();

    entities.forEach((ent, idx) => {
      if (!ent.entity_value || !ent.entity_type) return;

      const typeId = `category_${ent.entity_type}`;
      if (!categories.has(ent.entity_type)) {
        categories.add(ent.entity_type);
        nodes.push({
          id: typeId,
          name: ent.entity_type,
          group: "Category",
          val: 15,
          color: "#8b5cf6", // Purple for category
        });
        links.push({
          source: "FIR",
          target: typeId,
          value: 2,
        });
      }

      const nodeId = `entity_${idx}_${ent.entity_value}`;
      nodes.push({
        id: nodeId,
        name: ent.entity_value,
        group: ent.entity_type,
        val: 10,
        color: "#10b981", // Emerald for entity
      });

      links.push({
        source: typeId,
        target: nodeId,
        value: 1,
      });
    });

    return { nodes, links };
  }, [entities, caseNumber]);

  return (
    <div ref={containerRef} className="w-full h-[500px] rounded-xl overflow-hidden border border-white/[0.08] bg-black/40">
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeLabel="name"
        nodeColor={(node: any) => node.color}
        nodeRelSize={1}
        linkColor={() => "rgba(255,255,255,0.2)"}
        linkWidth={1.5}
        backgroundColor="transparent"
        d3VelocityDecay={0.3}
        onNodeDragEnd={(node: any) => {
          node.fx = node.x;
          node.fy = node.y;
        }}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.name;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.2); // some padding

          ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
          ctx.beginPath();
          ctx.roundRect(
            node.x - bckgDimensions[0] / 2,
            node.y - bckgDimensions[1] / 2,
            bckgDimensions[0],
            bckgDimensions[1],
            4 / globalScale // border radius
          );
          ctx.fill();

          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = node.color;
          ctx.fillText(label, node.x, node.y);

          node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
        }}
        nodePointerAreaPaint={(node: any, color: string, ctx) => {
          ctx.fillStyle = color;
          const bckgDimensions = node.__bckgDimensions;
          bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1]);
        }}
      />
    </div>
  );
}
