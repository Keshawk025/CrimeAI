"use client";

import React, { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronLeft,
  Search,
  Filter,
  Info,
  Calendar,
  Layers,
  Sparkles,
  ShieldCheck,
  FolderOpen
} from "lucide-react";

// Color mapping matching Task 13 requirements
const typeColors: Record<string, string> = {
  fir: "#6366f1",         // Indigo
  suspect: "#ef4444",     // Red
  victim: "#10b981",      // Emerald
  witness: "#f59e0b",     // Amber
  phone: "#06b6d4",       // Cyan
  vehicle: "#f43f5e",     // Rose
  location: "#3b82f6",    // Blue
  organization: "#a855f7",// Purple
  weapon: "#e11d48",      // Rose-Red
  evidence: "#ec4899",    // Pink
};

const typeLabels: Record<string, string> = {
  fir: "FIR Document",
  suspect: "Suspect",
  victim: "Victim",
  witness: "Witness",
  phone: "Phone / Contact",
  vehicle: "Vehicle",
  location: "Location",
  organization: "Organization",
  weapon: "Weapon",
  evidence: "Evidence",
};

interface GraphNode {
  id: string;
  label: string;
  type: string;
  metadata?: any;
  relatedFirs?: string[];
}

export default function RelationshipGraphPage() {
  const params = useParams();
  const router = useRouter();
  const firId = params?.id as string;

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  
  // Interaction states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<string[]>([
    "fir", "suspect", "victim", "witness", "phone", "vehicle", "location", "organization", "weapon", "evidence"
  ]);

  // Fetch graph details
  useEffect(() => {
    if (!firId) return;

    const fetchGraph = async () => {
      setLoading(true);
      try {
        const res = await fetch(`http://localhost:8000/api/v1/firs/${firId}/graph`);
        if (!res.ok) {
          throw new Error("Failed to load relationship graph data.");
        }
        const data = await res.json();
        setGraphData(data);
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Failed to load graph.");
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [firId]);

  // Load and initialize Cytoscape.js dynamically on client-side
  useEffect(() => {
    if (loading || error || graphData.nodes.length === 0 || !containerRef.current) return;

    let isMounted = true;

    import("cytoscape").then((cytoscapeModule) => {
      if (!isMounted) return;
      const cytoscape = cytoscapeModule.default;

      // Map backend nodes & edges to Cytoscape format
      const cyElements = [
        ...graphData.nodes.map((n) => ({
          data: {
            id: n.id,
            label: n.label,
            type: n.type,
            metadata: n.metadata,
          },
        })),
        ...graphData.edges.map((e, idx) => ({
          data: {
            id: `edge_${idx}`,
            source: e.source,
            target: e.target,
            label: e.label,
          },
        })),
      ];

      // Init cytoscape
      const cy = cytoscape({
        container: containerRef.current,
        elements: cyElements,
        boxSelectionEnabled: false,
        style: [
          {
            selector: "node",
            style: {
              "label": "data(label)",
              "color": "#f4f4f5",
              "font-size": "10px",
              "text-valign": "center",
              "text-halign": "center",
              "background-color": (ele: any) => typeColors[ele.data("type")] || "#a1a1aa",
              "width": (ele: any) => (ele.data("type") === "fir" ? "50px" : "34px"),
              "height": (ele: any) => (ele.data("type") === "fir" ? "50px" : "34px"),
              "border-width": "2.5px",
              "border-color": "#ffffff12",
              "text-wrap": "wrap",
              "text-max-width": "75px",
              "overlay-opacity": 0,
              "text-outline-color": "#09090b",
              "text-outline-width": "2px",
            },
          },
          {
            selector: "edge",
            style: {
              "label": "data(label)",
              "color": "#a1a1aa",
              "font-size": "8px",
              "width": "1.5px",
              "line-color": "#ffffff15",
              "target-arrow-color": "#ffffff15",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "text-outline-color": "#09090b",
              "text-outline-width": "1.5px",
              "arrow-scale": 0.8,
            },
          },
          {
            selector: "node:selected",
            style: {
              "border-color": "#10b981",
              "border-width": "3px",
              "background-color": "#059669",
            },
          },
          {
            selector: ".dimmed",
            style: {
              "opacity": 0.15,
              "line-color": "#ffffff05",
              "target-arrow-color": "#ffffff05",
            },
          },
        ],
        layout: {
          name: "cose",
          nodeOverlap: 20,
          nestingFactor: 1.2,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
          animate: false,
        },
      });

      cyRef.current = cy;

      // Event listener: click node
      cy.on("tap", "node", (evt: any) => {
        const node = evt.target;
        setSelectedNode({
          id: node.data("id"),
          label: node.data("label"),
          type: node.data("type"),
          metadata: node.data("metadata") || {},
          relatedFirs: node.data("metadata")?.related_firs || [],
        });

        // Highlight connected neighborhood
        const neighborhood = node.neighborhood();
        cy.elements().addClass("dimmed");
        node.removeClass("dimmed");
        neighborhood.removeClass("dimmed");
      });

      // Event listener: click backdrop -> reset highlight
      cy.on("tap", (evt: any) => {
        if (evt.target === cy) {
          cy.elements().removeClass("dimmed");
          setSelectedNode(null);
        }
      });

      // Fit view initial
      cy.fit();
    });

    return () => {
      isMounted = false;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [loading, error, graphData]);

  // Handle filter changes
  useEffect(() => {
    if (!cyRef.current) return;

    cyRef.current.batch(() => {
      cyRef.current.nodes().forEach((node: any) => {
        const type = node.data("type");
        if (activeFilters.includes(type)) {
          node.style("display", "element");
        } else {
          node.style("display", "none");
        }
      });
    });
  }, [activeFilters]);

  // Zoom operations
  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
  const handleZoomFit = () => {
    cyRef.current?.fit();
    cyRef.current?.elements().removeClass("dimmed");
    setSelectedNode(null);
  };

  // Node Search function
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !cyRef.current) return;

    const matched = cyRef.current.nodes().filter((ele: any) =>
      ele.data("label").toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (matched.length > 0) {
      cyRef.current.animate({
        center: { eles: matched.first() },
        zoom: 1.5,
      });
      matched.first().select();
      matched.first().trigger("tap");
    }
  };

  // Toggle categories helper
  const toggleFilter = (type: string) => {
    setActiveFilters((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  return (
    <div className="min-h-screen bg-[#070709] bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.08),rgba(255,255,255,0))] text-zinc-100 flex flex-col font-sans antialiased overflow-hidden">
      {/* Header Bar */}
      <header className="h-16 px-6 border-b border-white/[0.06] bg-zinc-950/60 backdrop-blur-xl flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/investigations/upload")}
            className="p-2 rounded-xl bg-white/5 border border-white/[0.08] hover:bg-white/10 hover:border-white/[0.15] text-zinc-300 transition-all flex items-center justify-center"
          >
            <ChevronLeft size={16} />
          </button>
          <div className="h-5 w-px bg-white/[0.08]" />
          <div>
            <h1 className="text-sm font-extrabold tracking-tight text-zinc-100 flex items-center gap-2">
              <Sparkles size={14} className="text-indigo-400" />
              Criminal Relationship Graph
            </h1>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Visualizing linked suspects, vehicles, phone networks, and crime scenes
            </p>
          </div>
        </div>

        {/* Search bar */}
        <form onSubmit={handleSearchSubmit} className="relative w-64 max-w-sm">
          <input
            type="text"
            placeholder="Search suspect name, vehicle..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-9 pr-4 py-1.5 text-xs text-zinc-100 placeholder-muted-foreground/60 focus:outline-none focus:border-indigo-500/50 transition-all"
          />
          <Search size={13} className="absolute left-3.5 top-2.5 text-muted-foreground/60" />
        </form>
      </header>

      {/* Main content grid */}
      <div className="flex-1 flex min-h-0 relative">
        {/* Graph Canvas Container */}
        <div className="flex-1 min-w-0 h-full relative bg-[#09090b]">
          {/* Cyber grid overlays */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808006_1px,transparent_1px),linear-gradient(to_bottom,#80808006_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
          
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#09090b]/80 z-20">
              <div className="text-center space-y-3">
                <span className="inline-block w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                <p className="text-xs text-muted-foreground">Orchestrating network linkages from PostgreSQL...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#09090b]/80 z-20 p-6">
              <div className="card-glass border border-red-500/20 bg-red-950/20 rounded-2xl p-6 max-w-md text-center space-y-3">
                <p className="text-xs text-red-400 font-medium">Linkage Generation Failed</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{error}</p>
                <button
                  onClick={() => window.location.reload()}
                  className="bg-white/10 hover:bg-white/20 text-xs px-3.5 py-1.5 rounded-lg border border-white/10"
                >
                  Retry Linkage
                </button>
              </div>
            </div>
          )}

          {/* Cytoscape target div */}
          <div ref={containerRef} className="w-full h-full" />

          {/* Floating Canvas Controls Overlay */}
          <div className="absolute bottom-6 left-6 z-10 flex items-center gap-1.5 bg-zinc-950/80 border border-white/[0.08] backdrop-blur-md rounded-xl p-1.5 shadow-2xl">
            <button
              onClick={handleZoomIn}
              className="p-2 text-zinc-300 hover:text-white rounded-lg hover:bg-white/5 transition-all"
              title="Zoom In"
            >
              <ZoomIn size={14} />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 text-zinc-300 hover:text-white rounded-lg hover:bg-white/5 transition-all"
              title="Zoom Out"
            >
              <ZoomOut size={14} />
            </button>
            <button
              onClick={handleZoomFit}
              className="p-2 text-zinc-300 hover:text-white rounded-lg hover:bg-white/5 transition-all"
              title="Reset View"
            >
              <Maximize2 size={14} />
            </button>
          </div>
        </div>

        {/* Sidebar Panel: Left Sidebar for Filters, Right Sidebar for Node Details */}
        {/* Left Filters Panel */}
        <div className="w-64 border-r border-white/[0.06] bg-zinc-950/40 backdrop-blur-xl flex flex-col shrink-0 min-h-0">
          <div className="p-4 border-b border-white/[0.06] flex items-center gap-2">
            <Filter size={13} className="text-indigo-400" />
            <h4 className="text-xs font-bold text-zinc-200">Category Filters</h4>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {Object.keys(typeColors).map((type) => {
              const active = activeFilters.includes(type);
              return (
                <button
                  key={type}
                  onClick={() => toggleFilter(type)}
                  className={`w-full flex items-center justify-between p-2 rounded-xl text-left border transition-all ${
                    active
                      ? "bg-white/[0.02] border-white/[0.08] hover:bg-white/[0.04]"
                      : "opacity-40 border-transparent hover:opacity-60"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full shrink-0 border border-white/10"
                      style={{ backgroundColor: typeColors[type] }}
                    />
                    <span className="text-xs font-medium text-zinc-300">{typeLabels[type]}</span>
                  </div>
                  {active && (
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Node Details Sidebar */}
        <div className="w-80 border-l border-white/[0.06] bg-zinc-950/45 backdrop-blur-2xl flex flex-col shrink-0 min-h-0">
          <div className="p-4 border-b border-white/[0.06] flex items-center gap-2">
            <Info size={13} className="text-indigo-400" />
            <h4 className="text-xs font-bold text-zinc-200">Relationship Details</h4>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {selectedNode ? (
              <div className="space-y-6">
                {/* Node Title Header */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block px-2 py-0.5 rounded text-[9px] font-bold border"
                      style={{
                        color: typeColors[selectedNode.type],
                        borderColor: `${typeColors[selectedNode.type]}20`,
                        backgroundColor: `${typeColors[selectedNode.type]}08`,
                      }}
                    >
                      {typeLabels[selectedNode.type] || selectedNode.type}
                    </span>
                  </div>
                  <h3 className="text-sm font-extrabold text-zinc-100 select-text leading-snug">
                    {selectedNode.label}
                  </h3>
                </div>

                {/* Metadata Properties */}
                {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
                      <Layers size={11} />
                      Attributes
                    </h5>
                    <div className="space-y-2 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                      {Object.entries(selectedNode.metadata).map(([key, val]) => {
                        if (key === "related_firs") return null;
                        return (
                          <div key={key} className="flex justify-between items-start text-[11px] font-mono leading-relaxed">
                            <span className="text-zinc-500 uppercase text-[9px] mt-0.5">{key.replace("_", " ")}:</span>
                            <span className="text-zinc-300 text-right max-w-[70%] truncate select-text">
                              {typeof val === "object" ? JSON.stringify(val) : String(val)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Connected / Associated Cases */}
                {selectedNode.relatedFirs && selectedNode.relatedFirs.length > 0 && (
                  <div className="space-y-3">
                    <h5 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1.5">
                      <FolderOpen size={11} />
                      Related Cases
                    </h5>
                    <div className="flex flex-col gap-1.5">
                      {selectedNode.relatedFirs.map((caseNo) => (
                        <div
                          key={caseNo}
                          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.01] border border-white/[0.04] text-xs font-medium text-zinc-300"
                        >
                          <Calendar size={12} className="text-zinc-500 shrink-0" />
                          <span>{caseNo}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-4">
                <div className="p-3.5 rounded-full bg-white/[0.02] border border-white/[0.06] text-muted-foreground/60 mb-3.5">
                  <ShieldCheck size={20} />
                </div>
                <p className="text-xs text-zinc-300 font-semibold">No node selected</p>
                <p className="text-[10px] text-muted-foreground mt-1 max-w-[200px] leading-relaxed">
                  Click any node in the graph map to load attributes, connections, and metadata.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
